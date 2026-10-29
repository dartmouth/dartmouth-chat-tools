# Dartmouth Chat Tools

This repo contains tools for Open WebUI, located in `src/dartmouth_chat_tools/`.

See the Open WebUI docs for [Tool development](https://docs.openwebui.com/features/extensibility/plugin/tools/development) and [Function development](https://docs.openwebui.com/features/extensibility/plugin/functions/).

## Overview

The codebase consists of two categories of tools:

1. **Builtin-derived tools**: Extracted from Open WebUI's `builtin.py`. These map to specific `# SECTION NAME` blocks in the upstream source.
2. **Fully-custom tools**: Original tools that interface with Open WebUI's private API (`open_webui.models.*`, `open_webui.routers.*`, `open_webui.utils.*`).

### Key Integration Details
- **Fragility**: Because these tools rely on private internals, they are susceptible to breaking changes (renamed methods, signature changes, or sync-to-async conversions) during Open WebUI upgrades.
- **Versioning**: Every tool file includes a `version:` header tracking the Open WebUI version it was last verified against.
- **Customizations**: Some tools, such as `auto_memory.py` and `knowledge.py`, are heavily customized forks of the builtin tools and should be updated with caution.

## Agent skills

### Issue tracker

GitHub issues. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical triage roles. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. See `docs/agents/domain.md`.


