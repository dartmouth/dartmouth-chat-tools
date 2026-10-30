# DISC Risk Gate runs on the `request` hook; task-model traffic is out of scope

The DISC Risk Gate is an Open WebUI filter that implements `request`, not `inlet`. `inlet` runs once per user turn, before attachments, RAG context and tool results are added. In native function calling, file content reaches the model provider only as tool results (via `view_attachment` / `view_file`), so an `inlet` gate would miss the place where DISC 3 data is most likely to be. `request` runs before every call to the model provider, including each pass through the tool loop, and sees the exact messages being sent.

The gate deliberately does not cover calls to the task model (titles, tags, follow-ups, query generation, memory review, context compaction). Those go through `generate_chat_completion`, which runs no function filters, and title generation for a new chat starts before any filter runs. Covering them would mean patching the fork or enforcing at the LiteLLM layer. We accept the gap: the gate warns a person about what *they* are sending to the model they chose. It is not a data-loss-prevention control.

## Considered Options

- **`inlet`**: rejected, because it can't see tool results, file content or RAG context.
- **Patching `generate_chat_completion` in the fork**: rejected for now. It's a larger change to private internals, and task calls happen in the background, where there's no way to prompt the user.
- **Enforcing at the LiteLLM / provider layer**: rejected, because it can't show a confirmation dialog to the user.

## Consequences

- Classification runs before every provider call, so a turn with many tool calls pays the classifier's delay several times.
- The gate relies on `request`, an upstream hook that is fairly new (added August 2026). Open WebUI upgrades must check that it still runs in the tool loop.
