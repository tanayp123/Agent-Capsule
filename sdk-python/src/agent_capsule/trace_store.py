import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from cryptography.fernet import Fernet, InvalidToken

from .hashing import canonical_json, content_hash


class TraceStoreError(Exception):
    pass


class TracePayloadCorruptionError(TraceStoreError):
    pass


@dataclass
class PayloadRecord:
    payload_id: str
    trace_id: str
    run_id: str
    span_id: str
    kind: str
    content_hash: str
    path: str


class EncryptedTraceStore:
    def __init__(self, root: Path, key_path: Optional[Path] = None) -> None:
        self.root = Path(root)
        self.metadata_dir = self.root / "metadata"
        self.payload_dir = self.root / "payloads"
        self.index_dir = self.root / "payload-index"
        self.key_path = key_path or (self.root / "keys" / "local.key")
        self._fernet = Fernet(self._load_or_create_key())

    def ensure_layout(self) -> None:
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.payload_dir.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)

    def write_trace(self, trace: Dict[str, Any], payloads: Iterable[Dict[str, Any]]) -> Path:
        self.ensure_layout()
        trace_id = trace["trace_id"]
        run_id = trace["run_id"]
        records = []

        try:
            for payload in payloads:
                records.append(self.write_payload(trace_id=trace_id, run_id=run_id, **payload))

            metadata_path = self.metadata_path(trace_id)
            metadata_path.write_text(
                json.dumps(trace, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            index_path = self.index_path(trace_id)
            index_path.write_text(
                json.dumps([record.__dict__ for record in records], indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return metadata_path
        except Exception as exc:
            self._cleanup_partial_trace(trace_id)
            raise TraceStoreError("trace store write failed") from exc

    def write_payload(
        self,
        trace_id: str,
        run_id: str,
        span_id: str,
        kind: str,
        payload: Any,
    ) -> PayloadRecord:
        self.ensure_layout()
        payload_id = "%s-%s" % (span_id, kind)
        payload_hash = content_hash(payload)
        payload_path = self.payload_path(trace_id, payload_id)
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        plaintext = canonical_json(
            {
                "payload_schema_version": 1,
                "trace_id": trace_id,
                "run_id": run_id,
                "span_id": span_id,
                "kind": kind,
                "content_hash": payload_hash,
                "payload": payload,
            }
        ).encode("utf-8")
        payload_path.write_bytes(self._fernet.encrypt(plaintext))
        return PayloadRecord(
            payload_id=payload_id,
            trace_id=trace_id,
            run_id=run_id,
            span_id=span_id,
            kind=kind,
            content_hash=payload_hash,
            path=str(payload_path.relative_to(self.root)),
        )

    def read_trace(self, trace_id: str) -> Dict[str, Any]:
        path = self.metadata_path(trace_id)
        if not path.exists():
            raise FileNotFoundError(trace_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def find_trace_by_run_id(self, run_id: str) -> Optional[Dict[str, Any]]:
        for summary in self.list_traces():
            if summary["run_id"] == run_id:
                return self.read_trace(summary["trace_id"])
        return None

    def list_traces(self) -> List[Dict[str, Any]]:
        self.ensure_layout()
        summaries = []
        for path in sorted(self.metadata_dir.glob("*.json")):
            try:
                trace = json.loads(path.read_text(encoding="utf-8"))
                summaries.append(
                    {
                        "trace_id": trace["trace_id"],
                        "run_id": trace["run_id"],
                        "agent_name": trace["agent"]["name"],
                        "mode": trace["mode"],
                        "created_at": trace["created_at"],
                        "span_count": len(trace["spans"]),
                    }
                )
            except Exception:
                continue
        return summaries

    def read_payload(self, trace_id: str, payload_id: str) -> Dict[str, Any]:
        payload_path = self.payload_path(trace_id, payload_id)
        try:
            encrypted = payload_path.read_bytes()
            plaintext = self._fernet.decrypt(encrypted)
            return json.loads(plaintext.decode("utf-8"))
        except InvalidToken as exc:
            raise TracePayloadCorruptionError("encrypted payload failed authentication") from exc
        except Exception as exc:
            raise TraceStoreError("payload read failed") from exc

    def delete_run(self, run_id: str) -> int:
        deleted = 0
        for summary in list(self.list_traces()):
            if summary["run_id"] != run_id:
                continue
            trace_id = summary["trace_id"]
            for path in [
                self.metadata_path(trace_id),
                self.index_path(trace_id),
            ]:
                if path.exists():
                    path.unlink()
                    deleted += 1
            payload_root = self.payload_dir / trace_id
            if payload_root.exists():
                shutil.rmtree(payload_root)
                deleted += 1
        return deleted

    def apply_retention(self, max_age_days: int, now: Optional[datetime] = None) -> List[str]:
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=max_age_days)
        deleted_runs = []
        for summary in list(self.list_traces()):
            created_at = _parse_timestamp(summary["created_at"])
            if created_at < cutoff:
                self.delete_run(summary["run_id"])
                deleted_runs.append(summary["run_id"])
        return deleted_runs

    def migrate_metadata(self, target_version: int = 1) -> List[str]:
        migrated = []
        for summary in self.list_traces():
            trace = self.read_trace(summary["trace_id"])
            if trace.get("trace_schema_version") != target_version:
                trace["trace_schema_version"] = target_version
                self.metadata_path(trace["trace_id"]).write_text(
                    json.dumps(trace, indent=2, sort_keys=True),
                    encoding="utf-8",
                )
                migrated.append(trace["trace_id"])
        return migrated

    def metadata_path(self, trace_id: str) -> Path:
        return self.metadata_dir / ("%s.json" % trace_id)

    def index_path(self, trace_id: str) -> Path:
        return self.index_dir / ("%s.json" % trace_id)

    def payload_path(self, trace_id: str, payload_id: str) -> Path:
        return self.payload_dir / trace_id / ("%s.enc" % payload_id)

    def _cleanup_partial_trace(self, trace_id: str) -> None:
        for path in [
            self.metadata_path(trace_id),
            self.index_path(trace_id),
        ]:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                pass
        payload_root = self.payload_dir / trace_id
        try:
            if payload_root.exists():
                shutil.rmtree(payload_root)
        except OSError:
            pass

    def _load_or_create_key(self) -> bytes:
        env_key = os.environ.get("AGENT_CAPSULE_TRACE_KEY")
        if env_key:
            return env_key.encode("utf-8")

        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            return self.key_path.read_bytes().strip()

        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        try:
            os.chmod(self.key_path, 0o600)
        except OSError:
            pass
        return key


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
