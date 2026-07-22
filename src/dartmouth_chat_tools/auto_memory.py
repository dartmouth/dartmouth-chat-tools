"""
title: Memory
author: Simon Stone
version: 0.10.2

This is a modified version of:

original title: Auto Memory
original author: @nokodo
author_email: nokodo@nokodo.net
author_url: https://nokodo.net
repository_url: https://nokodo.net/github/open-webui-extensions
original version: 1.0.0-alpha7
required_open_webui_version: 0.10.2
funding_url: https://ko-fi.com/nokodo
license: see extension documentation file `auto_memory.md` (License section)
for the licensing terms.
"""

import asyncio
import json
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from fastapi.requests import Request
from open_webui.models.memories import Memories, MemoryModel
from open_webui.models.users import UserModel, Users
from open_webui.retrieval.vector.main import SearchResult
from open_webui.routers.memories import (
    QueryMemoryForm,
    UpdateMemoriesForm,
    query_memory,
    update_memories,
)
from open_webui.utils.chat import generate_chat_completion
from pydantic import BaseModel, Field, ValidationError, create_model

LogLevel = Literal["debug", "info", "warning", "error"]
STRINGIFIED_MESSAGE_TEMPLATE = "-{index}. {role}: ```{content}```"

UNIFIED_SYSTEM_PROMPT = """\
You are maintaining a collection of Memories - individual "journal entries" or facts about a user, each automatically timestamped upon creation or update.
You will be provided with:
1. Recent messages from a conversation (displayed with negative indices; -1 is the most recent overall message)
2. Any existing related memories that might potentially be relevant
Your job is to determine what actions to take on the memory collection based on the User's **latest** message (-2).
<key_instructions>
## Instructions
1. Focus ONLY on the **User's most recent message** (-2). Older messages provide context but should not generate new memories unless explicitly referenced in the latest message.
2. Each Memory should represent **a single fact or statement**. Never combine multiple facts into one Memory.
3. When the User's latest message contradicts existing memories, **update the existing memory** rather than creating a conflicting new one.
4. If memories are exact duplicates or direct conflicts about the same topic, **consolidate them by updating or deleting** as appropriate.
5. **Link related Memories** by including brief references when relevant to maintain semantic connections.
6. Capture anything valuable for **personalizing future interactions** with the User.
7. Honor **explicit user requests** to "remember", "forget", or "update" information.
8. Each memory must be **self-contained and understandable without external context.** Avoid ambiguous references like "it", "that", or "there" - instead, include the specific subject being referenced. For example, prefer "User's new TV broke" over "It broke".
9. Be alert to **sarcasm, jokes, and non-literal language.** If the User's statement appears to be hyperbole, sarcasm, or non-literal rather than a factual claim, do not store it as a memory.
10. When determining which memory is "most recent" for conflict resolution, **refer to the `created_at` or `update_at` timestamps** from the existing memories.
</key_instructions>
<what_to_extract>
## What you WANT to extract
- Personal preferences, opinions, and feelings
- Long-term information (likely true for months/years)
- Future-oriented statements ("from now on", "going forward")
- Direct memory requests ("remember that", "note this", "forget that")
- Hobbies, interests, skills, activities
- Important life details (job, education, relationships, location)
- Goals, plans, aspirations
- Recurring patterns or habits
- Strong likes/dislikes affecting future conversations
</what_to_extract>
<what_not_to_extract>
## What you do NOT want to extract
- User/assistant names (already in profile)
- Ephemeral states ("I'm reading this now", "I just woke up")
- Information the assistant confirms is already known
- Content from translation/rewrite requests
- Trivial observations or fleeting thoughts
- Temporary activities
- Sarcastic remarks or obvious jokes
- Non-literal statements or hyperbole
- Tasks the user is working on right now, but that probably won't have any bearing on future conversations
</what_not_to_extract>
<actions_to_take>
Based on your analysis, return a list of actions:
**ADD**: Create new memory when:
- New information not covered by existing memories
- Distinct facts even if related to existing topics
- User explicitly requests to remember something
**REPLACE**: Modify an existing memory's content when:
- User provides updated/corrected information about the same fact
- User explicitly asks to update something
- New information refines but doesn't fundamentally change existing memory
**MOVE**: Change only an existing memory's `path` (grouping) when:
- The memory's content is still accurate, but it should be reclassified/regrouped
- No content change is needed, only where the memory is filed
**REMOVE**: Delete existing memory when:
- User explicitly requests to forget something
- User's statement directly contradicts an existing memory
- Memory is completely obsolete due to new information
- Duplicate memories exist (keep oldest based on `created_at` timestamp)
When replacing, moving, or removing, ONLY use the memory ID from the related memories list.

## `type` and `path` fields
- `type` is either `"user"` (durable facts, preferences, or instructions about the user) or `"context"` (other durable context that may help future conversations). Default to `"context"` when unsure.
- `path` is an optional hierarchical grouping string (e.g. `"work/employer"`, `"preferences/languages"`).
  - Use `path` when there is a clear place for the memory.
  - Leave `path` empty/omitted when there is no clear grouping.
- Prefer `replace`/`move`/`remove` over creating a duplicate `add` when an existing memory should change instead.
</actions_to_take>
<consolidation_rules>
- Only combine memories if they are exact duplicates or direct conflicts about the same topic
- For duplicates: keep only the oldest (based on `created_at` timestamp)
- For conflicts: update to reflect the latest information
- For similar but distinct facts: keep them separate (e.g., "likes oranges" vs "likes ripe oranges")
- Past events remain as separate journal entries unless explicitly contradicted
</consolidation_rules>
<examples>
**Example 1 - Store new memories when no related found**
Conversation:
-2. user: ```I work as a senior data scientist at Tesla and my favorite programming language is Rust```
-1. assistant: ```That's impressive! Working at Tesla must be exciting, and Rust is a great choice for systems programming```
Related Memories:
[
  {"id": "1", "type": "user", "path": "hobbies", "created_at": "2024-01-05T10:00:00", "update_at": "2024-01-05T10:00:00", "content": "User enjoys electric vehicles"},
  {"id": "2", "type": "user", "path": "skills", "created_at": "2024-02-10T14:00:00", "update_at": "2024-02-10T14:00:00", "content": "User has experience with Python and data analysis"},
  {"id": "3", "type": "user", "path": "hobbies", "created_at": "2024-01-20T09:30:00", "update_at": "2024-01-20T09:30:00", "content": "User likes reading science fiction novels"}
]
**Analysis**
- Existing memories might be tangentially related (electric vehicles/Tesla, data analysis) but don't actually cover the specific facts mentioned
- User provides two distinct new facts: job/company and programming preference
- Each should be stored as a separate new memory
Output:
{
  "actions": [
    {"action": "add", "content": "User works as a senior data scientist at Tesla", "type": "user", "path": "work/employer"},
    {"action": "add", "content": "User's favorite programming language is Rust", "type": "user", "path": "preferences/languages"}
  ]
}
**Example 2 - Consolidate similar memories while retaining context**
Conversation:
-2. user: ```Actually I prefer TypeScript over JavaScript for frontend work these days```
-1. assistant: ```TypeScript's type safety definitely makes frontend development more maintainable!```
Related Memories:
[
  {"id": "123", "type": "user", "path": "preferences/languages", "created_at": "2024-01-15T10:00:00", "update_at": "2024-01-15T10:00:00", "content": "User likes JavaScript for web development"},
  {"id": "456", "type": "user", "path": "preferences/languages", "created_at": "2024-02-20T14:30:00", "update_at": "2024-02-20T14:30:00", "content": "User prefers JavaScript for frontend projects"},
  {"id": "789", "type": "user", "path": "skills", "created_at": "2024-03-01T09:00:00", "update_at": "2024-03-01T09:00:00", "content": "User is learning React"}
]
**Analysis**
- Two existing similar memories about JavaScript preference
- User said they now prefer TypeScript, but it doesn't mean they don't *like* JavaScript anymore
- Replace one memory to reflect the new preference, leave all other memories untouched
Output:
{
  "actions": [
    {"action": "replace", "id": "456", "content": "User prefers TypeScript for frontend work"}
  ]
}
**Example 3 - Delete conflicting memory while retaining others**
Conversation:
-2. user: ```I'm joking! I didn't actually buy the iPhone!```
-1. assistant: ```Ahh, you got me there! No worries.```
Related Memories:
[
  {"id": "789", "type": "context", "path": "purchases", "created_at": "2024-03-01T09:00:00", "update_at": "2024-03-01T09:00:00", "content": "User just bought a new iPhone"},
  {"id": "012", "type": "user", "path": "preferences", "created_at": "2024-03-02T11:00:00", "update_at": "2024-03-02T11:00:00", "content": "User likes Apple products"},
  {"id": "345", "type": "context", "path": "purchases", "created_at": "2024-03-02T11:00:00", "update_at": "2024-03-02T11:00:00", "content": "User is considering buying a new iPad"}
]
**Analysis**
- User negates a previous statement about buying an iPhone
- We should remove the memory about the iPhone purchase
- The other memories about liking Apple products and considering an iPad remain valid
Output:
{
  "actions": [
    {"action": "remove", "id": "789"}
  ]
}
**Example 4 - Handling multiple updates while retaining context**
Conversation:
-4. user: ```I'm thinking of switching from my current role```
-3. assistant: ```What's motivating you to consider a change?```
-2. user: ```Well, I got promoted to team lead last month, but I'm also interviewing at Google next week. The commute would be better since I just moved to Mountain View```
-1. assistant: ```Congratulations on the promotion! That's interesting timing with the Google interview```
Related Memories:
[
  {"id": "345", "type": "user", "path": "location", "created_at": "2024-02-15T10:00:00", "update_at": "2024-02-15T10:00:00", "content": "User lives in San Francisco"},
  {"id": "678", "type": "user", "path": "work/role", "created_at": "2024-01-10T08:00:00", "update_at": "2024-01-10T08:00:00", "content": "User works as a software engineer"}
]
**Analysis**
- User reveals: promoted to team lead (updates role), moved to Mountain View (conflicts with SF), interviewing at Google (new info)
- We don't want to forget any of the user's life details, unless there is a conflict. So we create new memories, and replace the legacy ones.
- Add new memory about Google interview as it's distinct future event
Output:
{
  "actions": [
    {"action": "replace", "id": "345", "content": "User used to live in San Francisco"},
    {"action": "replace", "id": "678", "content": "User works as a team lead software engineer"},
    {"action": "add", "content": "User got promoted to team lead", "type": "user", "path": "work/role"},
    {"action": "add", "content": "User has just moved to Mountain View", "type": "user", "path": "location"},
    {"action": "add", "content": "User lives in Mountain View", "type": "user", "path": "location"},
    {"action": "add", "content": "User has an interview at Google", "type": "user", "path": "work/events"}
  ]
}
**Example 5 - Handling sarcasm and non-literal language**
Conversation:
-3. assistant: ```As an AI assistant, I can perform extremely complex calculations in seconds.```
-2. user: ```Oh yeah? I can do that with my eyes closed! I'm basically a human calculator!```
-1. assistant: ```😂 Sure you can!```
Related Memories:
[]
**Analysis**
- The User's message is clearly sarcastic/joking - they're not literally claiming to be a human calculator
- This is hyperbole used for humorous effect, not a factual statement about their abilities
- No memories should be created from obvious sarcasm or jokes
Output:
{
  "actions": []
}
**Example 6 - Cross-message context linking**
Conversation:
-5. assistant: ```How's your new TV working out?```
-4. user: ```Remember how I bought that Samsung OLED TV last week?```
-3. assistant: ```Yes, I remember that. What about it?```
-2. user: ```Well, it broke down today! The screen just went black.```
-1. assistant: ```Oh no! That's terrible for such a new TV!```
Related Memories:
[
  {"id": "101", "type": "context", "path": "purchases", "created_at": "2024-03-15T10:00:00", "update_at": "2024-03-15T10:00:00", "content": "User bought a Samsung OLED TV"}
]
**Analysis**
- The User's latest message provides new information about the TV breaking
- We need to create a self-contained memory that includes context from earlier messages
- The new memory should reference the Samsung OLED TV specifically, not just "it" or "the TV"
- This helps semantically link to the existing memory about the purchase
Output:
{
  "actions": [
    {"action": "add", "content": "User's Samsung OLED TV, that was recently purchased, just broke down with a black screen", "type": "context", "path": "purchases"}
  ]
}
**Example 7 - Reclassifying a memory's grouping only**
Conversation:
-2. user: ```Actually, my love of hiking is really more of a professional thing now - I'm training to be a wilderness guide```
-1. assistant: ```That's a great transition from hobby to career!```
Related Memories:
[
  {"id": "202", "type": "user", "path": "hobbies", "created_at": "2024-01-01T10:00:00", "update_at": "2024-01-01T10:00:00", "content": "User enjoys hiking"}
]
**Analysis**
- The underlying fact (enjoys hiking) is still accurate and doesn't need new content
- Only the grouping should change, from a hobby to a career-related path
- Use move to change only the path, not the content
Output:
{
  "actions": [
    {"action": "move", "id": "202", "path": "work/career"}
  ]
}
</examples>\
"""


async def emit_status(
    description: str,
    emitter: Callable[[Any], Awaitable[None]],
    status: Literal["in_progress", "complete", "error"] = "complete",
    done: Optional[bool] = None,
):
    """Emit a status event with sensible defaults.
    Defaults:
    - status defaults to "complete"
    - done defaults to True unless status == "in_progress" (then False)
    """
    if not emitter:
        raise ValueError("emitter is required")
    if done is None:
        done = status != "in_progress"
    await emitter(
        {
            "type": "status",
            "data": {
                "description": description,
                "status": status,
                "done": done,
            },
        }
    )


class MemoryAddAction(BaseModel):
    action: Literal["add"] = Field(..., description="Action type (add)")
    content: str = Field(..., description="Content of the memory to add")
    type: Literal["user", "context"] = Field(
        default="context",
        description="Memory type: 'user' for durable facts/preferences about the user, 'context' for other durable context",
    )
    path: Optional[str] = Field(
        default=None,
        description="Optional hierarchical grouping for the memory (e.g. 'work/employer')",
    )

    def __str__(self) -> str:
        return f"Memory added. Content: '{self.content}'"


class MemoryReplaceAction(BaseModel):
    action: Literal["replace"] = Field(..., description="Action type (replace)")
    id: str = Field(..., description="ID of the memory to replace")
    content: str = Field(..., description="New content for the memory")
    type: Optional[Literal["user", "context"]] = Field(
        default=None, description="Optional new memory type"
    )
    path: Optional[str] = Field(
        default=None, description="Optional new hierarchical grouping for the memory"
    )

    def __str__(self) -> str:
        return f"Memory replaced. New content: '{self.content}'"


class MemoryMoveAction(BaseModel):
    action: Literal["move"] = Field(..., description="Action type (move)")
    id: str = Field(..., description="ID of the memory to move")
    path: Optional[str] = Field(
        default=None, description="New hierarchical grouping for the memory"
    )

    def __str__(self) -> str:
        return f"Memory moved. New path: '{self.path}'"


class MemoryRemoveAction(BaseModel):
    action: Literal["remove"] = Field(..., description="Action type (remove)")
    id: str = Field(..., description="ID of the memory to remove")

    def __str__(self) -> str:
        return f"Memory removed. ID: '{self.id}'"


class MemoryActionRequestStub(BaseModel):
    """This is a stub model to correctly type parameters. Not used directly."""

    actions: list[
        Union[
            MemoryAddAction, MemoryReplaceAction, MemoryMoveAction, MemoryRemoveAction
        ]
    ] = Field(
        default_factory=list,
        description="List of actions to perform on memories",
        max_length=20,
    )


def build_actions_request_model(existing_ids: list[str]):
    """Dynamically build versions of the Replace/Move/Remove action models whose `id`
    fields are Literal[...] constrained to the provided existing_ids.
    If existing_ids is empty, we still return permissive forms (falls back to str) so
    that add-only flows still parse.
    """
    if not existing_ids:
        # No IDs to constrain, so no relevant memories = can only create new memories
        allowed_actions = MemoryAddAction
    else:
        id_literal_type = Literal[tuple(existing_ids)]
        DynamicMemoryReplaceAction = create_model(
            "MemoryReplaceAction",
            id=(id_literal_type, ...),
            __base__=MemoryReplaceAction,
        )
        DynamicMemoryMoveAction = create_model(
            "MemoryMoveAction",
            id=(id_literal_type, ...),
            __base__=MemoryMoveAction,
        )
        DynamicMemoryRemoveAction = create_model(
            "MemoryRemoveAction",
            id=(id_literal_type, ...),
            __base__=MemoryRemoveAction,
        )
        allowed_actions = Union[
            MemoryAddAction,
            DynamicMemoryReplaceAction,
            DynamicMemoryMoveAction,
            DynamicMemoryRemoveAction,
        ]
    return create_model(
        "MemoriesActionRequest",
        actions=(
            list[allowed_actions],
            Field(
                default_factory=list,
                description="List of actions to perform on memories",
                max_length=20,
            ),
        ),
        __base__=BaseModel,
    )


def searchresult_to_memory_models(
    result: SearchResult, all_memories: list[MemoryModel]
) -> list[MemoryModel]:
    """Map ids returned by a vector search to their full MemoryModel records.

    If a returned id isn't found in all_memories (edge case), it is skipped.
    """
    memories_by_id = {memory.id: memory for memory in all_memories}
    resolved: list[MemoryModel] = []
    if not result.ids:
        return resolved
    for ids_batch in result.ids:
        for mem_id in ids_batch:
            memory = memories_by_id.get(mem_id)
            if memory is not None:
                resolved.append(memory)
    return resolved


R = TypeVar("R", bound=BaseModel)


class Filter:
    class Valves(BaseModel):
        model: str = Field(
            default="",
            description="Select the default model for memory extraction (can be overidden by user).",
            json_schema_extra={
                "dynamic_enum": {
                    "endpoint": "/models",
                    "response_path": "data",
                    "value_field": "id",
                    "label_field": "name",
                    "cache_ttl": 300,  # Cache for 5 minutes
                    "fallback": [],  # Fallback options if fetch fails
                    "filters": [
                        {
                            "field": "tags",
                            "value_path": "name",
                            "exclude": ["Embedding"],
                        }
                    ],
                }
            },
        )
        messages_to_consider: int = Field(
            default=4,
            description="Number of recent messages to consider for memory extraction (can be overidden by user).",
        )
        related_memories_n: int = Field(
            default=5,
            description="Number of related memories to consider when updating memories.",
        )
        related_memories_dist: float = Field(
            default=0.75,
            description="Semantic distance of memories to consider for updates. Smaller number will be more closely related.",
        )
        debug_mode: bool = Field(
            default=False,
            description="Enable debug logging",
        )

    class UserValves(BaseModel):
        model: str = Field(
            default="",
            description=(
                "Select your preferred model to extract Memories. "
                "This will consume a significant amount of additional tokens."
            ),
            json_schema_extra={
                "dynamic_enum": {
                    "endpoint": "/models",
                    "response_path": "data",  # Extract array from nested response
                    "value_field": "id",
                    "label_field": "name",
                    "cache_ttl": 300,  # Cache for 5 minutes
                    "fallback": [],  # Fallback options if fetch fails
                    "filters": [
                        {
                            "field": "tags",
                            "value_path": "name",
                            "exclude": ["Embedding"],
                        }
                    ],
                }
            },
        )
        show_status: bool = Field(
            default=True,
            description="Show status notifications about extracted or updated Memory events.",
        )
        messages_to_consider: Optional[int] = Field(
            default=None,
            description="Number of recent messages to consider (includes AI responses).",
        )

    def log(self, message: str, level: LogLevel = "info"):
        if level == "debug" and not self.valves.debug_mode:
            return
        if level not in {"debug", "info", "warning", "error"}:
            level = "info"
        logger = logging.getLogger()
        getattr(logger, level, logger.info)(message)

    def messages_to_string(self, messages: list[dict[str, Any]]) -> str:
        stringified_messages: list[str] = []
        effective_messages_to_consider = (
            self.user_valves.messages_to_consider
            if self.user_valves.messages_to_consider is not None
            else self.valves.messages_to_consider
        )
        self.log(
            f"using last {effective_messages_to_consider} messages",
            level="debug",
        )
        for i in range(1, effective_messages_to_consider + 1):
            if i > len(messages):
                break
            try:
                message = messages[-i]
                stringified_messages.append(
                    STRINGIFIED_MESSAGE_TEMPLATE.format(
                        index=i,
                        role=message.get("role", "user"),
                        content=message.get("content", ""),
                    )
                )
            except Exception as e:
                self.log(f"error stringifying message {i}: {e}", level="warning")
        return "\n".join(stringified_messages)

    @overload
    async def query_chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        response_model: Type[R],
        request: Request,
        user: UserModel,
    ) -> R: ...

    @overload
    async def query_chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        response_model: None = None,
        request: Request = None,
        user: UserModel = None,
    ) -> str: ...

    async def query_chat_completion(
        self,
        system_prompt: str,
        user_message: str,
        response_model: Optional[Type[R]] = None,
        request: Request = None,
        user: UserModel = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Union[str, R]:
        """Generic wrapper around generate_chat_completion.
        - Uses structured outputs when response_model is provided
        - Returns: model instance or raw string
        """
        model_name = self.user_valves.model or self.valves.model
        if not model_name:
            raise ValueError(
                "No model configured for memory extraction. "
                "Please set a model in the Memory filter valves."
            )
        temperature = 0.3 if "gpt-5" not in model_name else 1

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        form_data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        # Mirror the built-in background reviewer's pattern of passing chat/message
        # context via metadata instead of a fake chat_id, falling back to the old
        # "local:memory" sentinel if no metadata is available from the outlet.
        if metadata and (metadata.get("chat_id") or metadata.get("message_id")):
            form_data["metadata"] = {
                "task": "memory_extraction",
                "chat_id": metadata.get("chat_id"),
                "message_id": metadata.get("message_id"),
            }
        else:
            form_data["chat_id"] = "local:memory"  # treat as temp chat to avoid DB/session logic

        # Add response_format for structured outputs if response_model is provided
        if response_model is not None:
            form_data["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": False,
                },
            }

        try:
            response = await generate_chat_completion(
                request=request,
                form_data=form_data,
                user=user,
            )

            self.log(f"chat completion response: {response}", level="debug")

            # Extract content from response
            if isinstance(response, dict):
                content = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
            else:
                content = str(response)

            if not content:
                raise ValueError(f"no text response from LLM. response={response}")

            # Parse structured output if response_model provided
            if response_model:
                try:
                    return response_model.model_validate_json(content)
                except ValidationError as e:
                    self.log(f"response model validation error: {e}", level="warning")
                    raise

            return content

        except Exception as e:
            self.log(f"chat completion failed: {e}", level="error")
            raise

    def __init__(self):
        self.toggle = True
        self.icon = """data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGNsYXNzPSJsdWNpZGUgbHVjaWRlLWJyYWluLWljb24gbHVjaWRlLWJyYWluIj48cGF0aCBkPSJNMTIgMThWNSIvPjxwYXRoIGQ9Ik0xNSAxM2E0LjE3IDQuMTcgMCAwIDEtMy00IDQuMTcgNC4xNyAwIDAgMS0zIDQiLz48cGF0aCBkPSJNMTcuNTk4IDYuNUEzIDMgMCAxIDAgMTIgNWEzIDMgMCAxIDAtNS41OTggMS41Ii8+PHBhdGggZD0iTTE3Ljk5NyA1LjEyNWE0IDQgMCAwIDEgMi41MjYgNS43NyIvPjxwYXRoIGQ9Ik0xOCAxOGE0IDQgMCAwIDAgMi03LjQ2NCIvPjxwYXRoIGQ9Ik0xOS45NjcgMTcuNDgzQTQgNCAwIDEgMSAxMiAxOGE0IDQgMCAxIDEtNy45NjctLjUxNyIvPjxwYXRoIGQ9Ik02IDE4YTQgNCAwIDAgMS0yLTcuNDY0Ii8+PHBhdGggZD0iTTYuMDAzIDUuMTI1YTQgNCAwIDAgMC0yLjUyNiA1Ljc3Ii8+PC9zdmc+"""
        self.valves = self.Valves()

    async def get_related_memories(
        self,
        messages: list[dict[str, Any]],
        user: UserModel,
        request: Request,
    ) -> list[MemoryModel]:
        # Extract latest user message for finding related memories
        latest_user_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                latest_user_msg = msg.get("content", "")
                break
        else:
            raise ValueError("no user message found in messages")
        # Query related memories
        try:
            results = await query_memory(
                request=request,
                form_data=QueryMemoryForm(
                    content=latest_user_msg, k=self.valves.related_memories_n
                ),
                user=user,
            )
        except Exception as e:
            self.log(f"failed to query memories: {e}", level="warning")
            return []
        if not results:
            return []
        all_memories = await Memories.get_memories_by_user_id(user.id) or []
        related_memories = searchresult_to_memory_models(results, all_memories)
        self.log(f"found {len(related_memories)} related memories", level="info")
        self.log(f"related memories: {related_memories}", level="debug")
        return related_memories

    async def auto_memory(
        self,
        messages: list[dict[str, Any]],
        user: UserModel,
        emitter: Callable[[Any], Awaitable[None]],
        request: Request,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Execute the auto-memory extraction and update flow."""
        if len(messages) < 2:
            self.log("need at least 2 messages for context", level="debug")
            return
        self.log(f"flow started. user ID: {user.id}", level="debug")
        related_memories = await self.get_related_memories(
            messages=messages, user=user, request=request
        )
        stringified_memories = json.dumps(
            [memory.model_dump(mode="json") for memory in related_memories]
        )
        conversation_str = self.messages_to_string(messages)
        try:
            action_plan = await self.query_chat_completion(
                system_prompt=UNIFIED_SYSTEM_PROMPT,
                user_message=f"Conversation snippet:\n{conversation_str}\n\nRelated Memories:\n{stringified_memories}",
                response_model=build_actions_request_model(
                    [m.id for m in related_memories]
                ),
                request=request,
                user=user,
                metadata=metadata,
            )
            self.log(f"action plan: {action_plan}", level="debug")
            # Apply the actions
            await self.apply_memory_actions(
                action_plan=action_plan, user=user, emitter=emitter, request=request
            )
        except Exception as e:
            self.log(f"LLM query failed: {e}", level="error")
            if self.user_valves.show_status:
                await emit_status(
                    "Memory processing failed", emitter=emitter, status="error"
                )
            return None

    async def apply_memory_actions(
        self,
        action_plan: MemoryActionRequestStub,
        user: UserModel,
        emitter: Callable[[Any], Awaitable[None]],
        request: Request,
    ) -> None:
        """Execute memory actions from the plan via the batched update_memories endpoint."""
        self.log("started apply_memory_actions", level="debug")
        actions = action_plan.actions
        if not actions:
            self.log("no changes", level="info")
            return
        if emitter:
            self.log(f"processing {len(actions)} memory actions", level="debug")
            await emit_status(
                f"Processing {len(actions)} Memory actions",
                emitter=emitter,
                status="in_progress",
            )

        operations = [a.model_dump(exclude_none=True) for a in actions]
        try:
            results = await update_memories(
                request,
                UpdateMemoriesForm(operations=operations, source="tool"),
                user,
            )
        except Exception as e:
            self.log(f"failed to apply memory actions: {e}", level="error")
            if self.user_valves.show_status:
                await emit_status(
                    "Memory processing failed", emitter=emitter, status="error"
                )
            return

        counts = {"add": 0, "replace": 0, "move": 0, "remove": 0}
        for result in results:
            status = result.get("status")
            if status == "created":
                counts["add"] += 1
            elif status == "updated":
                # both 'replace' and 'move' produce status == 'updated'; use result['action']
                counts[result.get("action", "replace")] += 1
            elif status == "deleted":
                counts["remove"] += 1
            # 'skipped' (duplicate add) intentionally not counted/announced

        verb = {"add": "saved", "replace": "updated", "move": "moved", "remove": "deleted"}
        status_parts = [
            f"{verb[op]} {n} {'Memory' if n == 1 else 'Memories'}"
            for op, n in counts.items()
            if n
        ]
        status_message = ", ".join(status_parts)
        self.log(status_message or "no changes", level="info")
        if status_message and self.user_valves.show_status:
            await emit_status(status_message, emitter=emitter, status="complete")

    def inlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __user__: Optional[dict] = None,
    ) -> dict:
        return body

    async def outlet(
        self,
        body: dict,
        __event_emitter__: Callable[[Any], Awaitable[None]],
        __user__: Optional[dict] = None,
        __request__: Optional[Request] = None,
        __metadata__: Optional[dict] = None,
    ) -> dict:
        self.log("outlet invoked")
        if __user__ is None:
            raise ValueError("user information is required")
        if __request__ is None:
            raise ValueError("request is required")
        self.user_valves = __user__.get("valves", self.UserValves())

        user = await Users.get_user_by_id(__user__["id"])
        if user is None:
            raise ValueError("user not found")
        self.log(f"input user type = {type(__user__)}", level="debug")
        self.log(
            f"user.id = {user.id} user.name = {user.name} user.email = {user.email}",
            level="debug",
        )
        self.user_valves = __user__.get("valves", self.UserValves())
        if not isinstance(self.user_valves, self.UserValves):
            raise ValueError("invalid user valves")
        self.user_valves = cast(Filter.UserValves, self.user_valves)
        self.log(f"user valves = {self.user_valves}", level="debug")
        asyncio.create_task(
            self.auto_memory(
                body.get("messages", []),
                user=user,
                emitter=__event_emitter__,
                request=__request__,
                metadata=__metadata__ or body.get("metadata"),
            )
        )
        return body
