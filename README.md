# dartmouth-chat-tools
A collection of tools for use in Dartmouth Chat.

## Requirements

The following tools have special requirements:

- `create_document`: Requires the template files in `resources/` to be present in OWUI's `data/resources` folder.
- `disc_risk_gate`: Calls the System One classifier through LiteLLM directly, so Open WebUI needs `LITELLM_PROXY_BASE_URL` and `LITELLM_PROXY_API_KEY` set. It runs on the `request` filter hook (see `docs/adr/0001-disc-risk-gate-request-hook-and-scope.md`).

## Tests

```sh
uv run pytest
```
