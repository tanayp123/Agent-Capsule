# Trace Store

Purpose: local encrypted trace storage.

Phase 3 status: implemented in the Python SDK as `agent_capsule.trace_store.EncryptedTraceStore`.

Planned features:

- Encrypted raw payload storage
- Safe metadata storage
- Retention configuration
- Deletion by run ID
- Trace listing
- Trace lookup by run ID
- Schema migration hooks
- Safe trace export support

Raw payloads must remain local by default.

## Store Layout

Given a trace-store root directory:

```text
metadata/
  <trace_id>.json
payloads/
  <trace_id>/
    <payload_id>.enc
payload-index/
  <trace_id>.json
keys/
  local.key
```

`metadata/` contains schema-compatible trace metadata. `payloads/` contains encrypted payload sidecars. `payload-index/` maps trace spans to payload sidecars. `keys/local.key` is a local development key generated automatically unless `AGENT_CAPSULE_TRACE_KEY` is provided.

## Run Checks

From the repository root:

```bash
bash ci/check-phase3.sh
```
