import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agent_capsule import Capsule, Destination
from agent_capsule.trace_store import EncryptedTraceStore, TracePayloadCorruptionError


DESTINATION = Destination(
    id="crm",
    type="external_tool",
    domain="api.crm.example",
    provider="Example CRM",
    risk="high",
)


def _make_trace(root, run_id=None, raw_email="private@example.com"):
    capsule = Capsule.init(mode="observe", trace_dir=root)

    with capsule.run("store-run", run_id=run_id) as run:
        with run.span(
            "tool_call",
            "crm.update",
            payload={"email": raw_email, "account_notes": "private note"},
            destination=DESTINATION,
        ):
            pass
    return capsule.trace_store, run


class TraceStoreTests(unittest.TestCase):
    def test_payload_is_encrypted_and_metadata_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, run = _make_trace(tmp)
            metadata_text = Path(run.trace_path).read_text(encoding="utf-8")
            self.assertNotIn("private@example.com", metadata_text)

            encrypted_payloads = list((Path(tmp) / "payloads").glob("**/*.enc"))
            self.assertTrue(encrypted_payloads)
            encrypted_bytes = encrypted_payloads[0].read_bytes()
            self.assertNotIn(b"private@example.com", encrypted_bytes)

            index = json.loads(next((Path(tmp) / "payload-index").glob("*.json")).read_text(encoding="utf-8"))
            decrypted = store.read_payload(run.trace_id, index[0]["payload_id"])
            self.assertEqual(decrypted["payload"]["email"], "private@example.com")

    def test_list_and_find_trace_do_not_require_payload_decryption(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, run = _make_trace(tmp, run_id="run_lookup")
            encrypted_payload = next((Path(tmp) / "payloads").glob("**/*.enc"))
            encrypted_payload.write_bytes(b"corrupted")

            summaries = store.list_traces()
            self.assertEqual(summaries[0]["run_id"], "run_lookup")
            found = store.find_trace_by_run_id("run_lookup")
            self.assertEqual(found["trace_id"], run.trace_id)

    def test_delete_run_removes_metadata_index_and_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _run = _make_trace(tmp, run_id="run_delete")
            deleted = store.delete_run("run_delete")
            self.assertGreaterEqual(deleted, 3)
            self.assertFalse(list((Path(tmp) / "metadata").glob("*.json")))
            self.assertFalse(list((Path(tmp) / "payload-index").glob("*.json")))
            self.assertFalse(list((Path(tmp) / "payloads").glob("**/*.enc")))

    def test_retention_deletes_old_traces(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, old_run = _make_trace(tmp, run_id="run_old", raw_email="old@example.com")
            _store, new_run = _make_trace(tmp, run_id="run_new", raw_email="new@example.com")

            old_trace = store.read_trace(old_run.trace_id)
            old_trace["created_at"] = (
                datetime.now(timezone.utc) - timedelta(days=30)
            ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            store.metadata_path(old_run.trace_id).write_text(
                json.dumps(old_trace, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            deleted = store.apply_retention(max_age_days=14)
            self.assertEqual(deleted, ["run_old"])
            self.assertIsNone(store.find_trace_by_run_id("run_old"))
            self.assertEqual(store.find_trace_by_run_id("run_new")["trace_id"], new_run.trace_id)

    def test_corrupted_payload_raises_without_plaintext_in_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, run = _make_trace(tmp)
            index = json.loads(next((Path(tmp) / "payload-index").glob("*.json")).read_text(encoding="utf-8"))
            payload_path = store.payload_path(run.trace_id, index[0]["payload_id"])
            payload_path.write_bytes(b"not-valid-fernet-token")

            with self.assertRaises(TracePayloadCorruptionError) as raised:
                store.read_payload(run.trace_id, index[0]["payload_id"])
            self.assertNotIn("private@example.com", str(raised.exception))

    def test_migration_hook_updates_schema_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, run = _make_trace(tmp)
            trace = store.read_trace(run.trace_id)
            trace["trace_schema_version"] = 0
            store.metadata_path(run.trace_id).write_text(
                json.dumps(trace, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            migrated = store.migrate_metadata(target_version=1)
            self.assertEqual(migrated, [run.trace_id])
            self.assertEqual(store.read_trace(run.trace_id)["trace_schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
