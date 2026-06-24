# Phase 8 Review

## Scope Reviewed

- Agent Capsule Console Next.js codebase.
- Fixture-backed local API bridge client.
- Ephemeral session token handling.
- Runs dashboard, timeline, data-flow graph, privacy map, review queue, policy decisions, safe trace export, replay comparison, manifest inspection, and local settings.
- Explicit local payload reveal confirmation.
- Browser tests for no plaintext on first render and desktop/mobile layout.

## Findings Fixed

- Added an npm PostCSS override so Next uses the patched PostCSS version and `npm audit` passes.
- Changed Playwright mobile checks to Chromium with a mobile viewport so CI uses one browser dependency.
- Tightened Playwright selectors to avoid ambiguous nav/header matches.
- Removed stale manifest-inspection wording from the CLI.

## Residual Risks

- The console uses fixture data until Phase 9 lands the localhost API bridge server.
- Payload reveal is a confirmed UI state only in Phase 8; Phase 9 owns audited reveal endpoints.
- Replay fixtures are viewable but do not yet have a dedicated JSON schema.

## Verification

```bash
bash ci/check-phase8.sh
```
