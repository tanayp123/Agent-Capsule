# Agent Capsule Product Website

Separate product website for Agent Capsule. This codebase is intentionally independent from `agent-capsule-console`.

Phase 15 status: implemented.

## Stack

- Next.js App Router
- TypeScript
- Tailwind CSS
- shadcn/ui-style component primitives
- Playwright browser checks
- US English copy

## Install Dependencies

```bash
npm ci
```

If `package-lock.json` is not present yet, run:

```bash
npm install
```

## Run Locally

```bash
npm run dev -- --port 3020
```

Open:

```text
http://127.0.0.1:3020
```

## Build

```bash
npm run build
```

## Start Production Build

```bash
npm run start -- --port 3020
```

## Test

```bash
npm test
```

The Playwright checks verify required content, no plaintext-sensitive sample values, no visible icons, no emojis, no bold computed font weights, first-viewport product evidence, and responsive layout without page-level horizontal overflow.

## shadcn/ui Setup

`components.json` is included with aliases for:

- `@/components`
- `@/components/ui`
- `@/lib`
- `@/lib/utils`

The website uses shadcn/ui-style primitives in `components/ui/` without an icon library. Add new UI primitives by following the same file layout and Tailwind token usage.

## Design Rules

- No emojis in visible UI.
- No icons, icon libraries, decorative icon systems, or SVG icon substitutes in visible UI.
- No bold fonts. Headings, navigation, buttons, and labels use regular weight.
- Keep the look restrained and enterprise-oriented.
- Keep page sections full-width. Use cards only for repeated items or framed product evidence.
- Do not overstate security claims. Distinguish local confidential-like demo checks from hosted confidential-computing environments.

## Required Sections

The page includes:

- Header
- Hero with Agent Capsule name and clear offer
- Product visual showing trace, policy, and data-flow evidence
- Problem section
- Observe, Guard, and Confidential workflow
- Privacy review
- Safe trace collaboration
- Confidential demo
- Multi-language SDK support
- Hardware requirements
- Enterprise evidence
- Footer
