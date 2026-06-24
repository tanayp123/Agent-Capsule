# Phase 15 Review: Product Website

## Scope Reviewed

- Created `agent-capsule-website` as a separate Next.js and TypeScript codebase.
- Added Tailwind CSS and shadcn/ui-style component setup.
- Built an enterprise-oriented product website with required sections.
- Added Playwright browser checks for content, responsive layout, first-viewport product evidence, no icons, no emojis, and no bold computed font weights.
- Added repository-level Phase 15 CI.

## Visual Design Review

The page uses a restrained enterprise style with full-width sections, regular-weight type, compact evidence panels, and operational product copy. The first viewport presents Agent Capsule by name and shows a product evidence surface with trace, policy, destination, manifest, attestation, and secret-release metadata.

## Copy Review

The copy avoids claims that Agent Capsule guarantees complete AI safety or eliminates prompt injection. It distinguishes local confidential-like demo checks from hosted confidential-computing environments.

## No Emoji And No Icon Review

The website does not use visible icon libraries, SVG icons, decorative icon systems, or emoji. `components.json` is configured with `iconLibrary` set to `none`.

## No Bold Font Review

Global CSS sets regular font weight across visible elements. Playwright checks computed font weight and fails if visible text exceeds the allowed threshold.

## Responsive Review

The hero product evidence surface stays in the first viewport and scrolls internally on narrow screens. Browser checks verify no page-level horizontal overflow on desktop and mobile viewports.

## Verification

Run:

```bash
bash ci/check-phase15.sh
```

This runs previous phase checks, installs website dependencies, builds the Next.js app, runs Playwright browser tests, and performs static checks for icon and bold-font violations.
