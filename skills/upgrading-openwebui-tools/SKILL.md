---
name: upgrading-openwebui-tools
description: Verifies and updates the extracted Dartmouth Chat tools for compatibility after an Open WebUI upgrade. Use when open-webui has been bumped to a new version and the tools in src/dartmouth_chat_tools/ need to be checked for breaking changes against open_webui builtin.py and the private API surface.
---

# Upgrading Open WebUI tools

The tools in `src/dartmouth_chat_tools/` were extracted from Open WebUI's private
internals so they can be added to the Workspace as standalone tools. Two categories
exist:

1. **Builtin-derived tools** — pulled from `open_webui/tools/builtin.py`. Each maps
   to a `# SECTION NAME` block in that file. Their `version:` header tracks the
   Open WebUI version they were extracted from.
2. **Fully-custom tools** — written from scratch, but still call Open WebUI's
   private API (`open_webui.models.*`, `open_webui.routers.*`, `open_webui.utils.*`).

Both categories break when Open WebUI renames a method, changes a signature, or
makes a sync function async. This skill verifies compatibility after an upgrade
and applies the minimal fixes.

## When to run

The user upgraded open-webui (e.g. 0.9.2 → 0.9.6) and wants the tools confirmed
compatible and updated as needed.

## Key facts

- Installed package lives at `.venv/lib/python3.12/site-packages/open_webui/`.
- Confirm the installed version:
  `cat .venv/lib/python3.12/site-packages/open_webui-*/METADATA | grep -i "^Version:"`
- The old version's `builtin.py` is fetched from GitHub raw at tag `v<OLD>`:
  `https://raw.githubusercontent.com/open-webui/open-webui/v<OLD>/backend/open_webui/tools/builtin.py`
- The `version:` header in **every** tool file (builtin-derived and fully-custom
  alike) tracks the Open WebUI version it was last checked against. After an
  upgrade, bump every tool's `version:` header to the new Open WebUI version —
  even tools that needed zero code changes — once you've confirmed it still
  works. The version number is the audit trail: it shows at a glance whether a
  tool has been checked against the current Open WebUI version.

## Workflow

Copy this checklist and check off as you go:

```
Upgrade Progress:
- [ ] Step 1: Confirm old and new open-webui versions
- [ ] Step 2: Diff old vs new builtin.py; identify functional changes
- [ ] Step 3: Map builtin sections to local builtin-derived tool files
- [ ] Step 4: For each affected builtin-derived tool, verify + fix API usage
- [ ] Step 5: Verify fully-custom tools' private-API usage still resolves
- [ ] Step 6: Compile-check every changed file
- [ ] Step 7: Bump version headers on ALL tool files (ask first) and report
```

### Step 1: Confirm versions

Get the NEW (installed) version from METADATA. Get the OLD version from the current
`version:` headers: `grep -rn "^version:" src/dartmouth_chat_tools/*.py`.

### Step 2: Diff builtin.py

Fetch the old builtin.py and diff against the installed one. This is the fastest way
to find real changes instead of guessing:

```bash
python skills/upgrading-openwebui-tools/scripts/diff_builtin.py <OLD_VERSION>
```

The script prints a filtered diff highlighting changed `def`/`class`/`await` lines
and the full unified diff. **Ignore import reordering** (alphabetization is cosmetic).
Focus on:
- Renamed methods (e.g. `Automations.update` → `update_by_id`)
- sync → async conversions (a `to_thread(fn, ...)` wrapper is now wrong; call `await fn(...)`)
- Changed return shapes / new error branches
- New required params (params with defaults are safe)

### Step 3: Map sections to files

builtin.py is organized into `# SECTION NAME` banner comments. The mapping is:

| builtin.py section        | local file            |
| ------------------------- | --------------------- |
| TIME UTILITIES            | `time.py`             |
| WEB SEARCH TOOLS          | `web_search.py`       |
| IMAGE GENERATION TOOLS    | `image.py`            |
| CODE INTERPRETER TOOLS    | `code_interpreter.py` |
| MEMORY TOOLS              | `auto_memory.py`*     |
| NOTES TOOLS               | `notes.py`            |
| CHATS TOOLS               | `chats.py`            |
| CHANNELS TOOLS            | `channels.py`         |
| KNOWLEDGE BASE TOOLS      | `knowledge.py`*       |
| SKILLS TOOLS              | (not extracted)       |
| TASK MANAGEMENT TOOLS     | `tasks.py`            |
| AUTOMATION TOOLS          | `automations.py`      |
| CALENDAR TOOLS            | (not extracted)       |

*`auto_memory.py` and `knowledge.py` are heavily customized forks whose function
names differ from builtin. Do NOT port new builtin features into them — only verify
their existing private-API calls still resolve. Re-derive this table from the
banner comments if sections were added/removed (see script output).

### Step 4: Fix affected builtin-derived tools

For each tool whose section had a functional change, read the local file and the
corresponding installed builtin section, then apply the minimal edit that matches
upstream behavior. Verify every private-API symbol the change touches with the
resolver script (Step 5 command works for any file).

### Step 5: Verify fully-custom tools

Fully-custom tools (not in the table above) still import private Open WebUI API.
List every `open_webui` symbol each file uses and confirm it still exists with a
compatible signature in the installed package:

```bash
python skills/upgrading-openwebui-tools/scripts/check_api.py src/dartmouth_chat_tools/<file>.py
```

The script extracts `open_webui` imports (top-level and lazy/in-function) plus
`await X.method(` call sites, then greps the installed package for each definition
and prints its signature. Manually confirm:
- The symbol still exists.
- sync/async matches how the local code calls it (awaited vs not).
- Call-site kwargs are still valid params (new params with defaults are fine).

Pay special attention to functions that became `async` (must be `await`ed) and to
handlers called with a mock `Request` — confirm the code path the tool exercises
(e.g. `process=False` in `upload_file_handler`) doesn't read newly-required
`request.app.state` attributes.

### Step 6: Compile-check

```bash
for f in src/dartmouth_chat_tools/*.py; do .venv/bin/python -m py_compile "$f" \
  && echo "OK: $f" || echo "FAIL: $f"; done
```

Pre-existing `SyntaxWarning` on invalid escape sequences inside JS template strings
(e.g. `inline_visualizer_v2.py`) are harmless — they're not new.

### Step 7: Bump versions and report

Bump the `version:` header on **every** file in `src/dartmouth_chat_tools/` to the
new Open WebUI version, not just the ones that needed code changes. A tool that
required no fix is still "checked" against the new version, and the version
number is how that gets recorded — a stale version number looks unverified.
Ask the user before bumping (it implies a tool release), but bump all of them
together once confirmed:

```bash
cd src/dartmouth_chat_tools
for f in *.py; do
  grep -q "^version: <OLD>$" "$f" && sed -i '' 's/^version: <OLD>$/version: <NEW>/' "$f"; done
sed -i '' 's/^required_open_webui_version: <OLD>$/required_open_webui_version: <NEW>/' inline_visualizer_v2.py
```

Verify no file was missed: `grep -rn "^version:" src/dartmouth_chat_tools/*.py`
should show `<NEW>` everywhere.

Report per-tool: what changed upstream, what you fixed, and what was already
compatible (but still version-bumped). Call out any latent bugs you found (e.g.
an undefined constant) even if they predate the upgrade.

## Lessons from the 0.9.2 → 0.9.6 pass

Concrete examples of the change types to watch for:

- **sync → async:** `routers.retrieval.search_web` became `async`. `web_search.py`
  had `await asyncio.to_thread(_search_web, ...)`; fixed to `await _search_web(...)`.
- **New error branch:** `code_interpreter.py` needed the pyodide `event_call` error
  handling (`output.get("error")` → stderr) added to match builtin.
- **Latent bug surfaced:** `knowledge.py` referenced undefined `MAX_VIEW_FILE_CHARS`
  (a `NameError`); defined it as `100_000`.
- **Already fixed:** `automations.py` already used `Automations.update_by_id` (the
  renamed method) — no change needed.
- **Compatible-as-is:** most custom tools (`create_document.py`, `send_email.py`,
  `dchat_persona.py`) — verified their imports/signatures without edits.
- **Fragile integration to note:** `create_document.py`'s `_MockRequest` only
  supplies a few `request.app.state.config` attrs; it works because the `process=False`
  path doesn't touch the others. Flag this on every upgrade.
