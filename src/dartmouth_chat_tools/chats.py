import json
import logging
from typing import Optional

from fastapi import Request

from open_webui.models.chats import Chats

log = logging.getLogger(__name__)


class Tools:
    # =============================================================================
    # CHATS TOOLS
    # =============================================================================

    async def search_chats(
        self,
        query: str,
        count: int = 5,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search the user's previous chat conversations by title and message content.

        :param query: The search query to find matching chats
        :param count: Maximum number of results to return (default: 5)
        :param start_timestamp: Only include chats updated after this Unix timestamp (seconds)
        :param end_timestamp: Only include chats updated before this Unix timestamp (seconds)
        :return: JSON with matching chats containing id, title, updated_at, and content snippet
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id")

            chats = Chats.get_chats_by_user_id_and_search_text(
                user_id=user_id,
                search_text=query,
                include_archived=False,
                skip=0,
                limit=count * 3,  # Fetch more for filtering
            )

            results = []
            for chat in chats:
                # Apply date filters (updated_at is in seconds)
                if start_timestamp and chat.updated_at < start_timestamp:
                    continue
                if end_timestamp and chat.updated_at > end_timestamp:
                    continue

                # Find a matching message snippet
                snippet = ""
                messages = chat.chat.get("history", {}).get("messages", {})
                lower_query = query.lower()

                for msg_id, msg in messages.items():
                    content = msg.get("content", "")
                    if isinstance(content, str) and lower_query in content.lower():
                        idx = content.lower().find(lower_query)
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(query) + 100)
                        snippet = (
                            ("..." if start > 0 else "")
                            + content[start:end]
                            + ("..." if end < len(content) else "")
                        )
                        break

                if not snippet and lower_query in chat.title.lower():
                    snippet = f"Title match: {chat.title}"

                results.append(
                    {
                        "id": chat.id,
                        "title": chat.title,
                        "snippet": snippet,
                        "updated_at": chat.updated_at,
                    }
                )

                if len(results) >= count:
                    break

            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            log.exception(f"search_chats error: {e}")
            return json.dumps({"error": str(e)})

    async def view_chat(
        self,
        chat_id: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Get the full conversation history of a chat by its ID.

        :param chat_id: The ID of the chat to retrieve
        :return: JSON with the chat's id, title, and messages
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id")

            chat = Chats.get_chat_by_id_and_user_id(chat_id, user_id)

            if not chat:
                return json.dumps({"error": "Chat not found or access denied"})

            # Extract messages from history
            messages = []
            history = chat.chat.get("history", {})
            msg_dict = history.get("messages", {})

            # Build message chain from currentId
            current_id = history.get("currentId")
            visited = set()

            while current_id and current_id not in visited:
                visited.add(current_id)
                msg = msg_dict.get(current_id)
                if msg:
                    messages.append(
                        {
                            "role": msg.get("role", ""),
                            "content": msg.get("content", ""),
                        }
                    )
                current_id = msg.get("parentId") if msg else None

            # Reverse to get chronological order
            messages.reverse()

            return json.dumps(
                {
                    "id": chat.id,
                    "title": chat.title,
                    "messages": messages,
                    "updated_at": chat.updated_at,
                    "created_at": chat.created_at,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"view_chat error: {e}")
            return json.dumps({"error": str(e)})
