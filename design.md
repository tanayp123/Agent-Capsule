# Netrows Design System


> Extracted verbatim from the **Agent‑Reach / GitFinder** frontend
> (`Agent-Reach/linkedin/frontend`) so the Netrows frontend can replicate it
> pixel‑for‑pixel. Every token, class string, and pattern below is copied from
> the source — values are not paraphrased.
>
> **Design intent (from the source CSS):** _"Dina‑inspired light theme: soft
> lavender ground, slate‑indigo ink, one violet accent. Large radii, generous
> whitespace."_
>
> **Branding note:** The source app is "GitFinder". Wherever you see brand
> strings (`GitFinder`, author name, `github.gitdate.ink`), treat them as
> **placeholders** — swap in Netrows branding. The **tokens and components stay
> identical.**


---


## 1. Stack & toolchain


The target stack is the **same as the source** (confirmed). Reproduce it exactly:


| Concern | Choice |
| --- | --- |
| Framework | **Next.js (App Router)** — `next@16`, `react@19` |
| Styling | **Tailwind CSS v4** (`tailwindcss@^4`, `@tailwindcss/postcss`) + `tw-animate-css` |
| Component layer | **shadcn/ui**, style **`base-nova`**, built on **`@base-ui/react`** |
| Icons | **`lucide-react`** |
| Theming | **`next-themes`** — light only (`enableSystem={false}`) |
| Data / tables | **`@tanstack/react-query`**, **`@tanstack/react-table`** |
| Toasts | **`sonner`** |
| Command palette | **`cmdk`** |
| Class variants | **`class-variance-authority`** + `clsx` + `tailwind-merge` |


### `components.json` (shadcn config — copy verbatim)


```json
{
 "$schema": "https://ui.shadcn.com/schema.json",
 "style": "base-nova",
 "rsc": true,
 "tsx": true,
 "tailwind": {
   "config": "",
   "css": "app/globals.css",
   "baseColor": "neutral",
   "cssVariables": true,
   "prefix": ""
 },
 "iconLibrary": "lucide",
 "rtl": false,
 "aliases": {
   "components": "@/components",
   "utils": "@/lib/utils",
   "ui": "@/components/ui",
   "lib": "@/lib",
   "hooks": "@/hooks"
 },
 "menuColor": "default",
 "menuAccent": "subtle",
 "registries": {}
}
```


### `lib/utils.ts` — the `cn()` helper (every component depends on this)


```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"


export function cn(...inputs: ClassValue[]) {
 return twMerge(clsx(inputs))
}
```


---


## 2. Foundations — `app/globals.css`


This is the heart of the system. **Copy this file verbatim.** All color tokens
are **OKLCH**.


```css
@import "tailwindcss";
@import "tw-animate-css";
@import "shadcn/tailwind.css";


@custom-variant dark (&:is(.dark *));


@theme inline {
 --color-background: var(--background);
 --color-foreground: var(--foreground);
 --font-sans: var(--font-hanken);
 --font-mono: var(--font-geist-mono);
 --font-heading: var(--font-hanken);
 --color-brand: var(--brand);
 --color-brand-foreground: var(--brand-foreground);
 --color-sidebar-ring: var(--sidebar-ring);
 --color-sidebar-border: var(--sidebar-border);
 --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
 --color-sidebar-accent: var(--sidebar-accent);
 --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
 --color-sidebar-primary: var(--sidebar-primary);
 --color-sidebar-foreground: var(--sidebar-foreground);
 --color-sidebar: var(--sidebar);
 --color-chart-5: var(--chart-5);
 --color-chart-4: var(--chart-4);
 --color-chart-3: var(--chart-3);
 --color-chart-2: var(--chart-2);
 --color-chart-1: var(--chart-1);
 --color-ring: var(--ring);
 --color-input: var(--input);
 --color-border: var(--border);
 --color-destructive: var(--destructive);
 --color-accent-foreground: var(--accent-foreground);
 --color-accent: var(--accent);
 --color-muted-foreground: var(--muted-foreground);
 --color-muted: var(--muted);
 --color-secondary-foreground: var(--secondary-foreground);
 --color-secondary: var(--secondary);
 --color-primary-foreground: var(--primary-foreground);
 --color-primary: var(--primary);
 --color-popover-foreground: var(--popover-foreground);
 --color-popover: var(--popover);
 --color-card-foreground: var(--card-foreground);
 --color-card: var(--card);
 --radius-sm: calc(var(--radius) * 0.6);
 --radius-md: calc(var(--radius) * 0.8);
 --radius-lg: var(--radius);
 --radius-xl: calc(var(--radius) * 1.4);
 --radius-2xl: calc(var(--radius) * 1.8);
 --radius-3xl: calc(var(--radius) * 2.2);
 --radius-4xl: calc(var(--radius) * 2.6);
}


/* ── Dina-inspired light theme: soft lavender ground, slate-indigo ink,
     one violet accent. Large radii, generous whitespace. ── */
:root {
 --background: oklch(0.984 0.004 286);
 --foreground: oklch(0.345 0.027 281);
 --card: oklch(1 0 0);
 --card-foreground: oklch(0.345 0.027 281);
 --popover: oklch(1 0 0);
 --popover-foreground: oklch(0.345 0.027 281);
 --primary: oklch(0.365 0.035 282);
 --primary-foreground: oklch(0.985 0.003 286);
 --secondary: oklch(0.962 0.006 286);
 --secondary-foreground: oklch(0.365 0.035 282);
 --muted: oklch(0.966 0.005 286);
 --muted-foreground: oklch(0.553 0.022 283);
 --accent: oklch(0.95 0.012 287);
 --accent-foreground: oklch(0.365 0.035 282);
 --destructive: oklch(0.577 0.245 27.325);
 --border: oklch(0.917 0.006 286);
 --input: oklch(0.917 0.006 286);
 --ring: oklch(0.62 0.13 286);
 --brand: oklch(0.62 0.16 286);
 --brand-foreground: oklch(0.985 0.003 286);
 --chart-1: oklch(0.62 0.16 286);
 --chart-2: oklch(0.556 0.04 283);
 --chart-3: oklch(0.439 0.03 282);
 --chart-4: oklch(0.371 0.03 282);
 --chart-5: oklch(0.269 0.02 282);
 --radius: 0.85rem;
 --sidebar: oklch(0.975 0.005 286);
 --sidebar-foreground: oklch(0.345 0.027 281);
 --sidebar-primary: oklch(0.365 0.035 282);
 --sidebar-primary-foreground: oklch(0.985 0 0);
 --sidebar-accent: oklch(0.95 0.012 287);
 --sidebar-accent-foreground: oklch(0.365 0.035 282);
 --sidebar-border: oklch(0.917 0.006 286);
 --sidebar-ring: oklch(0.62 0.13 286);
}


.dark {
 --background: oklch(0.18 0.012 285);
 --foreground: oklch(0.96 0.004 286);
 --card: oklch(0.22 0.014 285);
 --card-foreground: oklch(0.96 0.004 286);
 --popover: oklch(0.22 0.014 285);
 --popover-foreground: oklch(0.96 0.004 286);
 --primary: oklch(0.92 0.01 286);
 --primary-foreground: oklch(0.24 0.02 285);
 --secondary: oklch(0.27 0.015 285);
 --secondary-foreground: oklch(0.96 0.004 286);
 --muted: oklch(0.27 0.015 285);
 --muted-foreground: oklch(0.7 0.02 285);
 --accent: oklch(0.3 0.02 286);
 --accent-foreground: oklch(0.96 0.004 286);
 --destructive: oklch(0.704 0.191 22.216);
 --border: oklch(1 0 0 / 10%);
 --input: oklch(1 0 0 / 15%);
 --ring: oklch(0.62 0.16 286);
 --brand: oklch(0.7 0.15 286);
 --brand-foreground: oklch(0.18 0.012 285);
 --sidebar: oklch(0.22 0.014 285);
 --sidebar-foreground: oklch(0.96 0.004 286);
 --sidebar-primary: oklch(0.62 0.16 286);
 --sidebar-primary-foreground: oklch(0.985 0 0);
 --sidebar-accent: oklch(0.3 0.02 286);
 --sidebar-accent-foreground: oklch(0.96 0.004 286);
 --sidebar-border: oklch(1 0 0 / 10%);
 --sidebar-ring: oklch(0.62 0.16 286);
}


@layer base {
 * {
   @apply border-border outline-ring/50;
 }
 body {
   @apply bg-background text-foreground;
   -webkit-font-smoothing: antialiased;
 }
 html {
   @apply font-sans;
 }
 h1,
 h2,
 h3 {
   letter-spacing: -0.02em;
 }
}


/* Soft, even lavender wash for marketing + auth screens. One centered top
  glow (symmetric — no left/right seams) settling into a flat light base, so it
  can cover a whole page continuously behind the floating nav. */
.bg-aurora {
 background:
   radial-gradient(1500px 600px at 50% -160px, oklch(0.92 0.045 290 / 0.55), transparent 70%),
   linear-gradient(180deg, oklch(0.98 0.008 286), oklch(0.985 0.004 286));
}
```


### Color token → role reference


| Token | Light value (OKLCH) | Role |
| --- | --- | --- |
| `--background` | `0.984 0.004 286` | Page ground (faint lavender‑white) |
| `--foreground` | `0.345 0.027 281` | Default ink (slate‑indigo) |
| `--card` / `--popover` | `1 0 0` (pure white) | Raised surfaces |
| `--primary` | `0.365 0.035 282` | Primary buttons/text (deep slate‑indigo) |
| `--secondary` / `--muted` / `--accent` | `0.95–0.966` lavender‑grays | Subtle fills, hovers |
| `--muted-foreground` | `0.553 0.022 283` | Secondary text |
| `--brand` | `0.62 0.16 286` | **The one violet accent** — eyebrow numbers, accent spans, chart‑1 |
| `--destructive` | `0.577 0.245 27.325` | Errors (red‑orange) |
| `--border` / `--input` | `0.917 0.006 286` | Hairlines, field borders |
| `--ring` | `0.62 0.13 286` | Focus ring |


**Important conventions baked into the theme:**
- Surfaces use `ring-1 ring-foreground/10` **instead of** a `border` for the soft separator look (cards, popovers, dialogs).
- Headings `h1–h3` get `letter-spacing: -0.02em` globally (tight tracking).
- Light mode only ships in production; dark tokens exist but are not toggled.


### Radius scale


Base `--radius: 0.85rem` (~13.6px). Tailwind utilities map to:


| Utility | Formula | ≈ value |
| --- | --- | --- |
| `rounded-sm` | `radius × 0.6` | 0.51rem |
| `rounded-md` | `radius × 0.8` | 0.68rem |
| `rounded-lg` | `radius` | 0.85rem |
| `rounded-xl` | `radius × 1.4` | 1.19rem |
| `rounded-2xl` | `radius × 1.8` | 1.53rem |
| `rounded-3xl` | `radius × 2.2` | 1.87rem |
| `rounded-4xl` | `radius × 2.6` | 2.21rem |


Usage: **`rounded-lg`** = buttons/inputs/menus · **`rounded-xl`** = cards/dialogs ·
**`rounded-2xl`/`rounded-3xl`** = marketing panels · **`rounded-4xl`** = badge pills ·
**`rounded-full`** = avatars + marketing CTAs/pill nav.


---


## 3. Typography


### Fonts — `app/layout.tsx`


```tsx
import { Hanken_Grotesk, Geist_Mono } from "next/font/google";


const hanken = Hanken_Grotesk({
 variable: "--font-hanken",
 subsets: ["latin"],
 weight: ["300", "400", "500", "600", "700"],
});


const geistMono = Geist_Mono({
 variable: "--font-geist-mono",
 subsets: ["latin"],
});


// on <html>:
className={`${hanken.variable} ${geistMono.variable} h-full antialiased`}
// on <body>:
className="flex min-h-full flex-col"
```


- **Sans / heading:** Hanken Grotesk (`--font-sans` **and** `--font-heading`).
- **Mono:** Geist Mono (`--font-mono`) — used for eyebrow numbers and `tabular-nums` data.


### Type scale (as used across pages)


| Role | Classes |
| --- | --- |
| Hero h1 | `text-5xl leading-[1.05] font-medium tracking-tight sm:text-6xl` |
| Section h2 | `text-4xl font-medium tracking-tight` (final CTA: `text-5xl`) |
| Sub‑section h3 | `text-xl font-medium tracking-tight` (or `text-lg`) |
| Page title (app) | `text-2xl font-medium tracking-tight` / `text-xl font-semibold` |
| Card / dialog / sheet title | `font-heading text-base leading-snug font-medium` |
| Lead paragraph | `text-muted-foreground text-lg leading-relaxed` |
| Body | `text-sm` |
| Secondary / metadata | `text-muted-foreground text-xs` |
| Eyebrow number | `text-brand font-mono text-sm` (muted variant: `text-muted-foreground/70 font-mono text-sm`) |
| Footer column title | `text-muted-foreground/80 text-xs font-medium tracking-wider uppercase` |
| Numeric/counts | add `tabular-nums` |


Weight vocabulary: body `400`, emphasis/titles `font-medium` (500), brand/logo `font-semibold` (600). Headings lean on `tracking-tight`; body lead on `leading-relaxed`.


---


## 4. App shell & providers


### `app/providers.tsx` (copy verbatim)


```tsx
"use client";


import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";
import { toast } from "sonner";


import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ApiError } from "@/lib/api";


function toastError(error: unknown) {
 const message = error instanceof ApiError ? error.message : "Request failed";
 const hint = error instanceof ApiError ? error.hint ?? undefined : undefined;
 toast.error(message, { description: hint });
}


export function Providers({ children }: { children: React.ReactNode }) {
 const [client] = useState(
   () =>
     new QueryClient({
       queryCache: new QueryCache({ onError: toastError }),
       mutationCache: new MutationCache({ onError: toastError }),
       defaultOptions: { queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false } },
     }),
 );


 return (
   <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} disableTransitionOnChange>
     <QueryClientProvider client={client}>
       <TooltipProvider>{children}</TooltipProvider>
       <Toaster position="top-right" />
     </QueryClientProvider>
   </ThemeProvider>
 );
}
```


Key defaults to keep: theme **light‑locked**, query `retry:1` / `staleTime:30_000` / `refetchOnWindowFocus:false`, all query+mutation errors funnel to a `sonner` toast, toaster pinned **top‑right**.


---


## 5. Core component specs (shadcn `base-nova`)


These are the exact `class-variance-authority` configs / class strings from
`components/ui/*`. Reproduce them precisely (or run `shadcn` with the
`base-nova` style + the `components.json` above and you'll get these).


### Shared conventions (repeated across every interactive primitive)


- **Focus ring:** `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50`
 (badge/tabs use `ring-[3px]`).
- **Invalid state:** `aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40`
- **Icon auto‑sizing:** `[&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4`
 (icons default to `size-4`; xs→`size-3`, sm→`size-3.5`).
- **Surface separators:** `ring-1 ring-foreground/10` + `shadow-md` on floating surfaces.


### Button — `components/ui/button.tsx`


```ts
// base
"group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4"


variants: {
 variant: {
   default:     "bg-primary text-primary-foreground hover:bg-primary/80",
   outline:     "border-border bg-background hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
   secondary:   "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
   ghost:       "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
   destructive: "bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40",
   link:        "text-primary underline-offset-4 hover:underline",
 },
 size: {
   default:   "h-8 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
   xs:        "h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs ... [&_svg:not([class*='size-'])]:size-3",
   sm:        "h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] ... [&_svg:not([class*='size-'])]:size-3.5",
   lg:        "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
   icon:      "size-8",
   "icon-xs": "size-6 rounded-[min(var(--radius-md),10px)] ... [&_svg:not([class*='size-'])]:size-3",
   "icon-sm": "size-7 rounded-[min(var(--radius-md),12px)] ...",
   "icon-lg": "size-9",
 },
}
defaultVariants: { variant: "default", size: "default" }
```


Notes: **`default` button is `h-8`** (compact). Pressing nudges down 1px
(`active:translate-y-px`). `destructive` is a **tinted** button (`bg-destructive/10
text-destructive`), not solid red.


### Badge — `components/ui/badge.tsx`


```ts
// base — note rounded-4xl pill + fixed h-5
"group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3!"


variants: {
 default:     "bg-primary text-primary-foreground [a]:hover:bg-primary/80",
 secondary:   "bg-secondary text-secondary-foreground [a]:hover:bg-secondary/80",
 destructive: "bg-destructive/10 text-destructive focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:focus-visible:ring-destructive/40 [a]:hover:bg-destructive/20",
 outline:     "border-border text-foreground [a]:hover:bg-muted [a]:hover:text-muted-foreground",
 ghost:       "hover:bg-muted hover:text-muted-foreground dark:hover:bg-muted/50",
 link:        "text-primary underline-offset-4 hover:underline",
}
```


### Card — `components/ui/card.tsx`


```
Card:            group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-xl bg-card py-(--card-spacing) text-sm text-card-foreground ring-1 ring-foreground/10 [--card-spacing:--spacing(4)] has-data-[slot=card-footer]:pb-0 ... data-[size=sm]:[--card-spacing:--spacing(3)] *:[img:first-child]:rounded-t-xl *:[img:last-child]:rounded-b-xl
CardHeader:      grid auto-rows-min items-start gap-1 rounded-t-xl px-(--card-spacing) has-data-[slot=card-action]:grid-cols-[1fr_auto] ...
CardTitle:       font-heading text-base leading-snug font-medium group-data-[size=sm]/card:text-sm
CardDescription: text-sm text-muted-foreground
CardAction:      col-start-2 row-span-2 row-start-1 self-start justify-self-end
CardContent:     px-(--card-spacing)
CardFooter:      flex items-center rounded-b-xl border-t bg-muted/50 p-(--card-spacing)
```


Card uses a `--card-spacing` CSS var (default `spacing(4)` = 1rem; `data-[size=sm]`
→ `spacing(3)`). Border look = `ring-1 ring-foreground/10` (no `border`). Footer is
a tinted bar (`bg-muted/50 border-t`).


### Input / Textarea — `components/ui/{input,textarea}.tsx`


```
Input:    h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:... md:text-sm dark:bg-input/30 ...
Textarea: flex field-sizing-content min-h-16 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-base ... md:text-sm dark:bg-input/30 ...
```


### Select / Dropdown / Popover (floating surfaces)


```
SelectTrigger:   flex w-fit items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-2.5 text-sm ... focus-visible:ring-3 focus-visible:ring-ring/50 data-[size=default]:h-8 data-[size=sm]:h-7 ...
SelectContent:   z-50 ... overflow-y-auto rounded-lg bg-popover text-popover-foreground shadow-md ring-1 ring-foreground/10 duration-100 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out ...
SelectItem:      relative flex w-full cursor-default items-center gap-1.5 rounded-md py-1 pr-8 pl-1.5 text-sm focus:bg-accent focus:text-accent-foreground ...
DropdownContent: z-50 ... min-w-32 overflow-y-auto rounded-lg bg-popover p-1 text-popover-foreground shadow-md ring-1 ring-foreground/10 duration-100 outline-none ...
DropdownItem:    relative flex cursor-default items-center gap-1.5 rounded-md px-1.5 py-1 text-sm focus:bg-accent focus:text-accent-foreground data-[variant=destructive]:text-destructive ...
PopoverContent:  z-50 flex w-72 origin-(--transform-origin) flex-col gap-2.5 rounded-lg bg-popover p-2.5 text-sm text-popover-foreground shadow-md ring-1 ring-foreground/10 outline-hidden duration-100 ...
```


Pattern: triggers `rounded-lg`, floating panels `rounded-lg bg-popover shadow-md
ring-1 ring-foreground/10` with `fade-in/zoom-in-95` open and `fade-out/zoom-out-95`
close animations.


### Table — `components/ui/table.tsx`


```
wrapper:     relative w-full overflow-x-auto      (commonly wrapped again: "overflow-x-auto rounded-md border")
Table:       w-full caption-bottom text-sm
TableHeader: [&_tr]:border-b
TableBody:   [&_tr:last-child]:border-0
TableFooter: border-t bg-muted/50 font-medium [&>tr]:last:border-b-0
TableRow:    border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted
TableHead:   h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0
TableCell:   p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0
TableCaption: mt-4 text-sm text-muted-foreground
```


Density: header `h-10`, cells `p-2`, everything `text-sm whitespace-nowrap`. Clickable
rows add `cursor-pointer`.


### Dialog / Sheet — `components/ui/{dialog,sheet}.tsx`


```
DialogOverlay: fixed inset-0 isolate z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0
DialogContent: fixed top-1/2 left-1/2 z-50 grid w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 duration-100 outline-none sm:max-w-sm data-open:zoom-in-95 ...
DialogFooter:  -mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t bg-muted/50 p-4 sm:flex-row sm:justify-end
DialogTitle:   font-heading text-base leading-none font-medium


SheetOverlay:  fixed inset-0 z-50 bg-black/10 transition-opacity duration-150 ... supports-backdrop-filter:backdrop-blur-xs
SheetContent:  fixed z-50 flex flex-col gap-4 bg-popover bg-clip-padding text-sm text-popover-foreground shadow-lg transition duration-200 ... data-[side=right]:w-3/4 data-[side=right]:border-l ... data-[side=right]:sm:max-w-sm  (left/right side panels cap at sm:max-w-sm)
```


Both use a light scrim: **`bg-black/10` + `backdrop-blur-xs`** (not a heavy black overlay).


### Tabs — `components/ui/tabs.tsx`


```
Tabs:        group/tabs flex gap-2 data-horizontal:flex-col
TabsList (default): inline-flex w-fit items-center justify-center rounded-lg p-[3px] text-muted-foreground ... bg-muted
TabsList (line):    ... rounded-none p-[3px] gap-1 bg-transparent
TabsTrigger: relative inline-flex h-[calc(100%-1px)] flex-1 items-center justify-center gap-1.5 rounded-md border border-transparent px-1.5 py-0.5 text-sm font-medium text-foreground/60 transition-all hover:text-foreground focus-visible:ring-[3px] ... data-active:bg-background data-active:text-foreground (default) | line variant uses an under-bar via after: + data-active:after:opacity-100
TabsContent: flex-1 text-sm outline-none
```


Two looks: **segmented** (`default`, pill group on `bg-muted`) and **underline**
(`line`, active tab shows a 2px `after:` bar).


### Tooltip — `components/ui/tooltip.tsx`


```
TooltipContent: z-50 inline-flex w-fit max-w-xs items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-xs text-background ... data-open:zoom-in-95 ...
TooltipArrow:   z-50 size-2.5 rotate-45 rounded-[2px] bg-foreground fill-foreground ...
```


Inverted chip: **dark `bg-foreground` with `text-background`**.


### Misc primitives


```
Separator: shrink-0 bg-border data-horizontal:h-px data-horizontal:w-full data-vertical:w-px data-vertical:self-stretch
Skeleton:  animate-pulse rounded-md bg-muted
Spinner:   size-4 animate-spin            (lucide <Loader2Icon />)
Alert:     relative flex w-full gap-3 rounded-lg border px-4 py-3 text-sm [&>svg]:size-4 [&>svg]:translate-y-0.5
          variant default     → bg-card text-card-foreground
          variant destructive → text-destructive border-destructive/30 bg-destructive/5 [&>svg]:text-destructive
 AlertTitle: font-medium · AlertDescription: text-muted-foreground text-sm [&_p]:leading-relaxed
Empty:     flex min-h-48 flex-col items-center justify-center gap-3 rounded-md border border-dashed p-8 text-center
 EmptyMedia: text-muted-foreground/70 flex size-10 items-center justify-center [&_svg]:size-6
 EmptyTitle: text-sm font-medium · EmptyDescription: text-muted-foreground max-w-sm text-sm
 EmptyContent: flex flex-wrap items-center justify-center gap-2
```


### Sonner toast — `components/ui/sonner.tsx`


```tsx
<Sonner
 theme={theme}
 className="toaster group"
 icons={{
   success: <CircleCheckIcon className="size-4" />,
   info:    <InfoIcon className="size-4" />,
   warning: <TriangleAlertIcon className="size-4" />,
   error:   <OctagonXIcon className="size-4" />,
   loading: <Loader2Icon className="size-4 animate-spin" />,
 }}
 style={{
   "--normal-bg": "var(--popover)",
   "--normal-text": "var(--popover-foreground)",
   "--normal-border": "var(--border)",
   "--border-radius": "var(--radius)",
 }}
 toastOptions={{ classNames: { toast: "cn-toast" } }}
/>
```


---


## 6. Layout patterns


### 6.1 Marketing / landing — `bg-aurora` page


Page wrapper: `<div className="bg-aurora flex min-h-full flex-col">`.


**Floating pill nav** (`components/marketing/site-header.tsx`):


```tsx
<header className="sticky top-4 z-50 px-4">
 <div className="border-border/70 bg-card/80 mx-auto flex max-w-5xl items-center justify-between gap-4 rounded-full border px-5 py-2.5 shadow-sm backdrop-blur">
   <Link href="/" className="text-[15px] font-semibold tracking-tight">GitFinder</Link>
   <nav className="text-muted-foreground hidden items-center gap-7 text-sm md:flex"> … hover:text-foreground transition-colors </nav>
   <div className="flex items-center gap-1.5">
     {/* sign-in: text link · CTA: bg-primary text-primary-foreground rounded-full px-4 py-1.5 text-sm font-medium hover:opacity-90 */}
   </div>
 </div>
</header>
```


**Hero + section rhythm** (`app/page.tsx`):


- Hero: `<section className="px-6 pt-20 pb-24 text-center sm:pt-28">` → inner `mx-auto max-w-3xl`.
- h1 `text-5xl leading-[1.05] font-medium tracking-tight sm:text-6xl`; lead `text-muted-foreground mx-auto mt-6 max-w-xl text-lg leading-relaxed`.
- Hero CTAs are **pills**: primary `bg-primary text-primary-foreground rounded-full px-6 py-3 text-sm font-medium transition-opacity hover:opacity-90`; secondary `text-foreground hover:bg-accent rounded-full px-6 py-3 text-sm font-medium`.
- Standard section spacing: **`px-6 py-24`**, content centered in `max-w-5xl`.
- Section h2 `text-4xl font-medium tracking-tight`, with the **violet accent** on a `<span className="text-brand">` highlight line.


**Feature grid:**
```tsx
<div className="mx-auto grid max-w-5xl gap-5 sm:grid-cols-2">
 <div className="border-border/70 bg-card rounded-2xl border p-8">
   <div className="text-brand font-mono text-sm">{n}</div>
   <h3 className="mt-4 text-xl font-medium tracking-tight">{title}</h3>
   <p className="text-muted-foreground mt-3 leading-relaxed">{body}</p>
 </div>
</div>
```


**"How it works" hairline grid** (cells separated by 1px gaps over the ground):
```tsx
<div className="mt-12 grid gap-px overflow-hidden rounded-2xl sm:grid-cols-2 lg:grid-cols-4">
 <div className="bg-card border-border/70 border p-7"> … </div>
</div>
```


**Invite band:** `border-border/70 bg-card mx-auto max-w-5xl rounded-3xl border px-8 py-14 text-center`.
**Final CTA:** `max-w-2xl`, h2 `text-5xl`.


**Footer** (`components/marketing/site-footer.tsx`): `border-border/70 border-t px-6 py-14`;
inner `mx-auto grid max-w-5xl gap-10 md:grid-cols-[1.5fr_1fr_1fr_1fr]`; column titles
`text-muted-foreground/80 text-xs font-medium tracking-wider uppercase`; links
`text-muted-foreground hover:text-foreground text-sm transition-colors`; legal row
`border-t pt-6 text-xs`.


### 6.2 Dashboard shell — `app/(dashboard)/layout.tsx`


```tsx
<SidebarProvider>
 <AppSidebar />
 <SidebarInset>
   <header className="bg-background/80 sticky top-0 z-10 flex h-14 items-center gap-2 border-b px-4 backdrop-blur">
     <SidebarTrigger />
     <span className="text-muted-foreground text-sm font-medium">GitFinder</span>
   </header>
   <main className="flex-1">{children}</main>
 </SidebarInset>
</SidebarProvider>
```


Sidebar dimensions (`components/ui/sidebar.tsx`): **`SIDEBAR_WIDTH = 16rem`**,
`SIDEBAR_WIDTH_ICON = 3rem` (collapsed), `SIDEBAR_WIDTH_MOBILE = 18rem`.
Top header is `h-14`, sticky, `border-b`, translucent `bg-background/80 backdrop-blur`.


**Sidebar nav** (`components/app-sidebar.tsx`): `SidebarHeader` brand link
(`px-2 py-1.5 text-base font-semibold tracking-tight`) → `SidebarContent` with
`SidebarMenu` items (lucide icon + label, `isActive` highlight, `SidebarMenuBadge`
for counts, collapsible sub‑groups whose chevron rotates 90°) → `SidebarFooter`
with the user menu.


**User menu** (`components/dashboard/user-menu.tsx`): round avatar
`bg-sidebar-accent text-sidebar-accent-foreground flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-medium`,
truncating label, ghost "Sign out" text button.


### 6.3 Auth shell — `components/auth/auth-shell.tsx`


```tsx
<div className="bg-aurora flex min-h-full flex-col items-center justify-center px-6 py-16">
 <div className="w-full max-w-sm">
   <Link href="/" className="block text-center text-[15px] font-semibold tracking-tight">GitFinder</Link>
   <div className="border-border/70 bg-card mt-6 rounded-2xl border p-8 shadow-sm">
     <h1 className="text-2xl font-medium tracking-tight">{title}</h1>
     {subtitle && <p className="text-muted-foreground mt-1.5 text-sm">{subtitle}</p>}
     <div className="mt-6">{children}</div>
   </div>
   {footer && <div className="text-muted-foreground mt-5 text-center text-sm">{footer}</div>}
 </div>
</div>
```


Field row: `<label className="block space-y-1.5"><span className="text-foreground text-sm font-medium">{label}</span> … {hint && <span className="text-muted-foreground block text-xs">…</span>}</label>`.
Submit button is full‑width (`className="w-full"`); error text `text-destructive text-sm`.


---


## 7. Application / data patterns


**Page container (app routes):** `w-full space-y-6 px-6 py-6 sm:px-8`.
**Section card:** `<Card className="space-y-4 p-6">` · **compact card:** `space-y-3 p-4`.
**Page header row:** `flex items-center justify-between` — title `text-2xl font-medium tracking-tight` (or `text-xl font-semibold`), subtitle `text-muted-foreground text-sm`, primary action button on the right.


**ScoreBar** (mini progress used in table cells):
```tsx
<div className="flex items-center gap-2">
 <div className="bg-muted h-1.5 w-12 overflow-hidden rounded-full">
   <div className="bg-primary h-full rounded-full" style={{ width: `${Math.min(score, 100)}%` }} />
 </div>
 <span className="tabular-nums">{score}</span>
</div>
```


**Progress** (`components/ui/progress.tsx`): track `relative flex h-1 w-full items-center overflow-x-hidden rounded-full bg-muted`, indicator `h-full bg-primary transition-all`, value label `ml-auto text-sm text-muted-foreground tabular-nums`.


**Status / badge color conventions:**
- Languages / neutral tags → `Badge variant="secondary"`.
- Filters, examples, clickable chips → `Badge variant="outline"` (+ `cursor-pointer`).
- Errors → `text-destructive` / `Badge variant="destructive"`.
- Completed step check → lucide `Check` with **`text-emerald-600`** (`size-3.5`); in‑progress → `Loader2 size-3.5 animate-spin text-muted-foreground`.
- Status enum labels (from `lib/format.ts`): `new → "New"`, `shortlisted → "Shortlisted"`, `to_contact → "To contact"`, `archived → "Archived"`, surfaced via a `StatusSelect` (`SelectTrigger size="sm" className="w-36"`).


**Data table:** wrap in `overflow-x-auto rounded-md border`; rows `cursor-pointer`
with the table row hover/selected states above. **Sortable header** = ghost button:
```tsx
<Button variant="ghost" size="sm" className="-ml-2 h-8 data-[state=open]:bg-accent">
 {title}
 {/* ArrowUp / ArrowDown / ChevronsUpDown — all className="ml-1 size-3.5"; inactive opacity-50 */}
</Button>
```
**Pagination row:** `flex flex-wrap items-center justify-between gap-2 px-1 py-2 text-sm`; nav buttons `variant="outline" size="icon" className="size-8"`.
**Facet filter chips:** `flex flex-wrap items-center gap-2`; active `variant="default"` / inactive `variant="outline"`, `size="sm" className="h-7 px-2"`; clear = ghost button + `X size-3.5`.


**Detail sheet** (e.g. candidate): `<SheetContent className="w-full overflow-y-auto sm:max-w-md">` (right side), body `space-y-5 p-4`; section labels `text-sm font-medium`; `<Progress className="mt-2" />` for match score; evidence list rows `flex items-center justify-between gap-2` with `tabular-nums` figures; loading `<Skeleton className="mt-2 h-20 w-full" />`; action row `flex flex-wrap gap-2` (outline for secondary, default for primary).


**TagInput** (`components/search/tag-input.tsx`): wrapper
`border-input flex flex-wrap items-center gap-1.5 rounded-md border px-2 py-1.5`;
tags `Badge variant="secondary"` with an inline `X size-3` remove button; the inner
field is borderless `h-7 min-w-24 flex-1 border-0 px-1 shadow-none focus-visible:ring-0`.


**Form row** (query plan editor): `grid grid-cols-[150px_1fr] items-center gap-3`
(fixed label column); hint icon = lucide `Info` + tooltip, trigger
`text-muted-foreground inline-flex cursor-help`; sections divided by `border-t pt-4`.


**Add‑to‑list (cmdk popover):** trigger `Button variant="outline" size="sm"` + `Plus size-3.5`;
`PopoverContent align="end" className="w-64 p-0"` containing a `Command` with
`CommandInput`, grouped `CommandGroup` ("Your lists" with right‑aligned
`text-muted-foreground ml-auto text-xs tabular-nums` counts, plus a "Create" group).


**Empty states inside tables:** `<Empty className="border-0">` (drop the dashed border)
with a lucide icon in `EmptyMedia` (`SearchX`, `Users`, `FolderKanban`, …).
**Skeleton sizes seen:** `h-20 w-full` (evidence), `h-36 w-full rounded-md` (mobile card),
`h-40 w-full rounded-xl` (list‑card grid).


---


## 8. Quick‑reference cheat sheet


### Component density


| Element | Height | Padding | Radius |
| --- | --- | --- | --- |
| Button (default) | `h-8` | `px-2.5` `gap-1.5` | `rounded-lg` |
| Button (sm) | `h-7` | `px-2.5` `gap-1` | `rounded-[min(var(--radius-md),12px)]` |
| Button (icon) | `size-8` | — | `rounded-lg` |
| Badge | `h-5` | `px-2 py-0.5` | `rounded-4xl` |
| Input / Select trigger | `h-8` | `px-2.5` | `rounded-lg` |
| Table head / cell | `h-10` / — | `px-2` / `p-2` | — |
| Card | — | `--card-spacing` (1rem) | `rounded-xl` |
| Dialog | — | `p-4` | `rounded-xl` |


### State recipes (memorize these)


| State | Classes |
| --- | --- |
| Focus | `focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50` |
| Invalid | `aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20` |
| Row hover | `hover:bg-muted/50` |
| Row selected | `data-[state=selected]:bg-muted` |
| Button press | `active:translate-y-px` |
| Disabled | `disabled:pointer-events-none disabled:opacity-50` |
| Floating surface | `bg-popover shadow-md ring-1 ring-foreground/10` + `data-open:fade-in-0 data-open:zoom-in-95` |
| Overlay scrim | `bg-black/10 backdrop-blur-xs` |
| Icon default size | `[&_svg:not([class*='size-'])]:size-4` |


### Common class strings


```
Page (app):        w-full space-y-6 px-6 py-6 sm:px-8
Section (marketing): px-6 py-24  →  inner mx-auto max-w-5xl
Section card:      space-y-4 p-6        (compact: space-y-3 p-4)
Marketing CTA pill: bg-primary text-primary-foreground rounded-full px-6 py-3 text-sm font-medium transition-opacity hover:opacity-90
Feature card:      border-border/70 bg-card rounded-2xl border p-8
Table wrapper:     overflow-x-auto rounded-md border
Secondary text:    text-muted-foreground text-sm     (tertiary: text-xs)
Eyebrow number:    text-brand font-mono text-sm
Numbers/counts:    tabular-nums
Truncation:        truncate  /  line-clamp-2
```


### Container widths


| Context | Width |
| --- | --- |
| Marketing sections / nav / footer | `max-w-5xl` |
| Hero copy | `max-w-3xl` |
| Final CTA | `max-w-2xl` |
| Lead paragraphs | `max-w-xl` |
| Auth card | `max-w-sm` |
| Right detail sheet | `sm:max-w-md` |
| Dialog | `sm:max-w-sm` |


### The "feel" in one paragraph


Cool lavender‑white ground (`bg-background`), slate‑indigo ink, **one** violet
accent (`text-brand`) used sparingly on eyebrow numbers and highlight spans.
Large radii everywhere (`rounded-lg`→`rounded-3xl`, pill badges/CTAs).
Surfaces float on soft `ring-1 ring-foreground/10` instead of hard borders.
Compact controls (`h-8` buttons/inputs, `text-sm` body) but generous page
whitespace (`py-24` marketing sections, `space-y-6` app pages). Marketing screens
sit on `.bg-aurora` with a centered top glow and a sticky frosted pill nav.


---


_Source of truth: `Agent-Reach/linkedin/frontend` (`app/globals.css`,
`app/layout.tsx`, `app/providers.tsx`, `app/page.tsx`, `components/ui/*`,
`components/marketing/*`, `components/{auth,dashboard,search,results,lists}/*`).
Re‑verify token values and cva strings against those files if anything looks off._




