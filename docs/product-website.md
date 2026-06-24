# Product Website

The Agent Capsule product website lives in `agent-capsule-website/` as a separate Next.js codebase from the developer console.

## Purpose

The website communicates:

- Private debugging with encrypted traces.
- Policy review and data-flow visibility.
- Safe trace collaboration.
- Confidential customer demonstrations.
- Multi-language SDK support.
- Hardware and runtime requirements.
- Enterprise evidence artifacts.

## Run Locally

```bash
cd agent-capsule-website
npm ci
npm run dev -- --port 3020
```

Open `http://127.0.0.1:3020`.

## Build And Test

```bash
cd agent-capsule-website
npm run build
npm test
```

Repository-level check:

```bash
bash ci/check-phase15.sh
```

## Design Constraints

- US English copy.
- Enterprise-oriented, restrained visual style.
- No emojis.
- No icons, icon libraries, decorative icon systems, or SVG icon substitutes.
- No bold fonts.
- No overstated security claims.
- Distinguish the local confidential-like demo path from hosted confidential-computing environments.
- Keep the Agent Capsule name and product evidence visible in the first viewport.

## shadcn/ui

The website includes `components.json`, `lib/utils.ts`, and shadcn/ui-style primitives in `components/ui/`. The component setup intentionally omits icon libraries.
