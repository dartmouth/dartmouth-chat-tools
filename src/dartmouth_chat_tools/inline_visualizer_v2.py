"""
title: Inline Visualizer v2
author: Classic298
version: 2.1.1-dc
required_open_webui_version: 0.9.2
description: Renders interactive HTML/SVG visualizations inline in chat. Requires "iframe Sandbox Allow Same Origin" to be enabled in Open WebUI Settings -> Interface. Call get_visualization_skill() first to load the design-system instructions, then render_visualization() to mount the iframe.
original source: https://github.com/Classic298/open-webui-plugins
"""

import re
from typing import Literal

# Build marker embedded into the rendered iframe so the running
# version can be verified at runtime (search DevTools for
# `data-iv-build` on <html>).  Bump on every protocol-level change
# so stale cached iframes can be spotted immediately.
_IV_BUILD = "2.1.1-dc"

from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Injected CSS — Theme variables (light default, dark via data-theme)
# ---------------------------------------------------------------------------

THEME_CSS = """
:root {
  --color-text-primary: #1F2937;
  --color-text-secondary: #6B7280;
  --color-text-tertiary: #9CA3AF;
  --color-text-info: #267aba;
  --color-text-success: #00693e;
  --color-text-warning: #854F0B;
  --color-text-danger: #9d162e;
  --color-bg-primary: #FFFFFF;
  --color-bg-secondary: #f7f7f7;
  --color-bg-tertiary: #e2e2e2;
  --color-border-tertiary: rgba(0,0,0,0.15);
  --color-border-secondary: rgba(0,0,0,0.3);
  --color-border-primary: rgba(0,0,0,0.4);
  --font-sans: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', Menlo, Consolas, monospace;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  /* --- Color ramp variables (light) — Dartmouth tertiary palette --- */
  /* purple slot → Dartmouth Green (primary brand) */
  --ramp-purple-fill:#e0f0e9; --ramp-purple-stroke:#00693e; --ramp-purple-th:#004d2d; --ramp-purple-ts:#00693e;
  /* teal slot → River Blue */
  --ramp-teal-fill:#daedf8;   --ramp-teal-stroke:#267aba;   --ramp-teal-th:#003c73;   --ramp-teal-ts:#267aba;
  /* coral slot → Bonfire Orange */
  --ramp-coral-fill:#fff0d4;  --ramp-coral-stroke:#c77800;  --ramp-coral-th:#7a4a00;  --ramp-coral-ts:#c77800;
  /* pink slot → Bonfire Red */
  --ramp-pink-fill:#f7dfe3;   --ramp-pink-stroke:#9d162e;   --ramp-pink-th:#6e0f20;   --ramp-pink-ts:#9d162e;
  /* gray slot → Granite Gray */
  --ramp-gray-fill:#ebebeb;   --ramp-gray-stroke:#424141;   --ramp-gray-th:#2a2a2a;   --ramp-gray-ts:#424141;
  /* blue slot → River Navy */
  --ramp-blue-fill:#d9e5f0;   --ramp-blue-stroke:#003c73;   --ramp-blue-th:#002550;   --ramp-blue-ts:#003c73;
  /* green slot → Rich Spring Green */
  --ramp-green-fill:#eef6da;  --ramp-green-stroke:#6a9c2a;  --ramp-green-th:#3d5c14;  --ramp-green-ts:#6a9c2a;
  /* amber slot → Summer Yellow */
  --ramp-amber-fill:#fdf6d0;  --ramp-amber-stroke:#a08a00;  --ramp-amber-th:#5e5000;  --ramp-amber-ts:#a08a00;
  /* red slot → Tuck Orange */
  --ramp-red-fill:#fce8e2;    --ramp-red-stroke:#d94415;    --ramp-red-th:#a02e0c;    --ramp-red-ts:#d94415;
  /* --- Common aliases (catch hallucinated variable names) --- */
  /* Text */
  --fg: var(--color-text-primary);
  --text: var(--color-text-primary);
  --foreground: var(--color-text-primary);
  --text-primary: var(--color-text-primary);
  --text-color: var(--color-text-primary);
  --color-text: var(--color-text-primary);
  --color-foreground: var(--color-text-primary);
  --body-color: var(--color-text-primary);
  --muted: var(--color-text-secondary);
  --muted-foreground: var(--color-text-secondary);
  --text-muted: var(--color-text-secondary);
  --text-secondary: var(--color-text-secondary);
  --secondary: var(--color-text-secondary);
  --subtle: var(--color-text-tertiary);
  --text-tertiary: var(--color-text-tertiary);
  /* Backgrounds */
  --bg: var(--color-bg-primary);
  --background: var(--color-bg-primary);
  --bg-primary: var(--color-bg-primary);
  --body-bg: var(--color-bg-primary);
  --color-bg: var(--color-bg-primary);
  --surface: var(--color-bg-secondary);
  --surface-1: var(--color-bg-secondary);
  --surface-2: var(--color-bg-tertiary);
  --card: var(--color-bg-secondary);
  --card-bg: var(--color-bg-secondary);
  --card-foreground: var(--color-text-primary);
  --card-background: var(--color-bg-secondary);
  --popover: var(--color-bg-secondary);
  --popover-foreground: var(--color-text-primary);
  --hover: rgba(0,0,0,0.04);
  /* Borders */
  --border: var(--color-border-tertiary);
  --border-color: var(--color-border-tertiary);
  --divider: var(--color-border-tertiary);
  --separator: var(--color-border-tertiary);
  --input: var(--color-border-tertiary);
  --ring: var(--color-border-secondary);
  /* Accent / Primary — Dartmouth Green */
  --primary: #00693e;
  --primary-foreground: #ffffff;
  --accent: #00693e;
  --accent-foreground: #ffffff;
  /* Themed select chevron (light) — used by the pre-styled <select> */
  --select-arrow: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M3 4.5l3 3 3-3' fill='none' stroke='%236B7280' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}
:root[data-theme="dark"] {
  --color-text-primary: #E5E7EB;
  --color-text-secondary: #9CA3AF;
  --color-text-tertiary: #6B7280;
  --color-text-info: #5DCAA5;
  --color-text-success: #a5d75f;
  --color-text-warning: #f5dc69;
  --color-text-danger: #F87171;
  --color-bg-primary: #0D1E1C;
  --color-bg-secondary: #12312b;
  --color-bg-tertiary: #0a1513;
  --color-border-tertiary: rgba(255,255,255,0.12);
  --color-border-secondary: rgba(255,255,255,0.25);
  --color-border-primary: rgba(255,255,255,0.38);
  /* --- Color ramp variables (dark) — Dartmouth palette on deep green bg --- */
  /* purple slot → Dartmouth Green (lightened for dark bg) */
  --ramp-purple-fill:#003d24; --ramp-purple-stroke:#5DCAA5; --ramp-purple-th:#9FE1CB; --ramp-purple-ts:#5DCAA5;
  /* teal slot → River Blue (lightened) */
  --ramp-teal-fill:#002a52;   --ramp-teal-stroke:#85B7EB;   --ramp-teal-th:#B5D4F4;   --ramp-teal-ts:#85B7EB;
  /* coral slot → Bonfire Orange (lightened) */
  --ramp-coral-fill:#4a2e00;  --ramp-coral-stroke:#ffa00f;  --ramp-coral-th:#f5dc69;  --ramp-coral-ts:#ffa00f;
  /* pink slot → Bonfire Red (lightened) */
  --ramp-pink-fill:#4a0a15;   --ramp-pink-stroke:#e87b8e;   --ramp-pink-th:#f4b8c3;   --ramp-pink-ts:#e87b8e;
  /* gray slot → Granite Gray (lightened) */
  --ramp-gray-fill:#2a2a2a;   --ramp-gray-stroke:#B4B2A9;   --ramp-gray-th:#D3D1C7;   --ramp-gray-ts:#B4B2A9;
  /* blue slot → River Navy (lightened) */
  --ramp-blue-fill:#001833;   --ramp-blue-stroke:#85B7EB;   --ramp-blue-th:#B5D4F4;   --ramp-blue-ts:#85B7EB;
  /* green slot → Rich Spring Green (lightened) */
  --ramp-green-fill:#1e3a08;  --ramp-green-stroke:#a5d75f;  --ramp-green-th:#c4dd88;  --ramp-green-ts:#a5d75f;
  /* amber slot → Summer Yellow (lightened) */
  --ramp-amber-fill:#3a2e00;  --ramp-amber-stroke:#f5dc69;  --ramp-amber-th:#faeea0;  --ramp-amber-ts:#f5dc69;
  /* red slot → Tuck Orange (lightened) */
  --ramp-red-fill:#3a1508;    --ramp-red-stroke:#f0906a;    --ramp-red-th:#f7bda6;    --ramp-red-ts:#f0906a;
  /* --- Common aliases (dark overrides) --- */
  --text: var(--color-text-primary);
  --foreground: var(--color-text-primary);
  --text-primary: var(--color-text-primary);
  --text-color: var(--color-text-primary);
  --color-text: var(--color-text-primary);
  --body-color: var(--color-text-primary);
  --muted: var(--color-text-secondary);
  --muted-foreground: var(--color-text-secondary);
  --text-muted: var(--color-text-secondary);
  --text-secondary: var(--color-text-secondary);
  --secondary: var(--color-text-secondary);
  --subtle: var(--color-text-tertiary);
  --text-tertiary: var(--color-text-tertiary);
  --bg: var(--color-bg-primary);
  --background: var(--color-bg-primary);
  --bg-primary: var(--color-bg-primary);
  --body-bg: var(--color-bg-primary);
  --color-bg: var(--color-bg-primary);
  --surface: var(--color-bg-secondary);
  --surface-1: var(--color-bg-secondary);
  --surface-2: var(--color-bg-tertiary);
  --card: var(--color-bg-secondary);
  --card-bg: var(--color-bg-secondary);
  --card-foreground: var(--color-text-primary);
  --card-background: var(--color-bg-secondary);
  --popover: var(--color-bg-secondary);
  --popover-foreground: var(--color-text-primary);
  --hover: rgba(255,255,255,0.06);
  --border: var(--color-border-tertiary);
  --border-color: var(--color-border-tertiary);
  --divider: var(--color-border-tertiary);
  --separator: var(--color-border-tertiary);
  --input: var(--color-border-tertiary);
  --ring: var(--color-border-secondary);
  /* Accent / Primary — light green tint on dark Forest Green backgrounds */
  --primary: #5DCAA5;
  --primary-foreground: #0D1E1C;
  --accent: #5DCAA5;
  --accent-foreground: #0D1E1C;
  --select-arrow: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'><path d='M3 4.5l3 3 3-3' fill='none' stroke='%239CA3AF' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}

/* --- Named accent palette ---
 * Apply data-accent="<name>" on <html> for global, on any element
 * for local override. The variants reuse the existing color-ramp
 * stroke colors so charts and forms share visual vocabulary
 * (teal here = teal in a chart). Each variant works in both
 * light and dark themes — --accent picks up the ramp's per-theme
 * stroke automatically; --accent-foreground flips dark in dark
 * mode so text stays legible on pastel accents.
 */
[data-accent="purple"] { --accent: var(--ramp-purple-stroke); --accent-foreground: #ffffff; }
[data-accent="teal"]   { --accent: var(--ramp-teal-stroke);   --accent-foreground: #ffffff; }
[data-accent="coral"]  { --accent: var(--ramp-coral-stroke);  --accent-foreground: #ffffff; }
[data-accent="pink"]   { --accent: var(--ramp-pink-stroke);   --accent-foreground: #ffffff; }
[data-accent="gray"]   { --accent: var(--ramp-gray-stroke);   --accent-foreground: #ffffff; }
[data-accent="blue"]   { --accent: var(--ramp-blue-stroke);   --accent-foreground: #ffffff; }
[data-accent="green"]  { --accent: var(--ramp-green-stroke);  --accent-foreground: #ffffff; }
[data-accent="amber"]  { --accent: var(--ramp-amber-stroke);  --accent-foreground: #ffffff; }
[data-accent="red"]    { --accent: var(--ramp-red-stroke);    --accent-foreground: #ffffff; }

[data-theme="dark"] [data-accent],
[data-theme="dark"][data-accent] {
  --accent-foreground: #0D1E1C;
}
"""

# ---------------------------------------------------------------------------
# Injected CSS — SVG utility classes + color ramp selectors
# ---------------------------------------------------------------------------

SVG_CLASSES = """
/* --- Text --- */
.t  { font: 400 14px/1.4 var(--font-sans); fill: var(--color-text-primary); }
.ts { font: 400 12px/1.4 var(--font-sans); fill: var(--color-text-secondary); }
.th { font: 500 14px/1.4 var(--font-sans); fill: var(--color-text-primary); }

/* --- Shapes --- */
.box    { fill: var(--color-bg-secondary); stroke: var(--color-border-tertiary); stroke-width: 0.5; }
.node   { cursor: pointer; }
.node:hover { opacity: 0.85; }
.arr    { stroke: var(--color-border-secondary); stroke-width: 1.5; fill: none; }
.leader { stroke: var(--color-text-tertiary); stroke-width: 0.5; stroke-dasharray: 3 2; fill: none; }

/* --- Color ramp selectors (fill/stroke adapt via CSS vars) --- */
.c-purple>rect,.c-purple>circle,.c-purple>ellipse{fill:var(--ramp-purple-fill);stroke:var(--ramp-purple-stroke);stroke-width:.5}
.c-purple>.th{fill:var(--ramp-purple-th)!important} .c-purple>.ts{fill:var(--ramp-purple-ts)!important}
.c-teal>rect,.c-teal>circle,.c-teal>ellipse{fill:var(--ramp-teal-fill);stroke:var(--ramp-teal-stroke);stroke-width:.5}
.c-teal>.th{fill:var(--ramp-teal-th)!important} .c-teal>.ts{fill:var(--ramp-teal-ts)!important}
.c-coral>rect,.c-coral>circle,.c-coral>ellipse{fill:var(--ramp-coral-fill);stroke:var(--ramp-coral-stroke);stroke-width:.5}
.c-coral>.th{fill:var(--ramp-coral-th)!important} .c-coral>.ts{fill:var(--ramp-coral-ts)!important}
.c-pink>rect,.c-pink>circle,.c-pink>ellipse{fill:var(--ramp-pink-fill);stroke:var(--ramp-pink-stroke);stroke-width:.5}
.c-pink>.th{fill:var(--ramp-pink-th)!important} .c-pink>.ts{fill:var(--ramp-pink-ts)!important}
.c-gray>rect,.c-gray>circle,.c-gray>ellipse{fill:var(--ramp-gray-fill);stroke:var(--ramp-gray-stroke);stroke-width:.5}
.c-gray>.th{fill:var(--ramp-gray-th)!important} .c-gray>.ts{fill:var(--ramp-gray-ts)!important}
.c-blue>rect,.c-blue>circle,.c-blue>ellipse{fill:var(--ramp-blue-fill);stroke:var(--ramp-blue-stroke);stroke-width:.5}
.c-blue>.th{fill:var(--ramp-blue-th)!important} .c-blue>.ts{fill:var(--ramp-blue-ts)!important}
.c-green>rect,.c-green>circle,.c-green>ellipse{fill:var(--ramp-green-fill);stroke:var(--ramp-green-stroke);stroke-width:.5}
.c-green>.th{fill:var(--ramp-green-th)!important} .c-green>.ts{fill:var(--ramp-green-ts)!important}
.c-amber>rect,.c-amber>circle,.c-amber>ellipse{fill:var(--ramp-amber-fill);stroke:var(--ramp-amber-stroke);stroke-width:.5}
.c-amber>.th{fill:var(--ramp-amber-th)!important} .c-amber>.ts{fill:var(--ramp-amber-ts)!important}
.c-red>rect,.c-red>circle,.c-red>ellipse{fill:var(--ramp-red-fill);stroke:var(--ramp-red-stroke);stroke-width:.5}
.c-red>.th{fill:var(--ramp-red-th)!important} .c-red>.ts{fill:var(--ramp-red-ts)!important}
"""

# ---------------------------------------------------------------------------
# Injected CSS — Base resets & interactive element styles
# ---------------------------------------------------------------------------

BASE_STYLES = """
* { box-sizing: border-box; margin: 0; font-family: var(--font-sans); }
html, body { overflow: hidden; }
body { background: transparent; color: var(--color-text-primary); line-height: 1.5; padding: 8px; }
svg { overflow: visible; }
svg text { fill: var(--color-text-primary); }
h1 { font-size: 22px; font-weight: 500; color: var(--color-text-primary); margin-bottom: 12px; }
h2 { font-size: 18px; font-weight: 500; color: var(--color-text-primary); margin-bottom: 8px; }
h3 { font-size: 16px; font-weight: 500; color: var(--color-text-primary); margin-bottom: 6px; }
p  { font-size: 14px; color: var(--color-text-secondary); margin-bottom: 8px; }
/* --- Pre-styled form elements ---
 * Each rule is gated with :not([class]):not([style]) so the model
 * opts in by emitting bare HTML. Adding either attribute is treated
 * as opting out — the default suppresses and the model styles from
 * scratch. Keeps token cost low for vanilla cases without locking
 * the design space.
 */
button:not([class]):not([style]) {
  background: transparent; border: 0.5px solid var(--color-border-secondary);
  border-radius: var(--radius-md); padding: 6px 14px; font-size: 13px;
  color: var(--color-text-primary); cursor: pointer; font-family: var(--font-sans);
}
button:not([class]):not([style]):hover { background: var(--color-bg-secondary); }

input[type="text"]:not([class]):not([style]),
input[type="number"]:not([class]):not([style]),
input[type="email"]:not([class]):not([style]),
input[type="search"]:not([class]):not([style]),
input[type="password"]:not([class]):not([style]),
input[type="tel"]:not([class]):not([style]),
input[type="url"]:not([class]):not([style]),
input[type="date"]:not([class]):not([style]),
input[type="time"]:not([class]):not([style]),
input[type="datetime-local"]:not([class]):not([style]) {
  background: var(--color-bg-primary);
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md); padding: 6px 10px; font-size: 13px;
  color: var(--color-text-primary); font-family: var(--font-sans);
  outline: none; transition: border-color 0.15s ease;
}
input[type="text"]:not([class]):not([style]):focus,
input[type="number"]:not([class]):not([style]):focus,
input[type="email"]:not([class]):not([style]):focus,
input[type="search"]:not([class]):not([style]):focus,
input[type="password"]:not([class]):not([style]):focus,
input[type="tel"]:not([class]):not([style]):focus,
input[type="url"]:not([class]):not([style]):focus,
input[type="date"]:not([class]):not([style]):focus,
input[type="time"]:not([class]):not([style]):focus,
input[type="datetime-local"]:not([class]):not([style]):focus {
  border-color: var(--color-border-primary);
}

/* Drop the type=number spinner — clashes with the field's borders. */
input[type="number"]:not([class]):not([style]) {
  -moz-appearance: textfield; appearance: textfield;
}
input[type="number"]:not([class]):not([style])::-webkit-outer-spin-button,
input[type="number"]:not([class]):not([style])::-webkit-inner-spin-button {
  -webkit-appearance: none; margin: 0;
}

textarea:not([class]) {
  background: var(--color-bg-primary);
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md); padding: 8px 10px; font-size: 13px;
  color: var(--color-text-primary); font-family: var(--font-sans);
  outline: none; resize: vertical; min-height: 60px;
  transition: border-color 0.15s ease;
}
textarea:not([class]):focus { border-color: var(--color-border-primary); }

/* accent-color always applies, regardless of class/style — it's a
 * tint property the model is highly unlikely to set themselves, and
 * letting it ride keeps palette switches consistent even when the
 * model adds inline width/max-width styling to the slider. */
input[type="range"], input[type="checkbox"], input[type="radio"] {
  accent-color: var(--accent);
}
input[type="range"]:not([class]):not([style]) { width: 100%; }

input[type="checkbox"]:not([class]):not([style]),
input[type="radio"]:not([class]):not([style]) {
  /* accent-color comes from the always-on rule above. */
  cursor: pointer;
}

select:not([class]):not([style]) {
  appearance: none; -webkit-appearance: none; -moz-appearance: none;
  background-color: var(--color-bg-secondary);
  background-image: var(--select-arrow);
  background-repeat: no-repeat;
  background-position: right 10px center;
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md); padding: 6px 28px 6px 10px;
  font-size: 13px; color: var(--color-text-primary); font-family: var(--font-sans);
  outline: none; cursor: pointer;
}
select:not([class]):not([style]):focus { border-color: var(--color-border-primary); }

label:not([class]):not([style]) {
  font-size: 13px; color: var(--color-text-primary); cursor: pointer;
}
fieldset:not([class]):not([style]) {
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md); padding: 12px;
}
legend:not([class]):not([style]) {
  font-size: 12px; color: var(--color-text-secondary); padding: 0 6px;
}

/* Validation error border — standard a11y attribute, no class needed. */
input[aria-invalid="true"]:not([class]):not([style]),
textarea[aria-invalid="true"]:not([class]),
select[aria-invalid="true"]:not([class]):not([style]) {
  border-color: var(--color-text-danger);
}

/* Keyboard-only focus rings (accent outline). Mouse focus stays subtle. */
button:not([class]):not([style]):focus-visible,
input:not([class]):not([style]):focus-visible,
textarea:not([class]):focus-visible,
select:not([class]):not([style]):focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

code {
  font-family: var(--font-mono); font-size: 13px; background: var(--color-bg-tertiary);
  padding: 2px 6px; border-radius: 4px;
}

/* <kbd> — keyboard-key pill (cmd/ctrl/k style). */
kbd:not([class]):not([style]) {
  font-family: var(--font-mono); font-size: 12px;
  background: var(--color-bg-secondary);
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: 4px; padding: 1px 6px;
  color: var(--color-text-primary);
}

/* <hr> — flat divider matching the rest of the borders. */
hr:not([class]):not([style]) {
  border: none;
  border-top: 0.5px solid var(--color-border-tertiary);
  margin: 1.5rem 0;
}

/* <details> / <summary> — themed disclosure with a bigger chevron.
 * Container is an invisible rounded "wrapper" — the visible card-
 * shape is the summary header itself. This way if a model adds its
 * own summary background/border, the result is still single-card,
 * not nested. Chevron is sized to be clearly visible. */
details:not([class]):not([style]) {
  margin: 12px 0;
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md);
  overflow: hidden;
}
details:not([class]):not([style]) > summary {
  cursor: pointer; list-style: none; user-select: none;
  font-weight: 500; color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  padding: 10px 14px 10px 34px;
  position: relative;
  transition: background-color 0.15s ease;
}
details:not([class]):not([style]) > summary:hover {
  background: var(--color-bg-tertiary);
}
details:not([class]):not([style]) > summary::-webkit-details-marker { display: none; }
details:not([class]):not([style]) > summary::marker { content: ''; }
details:not([class]):not([style]) > summary::before {
  content: '\\25B8'; /* ▸ */
  position: absolute; left: 12px; top: 50%;
  transform: translateY(-50%);
  transition: transform 0.15s ease;
  color: var(--color-text-secondary);
  font-size: 18px;
  line-height: 1;
}
details[open]:not([class]):not([style]) > summary::before {
  transform: translateY(-50%) rotate(90deg);
}
details[open]:not([class]):not([style]) > summary {
  border-bottom: 0.5px solid var(--color-border-tertiary);
}
/* Margin (not padding) so children with their own bg inset properly. */
details:not([class]):not([style]) > *:not(summary) {
  margin: 12px 14px;
}

blockquote:not([class]):not([style]) {
  border-left: 4px solid var(--accent);
  background: var(--color-bg-secondary);
  padding: 12px 18px;
  margin: 16px 0;
  color: var(--color-text-secondary);
  border-radius: var(--radius-md);
}
blockquote:not([class]):not([style]) > :last-child { margin-bottom: 0; }
blockquote:not([class]):not([style]) > :first-child { margin-top: 0; }

/* <table> — flat data table, theme-matched borders, header pill,
 * row hover, last-row borderless, no zebra (kept calm). For numeric
 * columns, add align="right" or class="num" to <th>/<td>. */
table:not([class]):not([style]) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 13px;
  color: var(--color-text-primary);
  font-family: var(--font-sans);
}
table:not([class]):not([style]) caption {
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  padding: 0 0 8px;
  caption-side: top;
}
table:not([class]):not([style]) th {
  text-align: left;
  padding: 8px 12px;
  /* Reset all sides so a model's `border:` shorthand can't leak through. */
  border: none;
  border-bottom: 0.5px solid var(--color-border-secondary);
  font-weight: 500;
  font-size: 11px;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--color-bg-secondary);
  white-space: nowrap;
}
table:not([class]):not([style]) td {
  padding: 10px 12px;
  border: none;
  border-bottom: 0.5px solid var(--color-border-tertiary);
  vertical-align: top;
}
table:not([class]):not([style]) tr:last-child > td {
  border-bottom: none;
}
table:not([class]):not([style]) tbody tr {
  transition: background-color 0.1s ease;
}
table:not([class]):not([style]) tbody tr:hover {
  background: var(--color-bg-secondary);
}
/* Numeric columns: opt-in via align="right" or class="num" on cells. */
table:not([class]):not([style]) td[align="right"],
table:not([class]):not([style]) th[align="right"],
table:not([class]):not([style]) td.num,
table:not([class]):not([style]) th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

mark:not([class]):not([style]) {
  background: var(--ramp-amber-fill);
  color: var(--ramp-amber-th);
  padding: 0 4px;
  border-radius: 3px;
}

/* <dl> three modes — default stacked, data-layout="grid", data-layout="inline".
 * data-layout is the explicit opt-in, so [data-layout] rules skip the class/style gate. */
dl:not([class]):not([style]) { margin: 12px 0; }
dl:not([class]):not([style]) > dt {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 14px;
  margin-top: 12px;
}
dl:not([class]):not([style]) > dt:first-child { margin-top: 0; }
dl:not([class]):not([style]) > dd {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary);
}

/* `display: contents` on the optional wrapping div + dual selectors below
 * tolerates both flat <dt><dd>… and <div><dt><dd></div>… markup. */
dl[data-layout="grid"] {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 8px 16px;
  align-items: baseline;
  padding: 12px 16px;
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: var(--radius-md);
  background: var(--color-bg-secondary);
  margin: 12px 0;
}
dl[data-layout="grid"] > div { display: contents; }
dl[data-layout="grid"] > dt,
dl[data-layout="grid"] > div > dt {
  font-weight: 400;
  color: var(--color-text-secondary);
  font-size: 13px;
  margin: 0;
}
dl[data-layout="grid"] > dd,
dl[data-layout="grid"] > div > dd {
  margin: 0;
  text-align: right;
  color: var(--color-text-primary);
  font-weight: 500;
  font-size: 13px;
}

/* data-layout="inline" — pill row. Each <dt>/<dd> pair wrapped in <div>.
 * Same opt-in-via-attribute logic as grid above — no :not() gate. */
dl[data-layout="inline"] {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0;
}
dl[data-layout="inline"] > div {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  padding: 4px 10px;
  border: 0.5px solid var(--color-border-tertiary);
  border-radius: 999px;
  font-size: 12px;
  background: var(--color-bg-secondary);
}
dl[data-layout="inline"] > div > dt {
  margin: 0;
  font-weight: 400;
  color: var(--color-text-secondary);
  font-size: 12px;
}
dl[data-layout="inline"] > div > dt::after {
  content: ":";
  margin-right: 2px;
}
dl[data-layout="inline"] > div > dd {
  margin: 0;
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 12px;
}

#iv-dl-wrap{position:fixed;top:4px;right:4px;z-index:9999}
#iv-dl-btn{width:26px;height:26px;padding:0;display:flex;align-items:center;justify-content:center;
  opacity:0.3;border-color:var(--color-border-tertiary);background:var(--color-bg-primary)}
#iv-dl-btn:hover{opacity:0.9;background:var(--color-bg-secondary)}
#iv-dl-btn svg{width:14px;height:14px;stroke:var(--color-text-secondary);fill:none;
  stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
/* --- Print ---
 * overflow:hidden on html/body clips content in print (needed on screen
 * for iframe sizing). Chart.js canvas scaling is handled by JS beforeprint
 * handler in BODY_SCRIPTS — it directly mutates inline styles that CSS
 * cannot reliably override in Chrome's print engine.
 */
@media print {
  @page { margin: 12mm; }
  html, body { overflow: visible !important; height: auto !important;
    background: #fff !important; }
  body { padding: 4px !important; }
  #iv-dl-wrap { display: none !important; }
  * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""

# ---------------------------------------------------------------------------
# Injected JavaScript — theme detection (head), height reporting & bridges (body)
# ---------------------------------------------------------------------------
# Theme script runs in <head> before user content so CSS vars are resolved
# when model scripts read them at parse time.
#
# !! SRCDOC SAFETY !!  Do NOT write the literal tokens <!-- , --> ,
# <![CDATA[ , ]]> , <script> or </script> ANYWHERE in this body —
# not even inside JS comments. The iframe srcdoc's HTML5 tokenizer
# treats them as parser state changes regardless of JS context, and
# silently breaks the IIFE (see _assert_srcdoc_safe near the bottom
# of this file for the runtime guard).
THEME_DETECTION_SCRIPT = """
<script>
(function() {
  function detectTheme(root) {
    return root.classList.contains('dark')
      || root.getAttribute('data-theme') === 'dark'
      || getComputedStyle(root).colorScheme === 'dark';
  }

  function applyTheme(isDark) {
    var theme = isDark ? 'dark' : 'light';
    if (document.documentElement.getAttribute('data-theme') === theme) return;
    document.documentElement.setAttribute('data-theme', theme);
    if (window.Chart && Chart.instances) {
      var s = getComputedStyle(document.documentElement);
      var tc = s.getPropertyValue('--color-text-secondary').trim();
      var gc = s.getPropertyValue('--color-border-tertiary').trim();
      Chart.defaults.color = tc;
      Chart.defaults.borderColor = gc;
      Object.values(Chart.instances).forEach(function(chart) {
        Object.values(chart.options.scales || {}).forEach(function(scale) {
          if (scale.ticks) scale.ticks.color = tc;
          if (scale.grid) scale.grid.color = gc;
        });
        var leg = (chart.options.plugins || {}).legend;
        if (leg && leg.labels) leg.labels.color = tc;
        chart.update();
      });
    }
  }

  try {
    var p = parent.document.documentElement;
    applyTheme(detectTheme(p));
    new MutationObserver(function() {
      applyTheme(detectTheme(p));
    }).observe(p, { attributes: true, attributeFilter: ['class', 'data-theme', 'style'] });
  } catch(e) {
    // No same-origin access — fall back to OS preference.
    var mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    if (mq) {
      applyTheme(mq.matches);
      mq.addEventListener('change', function(e) { applyTheme(e.matches); });
    }
  }
})();
</script>
"""

# !! SRCDOC SAFETY !!  Do NOT write the literal tokens <!-- , --> ,
# <![CDATA[ , ]]> , <script> or </script> ANYWHERE in this body —
# not even inside JS comments. See THEME_DETECTION_SCRIPT for full rationale.
BODY_SCRIPTS = """
<script>
// --- Height reporting ---
var _rh_last = 0;          // last reported height
var _rh_consecutive = 0;   // consecutive small-growth reports
var _rh_raf = 0;           // rAF id for debouncing ResizeObserver

function reportHeight() {
  var b = document.body;
  // Measure SVG overflow before the body collapse below — getBBox
  // needs normal layout.
  var svgOverflow = 0;
  document.querySelectorAll('svg[viewBox]').forEach(function(svg) {
    try {
      var bbox = svg.getBBox();
      var vb = svg.viewBox.baseVal;
      if (vb && vb.width > 0 && vb.height > 0) {
        var overflow = bbox.y + bbox.height - (vb.y + vb.height);
        if (overflow > 0) {
          var scale = svg.getBoundingClientRect().width / vb.width;
          svgOverflow += Math.ceil(overflow * scale);
        }
      }
    } catch(e) {}
  });

  // Force height:auto on body + direct children — vh in an auto-sized
  // iframe tracks iframe height, creating a feedback loop.
  var savedBody = b.style.cssText;
  b.style.setProperty('height', 'auto', 'important');
  b.style.setProperty('overflow', 'visible', 'important');
  b.style.setProperty('display', 'block', 'important');
  var saved = [];
  Array.from(b.children).forEach(function(el) {
    if (el.nodeType !== 1) return;
    saved.push({ el: el, css: el.style.cssText });
    el.style.setProperty('height', 'auto', 'important');
    el.style.setProperty('max-height', 'none', 'important');
    el.style.setProperty('min-height', '0', 'important');
    el.style.setProperty('overflow', 'visible', 'important');
  });

  // Collapse any descendant with viewport-unit dimensions — 100vh
  // resolves to our own reported height, so leaving it intact
  // creates a feedback loop where body grows each cycle.
  var savedVh = [];
  try {
    var vhUsers = b.querySelectorAll(
      '[style*="vh"], [style*="vw"], [style*="vmin"], [style*="vmax"]'
    );
    for (var k = 0; k < vhUsers.length; k++) {
      var ve = vhUsers[k];
      savedVh.push({ el: ve, css: ve.style.cssText });
      ve.style.setProperty('min-height', '0', 'important');
      ve.style.setProperty('max-height', 'none', 'important');
      ve.style.setProperty('height', 'auto', 'important');
    }
  } catch(e) {}

  // Collapse <canvas> elements during measurement — models often set
  // canvas.width/height = window.innerWidth/innerHeight in JS. This
  // bypasses CSS vh-unit detection above, but still causes the same
  // feedback loop: iframe height grows → window.innerHeight grows →
  // canvas grows → body.scrollHeight grows → repeat. Temporarily
  // override the canvas dimensions so scrollHeight reflects only the
  // surrounding layout, not the canvas pixel size itself.
  var savedCanvas = [];
  try {
    var canvases = b.querySelectorAll('canvas');
    for (var ci = 0; ci < canvases.length; ci++) {
      var cv = canvases[ci];
      savedCanvas.push({ el: cv, style: cv.style.cssText });
      cv.style.setProperty('height', 'auto', 'important');
      cv.style.setProperty('max-height', 'none', 'important');
      cv.style.setProperty('min-height', '0', 'important');
    }
  } catch(e) {}

  var h = b.scrollHeight + svgOverflow;
  b.style.cssText = savedBody;
  saved.forEach(function(s) { s.el.style.cssText = s.css; });
  for (var v = 0; v < savedVh.length; v++) {
    savedVh[v].el.style.cssText = savedVh[v].css;
  }
  for (var cc = 0; cc < savedCanvas.length; cc++) {
    savedCanvas[cc].el.style.cssText = savedCanvas[cc].style;
  }

  // Hard cap: never report more than 1.5× the physical screen height.
  // This is a last-resort guard against runaway canvas/vh feedback
  // loops where the model's JS reads window.innerHeight and sets it
  // as the canvas height, inflating body.scrollHeight indefinitely.
  var maxH = window.screen && window.screen.height ? window.screen.height * 1.5 : 4000;
  if (h > maxH) h = maxH;

  // Loop guard: 3+ consecutive small monotonic increases → stop.
  var delta = h - _rh_last;
  if (_rh_last > 0 && delta > 0 && delta < 50) {
    _rh_consecutive++;
    if (_rh_consecutive >= 3) return;
  } else {
    _rh_consecutive = 0;
  }

  _rh_last = h;
  parent.postMessage({ type: 'iframe:height', height: h }, '*');
}
window.addEventListener('load', reportHeight);
window.addEventListener('resize', reportHeight);
// rAF-debounced ResizeObserver avoids tight synchronous loops.
new ResizeObserver(function() {
  cancelAnimationFrame(_rh_raf);
  _rh_raf = requestAnimationFrame(reportHeight);
}).observe(document.body);
// <details> toggle — ResizeObserver misses this in some browsers.
document.addEventListener('toggle', function() {
  _rh_consecutive = 0;
  setTimeout(reportHeight, 50);
}, true);
// Dynamic content swaps (innerHTML assignments, SPA-style updates).
var _rh_mutRaf = 0;
new MutationObserver(function() {
  _rh_consecutive = 0;
  cancelAnimationFrame(_rh_mutRaf);
  _rh_mutRaf = requestAnimationFrame(reportHeight);
}).observe(document.body, { childList: true, subtree: true });
// Click covers custom expand/collapse via style.display / class swaps.
document.addEventListener('click', function() {
  _rh_consecutive = 0;
  cancelAnimationFrame(_rh_mutRaf);
  _rh_mutRaf = requestAnimationFrame(reportHeight);
}, true);

// --- Post-render fixes (theme defaults, overlap prevention) ---
window.addEventListener('load', function() {
  // Chart.js theme defaults + legend overflow prevention
  if (window.Chart) {
    var s = getComputedStyle(document.documentElement);
    var textColor = s.getPropertyValue('--color-text-secondary').trim();
    var gridColor = s.getPropertyValue('--color-border-tertiary').trim();
    Chart.defaults.color = textColor;
    Chart.defaults.borderColor = gridColor;
    Chart.defaults.plugins.legend.labels.color = textColor;
    Chart.defaults.plugins.legend.maxHeight = 120;
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.legend.labels.font = { size: 11 };
    Object.values(Chart.instances || {}).forEach(function(chart) {
      var leg = chart.options.plugins && chart.options.plugins.legend;
      if (leg) {
        leg.maxHeight = leg.maxHeight || 120;
        if (leg.labels) {
          leg.labels.boxWidth = leg.labels.boxWidth || 12;
        }
      }
      chart.update();
    });
  }

  // De-overlap SVG axis labels only — add data-no-stagger on a <svg>
  // to opt out.
  document.querySelectorAll('svg').forEach(function(svg) {
    if (svg.hasAttribute('data-no-stagger')) return;
    var texts = Array.from(svg.querySelectorAll('text'));
    if (texts.length < 4) return;
    var items = [];
    texts.forEach(function(t) {
      var r = t.getBoundingClientRect();
      if (r.width < 1) return;
      items.push({ el: t, rect: r, cx: r.left + r.width / 2, cy: r.top + r.height / 2 });
    });
    if (items.length < 4) return;
    // Only touch texts in a narrow y-band (axis labels). Diagrams with
    // texts spread across the canvas are left alone.
    var minY = Infinity, maxY = -Infinity;
    items.forEach(function(it) {
      if (it.cy < minY) minY = it.cy;
      if (it.cy > maxY) maxY = it.cy;
    });
    var ySpan = maxY - minY;
    if (ySpan < 1) return;
    // Pick the densest y-band (likely the axis row).
    var bandSize = 30;
    var bestBand = [], bestCount = 0;
    items.forEach(function(anchor) {
      var band = items.filter(function(it) { return Math.abs(it.cy - anchor.cy) < bandSize; });
      if (band.length > bestCount) { bestCount = band.length; bestBand = band; }
    });
    if (bestBand.length < 3 || bestBand.length === items.length && ySpan > 60) return;
    var groups = [];
    bestBand.forEach(function(it) {
      for (var i = 0; i < groups.length; i++) {
        if (Math.abs(groups[i].cx - it.cx) < 15) {
          groups[i].items.push(it);
          return;
        }
      }
      groups.push({ cx: it.cx, items: [it] });
    });
    if (groups.length < 3) return;
    groups.sort(function(a, b) { return a.cx - b.cx; });
    var needsStagger = false;
    for (var i = 0; i < groups.length - 1; i++) {
      var maxR = 0, minL = Infinity;
      groups[i].items.forEach(function(it) { if (it.rect.right > maxR) maxR = it.rect.right; });
      groups[i+1].items.forEach(function(it) { if (it.rect.left < minL) minL = it.rect.left; });
      if (maxR > minL - 2) { needsStagger = true; break; }
    }
    if (needsStagger) {
      for (var i = 1; i < groups.length; i += 2) {
        groups[i].items.forEach(function(it) {
          var cy = parseFloat(it.el.getAttribute('y') || 0);
          it.el.setAttribute('y', String(cy + 18));
        });
      }
    }
  });

  setTimeout(reportHeight, 100);
});

// --- sendPrompt bridge (requires iframe Sandbox Allow Same Origin) ---
function sendPrompt(text) {
  try {
    // Open WebUI's native prompt-submit postMessage — queues if the
    // model is mid-generation.
    parent.postMessage({ type: 'input:prompt:submit', text: text }, '*');
  } catch(e) { /* iframe sandbox restriction */ }
}

// --- Open link in parent window ---
function openLink(url) {
  try { parent.window.open(url, '_blank'); }
  catch(e) { window.open(url, '_blank'); }
}

// --- navigator.vibrate silencer ---
// Chrome spams `[Intervention] Blocked call to navigator.vibrate…` on
// every call without a prior user gesture. Replace with a no-op so the
// block path never runs.
try {
  if (typeof navigator !== 'undefined' && navigator.vibrate) {
    navigator.vibrate = function() { return false; };
  }
} catch(e) {}

// --- Toast bridge ---
// Floating auto-dismissing top-right banner. kind = success/info/warn/error.
function toast(msg, kind) {
  kind = kind || 'success';
  var color = kind === 'error' ? 'var(--color-text-danger)'
           : kind === 'info'  ? 'var(--color-text-info)'
           : kind === 'warn'  ? 'var(--color-text-warning)'
           : 'var(--color-text-success)';
  var wrap = document.getElementById('iv-toast-wrap');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.id = 'iv-toast-wrap';
    wrap.style.cssText =
      'position:fixed;top:4px;right:38px;z-index:9998;' +
      'display:flex;flex-direction:column;gap:4px;pointer-events:none;' +
      'max-width:280px;';
    document.body.appendChild(wrap);
  }
  var el = document.createElement('div');
  el.style.cssText =
    'padding:6px 12px;border-radius:var(--radius-md);' +
    'background:var(--color-bg-secondary);' +
    'border:0.5px solid var(--color-border-tertiary);' +
    'color:' + color + ';font-size:12px;line-height:1.4;' +
    'font-family:var(--font-sans);font-weight:500;' +
    'opacity:0;transform:translateY(-4px);transition:all 0.2s ease;' +
    'pointer-events:auto;white-space:nowrap;' +
    'overflow:hidden;text-overflow:ellipsis;';
  el.textContent = String(msg == null ? '' : msg);
  wrap.appendChild(el);
  requestAnimationFrame(function() {
    el.style.opacity = '1';
    el.style.transform = 'none';
  });
  setTimeout(function() {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-4px)';
    setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 220);
  }, 2200);
}

// --- copyText bridge ---
// Async Clipboard API with execCommand fallback (Open WebUI's iframe
// sandbox lacks allow-clipboard-write). Toast fires unconditionally —
// execCommand can silently fail and swallowing feedback leaves the user
// confused. silent=true suppresses the toast.
function copyText(text, silent) {
  var s = String(text == null ? '' : text);
  var label = (typeof _ivCopiedStr !== 'undefined' &&
               (_ivCopiedStr[_ivLang] || _ivCopiedStr.en)) || 'Copied';
  function fire() { if (!silent) try { toast(label, 'success'); } catch(e) {} }

  function legacy() {
    try {
      var ta = document.createElement('textarea');
      ta.value = s;
      ta.setAttribute('readonly', '');
      ta.style.cssText =
        'position:fixed;left:-9999px;top:-9999px;opacity:0;';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      try { ta.setSelectionRange(0, s.length); } catch(e) {}
      try { document.execCommand('copy'); } catch(e) {}
      ta.remove();
    } catch(e) {}
    fire();
  }

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(s).then(fire, legacy);
      return;
    }
  } catch(e) {}
  legacy();
}

// --- saveState / loadState bridges ---
// parent.localStorage proxy scoped to the assistant message id — state
// persists across reloads but never leaks between chats / messages.
// Silent no-op if localStorage / parent is unreachable.
function _ivStatePrefix() {
  try {
    var f = window.frameElement;
    var msg = f && f.closest && f.closest('[id^="message-"]');
    return 'iv-state:' + ((msg && msg.id) || 'global') + ':';
  } catch(e) { return 'iv-state:global:'; }
}
function saveState(key, value) {
  try {
    parent.localStorage.setItem(
      _ivStatePrefix() + String(key),
      JSON.stringify(value === undefined ? null : value)
    );
  } catch(e) {}
}
function loadState(key, fallback) {
  try {
    var v = parent.localStorage.getItem(_ivStatePrefix() + String(key));
    if (v == null) return fallback === undefined ? null : fallback;
    return JSON.parse(v);
  } catch(e) { return fallback === undefined ? null : fallback; }
}

/*__CHIME_BLOCK__*/

// --- Print fix for Chart.js canvases ---
// Chart.js writes explicit pixel widths as inline styles that CSS
// max-width can't override in Chrome's print engine. Mutate inline
// styles before print, restore after.
(function() {
  window.addEventListener('beforeprint', function() {
    document.querySelectorAll('canvas').forEach(function(c) {
      c.setAttribute('data-print-style', c.style.cssText);
      c.style.setProperty('width', '100%', 'important');
      c.style.setProperty('max-width', '100%', 'important');
      c.style.setProperty('height', 'auto', 'important');
      var p = c.parentElement;
      if (p) {
        p.setAttribute('data-print-style', p.style.cssText);
        p.style.setProperty('width', '100%', 'important');
        p.style.setProperty('max-width', '100%', 'important');
      }
    });
  });
  window.addEventListener('afterprint', function() {
    document.querySelectorAll('[data-print-style]').forEach(function(el) {
      el.style.cssText = el.getAttribute('data-print-style');
      el.removeAttribute('data-print-style');
    });
  });
})();

// --- Download visualization as self-contained HTML ---
var _ivLang = 'en';
var _ivStr = {
  // Required languages
  en: 'Download as HTML',
  de: 'Als HTML herunterladen',
  cs: 'Stáhnout jako HTML',
  hu: 'Letöltés HTML-ként',
  hr: 'Preuzmi kao HTML',
  pl: 'Pobierz jako HTML',
  fr: 'Télécharger en HTML',
  nl: 'Downloaden als HTML',
  // Western & Southern European
  es: 'Descargar como HTML',
  pt: 'Baixar como HTML',
  it: 'Scarica come HTML',
  ca: 'Baixa com a HTML',
  gl: 'Descargar como HTML',
  eu: 'Deskargatu HTML gisa',
  // Northern European
  da: 'Download som HTML',
  sv: 'Ladda ner som HTML',
  no: 'Last ned som HTML',
  fi: 'Lataa HTML-tiedostona',
  is: 'Hlaða niður sem HTML',
  // Eastern European & Slavic
  sk: 'Stiahnuť ako HTML',
  sl: 'Prenesi kot HTML',
  sr: 'Преузми као HTML',
  bs: 'Preuzmi kao HTML',
  bg: 'Изтегли като HTML',
  mk: 'Преземи како HTML',
  uk: 'Завантажити як HTML',
  ru: 'Скачать как HTML',
  be: 'Спампаваць як HTML',
  // Baltic
  lt: 'Atsisiųsti kaip HTML',
  lv: 'Lejupielādēt kā HTML',
  et: 'Laadi alla HTML-ina',
  // Other European
  ro: 'Descarcă ca HTML',
  el: 'Λήψη ως HTML',
  sq: 'Shkarko si HTML',
  // Middle Eastern
  tr: 'HTML olarak indir',
  ar: 'تحميل كـ HTML',

  he: 'הורד כ-HTML',
  // East & South Asian
  zh: '下载为HTML',
  ja: 'HTMLでダウンロード',
  ko: 'HTML로 다운로드',
  vi: 'Tải xuống dạng HTML',
  th: 'ดาวน์โหลดเป็น HTML',
  id: 'Unduh sebagai HTML',
  ms: 'Muat turun sebagai HTML',
  hi: 'HTML के रूप में डाउनलोड करें',
  bn: 'HTML হিসেবে ডাউনলোড করুন',
  // African
  sw: 'Pakua kama HTML'
};

// Loader label (shown while waiting for the first content chunk).
var _ivLoadStr = {
  en: 'Rendering visualization\u2026',
  de: 'Visualisierung wird erstellt\u2026',
  cs: 'Vykresluje se vizualizace\u2026',
  hu: 'Vizualizáció renderelése\u2026',
  hr: 'Iscrtavanje vizualizacije\u2026',
  pl: 'Renderowanie wizualizacji\u2026',
  fr: 'Rendu de la visualisation\u2026',
  nl: 'Visualisatie renderen\u2026',
  es: 'Renderizando visualización\u2026',
  pt: 'Renderizando visualização\u2026',
  it: 'Rendering della visualizzazione\u2026',
  ca: 'Renderitzant visualització\u2026',
  gl: 'Renderizando visualización\u2026',
  eu: 'Bistaratzea errendatzen\u2026',
  da: 'Gengiver visualisering\u2026',
  sv: 'Renderar visualisering\u2026',
  no: 'Gjengir visualisering\u2026',
  fi: 'Renderöidään visualisointia\u2026',
  is: 'Teiknar sjónræna framsetningu\u2026',
  sk: 'Vykresľuje sa vizualizácia\u2026',
  sl: 'Upodabljanje vizualizacije\u2026',
  sr: 'Исцртавање визуализације\u2026',
  bs: 'Iscrtavanje vizualizacije\u2026',
  bg: 'Изчертаване на визуализацията\u2026',
  mk: 'Исцртување на визуализацијата\u2026',
  uk: 'Відображення візуалізації\u2026',
  ru: 'Отрисовка визуализации\u2026',
  be: 'Адмалёўка візуалізацыі\u2026',
  lt: 'Atvaizduojama vizualizacija\u2026',
  lv: 'Vizualizācijas renderēšana\u2026',
  et: 'Visualiseeringu renderdamine\u2026',
  ro: 'Randare vizualizare\u2026',
  el: 'Απόδοση οπτικοποίησης\u2026',
  sq: 'Duke renderuar vizualizimin\u2026',
  tr: 'Görselleştirme oluşturuluyor\u2026',
  ar: 'جارٍ عرض التصور\u2026',
  he: 'מציג הדמיה\u2026',
  zh: '正在渲染可视化\u2026',
  ja: 'ビジュアライゼーションを描画中\u2026',
  ko: '시각화 렌더링 중\u2026',
  vi: 'Đang kết xuất hình ảnh\u2026',
  th: 'กำลังแสดงผลการแสดงภาพ\u2026',
  id: 'Merender visualisasi\u2026',
  ms: 'Memaparkan visualisasi\u2026',
  hi: 'विज़ुअलाइज़ेशन रेंडर हो रहा है\u2026',
  bn: 'ভিজ্যুয়ালাইজেশন রেন্ডার হচ্ছে\u2026',
  sw: 'Inarendi taswira\u2026'
};

// "Streaming visualization unavailable" title + body, shown only when
// the iframe cannot reach parent.document (Allow Same Origin disabled).
var _ivErrTitleStr = {
  en: 'Streaming visualization unavailable',
  de: 'Streaming-Visualisierung nicht verfügbar',
  cs: 'Streamovaná vizualizace není dostupná',
  hu: 'A streamelt vizualizáció nem érhető el',
  hr: 'Streaming vizualizacija nije dostupna',
  pl: 'Strumieniowa wizualizacja niedostępna',
  fr: 'Visualisation en streaming indisponible',
  nl: 'Streaming visualisatie niet beschikbaar',
  es: 'Visualización en streaming no disponible',
  pt: 'Visualização em streaming indisponível',
  it: 'Visualizzazione in streaming non disponibile',
  ca: 'Visualització en streaming no disponible',
  gl: 'Visualización en streaming non dispoñíbel',
  eu: 'Streaming bistaratzea ez dago erabilgarri',
  da: 'Streaming-visualisering utilgængelig',
  sv: 'Strömmande visualisering otillgänglig',
  no: 'Streaming-visualisering utilgjengelig',
  fi: 'Suoratoistettu visualisointi ei käytettävissä',
  is: 'Streymandi sjónræn framsetning ekki tiltæk',
  sk: 'Streamovaná vizualizácia nie je dostupná',
  sl: 'Pretočna vizualizacija ni na voljo',
  sr: 'Стриминг визуализација није доступна',
  bs: 'Streaming vizualizacija nije dostupna',
  bg: 'Поточната визуализация е недостъпна',
  mk: 'Стриминг визуализација недостапна',
  uk: 'Потокова візуалізація недоступна',
  ru: 'Потоковая визуализация недоступна',
  be: 'Струменевая візуалізацыя недаступная',
  lt: 'Srautinė vizualizacija nepasiekiama',
  lv: 'Straumētā vizualizācija nav pieejama',
  et: 'Voogedastuse visualiseering pole saadaval',
  ro: 'Vizualizarea în streaming indisponibilă',
  el: 'Η ροή οπτικοποίησης δεν είναι διαθέσιμη',
  sq: 'Vizualizimi i transmetimit i padisponueshëm',
  tr: 'Akış görselleştirmesi kullanılamıyor',
  ar: 'التصور المتدفق غير متاح',
  he: 'הדמיה בסטרימינג אינה זמינה',
  zh: '流式可视化不可用',
  ja: 'ストリーミングビジュアライゼーションは利用できません',
  ko: '스트리밍 시각화를 사용할 수 없습니다',
  vi: 'Hình ảnh trực quan phát trực tuyến không khả dụng',
  th: 'การแสดงผลแบบสตรีมไม่พร้อมใช้งาน',
  id: 'Visualisasi streaming tidak tersedia',
  ms: 'Visualisasi strim tidak tersedia',
  hi: 'स्ट्रीमिंग विज़ुअलाइज़ेशन अनुपलब्ध',
  bn: 'স্ট্রিমিং ভিজ্যুয়ালাইজেশন অনুপলব্ধ',
  sw: 'Taswira ya utiririshaji haipatikani'
};

// Confirmation toast shown after copyText() succeeds.
var _ivCopiedStr = {
  en: 'Copied', de: 'Kopiert', cs: 'Zkopírováno', hu: 'Másolva',
  hr: 'Kopirano', pl: 'Skopiowano', fr: 'Copié', nl: 'Gekopieerd',
  es: 'Copiado', pt: 'Copiado', it: 'Copiato', ca: 'Copiat',
  gl: 'Copiado', eu: 'Kopiatuta',
  da: 'Kopieret', sv: 'Kopierat', no: 'Kopiert', fi: 'Kopioitu',
  is: 'Afritað',
  sk: 'Skopírované', sl: 'Kopirano', sr: 'Копирано', bs: 'Kopirano',
  bg: 'Копирано', mk: 'Копирано', uk: 'Скопійовано', ru: 'Скопировано',
  be: 'Скапіявана',
  lt: 'Nukopijuota', lv: 'Nokopēts', et: 'Kopeeritud',
  ro: 'Copiat', el: 'Αντιγράφηκε', sq: 'U kopjua',
  tr: 'Kopyalandı', ar: 'تم النسخ', he: 'הועתק',
  zh: '已复制', ja: 'コピーしました', ko: '복사됨',
  vi: 'Đã sao chép', th: 'คัดลอกแล้ว', id: 'Disalin', ms: 'Disalin',
  hi: 'कॉपी किया गया', bn: 'অনুলিপি করা হয়েছে',
  sw: 'Imenakiliwa'
};

// Shown as a top-right toast when streaming completes and the
// visualization has finished rendering. Only appears if we actually
// witnessed live streaming — refreshes of completed messages stay silent.
var _ivDoneStr = {
  en: 'Visualization ready',
  de: 'Visualisierung bereit',
  cs: 'Vizualizace připravena',
  hu: 'Vizualizáció kész',
  hr: 'Vizualizacija spremna',
  pl: 'Wizualizacja gotowa',
  fr: 'Visualisation prête',
  nl: 'Visualisatie klaar',
  es: 'Visualización lista',
  pt: 'Visualização pronta',
  it: 'Visualizzazione pronta',
  ca: 'Visualització llesta',
  gl: 'Visualización lista',
  eu: 'Bistaratzea prest',
  da: 'Visualisering klar',
  sv: 'Visualisering klar',
  no: 'Visualisering klar',
  fi: 'Visualisointi valmis',
  is: 'Sjónræn framsetning tilbúin',
  sk: 'Vizualizácia pripravená',
  sl: 'Vizualizacija pripravljena',
  sr: 'Визуализација спремна',
  bs: 'Vizualizacija spremna',
  bg: 'Визуализацията е готова',
  mk: 'Визуализацијата е подготвена',
  uk: 'Візуалізація готова',
  ru: 'Визуализация готова',
  be: 'Візуалізацыя гатовая',
  lt: 'Vizualizacija paruošta',
  lv: 'Vizualizācija gatava',
  et: 'Visualiseering valmis',
  ro: 'Vizualizare gata',
  el: 'Η οπτικοποίηση είναι έτοιμη',
  sq: 'Vizualizimi gati',
  tr: 'Görselleştirme hazır',
  ar: 'التصور جاهز',
  he: 'ההדמיה מוכנה',
  zh: '可视化已完成',
  ja: 'ビジュアライゼーション完成',
  ko: '시각화 완료',
  vi: 'Hình ảnh đã sẵn sàng',
  th: 'การแสดงภาพพร้อมแล้ว',
  id: 'Visualisasi siap',
  ms: 'Visualisasi sedia',
  hi: 'विज़ुअलाइज़ेशन तैयार',
  bn: 'ভিজ্যুয়ালাইজেশন প্রস্তুত',
  sw: 'Taswira tayari'
};

var _ivErrBodyStr = {
  en: 'Open User Settings \u2192 Interface, scroll down, and enable "Allow iframe same origin" to use streaming mode.',
  de: 'Öffne Benutzereinstellungen \u2192 Oberfläche, scrolle nach unten und aktiviere „Allow iframe same origin" für den Streaming-Modus.',
  cs: 'Otevřete Uživatelská nastavení \u2192 Rozhraní, sjeďte dolů a zapněte „Allow iframe same origin" pro režim streamování.',
  hu: 'Nyissa meg a Felhasználói beállítások \u2192 Felület menüt, görgessen le, és kapcsolja be az „Allow iframe same origin" opciót a streamelési módhoz.',
  hr: 'Otvorite Korisničke postavke \u2192 Sučelje, pomaknite se prema dolje i uključite „Allow iframe same origin" za streaming način.',
  pl: 'Otwórz Ustawienia użytkownika \u2192 Interfejs, przewiń w dół i włącz „Allow iframe same origin" dla trybu strumieniowego.',
  fr: 'Ouvrez Paramètres utilisateur \u2192 Interface, faites défiler vers le bas et activez « Allow iframe same origin » pour le mode streaming.',
  nl: 'Open Gebruikersinstellingen \u2192 Interface, scrol omlaag en schakel "Allow iframe same origin" in voor streamingmodus.',
  es: 'Abre Configuración de usuario \u2192 Interfaz, desplázate hacia abajo y activa "Allow iframe same origin" para el modo streaming.',
  pt: 'Abra Configurações do usuário \u2192 Interface, role para baixo e ative "Allow iframe same origin" para o modo streaming.',
  it: 'Apri Impostazioni utente \u2192 Interfaccia, scorri in basso e attiva "Allow iframe same origin" per la modalità streaming.',
  ca: 'Obre Configuració d\u2019usuari \u2192 Interfície, desplaça\u2019t avall i activa "Allow iframe same origin" per al mode streaming.',
  gl: 'Abre Configuración de usuario \u2192 Interface, desprázate cara abaixo e activa "Allow iframe same origin" para o modo streaming.',
  eu: 'Ireki Erabiltzaile-ezarpenak \u2192 Interfazea, egin behera eta gaitu "Allow iframe same origin" streaming modua erabiltzeko.',
  da: 'Åbn Brugerindstillinger \u2192 Grænseflade, rul ned, og aktivér "Allow iframe same origin" for streamingtilstand.',
  sv: 'Öppna Användarinställningar \u2192 Gränssnitt, rulla ner och aktivera "Allow iframe same origin" för strömningsläge.',
  no: 'Åpne Brukerinnstillinger \u2192 Grensesnitt, rull ned og aktiver "Allow iframe same origin" for streamingmodus.',
  fi: 'Avaa Käyttäjäasetukset \u2192 Käyttöliittymä, vieritä alas ja ota "Allow iframe same origin" käyttöön suoratoistotilaa varten.',
  is: 'Opnaðu Notandastillingar \u2192 Viðmót, skrunaðu niður og kveiktu á "Allow iframe same origin" fyrir streymisstillingu.',
  sk: 'Otvorte Používateľské nastavenia \u2192 Rozhranie, posuňte sa nadol a zapnite „Allow iframe same origin" pre režim streamovania.',
  sl: 'Odprite Uporabniške nastavitve \u2192 Vmesnik, pomaknite se navzdol in omogočite "Allow iframe same origin" za pretočni način.',
  sr: 'Отворите Корисничка подешавања \u2192 Интерфејс, померите надоле и омогућите „Allow iframe same origin" за стриминг режим.',
  bs: 'Otvorite Korisničke postavke \u2192 Sučelje, skrolajte prema dolje i uključite "Allow iframe same origin" za streaming mod.',
  bg: 'Отворете Потребителски настройки \u2192 Интерфейс, превъртете надолу и активирайте „Allow iframe same origin" за поточен режим.',
  mk: 'Отворете Кориснички поставки \u2192 Интерфејс, листајте надолу и овозможете „Allow iframe same origin" за стриминг режим.',
  uk: 'Відкрийте Налаштування користувача \u2192 Інтерфейс, прокрутіть униз і ввімкніть «Allow iframe same origin» для потокового режиму.',
  ru: 'Откройте Настройки пользователя \u2192 Интерфейс, прокрутите вниз и включите «Allow iframe same origin» для режима потоковой передачи.',
  be: 'Адкрыйце Налады карыстальніка \u2192 Інтэрфейс, прагартайце ўніз і ўключыце «Allow iframe same origin» для струменевага рэжыму.',
  lt: 'Atidarykite Naudotojo nustatymai \u2192 Sąsaja, slinkite žemyn ir įjunkite „Allow iframe same origin" srautiniam režimui.',
  lv: 'Atveriet Lietotāja iestatījumi \u2192 Saskarne, ritiniet lejup un iespējojiet "Allow iframe same origin" straumēšanas režīmam.',
  et: 'Ava Kasutaja seaded \u2192 Liides, keri alla ja luba „Allow iframe same origin" voogedastusrežiimi jaoks.',
  ro: 'Deschide Setări utilizator \u2192 Interfață, derulează în jos și activează "Allow iframe same origin" pentru modul streaming.',
  el: 'Ανοίξτε Ρυθμίσεις χρήστη \u2192 Διεπαφή, κυλήστε προς τα κάτω και ενεργοποιήστε το «Allow iframe same origin» για λειτουργία ροής.',
  sq: 'Hapni Cilësimet e përdoruesit \u2192 Ndërfaqja, rrëshqitni poshtë dhe aktivizoni "Allow iframe same origin" për modalitetin e transmetimit.',
  tr: 'Kullanıcı Ayarları \u2192 Arayüz\u2019ü açın, aşağı kaydırın ve akış modu için "Allow iframe same origin" seçeneğini etkinleştirin.',
  ar: 'افتح إعدادات المستخدم \u2190 الواجهة، مرر لأسفل وفعّل "Allow iframe same origin" لاستخدام وضع التدفق.',
  he: 'פתח הגדרות משתמש \u2190 ממשק, גלול מטה והפעל את "Allow iframe same origin" למצב סטרימינג.',
  zh: '打开 用户设置 \u2192 界面，向下滚动并启用"Allow iframe same origin"以使用流式模式。',
  ja: 'ユーザー設定 \u2192 インターフェースを開き、下にスクロールして「Allow iframe same origin」を有効にするとストリーミングモードを使用できます。',
  ko: '사용자 설정 \u2192 인터페이스를 열고 아래로 스크롤하여 "Allow iframe same origin"을 활성화하면 스트리밍 모드를 사용할 수 있습니다.',
  vi: 'Mở Cài đặt người dùng \u2192 Giao diện, cuộn xuống và bật "Allow iframe same origin" để sử dụng chế độ phát trực tiếp.',
  th: 'เปิดการตั้งค่าผู้ใช้ \u2192 อินเทอร์เฟซ เลื่อนลงและเปิดใช้งาน "Allow iframe same origin" เพื่อใช้โหมดสตรีม',
  id: 'Buka Pengaturan Pengguna \u2192 Antarmuka, gulir ke bawah dan aktifkan "Allow iframe same origin" untuk mode streaming.',
  ms: 'Buka Tetapan Pengguna \u2192 Antara Muka, tatal ke bawah dan dayakan "Allow iframe same origin" untuk mod strim.',
  hi: 'उपयोगकर्ता सेटिंग्स \u2192 इंटरफ़ेस खोलें, नीचे स्क्रॉल करें और स्ट्रीमिंग मोड के लिए "Allow iframe same origin" सक्षम करें।',
  bn: 'ব্যবহারকারী সেটিংস \u2192 ইন্টারফেস খুলুন, নিচে স্ক্রোল করুন এবং স্ট্রিমিং মোডের জন্য "Allow iframe same origin" সক্ষম করুন।',
  sw: 'Fungua Mipangilio ya Mtumiaji \u2192 Kiolesura, sogeza chini na washa "Allow iframe same origin" kwa hali ya utiririshaji.'
};

(function() {
  function detectLang() {
    // 1. Pre-detected via __event_call__ (baked into HTML by the tool)
    var pre = document.documentElement.getAttribute('data-iv-lang');
    if (pre && _ivStr[pre]) return pre;
    // 2. Fallback: parent localStorage (needs same-origin)
    try {
      var s = parent.localStorage.getItem('locale')
           || parent.localStorage.getItem('language')
           || parent.localStorage.getItem('i18nextLng');
      if (s) { var l = s.split('-')[0].toLowerCase(); if (_ivStr[l]) return l; }
    } catch(e) {}
    // 3. Fallback: browser language (standalone HTML / no same-origin)
    try {
      var bl = (navigator.language || navigator.userLanguage || 'en').split('-')[0].toLowerCase();
      if (_ivStr[bl]) return bl;
    } catch(e) {}
    return 'en';
  }
  _ivLang = detectLang();
  var btn = document.getElementById('iv-dl-btn');
  if (btn) btn.title = _ivStr[_ivLang] || _ivStr.en;
  // Swap the server-baked English loader label for the detected locale.
  var loadLabel = document.querySelector('.iv-loading-label');
  if (loadLabel) loadLabel.textContent = _ivLoadStr[_ivLang] || _ivLoadStr.en;
})();

// ---------------------------------------------------------------------------
// Download as self-contained HTML
// ---------------------------------------------------------------------------
// Desktop / Android: blob + <a download> + target="_blank" safety net
// (gracefully opens in a new tab if the iframe sandbox blocks downloads).
// iOS: NO target="_blank" (would strand PWA users on a blob page with no
// back button), setTimeout(0) deferral avoids a synchronous WebKit
// "Load failed" throw, and error listeners suppress the residual toast
// for 60s. iOS detection also catches iPadOS via MacIntel+touchpoints.
// ---------------------------------------------------------------------------

var _ivIsIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
  || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

function _ivDownload() {
  // Strip download button + overflow:hidden for standalone use.
  var w = document.getElementById('iv-dl-wrap');
  if (w) w.remove();

  // Serialize from a clone so we can relocate model-imported scripts
  // without mutating the live iframe. enqueueScript appended each
  // imported script tags to head for sequenced execution during streaming
  // — but in a fresh standalone load, head scripts run BEFORE the body
  // is parsed, so any getElementById('chart-canvas') etc. returns null.
  // Move tagged scripts to the end of <body> so they execute after the
  // canvases / DOM nodes they reference.
  var docClone = document.documentElement.cloneNode(true);
  var headClone = docClone.querySelector('head');
  var bodyClone = docClone.querySelector('body');
  if (headClone && bodyClone) {
    var imported = headClone.querySelectorAll('script[data-iv-imported="1"]');
    for (var ii = 0; ii < imported.length; ii++) {
      bodyClone.appendChild(imported[ii]);
    }
  }
  var html = '<!DOCTYPE html>\\n' + docClone.outerHTML;

  if (w) document.body.appendChild(w);
  html = html.replace('html, body { overflow: hidden; }', '');

  var fname = (document.title || 'visualization').replace(/[<>:"\\/|?*]+/g, '-').replace(/\s+/g, ' ').trim();
  if (!fname) fname = 'visualization';
  // Cap at 200 chars to stay under the Windows 255-char filename limit.
  if (fname.length > 200) fname = fname.substring(0, 200).trim();
  fname += '.html';

  var blob = new Blob([html], {type: 'text/html;charset=utf-8'});
  var url = URL.createObjectURL(blob);

  if (_ivIsIOS) {
    // iOS — deferred click + "Load failed" error suppression.
    setTimeout(function() {
      var _origOnerror = window.onerror;
      window.onerror = function(msg) {
        if (typeof msg === 'string' && msg.indexOf('Load failed') !== -1) return true;
        if (_origOnerror) return _origOnerror.apply(this, arguments);
      };
      var _sup = function(ev) {
        var m = ev && (ev.message || (ev.reason && ev.reason.message) || '');
        if (m.indexOf('Load failed') !== -1) { ev.preventDefault(); ev.stopImmediatePropagation(); return true; }
      };
      window.addEventListener('error', _sup, true);
      window.addEventListener('unhandledrejection', _sup, true);

      var a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = fname;
      // No target="_blank" on iOS — strands PWA users on a blob page.
      document.body.appendChild(a);
      a.click();

      // Restore original handlers after 60s.
      setTimeout(function() {
        window.onerror = _origOnerror;
        window.removeEventListener('error', _sup, true);
        window.removeEventListener('unhandledrejection', _sup, true);
        URL.revokeObjectURL(url);
        a.remove();
      }, 60000);
    }, 0);
  } else {
    // Desktop / Android — straightforward blob download.
    var a = document.createElement('a');
    a.href = url;
    a.download = fname;
    // Safety net: new tab if the iframe sandbox blocks downloads.
    a.target = '_blank';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(function() { a.remove(); URL.revokeObjectURL(url); }, 60000);
  }
}
</script>
"""


# ---------------------------------------------------------------------------
# Happy chime on live-stream completion
# ---------------------------------------------------------------------------
# Injected into BODY_SCRIPTS via a /*__CHIME_BLOCK__*/ placeholder so the
# ``chime`` valve can strip it out entirely when disabled — no bytes
# shipped, not just a silent no-op. finalize() calls playDoneSound() inside
# a ``typeof playDoneSound === 'function'`` guard, so omission is safe.
# ---------------------------------------------------------------------------

# !! SRCDOC SAFETY !!  Do NOT write the literal tokens <!-- , --> ,
# <![CDATA[ , ]]> , <script> or </script> ANYWHERE in this body —
# not even inside JS comments. See THEME_DETECTION_SCRIPT for full rationale.
CHIME_SCRIPT = """
// --- Happy chime ---
// C-major arpeggio (C5 → E5 → G5) on sine oscillators with exponential
// decay. ~300 ms, gentle volume. Silent no-op if AudioContext is still
// suspended (no prior user gesture).
var _ivAudioCtx = null;
function playDoneSound() {
  try {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    if (!_ivAudioCtx) _ivAudioCtx = new AC();
    var ctx = _ivAudioCtx;
    if (ctx.state === 'suspended') { try { ctx.resume(); } catch(e) {} }
    var now = ctx.currentTime;
    var notes = [523.25, 659.25, 783.99]; // C5, E5, G5
    notes.forEach(function(freq, i) {
      var osc = ctx.createOscillator();
      var gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = freq;
      var start = now + i * 0.09;
      var dur = 0.35;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.16, start + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + dur);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + dur + 0.02);
    });
  } catch(e) {}
}
"""

# ---------------------------------------------------------------------------
# STRICT-mode script — strip query params from openLink / window.open /
# <a href>. Supplementary hygiene only; the real exfil blocker is the
# CSP connect-src directive. Paths, fragments, and location.assign are
# not intercepted.
# ---------------------------------------------------------------------------

# !! SRCDOC SAFETY !!  Do NOT write the literal tokens <!-- , --> ,
# <![CDATA[ , ]]> , <script> or </script> ANYWHERE in this body —
# not even inside JS comments. See THEME_DETECTION_SCRIPT for full rationale.
STRICT_SECURITY_SCRIPT = """
<script>
(function() {
  function stripParams(rawUrl) {
    try { var u = new URL(rawUrl, location.href); u.search = ''; return u.toString(); }
    catch(e) { return rawUrl; }
  }

  // Override openLink to strip query/hash parameters
  var _origOpenLink = window.openLink;
  window.openLink = function(url) {
    _origOpenLink(stripParams(url));
  };

  // Override window.open to strip query parameters
  var _origOpen = window.open;
  window.open = function(url) {
    arguments[0] = stripParams(url);
    return _origOpen.apply(this, arguments);
  };

  // Strip params from all existing and future <a> tags
  function sanitizeLinks(root) {
    (root.querySelectorAll ? root : document).querySelectorAll('a[href]').forEach(function(a) {
      a.href = stripParams(a.href);
    });
  }
  sanitizeLinks(document);
  new MutationObserver(function(muts) {
    muts.forEach(function(m) {
      m.addedNodes.forEach(function(n) { if (n.nodeType === 1) sanitizeLinks(n); });
    });
  }).observe(document.body, { childList: true, subtree: true });
})();
</script>
"""

# ---------------------------------------------------------------------------
# STREAMING mode — text-marker observer (CodeBlock-free)
# ---------------------------------------------------------------------------
# Model emits plain-text @@@VIZ-START … @@@VIZ-END markers (NOT a code
# fence — that path routed through CodeMirror's virtualizer and lost
# content on scroll / refresh). Markdown renders them as ordinary
# paragraph/html tokens, so nothing we scan goes through CodeBlock.
#
# Observer loop:
#   1. Find enclosing message via frame.closest('[id^="message-"]').
#   2. Read msg.textContent (skipping <details type="tool_calls"> etc).
#   3. Regex-extract the idx-th @@@VIZ-START … @@@VIZ-END block.
#   4. Safe-cut partial HTML, reconcile into #iv-render.
#   5. Walk the message DOM to hide the raw markers + between-marker
#      content inline (display:none !important).
#
# idx comes from the embed container id "{messageId}-embeds-{N}", so
# multiple visualizations in the same message claim in order.
#
# Requires iframe Sandbox Allow Same Origin.
# ---------------------------------------------------------------------------

# !! SRCDOC SAFETY !!  Do NOT write the literal tokens <!-- , --> ,
# <![CDATA[ , ]]> , <script> or </script> ANYWHERE in this body —
# not even inside JS comments. See THEME_DETECTION_SCRIPT for full rationale.
# This is the script that broke in 2.1.0–2.1.2 when a comment cleanup
# accidentally introduced literal <!-- and <script> inside JS comments.
STREAMING_OBSERVER_SCRIPT = """
<script>
(function() {
  'use strict';
  // Markers must match SKILL.md. Chosen so markdown never treats them
  // as a code fence (would put CodeMirror in the loop).
  var START_MARK = '@@@VIZ-START';
  var END_MARK = '@@@VIZ-END';

  // Stash the original text when we blank a node in place — wrapping
  // breaks Svelte's tracked refs, but blanked nodes still need to
  // surface the marker substring to the state machine.
  var _ivOriginalText = (typeof WeakMap !== 'undefined') ? new WeakMap() : null;
  function getEffectiveText(tn) {
    if (!tn) return '';
    var v = tn.nodeValue || '';
    if (v === '' && _ivOriginalText && _ivOriginalText.has(tn)) {
      return _ivOriginalText.get(tn) || '';
    }
    return v;
  }
  function blankPreserving(tn) {
    var current = tn.nodeValue || '';
    if (current === '') return;  // already blanked, idempotent no-op
    if (_ivOriginalText) _ivOriginalText.set(tn, current);
    try { tn.nodeValue = ''; } catch(e) {}
  }
  // `+?` (not `*?`): require ≥1 body char so a freshly emitted
  // @@@VIZ-START with no content yet doesn't match an empty capture
  // and trip finalize("") via the idle timer.
  var BLOCK_RE = /@@@VIZ-START\\n?([\\s\\S]+?)(?:\\n?@@@VIZ-END|$)/g;

  var renderArea = document.getElementById('iv-render');
  if (!renderArea) return;

  // Require same-origin access to parent — otherwise show a helpful notice.
  var hasParentAccess = false;
  try { void parent.document.body; hasParentAccess = true; } catch(e) {}
  if (!hasParentAccess) {
    // _ivLang / _ivErrTitleStr / _ivErrBodyStr come from BODY_SCRIPTS
    // which runs before this observer script.
    var _lang = (typeof _ivLang !== 'undefined' && _ivLang) || 'en';
    var _t = (typeof _ivErrTitleStr !== 'undefined' &&
              (_ivErrTitleStr[_lang] || _ivErrTitleStr.en)) ||
             'Streaming visualization unavailable';
    var _b = (typeof _ivErrBodyStr !== 'undefined' &&
              (_ivErrBodyStr[_lang] || _ivErrBodyStr.en)) ||
             'Open User Settings \u2192 Interface, scroll down, and enable ' +
             '"Allow iframe same origin" to use streaming mode.';
    function _esc(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
                      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
    renderArea.innerHTML =
      '<div style="padding:16px 18px;border:0.5px solid var(--color-border-tertiary);' +
      'border-radius:var(--radius-md);background:var(--color-bg-secondary);' +
      'color:var(--color-text-primary);font-size:13px;line-height:1.5;">' +
      '<div style="font-weight:500;margin-bottom:6px;">' + _esc(_t) + '</div>' +
      '<div style="color:var(--color-text-secondary);">' + _esc(_b) + '</div></div>';
    return;
  }

  // Claim: each tool call renders an embed at "{messageId}-embeds-{N}".
  // The N-th embed owns the N-th @@@VIZ-START/END pair in the message.

  var myMessage = null;
  var myIndex = null;        // this wrapper's position among embed siblings
  var lastRawText = '';
  var lastSafeRendered = '';
  var finalizeTimer = null;
  var finalized = false;

  function findMyMessage() {
    if (myMessage && parent.document.contains(myMessage)) return myMessage;
    try {
      var f = window.frameElement;
      if (!f) return null;
      // chat-assistant wrapper holds both streaming-time buffer and
      // settled content; response-content-container only populates on
      // rehydrate. Toolbar / suggestions row are siblings, not
      // descendants, so we won't scoop them up.
      myMessage = (f.closest && f.closest('.chat-assistant'))
        || (f.closest && f.closest('#response-content-container'))
        || (f.closest && f.closest('[id^="message-"]'))
        || null;
      return myMessage;
    } catch(e) { return null; }
  }

  function determineIndex() {
    if (myIndex !== null) return myIndex;
    try {
      var f = window.frameElement;
      if (!f) return null;
      var embedContainer = f.closest && f.closest('[id*="-embeds-"]');
      if (embedContainer) {
        var m = embedContainer.id.match(/-embeds-(\\d+)$/);
        if (m) { myIndex = parseInt(m[1], 10); return myIndex; }
      }
      // Fallback: count preceding sibling iframes within the same message.
      var msg = findMyMessage();
      if (msg) {
        var iframes = msg.querySelectorAll('iframe');
        for (var i = 0, n = 0; i < iframes.length; i++) {
          if (iframes[i] === f) { myIndex = n; return myIndex; }
          n++;
        }
      }
    } catch(e) {}
    return null;
  }

  // Concatenate searchable text, skipping reasoning / tool-result
  // subtrees so our own result_context example markers (and any
  // @@@VIZ markers the model wrote in chain-of-thought) don't trip
  // the state machine.
  // skipReasoning=true (strict): rejects reasoning subtrees too —
  // this is the preferred pass, since it ignores planning markers
  // a model may have written in chain-of-thought.
  // skipReasoning=false (lax): scans reasoning. Used as fallback for
  // providers that wrap the actual visible response inside
  // <details type="reasoning"> (Bedrock-hosted Haiku 4.5).
  function getSearchableText(msg, skipReasoning) {
    var out = '';
    try {
      var walker = parent.document.createTreeWalker(
        msg, NodeFilter.SHOW_TEXT, {
          acceptNode: function(n) {
            var p = n.parentNode;
            while (p && p !== msg) {
              if (p.nodeType === 1) {
                if (p.tagName === 'DETAILS') {
                  var t = p.getAttribute && p.getAttribute('type');
                  if (t === 'tool_calls' ||
                      t === 'code_execution' || t === 'code_interpreter') {
                    return NodeFilter.FILTER_REJECT;
                  }
                  if (skipReasoning && t === 'reasoning') {
                    return NodeFilter.FILTER_REJECT;
                  }
                }
                var pid = p.id || '';
                if (pid && pid.indexOf('-detail-group') !== -1) {
                  if (pid.indexOf('tool') !== -1 || pid.indexOf('code') !== -1) {
                    return NodeFilter.FILTER_REJECT;
                  }
                  if (skipReasoning) {
                    return NodeFilter.FILTER_REJECT;
                  }
                }
              }
              p = p.parentNode;
            }
            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );
      var t;
      while ((t = walker.nextNode())) out += getEffectiveText(t);
    } catch(e) { return msg.textContent || ''; }
    return out;
  }

  // Returns the regex match object for the idx-th block in `text`, or null.
  function _ivMatchBlock(text, idx) {
    BLOCK_RE.lastIndex = 0;
    var m, n = 0;
    while ((m = BLOCK_RE.exec(text)) !== null) {
      if (n === idx) return m;
      n++;
      if (m.index === BLOCK_RE.lastIndex) BLOCK_RE.lastIndex++;
    }
    return null;
  }

  // Strict pass first (skips reasoning); fall back to lax (scans
  // reasoning) only when strict yields no match. This way planning
  // markers a model wrote in chain-of-thought never win over a real
  // response — but providers that wrap the entire visible response
  // inside <details type="reasoning"> (Bedrock-routed Haiku 4.5) still
  // surface their content via the lax fallback.
  function _ivResolveBlock(idx) {
    var msg = findMyMessage();
    if (!msg) return null;
    var strict = _ivMatchBlock(getSearchableText(msg, true), idx);
    if (strict !== null) return strict;
    return _ivMatchBlock(getSearchableText(msg, false), idx);
  }

  function readSource() {
    var idx = determineIndex();
    if (idx === null) idx = 0;
    var m = _ivResolveBlock(idx);
    return m ? m[1] : null;
  }

  // Hide markers + between-marker content. Single-pass walker with
  // an OUTSIDE/INSIDE state machine. Runs every tick, idempotent.
  // Inline `display:none !important` survives Svelte re-renders.

  function hideEl(el) {
    if (!el || el.nodeType !== 1) return;
    if (el.getAttribute('data-iv-chat-hidden') !== '1') {
      el.setAttribute('data-iv-chat-hidden', '1');
    }
    try { el.style.setProperty('display', 'none', 'important'); } catch(e) {}
  }

  function wrapAndHideText(textNode) {
    var parent = textNode.parentNode;
    if (!parent) return;
    if (parent.nodeType === 1 &&
        parent.getAttribute &&
        parent.getAttribute('data-iv-chat-wrap') === '1') return;
    try {
      var doc = parent.ownerDocument || document;
      var wrap = doc.createElement('span');
      wrap.setAttribute('data-iv-chat-wrap', '1');
      wrap.setAttribute('data-iv-chat-hidden', '1');
      wrap.style.setProperty('display', 'none', 'important');
      parent.insertBefore(wrap, textNode);
      wrap.appendChild(textNode);
    } catch(e) {}
  }

  // Nearest ancestor that's a block-ish container — we prefer hiding
  // block elements over inline ones so we don't leave empty block
  // boxes visible. Stops at `stopAt` (the message root) — never hides
  // the message itself.
  function nearestBlockAncestor(el, stopAt) {
    var BLOCK = { P:1, DIV:1, SECTION:1, ARTICLE:1, BLOCKQUOTE:1,
                  PRE:1, H1:1, H2:1, H3:1, H4:1, H5:1, H6:1,
                  UL:1, OL:1, LI:1, TABLE:1 };
    var cur = el;
    while (cur && cur !== stopAt) {
      if (cur.nodeType === 1 && BLOCK[cur.tagName]) return cur;
      cur = cur.parentNode;
    }
    return null;
  }

  // allowWrap=false during streaming (wrapping a text node breaks
  // Svelte's tracked refs and stalls post-VIZ chunks), true on finalize.
  function hideMarkerRange(allowWrap) {
    var msg = findMyMessage();
    if (!msg) return;
    var myFrame = window.frameElement;

    // Never hide our own iframe's container.
    var myEmbedContainer = null;
    try { myEmbedContainer = myFrame && myFrame.closest('[id*="-embeds-"]'); }
    catch(e) {}
    var embedsRoot = null;
    try { embedsRoot = myFrame && myFrame.closest('[id$="-embeds-container"]'); }
    catch(e) {}

    // Skip reasoning / tool-result subtrees (same rationale as
    // getSearchableText).
    var walker;
    try {
      walker = parent.document.createTreeWalker(
        msg, NodeFilter.SHOW_TEXT, {
          acceptNode: function(n) {
            var p = n.parentNode;
            while (p && p !== msg) {
              if (p.nodeType === 1) {
                if (p.tagName === 'DETAILS') {
                  var t = p.getAttribute && p.getAttribute('type');
                  if (t === 'tool_calls' ||
                      t === 'code_execution' || t === 'code_interpreter') {
                    return NodeFilter.FILTER_REJECT;
                  }
                }
                var pid = p.id || '';
                if (pid && pid.indexOf('-detail-group') !== -1 &&
                    (pid.indexOf('tool') !== -1 ||
                     pid.indexOf('code') !== -1)) {
                  return NodeFilter.FILTER_REJECT;
                }
              }
              p = p.parentNode;
            }
            return NodeFilter.FILTER_ACCEPT;
          }
        }
      );
    } catch(e) { return; }

    var inside = false;
    var tn;
    var toHideEls = [];
    var toBlankText = [];

    while ((tn = walker.nextNode())) {
      if (embedsRoot && embedsRoot.contains(tn)) continue;
      if (myEmbedContainer && myEmbedContainer.contains(tn)) continue;

      // getEffectiveText surfaces the original (pre-blank) text so
      // blanked nodes still match.
      var tv = getEffectiveText(tn);
      var hadStartLocal = tv.indexOf(START_MARK) !== -1;
      var hadEndLocal = tv.indexOf(END_MARK) !== -1;

      var hideThis = inside || hadStartLocal || hadEndLocal;

      if (hideThis) {
        var block = nearestBlockAncestor(tn.parentNode, msg);
        if (block && block !== msg && !block.contains(myFrame)) {
          // Clean block ancestor — hide wholesale, no text touched.
          toHideEls.push(block);
        } else {
          // Block contains our iframe — can't hide the block. Blank
          // in place: nodeValue = '' preserves Svelte's ref identity.
          toBlankText.push(tn);
        }
      }

      // Flip state AFTER processing so the END-bearing node is hidden.
      if (hadStartLocal && hadEndLocal) {
        inside = false;
      } else if (hadStartLocal) {
        inside = true;
      } else if (hadEndLocal) {
        inside = false;
      }
    }

    for (var i = 0; i < toHideEls.length; i++) hideEl(toHideEls[i]);
    if (allowWrap) {
      // Finalize: wrap for tighter visual collapse (safe — Svelte
      // has stopped streaming chunks).
      for (var j = 0; j < toBlankText.length; j++) wrapAndHideText(toBlankText[j]);
    } else {
      for (var b = 0; b < toBlankText.length; b++) blankPreserving(toBlankText[b]);
    }
  }

  // Returns the last index where the parser is in TEXT state (not
  // mid-tag / mid-attr / mid-script / mid-CDATA). Browser auto-closes
  // open tags on innerHTML assignment — depth doesn't matter.
  var VOID_TAGS = {area:1,base:1,br:1,col:1,embed:1,hr:1,img:1,input:1,
                   link:1,meta:1,param:1,source:1,track:1,wbr:1};
  var RAW_TAGS = {script:1, style:1};

  function findSafeCut(text) {
    var i = 0, len = text.length;
    var state = 'TEXT';
    var quote = 0;
    var safeCut = 0;
    var tagNameBuf = '';
    var tagNameEnd = false;
    var inClosingTag = false;
    var selfClosing = false;
    var rawTag = '';  // active raw-text tag close-tag name

    while (i < len) {
      var ch = text.charCodeAt(i);

      if (state === 'RAW') {
        // Inside a raw-text element. Contents are NOT a safe cut — we
        // have to wait for the full close tag before flushing, otherwise
        // innerHTML would include partial JS/CSS.
        var marker = '</' + rawTag;
        if (text.substr(i, marker.length).toLowerCase() === marker) {
          var end = text.indexOf('>', i + marker.length);
          if (end === -1) break;
          rawTag = '';
          state = 'TEXT';
          i = end + 1;
          safeCut = i;
          continue;
        }
        i++; continue;
      }

      if (state === 'TEXT') {
        if (ch === 60 /* < */) {
          // The HTML-comment / CDATA opener tokens are built via
          // string concatenation. Embedding the raw forms in source
          // (even inside a JS comment) puts the enclosing srcdoc
          // parser into script-data-escape mode and breaks the IIFE.
          var CMT_OPEN = '<' + '!--';
          var CMT_CLOSE = '--' + '>';
          var CDATA_OPEN = '<' + '![CDATA[';
          if (text.substr(i, 4) === CMT_OPEN) {
            var ce = text.indexOf(CMT_CLOSE, i + 4);
            if (ce === -1) break;
            i = ce + 3;
            safeCut = i;
            continue;
          }
          if (text.substr(i, 9) === CDATA_OPEN) {
            // CDATA close — literal would put srcdoc parser into
            // script-data-escape mode; concatenate at runtime.
            var ke = text.indexOf(']]' + '>', i + 9);
            if (ke === -1) break;
            i = ke + 3;
            safeCut = i;
            continue;
          }
          state = 'TAG';
          tagNameBuf = ''; tagNameEnd = false;
          inClosingTag = false; selfClosing = false;
          i++; continue;
        }
        i++;
        safeCut = i;
        continue;
      }

      if (state === 'TAG') {
        if (ch === 47 /* / */) {
          if (tagNameBuf === '' && !tagNameEnd) { inClosingTag = true; i++; continue; }
          selfClosing = true; i++; continue;
        }
        if (ch === 62 /* > */) {
          var tn = tagNameBuf.toLowerCase();
          if (!inClosingTag && !selfClosing && RAW_TAGS[tn]) {
            state = 'RAW'; rawTag = tn; i++; continue;
          }
          state = 'TEXT'; i++;
          safeCut = i;
          continue;
        }
        if (ch === 32 || ch === 9 || ch === 10 || ch === 13) {
          tagNameEnd = true; i++; state = 'ATTR_NAME'; continue;
        }
        if (!tagNameEnd) tagNameBuf += text.charAt(i);
        i++; continue;
      }

      if (state === 'ATTR_NAME') {
        if (ch === 62) {
          var tn2 = tagNameBuf.toLowerCase();
          if (!inClosingTag && !selfClosing && RAW_TAGS[tn2]) {
            state = 'RAW'; rawTag = tn2; i++; continue;
          }
          state = 'TEXT'; i++;
          safeCut = i;
          continue;
        }
        if (ch === 47) { selfClosing = true; i++; continue; }
        if (ch === 61 /* = */) { state = 'ATTR_VAL_START'; i++; continue; }
        i++; continue;
      }

      if (state === 'ATTR_VAL_START') {
        if (ch === 32 || ch === 9 || ch === 10 || ch === 13) { i++; continue; }
        if (ch === 34) { quote = 34; state = 'ATTR_VAL_Q'; i++; continue; }
        if (ch === 39) { quote = 39; state = 'ATTR_VAL_Q'; i++; continue; }
        if (ch === 62) { state = 'ATTR_NAME'; continue; }
        state = 'ATTR_VAL_U'; i++; continue;
      }

      if (state === 'ATTR_VAL_Q') {
        if (ch === quote) { state = 'ATTR_NAME'; i++; continue; }
        i++; continue;
      }

      if (state === 'ATTR_VAL_U') {
        if (ch === 32 || ch === 9 || ch === 10 || ch === 13) { state = 'ATTR_NAME'; i++; continue; }
        if (ch === 62) { state = 'ATTR_NAME'; continue; }
        i++; continue;
      }
    }
    return safeCut;
  }

  // Incremental DOM reconciler — append-only, so existing elements
  // stay put (no reflow, no animation re-trigger). Attributes are
  // immutable between cuts (parser can't cut mid-tag).

  // Serializes script execution across the visualization — external
  // scripts load async while inline scripts run sync on insertion,
  // so we chain the insertions to enforce source order.
  var _ivScriptChain = Promise.resolve();
  var _ivEnqueuedScripts = Object.create(null);

  // FNV-1a content hash, used to dedupe script bodies across
  // reconciler branches that may re-encounter the same node.
  function _ivHashScript(s) {
    var h = 2166136261;
    for (var i = 0; i < s.length; i++) {
      h = (h ^ s.charCodeAt(i)) >>> 0;
      h = Math.imul(h, 16777619) >>> 0;
    }
    return h.toString(36);
  }

  function enqueueScript(incoming) {
    var src = incoming.getAttribute && incoming.getAttribute('src');
    var code = incoming.textContent || '';

    // Dedupe by src or content hash — reconciler may hit the same
    // script twice across streaming/finalize branches. Re-execution
    // would redeclare consts and double-wire listeners.
    var key = src ? ('src:' + src) : ('code:' + code.length + ':' + _ivHashScript(code));
    if (_ivEnqueuedScripts[key]) return;
    _ivEnqueuedScripts[key] = true;

    var attrs = [];
    for (var a = 0; a < incoming.attributes.length; a++) {
      attrs.push([incoming.attributes[a].name, incoming.attributes[a].value]);
    }
    // Each link in the chain is wrapped + .catch'd so a single bad
    // script (model wrote invalid JS, attribute name has weird chars,
    // appendChild's synchronous parse throws, etc.) can't kill the
    // chain and stall every script that follows.
    if (src) {
      _ivScriptChain = _ivScriptChain.then(function() {
        return new Promise(function(resolve) {
          try {
            var el = document.createElement('script');
            attrs.forEach(function(pair) {
              try { el.setAttribute(pair[0], pair[1]); } catch(_){}
            });
            // Tag for HTML export: _ivDownload moves these to end of body
            // so they execute after the model's canvases / DOM nodes exist.
            el.setAttribute('data-iv-imported', '1');
            el.onload = el.onerror = function() { resolve(); };
            document.head.appendChild(el);
          } catch(e) { resolve(); }
        });
      }).catch(function() {});
    } else {
      _ivScriptChain = _ivScriptChain.then(function() {
        try {
          var el = document.createElement('script');
          attrs.forEach(function(pair) {
            try { el.setAttribute(pair[0], pair[1]); } catch(_){}
          });
          el.setAttribute('data-iv-imported', '1');
          el.textContent = code;
          document.head.appendChild(el);
        } catch(e) {}
      }).catch(function() {});
    }
  }

  // importNode preserves SVG namespaces. Scripts go through
  // enqueueScript for source-order execution.
  function importAndAppend(parent, incoming) {
    var nt = incoming.nodeType;
    if (nt === 3) {
      parent.appendChild(document.createTextNode(incoming.textContent));
      return;
    }
    if (nt === 8) {
      parent.appendChild(document.createComment(incoming.textContent));
      return;
    }
    if (nt !== 1) return;
    var tag = incoming.nodeName;
    var el;
    if (tag === 'SCRIPT' || tag === 'script') {
      enqueueScript(incoming);
      return;
    }
    // Shallow import preserves HTML/SVG namespace.
    el = document.importNode(incoming, false);
    parent.appendChild(el);
    for (var i = 0; i < incoming.childNodes.length; i++) {
      importAndAppend(el, incoming.childNodes[i]);
    }
  }

  function reconcile(existing, incoming) {
    var existCh = existing.childNodes;
    var incCh = incoming.childNodes;
    // Source declares this element as a leaf (no children); any children
    // in the live DOM came from user scripts that target this element by
    // id (d3.select(...).append('svg'), new vis.Network(container, ...),
    // ECharts/Plotly/Vega painting into their target div, etc.). Trimming
    // them would erase the chart, so leave the leaf alone.
    if (incCh.length === 0) return;
    var i;
    for (i = 0; i < incCh.length; i++) {
      var inc = incCh[i];
      var exist = existCh[i];
      if (!exist) {
        importAndAppend(existing, inc);
        continue;
      }
      // Position mismatch — rare with append-only, but guard.
      if (exist.nodeType !== inc.nodeType ||
          (exist.nodeType === 1 && exist.nodeName !== inc.nodeName)) {
        existing.removeChild(exist);
        var next = existCh[i] || null;
        var holder = document.createDocumentFragment();
        importAndAppend(holder, inc);
        if (next) existing.insertBefore(holder, next);
        else existing.appendChild(holder);
        continue;
      }
      if (exist.nodeType === 3) {
        if (exist.nodeValue !== inc.nodeValue) exist.nodeValue = inc.nodeValue;
        continue;
      }
      if (exist.nodeType === 1) reconcile(exist, inc);
    }
    // Trim trailing TEXT nodes that were written by a previous streaming
    // tick but are no longer present in the incoming source (e.g. a
    // partial @@@VIZ-END fragment that leaked into the render area when
    // the regex captured to $ during streaming).  Text nodes are never
    // script-added chart elements — only element nodes (nodeType 1) need
    // the "no outer trim" protection below.
    for (var j = existCh.length - 1; j >= incCh.length; j--) {
      var stale = existCh[j];
      if (stale && stale.nodeType === 3) {
        try { existing.removeChild(stale); } catch(_) {}
      }
    }
    // No outer trim for ELEMENT children — streaming source is
    // append-only, so existing element children beyond incCh.length are
    // script-added (D3 SVG, vis-network canvas/SVG, ECharts canvas,
    // etc.). Removing them erases the chart mid-render even when the
    // script targeted a non-leaf container.
  }

  // withScripts=true materializes scripts (finalize path); false strips
  // them during streaming. Regex source is concatenated so the raw
  // open / close tokens never appear literally in this file.
  var _ivOpen = '<' + 'script';
  var _ivClose = '<' + '\\/script>';
  var _ivStripPaired = new RegExp(_ivOpen + '[\\\\s\\\\S]*?' + _ivClose, 'gi');
  var _ivStripOpen = new RegExp(_ivOpen + '[\\\\s\\\\S]*$', 'i');
  // Strip doc-level tags that models sometimes wrap VIZ content in.
  var _ivStripDocTags = new RegExp('<' + '!DOCTYPE[^>]*>|<' + '/?(?:html|head|body)[^>]*>', 'gi');

  // Open WebUI's chat sanitizer strips <style> but keeps the inner CSS
  // as text. Re-inflate consecutive bare CSS rules so the iframe can
  // apply them. Strict pattern + ≥2 adjacent rules guards against
  // accidental matches on JSON / object literals.
  var _ivCssRule = /[A-Za-z@.#:*\[\]>+\-,\s_~()='"&]+\{\s*(?:[A-Za-z-]+\s*:\s*[^;{}<>]+;\s*)+\}/g;
  function reinflateBareCSS(text) {
    if (/<style[\\s>]/i.test(text)) return text;
    _ivCssRule.lastIndex = 0;
    var matches = [], m;
    while ((m = _ivCssRule.exec(text)) !== null) {
      matches.push({ start: m.index, end: _ivCssRule.lastIndex });
      if (m.index === _ivCssRule.lastIndex) _ivCssRule.lastIndex++;
    }
    if (matches.length < 2) return text;
    // Group consecutive rules (separated by < 50 chars of whitespace)
    var groups = [], cur = null;
    for (var i = 0; i < matches.length; i++) {
      if (cur && matches[i].start - cur.end < 50) cur.end = matches[i].end;
      else { cur = { start: matches[i].start, end: matches[i].end, count: 1 }; groups.push(cur); }
      if (cur.start !== matches[i].start) cur.count = (cur.count || 1) + 1;
    }
    // Process from last to first to preserve indices
    for (var g = groups.length - 1; g >= 0; g--) {
      var grp = groups[g];
      var slice = text.substring(grp.start, grp.end);
      // Require multiple rules in the group
      var brace = slice.match(/\{/g);
      if (!brace || brace.length < 2) continue;
      text = text.substring(0, grp.start) + '<style>' + slice + '</style>' + text.substring(grp.end);
    }
    return text;
  }

  function renderSafeInto(text, withScripts) {
    var html = withScripts
      ? text
      : text.replace(_ivStripPaired, '').replace(_ivStripOpen, '');
    html = html.replace(_ivStripDocTags, '');
    html = reinflateBareCSS(html);
    var temp = document.createElement('div');
    try {
      temp.innerHTML = html;
    } catch(e) {
      // Fallback to full replace on any parse oddity.
      renderArea.innerHTML = html;
      return;
    }
    reconcile(renderArea, temp);
  }

  // ---- Fade-in animation for newly-complete elements ------------------
  function markAndAnimate(root) {
    var toAnimate = [];
    function visit(node, top) {
      if (!node || node.nodeType !== 1) return;
      var isSvgChild = node.ownerSVGElement != null;
      if ((top || isSvgChild || node.tagName === 'svg') && !node.hasAttribute('data-iv-faded')) {
        node.setAttribute('data-iv-faded', '1');
        toAnimate.push(node);
      }
      if (node.tagName === 'svg') {
        for (var c = node.firstElementChild; c; c = c.nextElementSibling) visit(c, false);
      }
    }
    for (var c = root.firstElementChild; c; c = c.nextElementSibling) visit(c, true);
    if (toAnimate.length === 0) return;
    requestAnimationFrame(function() {
      toAnimate.forEach(function(el) { el.classList.add('iv-fade-in'); });
    });
  }

  // ---- Height handling during streaming -------------------------------
  var heightRaf = 0;
  function scheduleHeight() {
    cancelAnimationFrame(heightRaf);
    heightRaf = requestAnimationFrame(function() {
      try { if (typeof reportHeight === 'function') reportHeight(); } catch(e) {}
    });
  }

  // ---- Finalize: run scripts, final height nudge ----------------------

  // Defensive post-finalize stripper. Two passes:
  //
  // Pass 1 (full range hide): walks ALL text nodes between @@@VIZ-START
  // and @@@VIZ-END and blanks them. This catches bare JS/CSS text that
  // the chat sanitizer exposed by stripping the surrounding script/style
  // tags — the content leaks as text nodes in the parent chat DOM even
  // though the markers correctly delimit the range.
  //
  // Pass 2 (marker cleanup): cleans any text nodes that still contain
  // the marker strings themselves (e.g. orphaned @@@VIZ-END left behind
  // by Svelte re-renders). Skips code/pre to avoid mangling code blocks.
  function stripFinalizeArtifacts() {
    var msg = findMyMessage();
    if (!msg) return;
    var myFrame = window.frameElement;
    var embedsRoot = null;
    try { embedsRoot = myFrame && myFrame.closest('[id$="-embeds-container"]'); }
    catch(e) {}
    var myEmbedContainer = null;
    try { myEmbedContainer = myFrame && myFrame.closest('[id*="-embeds-"]'); }
    catch(e) {}

    var nodes = [];
    try {
      var walker = parent.document.createTreeWalker(
        msg, NodeFilter.SHOW_TEXT, null
      );
      var t;
      while ((t = walker.nextNode())) nodes.push(t);
    } catch(e) { return; }

    // Pass 1: blank everything between the markers (full range hide).
    var inside = false;
    for (var i = 0; i < nodes.length; i++) {
      var tn = nodes[i];
      if (embedsRoot && embedsRoot.contains(tn)) continue;
      if (myEmbedContainer && myEmbedContainer.contains(tn)) continue;

      var v = getEffectiveText(tn);
      var hasStart = v.indexOf(START_MARK) !== -1;
      var hasEnd   = v.indexOf(END_MARK)   !== -1;

      var shouldHide = inside || hasStart || hasEnd;

      if (shouldHide) {
        // Never touch nodes inside <code>/<pre> — they may be the
        // original fenced code block the model placed outside the VIZ.
        var p = tn.parentNode, isCode = false;
        while (p && p !== msg) {
          if (p.nodeType === 1 && (p.tagName === 'CODE' || p.tagName === 'PRE')) {
            isCode = true; break;
          }
          p = p.parentNode;
        }
        if (!isCode) {
          try { tn.nodeValue = ''; } catch(e) {}
          // Also hide the nearest block ancestor if it's now empty,
          // to remove phantom whitespace / margin from the layout.
          var block = nearestBlockAncestor(tn.parentNode, msg);
          if (block && block !== msg && !block.contains(myFrame)) {
            hideEl(block);
          }
        }
      }

      if (hasStart && hasEnd) { inside = false; }
      else if (hasStart)      { inside = true;  }
      else if (hasEnd)        { inside = false; }
    }

    // Pass 2: scrub any surviving marker text from nodes that weren't
    // fully blanked (e.g. a node that mixes marker + prose).
    for (var j = 0; j < nodes.length; j++) {
      var tn2 = nodes[j];
      var v2 = tn2.nodeValue || '';
      if (!v2) continue;
      if (v2.indexOf(START_MARK) === -1 && v2.indexOf(END_MARK) === -1) continue;
      var p2 = tn2.parentNode, isCode2 = false;
      while (p2 && p2 !== msg) {
        if (p2.nodeType === 1 &&
            (p2.tagName === 'CODE' || p2.tagName === 'PRE')) {
          isCode2 = true; break;
        }
        p2 = p2.parentNode;
      }
      if (isCode2) continue;
      var cleaned = v2
        .split(START_MARK).join('')
        .split(END_MARK).join('')
        .replace(/<\/[a-z][a-z0-9]*\s*>/gi, '');
      try { tn2.nodeValue = cleaned.replace(/^\s+|\s+$/g, '') ? cleaned : ''; }
      catch(e) {}
    }
  }

  // Expand the viewBox of any <svg> inside renderArea whose declared
  // height is smaller than its actual content bounding box.  This is a
  // safety net for LLM-generated SVGs that miscalculate the viewBox
  // height (a common failure mode with long flowcharts).
  //
  // Uses getBBox() — available only after layout, so must run after the
  // final renderSafeInto() call and a rAF to let the browser paint.
  // getBBox() is SVG-only; HTML content is unaffected.
  function fixUnderSizedViewBox() {
    try {
      var svgs = renderArea.querySelectorAll('svg');
      for (var s = 0; s < svgs.length; s++) {
        var svg = svgs[s];
        // Skip SVGs that are children of another SVG (nested symbols etc.)
        if (svg.ownerSVGElement) continue;
        var vb = svg.getAttribute('viewBox');
        if (!vb) continue;
        var parts = vb.trim().split(/[\s,]+/);
        if (parts.length < 4) continue;
        var vbX = parseFloat(parts[0]);
        var vbY = parseFloat(parts[1]);
        var vbW = parseFloat(parts[2]);
        var vbH = parseFloat(parts[3]);
        if (isNaN(vbX) || isNaN(vbY) || isNaN(vbW) || isNaN(vbH)) continue;
        var bb;
        try { bb = svg.getBBox(); } catch(e) { continue; }
        // Content extends beyond declared viewBox?  Expand with 20px padding.
        var pad = 20;
        var needW = bb.x + bb.width  + pad - vbX;
        var needH = bb.y + bb.height + pad - vbY;
        var changed = false;
        if (needW > vbW) { vbW = Math.ceil(needW); changed = true; }
        if (needH > vbH) { vbH = Math.ceil(needH); changed = true; }
        if (changed) {
          svg.setAttribute('viewBox', vbX + ' ' + vbY + ' ' + vbW + ' ' + vbH);
        }
      }
    } catch(e) {}
  }

  function finalize(fullText) {
    if (finalized) return;
    finalized = true;
    // withScripts=true so the reconciler materializes script tags.
    renderSafeInto(fullText, true);
    // Expand any SVG viewBox that is smaller than its content — safety
    // net for LLM-generated SVGs with miscalculated viewBox height.
    // Must run after layout (rAF) so getBBox() returns real values.
    requestAnimationFrame(function() {
      try { fixUnderSizedViewBox(); } catch(e) {}
      // Re-nudge height after viewBox may have grown.
      scheduleHeight();
    });
    // Multi-shot strip — Svelte may flush chunks 1–2s after finalize
    // fires; each run is idempotent. stripFinalizeArtifacts now does
    // a full between-marker range hide (Pass 1) in addition to the
    // marker-text scrub (Pass 2).
    try { stripFinalizeArtifacts(); } catch(e) {}
    setTimeout(function() { try { stripFinalizeArtifacts(); } catch(e) {} }, 300);
    setTimeout(function() { try { stripFinalizeArtifacts(); } catch(e) {} }, 800);
    setTimeout(function() { try { stripFinalizeArtifacts(); } catch(e) {} }, 2000);
    setTimeout(function() { try { stripFinalizeArtifacts(); } catch(e) {} }, 4500);
    // Fix B: re-run hideMarkerRange(allowWrap=true) on a delay to
    // catch text nodes that Svelte recreates after finalize fires —
    // the chat renderer may flush buffered DOM mutations 100-500ms
    // after we blank them, replacing blanked nodes with fresh ones.
    setTimeout(function() { try { hideMarkerRange(true); } catch(e) {} }, 500);
    setTimeout(function() { try { hideMarkerRange(true); } catch(e) {} }, 1500);
    setTimeout(function() { try { hideMarkerRange(true); } catch(e) {} }, 3500);
    hideLoader();
    markAndAnimate(renderArea);
    // Nudge the height reporter across layout settle.
    scheduleHeight();
    setTimeout(scheduleHeight, 120);
    setTimeout(scheduleHeight, 400);
    // Done announcement — only on live streams, not on rehydration.
    if (wasStreaming) {
      try {
        var label = (typeof _ivDoneStr !== 'undefined' &&
                     (_ivDoneStr[_ivLang] || _ivDoneStr.en)) || 'Visualization ready';
        if (typeof toast === 'function') toast(label, 'success');
      } catch(e) {}
      try { if (typeof playDoneSound === 'function') playDoneSound(); } catch(e) {}
    }
  }

  function isBlockClosed() {
    var idx = determineIndex();
    if (idx === null) idx = 0;
    var m = _ivResolveBlock(idx);
    return !!m && m[0].indexOf(END_MARK) !== -1;
  }

  // Tick skips its whole pipeline when the searchable text is
  // unchanged. A childList mutation sets forceHide=true so Svelte
  // rebuilds that preserve the text string still get re-hidden.
  var lastMsgText = null;
  var wasStreaming = false;
  var firstSeenLen = null;

  function tick(forceHide) {
    if (finalized) return;
    var msg = findMyMessage();
    if (!msg) return;

    // Lax: tick on any text change, including reasoning-block edits
    // (Bedrock-routed Haiku 4.5 streams the response inside reasoning).
    var currentText = getSearchableText(msg, false);
    var textChanged = currentText !== lastMsgText;
    lastMsgText = currentText;

    // Live-stream detection by GROWTH — the first-seen searchable
    // length never grows on refreshes of completed messages, so
    // wasStreaming stays false and we don't fire the done toast/chime.
    if (firstSeenLen === null) firstSeenLen = currentText.length;
    else if (!wasStreaming && currentText.length > firstSeenLen) {
      wasStreaming = true;
    }

    // allowWrap=false: streaming-safe (no text-node wrapping — would
    // break Svelte's diff and stall post-VIZ chunks). finalize() runs
    // the wrap-allowed pass once the response is complete.
    if (textChanged || forceHide) hideMarkerRange(false);

    // Source-dependent work only runs on actual changes.
    if (!textChanged) return;

    var raw = readSource();
    if (raw === null) return;
    if (raw === lastRawText) {
      scheduleFinalize(raw);
      return;
    }
    lastRawText = raw;

    var cut = findSafeCut(raw);
    var safe = raw.substring(0, cut);

    if (safe !== lastSafeRendered && safe.length > 0) {
      lastSafeRendered = safe;
      renderSafeInto(safe, false);
      markAndAnimate(renderArea);
      scheduleHeight();
    }

    scheduleFinalize(raw);
  }

  // Forces hideMarkerRange to re-run even when textContent is unchanged
  // — Svelte can rebuild a text node without altering its string value.
  function _ivHasChildListMutation(records) {
    if (!records) return false;
    for (var i = 0; i < records.length; i++) {
      if (records[i] && records[i].type === 'childList') return true;
    }
    return false;
  }

  function scheduleFinalize(raw) {
    // Primary signal: @@@VIZ-END present → finalize instantly.
    // Fallback: 30s of completely stable source (user stopped
    // generation / model forgot END / network died). 30s is longer
    // than any realistic inter-chunk stall (Gemini 3.1 Pro 200-token
    // chunks, proxy buffering, etc) so we can't trip it mid-stream.
    clearTimeout(finalizeTimer);
    if (isBlockClosed()) { finalize(raw); return; }
    finalizeTimer = setTimeout(function() {
      if (finalized) return;
      var latest = readSource();
      if (latest === null) return;
      if (isBlockClosed() || latest === raw) {
        finalize(latest);
      }
    }, 30000);
  }

  // ---- Inject fade-in + loader CSS into our OWN document -------------
  (function injectFadeCss() {
    var s = document.createElement('style');
    s.textContent =
      '@keyframes iv-fade-in-kf {' +
      '  from { opacity: 0; transform: translateY(2px); }' +
      '  to   { opacity: 1; transform: none; }' +
      '}' +
      '@keyframes iv-fade-in-svg-kf {' +
      '  from { opacity: 0; } to { opacity: 1; }' +
      '}' +
      '#iv-render .iv-fade-in { animation: iv-fade-in-kf 500ms ease-out both; }' +
      '#iv-render svg .iv-fade-in { animation: iv-fade-in-svg-kf 500ms ease-out both; }' +
      // Three pulsing dots + label shown while waiting for content.
      '@keyframes iv-pulse-kf {' +
      '  0%, 80%, 100% { opacity: 0.25; transform: scale(0.85); }' +
      '  40%           { opacity: 1;    transform: scale(1); }' +
      '}' +
      '.iv-loading {' +
      '  display: flex; flex-direction: column; align-items: center;' +
      '  justify-content: center; gap: 12px;' +
      '  padding: 48px 20px; min-height: 120px;' +
      '  color: var(--color-text-tertiary);' +
      '  font-size: 12px; letter-spacing: 0.02em;' +
      '}' +
      '.iv-loading-dots { display: inline-flex; gap: 8px; }' +
      '.iv-loading-dots span {' +
      '  width: 8px; height: 8px; border-radius: 50%;' +
      '  background: var(--color-text-tertiary);' +
      '  animation: iv-pulse-kf 1.4s infinite ease-in-out both;' +
      '}' +
      '.iv-loading-dots span:nth-child(1) { animation-delay: -0.32s; }' +
      '.iv-loading-dots span:nth-child(2) { animation-delay: -0.16s; }' +
      '.iv-loading-label { opacity: 0.6; }';
    document.head.appendChild(s);
  })();

  // #iv-loader is rendered server-side as a sibling below #iv-render;
  // we only need to remove it on finalize.
  function hideLoader() {
    try {
      var l = document.getElementById('iv-loader');
      if (l && l.parentNode) l.parentNode.removeChild(l);
    } catch(e) {}
  }

  // Defense in depth: outer observer on parent.document.body sees new
  // messages as chat scrolls / navigates; inner observer on our own
  // message catches every streaming text mutation; 400ms poll is a
  // safety net in case the observers miss anything.
  var innerMo = null;
  function attachInnerObserver() {
    if (innerMo) return;
    var msg = findMyMessage();
    if (!msg) return;
    try {
      innerMo = new MutationObserver(function(records) {
        tick(_ivHasChildListMutation(records));
      });
      innerMo.observe(msg, {
        childList: true, subtree: true, characterData: true
      });
    } catch(e) {}
  }

  function pollTick() {
    try { tick(false); } catch(e) {}
    try { attachInnerObserver(); } catch(e) {}
  }

  // Each bootstrap step is independently guarded — any one of them
  // failing must not prevent the polling timer from being installed.
  // Without the timer the iframe goes silently dormant.
  try { tick(false); } catch(e) {}
  try { attachInnerObserver(); } catch(e) {}
  try {
    new MutationObserver(function(records) {
      try { tick(_ivHasChildListMutation(records)); } catch(e) {}
      try { attachInnerObserver(); } catch(e) {}
    }).observe(parent.document.body, {
      childList: true, subtree: true, characterData: true
    });
  } catch(e) {}
  setInterval(pollTick, 400);
})();
</script>
"""


# Kept for backwards compatibility in case anything references the old name
INJECTED_SCRIPTS = BODY_SCRIPTS


# ---------------------------------------------------------------------------
# srcdoc safety guard
#
# Every constant listed in _IFRAME_EMBEDDED_SCRIPTS below is concatenated
# into an iframe's srcdoc. Once that srcdoc is parsed by the browser's
# HTML5 tokenizer, the script-data state machine is sensitive to the
# following literal byte sequences appearing ANYWHERE inside a script
# body (including inside JS comments and string literals):
#
#   <!--           triggers "script data escape start"
#   -->            exits  "script data escaped"
#   <![CDATA[      same family of escape transitions
#   ]]>            same
#   <script        in escaped state, triggers "script data double escape start"
#   </script>      in double-escaped state, exits back to escaped — does
#                  NOT terminate the outer script
#
# When any of these appears inside a script body — even commented out —
# the outer script's actual `</script>` tag stops terminating the
# script. The IIFE then either never executes or executes incompletely,
# producing the silent failure mode we hit in 2.1.0–2.1.2 (every
# debugging path looks normal in isolation, but tick never runs).
#
# Always build these tokens via string concatenation in JS — never
# write them as literals, not even inside comments. The guard below
# raises at module load time so the plugin refuses to import if anyone
# ever reintroduces one.
_FORBIDDEN_SRCDOC_LITERALS = (
    "<!--",
    "-->",
    "<![CDATA[",
    "]]>",
    "<script",
    "</script",
)


def _assert_srcdoc_safe(name: str, body: str) -> None:
    """Refuse to load if `body` contains any HTML token that would
    confuse the iframe srcdoc's script-data state machine.

    Each script body is allowed exactly ONE legitimate `<script>` and
    one `</script>` — the wrapping tags themselves. Anything beyond
    that count is a reintroduction of the bug fixed in 2.1.3.
    """
    open_count = body.count("<script")
    close_count = body.count("</script")
    if open_count > 1 or close_count > 1:
        raise RuntimeError(
            f"Inline Visualizer: {name} contains an extra <script> or "
            f"</script> literal (open={open_count}, close={close_count}). "
            "These break HTML5 srcdoc parsing — build them via string "
            "concatenation in JS instead."
        )
    for tok in ("<!--", "-->", "<![CDATA[", "]]>"):
        if tok in body:
            raise RuntimeError(
                f"Inline Visualizer: {name} contains a literal {tok!r}. "
                "This puts the iframe srcdoc parser into script-data-escape "
                "mode and silently breaks the IIFE. Concatenate it in JS "
                "instead, even inside comments."
            )


_IFRAME_EMBEDDED_SCRIPTS = {
    "THEME_DETECTION_SCRIPT": THEME_DETECTION_SCRIPT,
    "BODY_SCRIPTS": BODY_SCRIPTS,
    "CHIME_SCRIPT": CHIME_SCRIPT,
    "STRICT_SECURITY_SCRIPT": STRICT_SECURITY_SCRIPT,
    "STREAMING_OBSERVER_SCRIPT": STREAMING_OBSERVER_SCRIPT,
}
for _name, _body in _IFRAME_EMBEDDED_SCRIPTS.items():
    _assert_srcdoc_safe(_name, _body)


DOWNLOAD_BUTTON = (
    '<div id="iv-dl-wrap">'
    '<button id="iv-dl-btn" onclick="_ivDownload()" title="Download">'
    '<svg viewBox="0 0 16 16"><path d="M8 2v8M5 7l3 3 3-3"/><path d="M3 12h10"/></svg>'
    "</button></div>"
)


# ---------------------------------------------------------------------------
# CSP generation per security level
# ---------------------------------------------------------------------------

_KNOWN_CDNS = (
    "https://cdnjs.cloudflare.com" " https://cdn.jsdelivr.net" " https://unpkg.com"
)


def _build_csp_tag(level: str) -> str:
    """Return a <meta> CSP tag for the given security level, or empty string.

    'unsafe-eval' is included because runtime expression compilers like
    Vega / Vega-Lite use new Function() internally and fail under
    strict CSP. 'unsafe-inline' is already present (inline scripts can
    execute arbitrary code), so adding 'unsafe-eval' does not
    meaningfully widen the attack surface — the real exfil blockers
    (connect-src, form-action, img-src, object-src) remain intact.
    """
    if level == "none":
        return ""

    if level == "strict":
        return (
            '<meta http-equiv="Content-Security-Policy" content="'
            f"default-src 'self'; "
            f"script-src 'unsafe-inline' 'unsafe-eval' {_KNOWN_CDNS}; "
            "style-src 'self' 'unsafe-inline'; "
            "connect-src 'none'; "
            "form-action 'none'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            '">'
        )

    # balanced: block outbound connections & forms, allow external images
    return (
        '<meta http-equiv="Content-Security-Policy" content="'
        f"default-src 'self'; "
        f"script-src 'unsafe-inline' 'unsafe-eval' {_KNOWN_CDNS}; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'none'; "
        "form-action 'none'; "
        "img-src * data: blob:; "
        "font-src 'self' data:; "
        "media-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        '">'
    )


def _build_html(
    security_level: str = "strict",
    title: str = "Visualization",
    lang: str = "en",
    chime: bool = True,
) -> str:
    """Wrap the streaming visualization shell: empty render area + observer.

    The observer tails the parent chat DOM for an ``@@@VIZ-START`` …
    ``@@@VIZ-END`` plain-text block in the assistant message and renders
    its contents live into #iv-render.
    """
    csp_tag = _build_csp_tag(security_level)
    strict_script = STRICT_SECURITY_SCRIPT if security_level == "strict" else ""
    safe_title = (
        title.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # Sanitize lang to a simple lowercase BCP-47 primary subtag.
    # Split on '-' first so "zh-CN" → "zh", not "zhcn".
    safe_lang = re.sub(r"[^a-z]", "", lang.split("-")[0].lower()[:5]) or "en"

    # Strip the chime script entirely when the valve is off — no bytes
    # shipped, no defined playDoneSound in the iframe. finalize()'s
    # typeof-function guard turns the missing definition into a no-op.
    body_scripts = BODY_SCRIPTS.replace(
        "/*__CHIME_BLOCK__*/", CHIME_SCRIPT if chime else ""
    )

    # Loader sits *below* the render area so content appears to flow
    # downward toward the pulsing dots — like a cursor following a pen.
    # The observer removes #iv-loader entirely on finalize().
    body_inner = (
        '<div id="iv-render"></div>\n'
        '<div id="iv-loader" class="iv-loading" aria-live="polite">'
        '<div class="iv-loading-dots"><span></span><span></span><span></span></div>'
        '<div class="iv-loading-label">Rendering visualization\u2026</div>'
        "</div>\n"
        f"{DOWNLOAD_BUTTON}\n"
        f"{body_scripts}"
        f"{STREAMING_OBSERVER_SCRIPT}"
        f"{strict_script}"
    )

    return (
        f'<!DOCTYPE html><html data-iv-lang="{safe_lang}" data-iv-build="{_IV_BUILD}"><head>'
        f"<title>{safe_title}</title>"
        f"{csp_tag}"
        f"<style>{THEME_CSS}\n{SVG_CLASSES}\n{BASE_STYLES}</style>"
        f'<script>try{{console.info("iv[build]","{_IV_BUILD}");}}catch(e){{}}</script>'
        f"{THEME_DETECTION_SCRIPT}"
        f"</head><body>\n{body_inner}\n</body></html>"
    )


# ---------------------------------------------------------------------------
# Valves (user-configurable settings)
# ---------------------------------------------------------------------------

# Developer reference for security levels:
#
#   STRICT   — Containment-oriented default. Blocks outbound fetch/XHR
#              (connect-src 'none'), form submissions, external images,
#              embedded objects, and base-URI hijacking. Injects a script
#              that strips URL query parameters from link navigation as
#              additional hygiene (query-only; does not cover path or
#              fragment, and does not intercept location.assign/replace).
#              Script execution within the visualization is intentionally
#              allowed ('unsafe-inline' + CDN allowlist) — this is
#              required for Chart.js, D3, and interactive visualizations.
#
#   BALANCED — Same as STRICT but allows external image loading (img-src *).
#              No URL parameter stripping. Note: img-src * permits
#              tracking pixels — this is an accepted privacy tradeoff
#              for visualizations that need external images.
#
#   NONE     — No CSP applied. Visualization can make arbitrary network
#              requests. Use only for visualizations that fetch live API
#              data (CORS restrictions still apply).
#
# Limitations that apply to ALL levels:
# - Script execution is always permitted (required for core features).
# - When iframe Same-Origin is enabled at the platform level, JS inside
#   the visualization can access the parent Open WebUI page. No CSP
#   level can prevent this — it is controlled by the platform setting.


# ---------------------------------------------------------------------------
# Inline Visualizer skill content — design system instructions returned by
# get_visualization_skill().  Kept here so the standalone tool file is fully
# self-contained and no separate Open WebUI skill needs to be installed.
# ---------------------------------------------------------------------------
_SKILL_CONTENT = """\
---
name: visualize
description: Render rich interactive visuals — SVG diagrams, HTML widgets, Chart.js charts, interactive explainers — directly inline in chat using the render_visualization tool. Use whenever the user asks to visualize, diagram, chart, draw, map out, or illustrate something, or when a topic has spatial, sequential, or systemic relationships a diagram would clarify better than prose.
---

# Inline Visualizer

Render rich interactive visuals directly inline in chat using `render_visualization`. Supports **live streaming** — the iframe fills in token-by-token as you generate the HTML/SVG.

## How to use

You call the tool with **only a title**, and then emit the HTML/SVG content wrapped in the **plain-text delimiters** `@@@VIZ-START` and `@@@VIZ-END`. The wrapper tails your stream and paints the iframe live.

1. Call `render_visualization(title="…")` - YOU MUST CALL THE TOOL, otherwise the visualization you output will not be rendered in the chat.
2. Open with `@@@VIZ-START` on its own line
3. Emit the HTML/SVG **content fragment** (no `<!DOCTYPE>`, `<html>`, `<head>`, `<body>`)
4. Close with `@@@VIZ-END` on its own line
5. Continue with any follow-up text

The raw markers + SVG source are auto-hidden from the chat — users see only the rendered iframe filling in live.

**Example response structure:**

```
I'll visualize the attention mechanism for you.

@@@VIZ-START
<svg viewBox="0 0 680 240">
  <!-- content streams here, renders live -->
</svg>
@@@VIZ-END

As you can see, each query token attends to all key tokens simultaneously.
```

**Streaming rules:**
- Use the delimiters EXACTLY `@@@VIZ-START` and `@@@VIZ-END` — case-sensitive, on their own lines. Do NOT put the content inside `` ``` ``, `~~~`, or `:::` fences.
- Do NOT wrap in HTML tags like `<viz>` or `<svg data-iv>` — only the text markers are detected.
- Emit **exactly ONE** `@@@VIZ-START` … `@@@VIZ-END` pair per tool call. For multiple visualizations, call the tool multiple times.
- Structure the content as always: `<style>` first → visible content → `<script>` last.
- Do NOT describe the HTML source in prose — users don't see it. Describe what the visualization **shows**.
- Requires **iframe Sandbox Allow Same Origin** in Open WebUI Settings → Interface. If disabled, the wrapper shows a notice — and the user won't see the visualization itself, just the notice.
- Any `<script>` you include runs once after the full block has streamed in.

## What's auto-injected

- Theme CSS, SVG classes, color ramps, height reporting, `sendPrompt()` bridge, and `openLink()` bridge
- Pre-styled bare-tag form elements (see below) — saves tokens on simple forms
- Consider making diagrams **conversational** with `sendPrompt()` — see the [sendPrompt bridge](#sendprompt-bridge--conversational-diagrams) section for patterns and examples

### Pre-styled form elements

These tags get theme-aware default styling **when emitted without a `class`
or inline `style` attribute**. Other attributes (`placeholder`, `value`,
`id`, `aria-*`, `min`/`max`, etc.) are fine — they don't disable the
defaults. Adding `class` or `style` is treated as an opt-out: the default
is suppressed and you can style it from scratch. Useful for short forms or
quick UIs where the design doesn't need to deviate.

Pre-styled (bare):

- `<button>` — themed button. Use it for actions.
- `<input type="text|number|email|search|password|tel|url|date|time|datetime-local">` — themed text input. Use it where a user types or picks a value.
- `<input type="range">` — slider. Use it for "from–to" picks, intensity dials, or any continuous value where exact precision doesn't matter.
- `<input type="checkbox">`, `<input type="radio">` — multi-pick / single-pick. Self-explanatory.
- `<textarea>` — multi-line text input.
- `<select>` — dropdown. Use it when a list of choices is too long for radios.
- `<label>`, `<fieldset>`, `<legend>` — form structure. Group related inputs and label them.
- `<kbd>` — keyboard-key cap. Use it whenever you mention a shortcut, so the key visually pops as a key.
  - Mac: `<kbd>⌘</kbd><kbd>K</kbd>`
  - Windows / Linux: `<kbd>Ctrl</kbd><kbd>K</kbd>`
- `<hr>` — horizontal divider. Separate sections inside a card or between groups of content.
- `<details>` / `<summary>` — collapsible disclosure. Use it for progressive disclosure: hide secondary detail behind a clickable summary so the surface stays clean.
- `<blockquote>` — pull-quote / callout. Use it to set apart a quote, an aside, or a piece of context the reader should pause on.
- `<table>` (with `<thead>` / `<tbody>` / `<th>` / `<td>` / `<caption>`) — tabular data with multiple columns and rows. Use it when the relationship between rows and columns matters. For numeric columns add `align="right"` or `class="num"` to the cells (right-aligns + tabular-nums).
- `<mark>` — highlighter. Use it sparingly to draw attention to a key word or number inside a sentence.
- `<dl>` / `<dt>` / `<dd>` — definition lists. **Far cheaper than tables for label/value layouts**. Three modes:
  - Bare `<dl>` → **stacked glossary**. Best when each term needs a sentence or two: definitions, FAQs, term-explained-below.
  - `<dl data-layout="grid">` → **two-column card**. The lightweight alternative to a table when you have key/value pairs and don't need row separators or hover: contact cards, metadata blocks, summary panels, settings rows.
  - `<dl data-layout="inline">` → **pill row** of `label: value` pairs (wrap each `<dt>`/`<dd>` in a `<div>`). Best for a tight strip of facts at the top of a card or near a chart: small numbers, status flags, tags. Colon separator is added automatically via CSS.

Bonus on bare elements:

- `aria-invalid="true"` paints a danger-colored border on input/textarea/select
- `:focus-visible` keyboard focus draws a clear `--accent` outline (mouse focus stays subtle)

```html
<!-- Bare → defaults apply -->
<label>Email <input type="email" placeholder="you@example.com"></label>
<button onclick="submit()">Save</button>

<!-- Custom — model owns the visual fully when class or style is present -->
<button class="primary-cta">Get started</button>
```

### Accent color palette

The default accent is **purple**. Switch to one of the other ramps via the
`data-accent` attribute. The chosen color drives `--accent` and
`--accent-foreground`, which in turn power focus rings, checkbox/radio
fills, and any `var(--accent)` reference you write yourself. The same
nine names match the chart color ramps, so a teal-accented form sits
naturally next to a teal-accented chart.

Available values: `purple` (default) · `teal` · `coral` · `pink` ·
`gray` · `blue` · `green` · `amber` · `red`

**Apply globally to the whole visualization** — wrap the entire content
in a single root `<div data-accent="…">`. Every supported element inside
inherits the chosen accent.

```html
<div data-accent="teal">
  <style>/* CSS */</style>
  …all focus rings, checkboxes, and var(--accent) consumers go teal…
</div>
```

**Apply to a section** — set `data-accent` on any inner container to recolor
just its subtree:

```html
<div data-accent="teal">
  <button>Save</button>            <!-- teal focus ring -->
  <input type="checkbox" checked>  <!-- teal accent -->
</div>
<button>Cancel</button>            <!-- still default purple -->
```

**Single element** — set directly on an element to recolor just it:

```html
<button data-accent="green">Approve</button>
<button data-accent="red">Reject</button>
```

Both light and dark themes are handled — accent values track per-theme
ramp stops automatically, and foreground text color flips for legibility
in dark mode. No manual override needed.

Pick an accent that matches the topic: `green` for finance/positive,
`red` for warnings/critical actions, `blue` for informational dashboards,
`amber` for attention/caution, etc. Default to `purple` for neutral or
multi-purpose visualizations.

## Output rules

These rules keep visuals clean, accessible, and consistent with the host UI:

- **Flat design** — no gradients, drop shadows, blur, glow, or noise textures (the host UI is flat; matching it prevents visual jarring). Exception: when the content is inherently full-bleed (maps, canvas simulations, space/astronomy diagrams, game boards), a custom background is permitted — but you then own all contrast. Every text element must achieve WCAG AA (≥4.5:1 contrast ratio) against your custom background. Use large, legible fonts (≥13px) for labels on dark backgrounds; do not rely on thin or rotated text where contrast is marginal.
- **No emoji** — use CSS shapes or SVG paths for icons (emoji render inconsistently across platforms)
- **Sentence case** — all labels and headings
- **Round displayed numbers** — use Math.round, toLocaleString, or Intl.NumberFormat
- **Min font size 11px** — smaller becomes unreadable on most screens
- **Text weights** — 400 regular, 500 for emphasis only
- **All explanatory text goes in your prose response**, not inside the visual (keeps visuals data-dense and lets the model's response provide context)
- **Build ambitiously when the topic supports it.** Treat each visualization like a small product surface, not a single static graphic. Combine multiple elements: a chart paired with a metric strip, a diagram with collapsible deep-dives, a comparison card with sliders that let the user explore tradeoffs. Use animation, hover, and click interactions where they help the reader notice or explore something — not for decoration. If the user asked for "a chart" and the topic naturally extends into a small dashboard, build the dashboard. Restraint is for cases where extra structure would distract; default to richness, not minimalism.

---

## Design system

### CSS variables (auto-injected — prefer these so light/dark mode just works)

The tool injects theme-aware CSS variables that adapt to light/dark mode automatically. Use them by default for text, surface, and border colors; reach for a specific hex only when the design genuinely calls for a fixed color (a brand mark, a deliberate accent that shouldn't track the theme).

| Token | Purpose |
|-------|---------|
| `--color-text-primary` | Main text |
| `--color-text-secondary` | Labels, muted text |
| `--color-text-tertiary` | Hints, placeholders |
| `--color-text-info/success/warning/danger` | Semantic text |
| `--color-bg-primary` | Main background |
| `--color-bg-secondary` | Cards, surfaces |
| `--color-bg-tertiary` | Page background |
| `--color-border-tertiary` | Default borders (0.15 alpha) |
| `--color-border-secondary` | Hover borders (0.3 alpha) |
| `--font-sans` | Default font |
| `--font-mono` | Code font |
| `--radius-md / --radius-lg / --radius-xl` | 8px / 12px / 16px |

### Color ramps (9 ramps, auto light/dark)

Each ramp provides fill, stroke, and text variants that adapt to the theme automatically via CSS classes.

| Ramp | 50 (light fill) | 200 | 400 | 600 (light stroke) | 800 (light title) |
|------|------|------|------|------|------|
| purple | #EEEDFE | #AFA9EC | #7F77DD | #534AB7 | #3C3489 |
| teal | #E1F5EE | #5DCAA5 | #1D9E75 | #0F6E56 | #085041 |
| coral | #FAECE7 | #F0997B | #D85A30 | #993C1D | #712B13 |
| pink | #FBEAF0 | #ED93B1 | #D4537E | #993556 | #72243E |
| gray | #F1EFE8 | #B4B2A9 | #888780 | #5F5E5A | #444441 |
| blue | #E6F1FB | #85B7EB | #378ADD | #185FA5 | #0C447C |
| green | #EAF3DE | #97C459 | #639922 | #3B6D11 | #27500A |
| amber | #FAEEDA | #EF9F27 | #BA7517 | #854F0B | #633806 |
| red | #FCEBEB | #F09595 | #E24B4A | #A32D2D | #791F1F |

**Color assignment rules:**
- Color encodes **meaning**, not sequence — don't cycle like a rainbow
- Group nodes by category — same type shares one color
- Use **gray** for neutral/structural nodes (start, end, generic)
- Use **2–3 colors** max per diagram
- Reserve blue/green/amber/red for semantic meaning (info/success/warning/error)

### Chart dataset colors (use 400 stops)

| Series | Color | Hex |
|--------|-------|-----|
| 1 | teal-400 | #1D9E75 |
| 2 | purple-400 | #7F77DD |
| 3 | coral-400 | #D85A30 |
| 4 | blue-400 | #378ADD |
| 5 | amber-400 | #BA7517 |

For area/line fills, use same color at 20% opacity.

---

## SVG setup

Always use this SVG boilerplate:

```svg
<svg width="100%" viewBox="0 0 680 H">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5"
      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke"
        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </marker>
  </defs>
</svg>
```

- viewBox width **always 680** — set H to **tightly fit** content (last element bottom + 40px). **Never oversize** — calculate the actual bottom of your last SVG element and add 40px. An SVG with content ending at y=180 must use H=220, not 500
- Safe area: x=40 to x=640
- Background transparent — host provides container. Exception: full-bleed content (space, maps, game boards) may set a custom background, but you must then guarantee WCAG AA contrast (≥4.5:1) for every text element against that background.

### SVG classes (auto-injected)

Drop these on SVG elements instead of writing inline `fill`, `stroke`, or
`font-size`. They track the theme automatically.

| Class | What it is | When to use |
|-------|------------|-------------|
| `.t` | 14px primary-color text | Default for any visible label inside a node, axis tick, or callout. |
| `.ts` | 12px secondary-color text | Subtitles, captions, units (e.g. "users", "ms"), supporting text under a `.t` label. |
| `.th` | 14px primary text, 500 weight | Node titles, KPI numbers, anything that needs to read as "the headline" of a small region. |
| `.box` | Neutral rect — secondary bg, tertiary border | Default container for a labeled region. Use whenever you need a neutral chip / panel and don't have a semantic color. |
| `.node` | Cursor-pointer + hover opacity on a `<g>` | Mark a `<g>` as clickable. Pair with `onclick="sendPrompt(...)"` so a user can drill into the topic. |
| `.arr` | 1.5px stroke matching theme borders | Arrow lines and connectors. Combine with `marker-end="url(#arrow)"`. |
| `.leader` | 0.5px dashed guide line | Pulling a label to a part of an illustration when the label can't sit on top of it. |
| `.c-{ramp}` | Sets fill/stroke + text colors on a whole `<g>` from one of the 9 color ramps | Color a node by category — apply `.c-teal` (etc.) to a `<g>` and every shape and text inside picks up the matching ramp. |

### Sizing text inside boxes

Browsers don't auto-size SVG boxes to text. To pick a width, estimate
the rendered glyph width per character and size the box from the
longest line.

- 14px text (`.t`, `.th`) → ~8 px / character
- 12px text (`.ts`) → ~7 px / character
- `box_width = max(title_chars × 8, subtitle_chars × 7) + 24` (12 px padding each side)

### Centering text in boxes

`<text>` defaults to `dominant-baseline="alphabetic"` — `y` is the text's
baseline, not its center, so a label placed at the vertical midpoint of
a box actually sits ~4 px too high. For text inside a node, callout, or
any rounded rect, add `dominant-baseline="central"` and put `y` at the
box midpoint.

Keep the default (no `dominant-baseline`) for text that's *meant* to sit
on a baseline: axis tick labels (resting on the axis line), legend labels
(aligned to the swatch baseline), and anything where the bottom edge of
the glyphs is the visual anchor. Setting `central` on those will make
them look ~4 px low instead.

---

## Diagram types

### Flowchart — sequential steps, decisions

- Max **4–5 nodes** per diagram — 6+ → decompose into overview + sub-flows
- Box spacing: 60px between boxes, 24px padding inside
- Single-line node: height 44px, two-line: 56px
- Arrows must not cross any box — use L-bends if needed
- Use `marker-end="url(#arrow)"` on arrow paths

Single-line node:
```svg
<g class="node c-teal" onclick="sendPrompt('Tell me about X')">
  <rect x="100" y="20" width="180" height="44" rx="8"/>
  <text class="th" x="190" y="42" text-anchor="middle" dominant-baseline="central">Label</text>
</g>
```

Two-line node:
```svg
<g class="node c-teal">
  <rect x="100" y="20" width="200" height="56" rx="8"/>
  <text class="th" x="200" y="38" text-anchor="middle" dominant-baseline="central">Title</text>
  <text class="ts" x="200" y="56" text-anchor="middle" dominant-baseline="central">Subtitle</text>
</g>
```

### Architecture — nested regions, layered systems

For diagrams that show **what contains what**: services inside zones,
modules inside layers, components inside subsystems. The nesting itself
is the information — outer regions are the system, inner regions are
the parts.

- Outermost container: `rx=20–24`, lightest ramp fill (the 50 stop), 0.5px stroke
- Inner regions: `rx=8–12`, a darker stop of the same ramp — or a different ramp when the inner region is semantically distinct (e.g. external service inside an internal cluster)
- 20px minimum padding between an inner region's bounds and its parent's edge
- Max 2–3 nesting levels — beyond that, decompose into a top-level overview plus sub-diagrams

### Illustrative — explain a mechanism by drawing it

For "how does this actually work" topics where the answer is spatial:
how light refracts through a prism, how a transformer attention head
weighs tokens, how a heat pump moves heat against a gradient. **Draw
the thing itself**, not a labeled diagram about it.

- Shapes are freeform — paths, ellipses, polygons, curves — not just rounded rects
- Color encodes intensity or state, not category: warm ramps for active / hot / energized, cool ramps for calm / cold / passive, gray for neutral / inert
- Labels live outside the object connected via `.leader` lines — reserve a ~140px gutter on the side you'll label from
- Strongly prefer **interactive** illustrative diagrams: if the real system has a knob, a slider, or a phase, expose it. A prism with a draggable angle slider teaches refraction better than five static frames.

---

## Charts (Chart.js)

Load Chart.js in your HTML fragment:
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
```

Setup pattern:
```html
<div style="position: relative; height: 300px;">
  <canvas id="chart"></canvas>
</div>
<script>
const ctx = document.getElementById('chart').getContext('2d');
const s = getComputedStyle(document.documentElement);
const textColor = s.getPropertyValue('--color-text-secondary').trim();
const gridColor = s.getPropertyValue('--color-border-tertiary').trim();

new Chart(ctx, {
  type: 'bar',
  data: {
    labels: ['Q1','Q2','Q3','Q4'],
    datasets: [{ label: 'Revenue', data: [12,19,8,15],
      backgroundColor: '#1D9E75', borderRadius: 4, borderSkipped: false }]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: textColor, font: { size: 12 } } } },
    scales: {
      x: { grid: { display: false }, ticks: { color: textColor, font: { size: 12 } }, border: { color: gridColor } },
      y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 12 } }, border: { display: false } }
    }
  }
});
</script>
```

**Chart rules:**
- Wrap canvas in container with `position: relative` and explicit height — without it, `maintainAspectRatio: false` collapses the canvas to zero
- Always pass `responsive: true, maintainAspectRatio: false` in `options` — without `maintainAspectRatio: false`, Chart.js locks the canvas to a 2:1 aspect and ignores the container height; without `responsive: true`, it won't redraw when the iframe re-measures. You have to set them explicitly on every `new Chart(...)` call (Chart.js reads options at construction time, so there's no global default we could pre-set for you).
- Read CSS variables for text/border colors so the chart tracks the theme
- `borderRadius: 4` on bars
- Line charts: `tension: 0.3` for smooth curves
- Doughnut: `cutout: '60%'` — never use pie

**Chart type selection:**

| Data shape | Type | Notes |
|-----------|------|-------|
| Categories + values (a few items, comparable magnitudes) | **Bar** | Default for "compare values across labels". Switch to a horizontal bar (`indexAxis: 'y'`) when labels are long, when there are 8+ categories, or when ranking is the point. |
| Time series, anything sampled at regular intervals | **Line** | `tension: 0.3` for a natural curve. Stack multiple datasets when you're comparing trends, not when each line wanders independently — overlap gets unreadable past 4 lines. |
| Parts of a whole, ≤5 slices | **Doughnut** | Use `cutout: '60%'` so the empty middle can hold a total or label. Skip if the segments are very uneven (one slice >70%) — the small slices vanish; show a stacked bar instead. |
| Two continuous variables, looking for correlation | **Scatter** | Add a trend line if the relationship is the takeaway. For dense clouds, drop point opacity to 0.3–0.5 so density reads. |
| Stacked / cumulative composition over time | **Stacked bar / stacked area** | Bar when the buckets are discrete (months, segments); area when the underlying signal is continuous. |
| Single-value vs target / threshold | **Bar with reference line** or KPI card | A whole chart is overkill for one number — consider a metric card with a sparkline instead. |
| Multi-dimensional comparison (3–6 axes) | **Radar** | Only when the axes are genuinely commensurate — otherwise a small-multiples bar grid is clearer. |

### Inline SVG charts (no library)

Reach for inline SVG when the data is small, the shape is simple, or
you want the chart to share design with surrounding diagrams (matching
corner radii, palette, type). No script, no CDN — just shapes and text.
Reach for Chart.js when you need axes, tooltips, hover, animation, or
many series.

**Good fits for inline SVG:**
- **Progress / completion bar** — a value rendered against a fixed track,
  often paired with a percentage label to its right
- **Ranking strip** — a small number of horizontal bars stacked
  vertically, each bar a different category color, sized by value
- **Sparkline** — a terse trend line with no axes that sits next to a
  number to give the number context
- **KPI donut / ring** — a single percentage rendered as a circle arc,
  with the number in the middle of the ring
- **Stacked composition row** — one horizontal bar split into colored
  segments to show parts of a whole, when a doughnut would feel heavy
- **Custom-shape charts** — anything where the chart shape is part of
  the metaphor (a thermometer for temperature, a battery for charge,
  a fuel gauge, a tide-line)

**Theme consistency for inline SVG:**
- Use the `.t` / `.ts` / `.th` classes on `<text>` for labels, captions,
  and headlines. They pick up the theme's text colors and typography
  scale automatically. Never set `font-size` or `fill` on label text
  manually unless you need a specific deviation.
- For neutral backgrounds (track behind a progress bar, empty slot in a
  ring), use `fill="var(--color-bg-secondary)"` so it blends into the
  surrounding card.
- For data colors, prefer the chart-dataset 400-stop hexes from the
  table above — they're calibrated to read on both light and dark
  backgrounds. If you need a *whole group* recolored (rect + label +
  stroke together), wrap it in a `<g class="c-teal">` (or any of the
  9 ramp classes) and let the SVG class system handle fill + stroke +
  text in one shot.
- Keep stroke-widths to 0.5 px for chrome (axis lines, grid) and
  1.5 px for data (lines, sparklines) — matches the 0.5 px borders
  the rest of the host UI uses, so the chart doesn't feel chunkier
  than its neighbors.
- Add `opacity="0.85"` on data fills — softens the color slightly so
  it sits comfortably next to text without overwhelming it.

**Math hints for the less obvious shapes:**
- Donut arc length: circumference = `2 × π × r`. To draw `v%` of the
  ring, set `stroke-dasharray="{v×circumference/100} {circumference}"`
  on the foreground circle, and `transform="rotate(-90 cx cy)"` so the
  arc starts at 12 o'clock instead of 3 o'clock.
- Bar widths in a `viewBox="0 0 680 …"`: leave 40 px of margin on each
  side, giving a 600 px usable plot width.

---

## Component patterns

### Metric cards — KPI strip
```html
<div style="display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px;">
  <div style="background:var(--color-bg-secondary); border:0.5px solid var(--color-border-tertiary);
    border-radius:var(--radius-lg); padding:16px;">
    <div style="font-size:12px; color:var(--color-text-secondary);">Revenue</div>
    <div style="font-size:28px; font-weight:500; color:var(--color-text-primary); margin-top:4px;">$3,870</div>
    <div style="font-size:12px; color:var(--color-text-success); margin-top:2px;">▲ 12.4%</div>
  </div>
  <!-- repeat for other metrics -->
</div>
```
Pair with a chart below for a compact dashboard. Add a tiny inline-SVG
sparkline under each value if the trend matters.

### Comparison layout — two paths side by side
```html
<div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
  <div style="background:var(--color-bg-secondary); border:0.5px solid var(--color-border-tertiary);
    border-radius:var(--radius-lg); padding:18px;">
    <div style="font-size:14px; font-weight:500;">Monolith</div>
    <dl data-layout="grid" style="margin-top:12px;">
      <dt>Deploy unit</dt><dd>1 service</dd>
      <dt>Latency</dt><dd>Low (in-process)</dd>
      <dt>Scaling</dt><dd>Vertical</dd>
    </dl>
  </div>
  <div style="background:var(--color-bg-secondary); border:0.5px solid var(--color-border-tertiary);
    border-radius:var(--radius-lg); padding:18px;">
    <div style="font-size:14px; font-weight:500;">Microservices</div>
    <dl data-layout="grid" style="margin-top:12px;">
      <dt>Deploy unit</dt><dd>N services</dd>
      <dt>Latency</dt><dd>Higher (network)</dd>
      <dt>Scaling</dt><dd>Horizontal per service</dd>
    </dl>
  </div>
</div>
```

### Interactive explainer — slider drives output
```html
<label style="display:flex; gap:12px; align-items:center;">
  <span style="min-width:80px;">Interest</span>
  <input type="range" id="rate" min="0" max="20" step="0.1" value="5" style="flex:1;">
  <span id="rate-out" style="min-width:48px; font-variant-numeric:tabular-nums;">5.0%</span>
</label>
<div id="result" style="margin-top:12px; font-size:24px; font-weight:500;"></div>

<script>
var rate = document.getElementById('rate');
var out = document.getElementById('rate-out');
var result = document.getElementById('result');
function recalc() {
  var r = parseFloat(rate.value);
  out.textContent = r.toFixed(1) + '%';
  result.textContent = '$' + (10000 * Math.pow(1 + r/100, 10)).toFixed(0);
}
rate.addEventListener('input', recalc);
recalc();
</script>
```
The pattern generalises: every interactive element binds an `input`
listener, recomputes a value, and writes it to a result node. Pair with
an inline SVG that re-draws on every input change for a "live diagram".

### Tabs — a piece of UI users already know
```html
<div style="display:flex; gap:4px; border-bottom:0.5px solid var(--color-border-tertiary);">
  <button class="tab active" onclick="showTab('a', this)">Overview</button>
  <button class="tab" onclick="showTab('b', this)">Details</button>
  <button class="tab" onclick="showTab('c', this)">Source</button>
</div>
<div id="tab-a" class="tab-panel">…</div>
<div id="tab-b" class="tab-panel" hidden>…</div>
<div id="tab-c" class="tab-panel" hidden>…</div>

<style>
  .tab { background:none; border:none; padding:8px 12px; cursor:pointer;
         border-bottom:2px solid transparent; }
  .tab.active { border-bottom-color: var(--accent); color: var(--color-text-primary); }
  .tab-panel { padding:12px 0; }
</style>

<script>
function showTab(id, btn) {
  document.querySelectorAll('.tab-panel').forEach(p => p.hidden = true);
  document.getElementById('tab-' + id).hidden = false;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}
</script>
```
Persist the active tab with `saveState`/`loadState` so it survives reloads.

**Charts in inactive tabs render at 0×0.** Plotly, ECharts, and
vis-network all measure their container at init time. If that container
is inside a `hidden` / `display:none` panel, they paint into a zero-size
canvas and stay blank even after the tab becomes visible. Two
workarounds, pick one:

1. **Lazy-init**: only call `Plotly.newPlot` / `echarts.init` /
   `new vis.Network` the first time its tab is shown (track a
   `tabInit[id]` flag in the handler).
2. **Resize on show**: init everything up front (so data is ready), then
   in `showTab` call the right resize hook for whichever lib is in that
   tab. Note the API differs per library — `c.resize()` does not work
   for all of them:

   ```js
   // ECharts: instance.resize()
   echartsInstance.resize();
   // Plotly: pass the container element, no .resize() on the chart
   Plotly.Plots.resize(document.getElementById('plotly-container'));
   // vis-network: redraw + fit — the instance has no .resize()
   networkInstance.redraw();
   networkInstance.fit();
   // Chart.js: instance.resize() — but Chart.js auto-resizes on
   // container size change so usually nothing needed.
   ```

   Skip the resize call for D3 / Vega-Lite / inline SVG — they paint
   declaratively into the SVG namespace and aren't bothered by hidden
   parents.

### Step-through walkthrough — guided narrative
A "Next ▶" button advances through a sequence of stages, each with its
own caption and (optionally) a different highlighted region of the same
diagram. Useful for explaining algorithms, processes, or any topic where
the order matters more than the totals.
```html
<div id="stage" style="font-size:14px;">Click Next to begin.</div>
<button onclick="step()">Next ▶</button>

<script>
var steps = [
  'Step 1: request lands at the load balancer',
  'Step 2: routed to a healthy backend',
  'Step 3: backend writes to primary DB',
  'Step 4: replica catches up async',
];
var i = 0;
function step() {
  document.getElementById('stage').textContent = steps[i % steps.length];
  i++;
}
</script>
```

---

## sendPrompt bridge — conversational diagrams

`sendPrompt(text)` is the function that makes visualizations conversational. When called, it injects the given text into the chat input field and submits it — exactly as if the user had typed and sent it themselves. The model then receives that message and responds normally, creating a feedback loop between the visual and the conversation.

This is what separates a static diagram from an **exploration interface**. A user sees a system architecture diagram, clicks on the "Load Balancer" node, and the model receives "Tell me more about the load balancer — how does it distribute traffic across the backend services?" as a user message. The model then responds with details, and could even generate a *new* sub-diagram showing the load balancer internals. The user never had to type anything — they just clicked.

### Why this matters

Without sendPrompt, interactive elements inside the iframe are isolated — they can toggle visibility, animate, or filter data, but they can never talk back to the model. The user sees a cool diagram but has to manually type follow-up questions. With sendPrompt, every clickable element becomes a conversation starter. The diagram itself becomes a navigation interface for the topic.

### Writing good sendPrompt text

The text you pass to sendPrompt becomes the user's message to the model. Write it as a natural follow-up question — conversational, specific, and referencing the context of the diagram:

**Good prompt text** (specific, contextual, references the diagram):
- `"Explain the attention mechanism — how does it decide which tokens to focus on?"`
- `"Break down the CI/CD pipeline stage. What tools are typically used here?"`
- `"Show me a more detailed diagram of the data processing layer"`
- `"What happens when the load balancer detects a failed backend node?"`
- `"Compare the pros and cons of the monolith vs microservices approach shown here"`

### Usage patterns

Simple patterns — single-click sendPrompt on a node or button:
- **Drill-down**: `onclick="sendPrompt('Explain the API gateway — what does it handle?')"` on a diagram node
- **Quiz answer**: `onclick="sendPrompt('I chose B: O(n log n). Am I right? Explain why.')"` on answer buttons
- **Guided exploration**: `onclick="sendPrompt('Show me a more advanced example with edge cases.')"` on a "Go deeper →" button
- **Comparison**: `onclick="sendPrompt('Compare REST vs GraphQL — when should I use each?')"` on one of two nodes

**Form / preference collector** — gather multiple user selections, then send them all at once. Use local JS to track choices (button highlights, state object) and a submit button that composes a sendPrompt from the collected answers:
```html
<script>
var choices = {};
function pick(category, value, btn) {
  choices[category] = value;
  // Highlight selected button, dim siblings
  btn.parentElement.querySelectorAll('button').forEach(function(b) {
    b.classList.toggle('active', b === btn);
  });
}
function submitChoices() {
  var parts = [];
  for (var k in choices) parts.push(k + ': ' + choices[k]);
  sendPrompt('Here are my preferences:\\n' + parts.join('\\n') + '\\nGive me a personalized recommendation based on these choices.');
}
</script>

<h3>What's your style?</h3>
<p style="margin:8px 0 4px;">Pace</p>
<button onclick="pick('pace','relaxed',this)">Relaxed</button>
<button onclick="pick('pace','moderate',this)">Moderate</button>
<button onclick="pick('pace','intensive',this)">Intensive</button>

<p style="margin:8px 0 4px;">Focus</p>
<button onclick="pick('focus','culture',this)">Culture</button>
<button onclick="pick('focus','nature',this)">Nature</button>
<button onclick="pick('focus','food',this)">Food</button>

<button onclick="submitChoices()" style="margin-top:12px; font-weight:500;">Get my recommendation →</button>
```
This pattern is powerful because the model receives a structured summary of all user preferences in one message. Use local JS for the selection UI (instant feedback), then sendPrompt only on final submit.

### When to use sendPrompt vs local JS:
| User action | Use | Why |
|------------|-----|-----|
| Learn more about a component | `sendPrompt` | Model gives a contextual explanation |
| Explore a stage / drill down | `sendPrompt` | Model can generate a sub-diagram |
| Submit answers or preferences | `sendPrompt` | Model evaluates or personalizes |
| Toggle views, adjust sliders | Local JS | Instant feedback, no reasoning needed |
| Filter/sort data | Local JS | Instant response, no model needed |

---

## Interactivity by default

Build dashboards, charts, graphs, interactive functions, animated sections, moving objects, explandable detail sections, cards, copyable text elements and more. If the topic allows and it makes sense for the topic, build complex and visually stunning elements.

Visualizations should feel alive and polished — not static images dumped into chat. Build interfaces that invite interaction:

- **Expandable sections** — use collapsible `<details>` elements or JS-toggled sections so users can explore at their own pace without overwhelming them upfront
- **Hover effects** — nodes, buttons, and cards should respond to hover (the `.node` class adds this for SVG elements; for HTML, use `:hover` styles)
- **Smooth transitions** — add `transition: all 0.2s ease` to interactive elements for a polished feel
- **Active states** — when a user selects an option or clicks a tab, make the selection visually clear with the `.active` class or distinct styling
- **Progressive disclosure** — show a clean overview first, let the user click to reveal detail (tabs, accordions, or sendPrompt for model-powered drill-down)

**The goal is to build something that feels like a real app component embedded in chat with reactivity, sections and extra elements** — not a screenshot. If the visualization has multiple facets, give the user controls to explore them. If it has hierarchical information, let them expand and collapse. If it has data, let them sort or filter.

---

## openLink bridge — opening URLs from visualizations

`openLink(url)` opens a URL in a new browser tab from within the visualization iframe. Normal `<a href="...">` links inside an iframe can behave unpredictably (opening inside the iframe, being blocked by sandbox restrictions, etc.). This function handles that by opening the link in the parent window instead.

```html
<button onclick="openLink('https://docs.example.com/api-reference')">
  Open API docs ↗
</button>
```

Or in SVG:
```svg
<g class="node c-blue" onclick="openLink('https://github.com/org/repo')">
  <rect x="100" y="20" width="200" height="44" rx="8"/>
  <text class="th" x="200" y="42" text-anchor="middle" dominant-baseline="central">View source ↗</text>
</g>
```

Use `openLink` for external references, documentation links, or source code links. Unlike `sendPrompt`, this navigates away from the chat — use it when the user needs to access an external resource, not when they need the model to explain something.

---

## copyText + toast bridges — feedback on user actions

`copyText(text)` copies `text` to the system clipboard and automatically shows a localized "Copied" toast in the top-right corner of the iframe. Works from HTTPS and HTTP origins (falls back to `execCommand('copy')` if the async Clipboard API is blocked). Use this on "Copy" buttons inside interactive visualizations — data tables, code snippets, shareable values.

```html
<button onclick="copyText(JSON.stringify(data, null, 2))">Copy JSON</button>
```

`toast(message, kind)` shows a small auto-dismissing banner inside the iframe. `kind` is optional and controls the text color: `'success'` (green, default), `'info'` (blue), `'warn'` (amber), `'error'` (red). Use it for status notifications inside long-running interactive tools — "Calculation done", "Invalid input", etc.

```html
<button onclick="recompute(); toast('Recomputed', 'info')">Recompute</button>
```

Toasts auto-dismiss after ~2.2 s and stack vertically if fired in quick succession.

---

## saveState + loadState bridges — persistent interactive state

`saveState(key, value)` and `loadState(key, fallback)` proxy `parent.localStorage` with a key prefix scoped to **this assistant message**. State survives page reloads and tab switches, but two different chats (or different messages in the same chat) each get their own independent state — no cross-contamination.

```html
<script>
  // Restore toggle state on load
  var showRaw = loadState('showRaw', false);
  document.getElementById('raw-toggle').checked = showRaw;
  applyView(showRaw);

  function onToggleChange(el) {
    saveState('showRaw', el.checked);
    applyView(el.checked);
  }
</script>
```

Use it for: selected tabs, picked chart range, hidden/shown layers, theme overrides, collapsed sections — anything the user would expect to be remembered when they re-open the chat.

Values are JSON-serialized. If `localStorage` is blocked (private browsing, sandboxed), both functions silently no-op and `loadState` returns `fallback`.

---

## CDN libraries

Strict-mode CSP allowlists three CDN hosts. Anything served from them
loads — no plugin tweaking needed, even in strict security mode.

Allowed hosts:
- `cdnjs.cloudflare.com` — widest coverage
- `cdn.jsdelivr.net` — npm / GitHub backed, supports minor-version pinning
- `unpkg.com` — npm mirror

Common picks:

| Library | Why reach for it | Example loader |
|---------|------------------|----------------|
| **Chart.js** | Bar / line / doughnut / scatter with animation out of the box | `<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>` |
| **D3.js** | Custom data-driven SVG (force graphs, arcs, maps, non-standard charts) | `<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>` |
| **Vega-Lite** | Declarative grammar of graphics — feed it a JSON spec, it draws the chart | `<script src="https://cdn.jsdelivr.net/npm/vega@5"></script><script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script><script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>` |
| **ECharts** | Rich interactive dashboards, advanced chart types | `<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.5.0/echarts.min.js"></script>` |
| **Plotly** | Scientific / 3D plots, statistical charts | `<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist@2"></script>` |
| **vis-network** | Force-directed network / node-link graphs | `<script src="https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>` (the **standalone** UMD bundle — exposes `vis.Network` *and* `vis.DataSet`. The bare `vis-network.min.js` on cdnjs is the *peer* build and requires `vis-data` loaded separately, otherwise `new vis.DataSet(...)` throws `vis is not defined`.) |
| **Tone.js / Wavesurfer** | Audio synthesis, waveform visualisation | `<script src="https://cdnjs.cloudflare.com/ajax/libs/tone/15.0.4/Tone.js"></script>` |

Anything else on those three CDNs is fair game — `apexcharts`, `d3-force`,
`konva`, `flatpickr`, etc. Pick whatever fits the topic.

---

## Library init

Two patterns to follow when using a CDN library:

### 1 · Wrap a Chart.js canvas in a fixed-height container

`maintainAspectRatio: false` makes Chart.js use the container's height.
If the canvas has no intrinsic height (e.g. inside a flex column without
a height set), it collapses to zero and nothing draws:

```html
<div style="position: relative; height: 260px;">
  <canvas id="chart"></canvas>
</div>
<script>
  new Chart(document.getElementById('chart').getContext('2d'), {
    type: 'bar',
    data: { /* … */ },
    options: { responsive: true, maintainAspectRatio: false, /* … */ }
  });
</script>
```

### 2 · Source order matters

Put external `<script src="…">` tags **before** the inline `<script>` that
uses them. They execute in order, so a consumer that runs before its
library is loaded will fail with `Chart is not defined`.

```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>/* uses Chart and d3 */</script>
```
"""


class Tools:
    """Inline Visualizer — renders interactive HTML/SVG in chat.

    Security is controlled via the ``security_level`` valve, which applies
    a Content Security Policy to the rendered iframe.  Defaults to STRICT,
    which blocks outbound network requests (fetch/XHR) and form submissions.
    Script execution is always permitted — it is required for interactive
    visualizations, Chart.js, and D3.  See the developer reference above
    for the full security model and its limitations.
    """

    class Valves(BaseModel):
        security_level: Literal["strict", "balanced", "none"] = Field(
            default="strict",
            description="Strict (default): blocks outbound fetch/XHR, images, and forms; scripts always allowed. Balanced: also allows external images. None: no restrictions.",
        )
        chime: bool = Field(
            default=True,
            description="Play a soft three-note chime when a live-streamed visualization finishes. When off, the chime script is omitted from the iframe entirely (not shipped as a no-op).",
        )
    def __init__(self):
        self.valves = self.Valves()

    async def render_visualization(
        self,
        title: str = "Visualization",
        __event_call__=None,
    ) -> tuple:
        """
        Render an interactive HTML or SVG visualization inline in the chat.

        IMPORTANT: You MUST call get_visualization_skill() FIRST to load the design system
        before calling this tool. Never generate a visualization without reading the skill
        instructions first — they contain critical rules for colors, layout, SVG setup,
        chart patterns, and common failure points.

        **IMPORTANT:** When to use the tool:
        Use this tool only when the user has explicitly said to visualize something.
        Do not use it when it would fit the response to visualize something but only when
        there is CLEAR INTENT by the user to want something visualized in the chat.

        The tool mounts an empty visualization wrapper in the chat.
        Then, in your text response that follows, wrap the HTML/SVG in the TEXT DELIMITERS
        @@@VIZ-START / @@@VIZ-END:

            @@@VIZ-START
            <svg viewBox="0 0 680 240">...</svg>
            @@@VIZ-END

        The wrapper tails your streaming text and renders the content between the
        markers LIVE, token-by-token, into the iframe. Users see the visualization
        paint progressively as you generate it. The raw markers + SVG source are
        auto-hidden from the chat, so users see only the rendered iframe.

        The system automatically injects:
        - Theme CSS variables (auto-detected light/dark mode)
        - SVG utility classes: .t .ts .th .box .node .arr .leader
        - Color ramp classes: .c-purple .c-teal .c-coral .c-pink .c-gray .c-blue .c-green .c-amber .c-red
        - Base element styles (button, range, select, code, headings)
        - Height auto-sizing script
        - sendPrompt(text) function — sends a message to the chat (requires iframe Sandbox Allow Same Origin)
        - openLink(url) function — opens a URL in a new tab
        - saveState() and loadState() function
        - copyText() function

        :param title: Short descriptive title for the visualization.
        :return: Interactive rich embed rendered in the chat, with LLM context.
        """
        # Detect UI language via parent page JS (same pattern as PDF/Gamma actions)
        lang = "en"
        if __event_call__:
            try:
                lang_result = await __event_call__(
                    {
                        "type": "execute",
                        "data": {"code": """
return (() => {
  try {
    const stored = localStorage.getItem('locale')
                || localStorage.getItem('language')
                || localStorage.getItem('i18nextLng');
    if (stored) {
      const l = stored.split('-')[0].toLowerCase();
      if (l) return l;
    }
  } catch (e) {}
  try {
    return (navigator.language || navigator.userLanguage || 'en').split('-')[0].toLowerCase();
  } catch (e) {}
  return 'en';
})();
"""},
                    }
                )
                if isinstance(lang_result, str) and lang_result.strip():
                    lang = lang_result.strip()
            except Exception:
                pass

        response = HTMLResponse(
            content=_build_html(
                self.valves.security_level,
                title,
                lang,
                chime=self.valves.chime,
            ),
            headers={"Content-Disposition": "inline"},
        )
        result_context = (
            f'Visualization wrapper "{title}" is mounted and waiting for content. '
            f"Now emit the HTML/SVG in your NEXT text response wrapped in the "
            f"TEXT delimiters @@@VIZ-START and @@@VIZ-END, each on their own line. "
            f"The wrapper will tail your stream and render live. These are PLAIN "
            f"TEXT markers — NOT a ``` code fence, NOT HTML tags, NOT a ::: fence. "
            f"Example:\n\n"
            f"    @@@VIZ-START\n"
            f'    <svg viewBox="0 0 680 240">…</svg>\n'
            f"    @@@VIZ-END\n\n"
            f"Write explanatory prose BEFORE and AFTER the block — do not describe "
            f"the HTML source itself. Emit exactly ONE @@@VIZ-START/@@@VIZ-END pair "
            f"for this tool call."
        )
        return response, result_context

    async def get_visualization_skill(self) -> str:
        """
        Load and return the Inline Visualizer design-system instructions.

        Call this tool BEFORE calling render_visualization. It returns the full
        skill reference — color system, layout rules, SVG patterns, chart recipes,
        and common failure points — that you must follow when authoring the
        HTML/SVG content for the visualization.

        :return: Full text of the inline-visualizer design-system skill.
        """
        return _SKILL_CONTENT
