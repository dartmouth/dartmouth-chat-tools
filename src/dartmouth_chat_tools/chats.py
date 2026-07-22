"""
title: Chats
version: 0.10.2
"""

import json
import logging
from typing import Optional

from fastapi import Request

from open_webui.models.chats import Chats

log = logging.getLogger(__name__)


class Tools:
    async def search_chats(
        self,
        query: str,
        count: int = 5,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        __request__: Request = None,
        __user__: dict = None,
        __chat_id__: str = None,
    ) -> str:
        """
        Search the user's previous chat conversations by title and message content.

        IMPORTANT: This tool performs a case-insensitive exact substring match. The entire
        query string must appear as a contiguous sequence of characters in the chat text or
        title. There is no fuzzy matching, full-text search, or word tokenization.
        A multi-word query like "tree car house" will ONLY match chats where those words
        appear together in exactly that order with exactly that spacing. To find chats that
        mention several concepts, call this tool multiple times with a single keyword each
        time, then combine results. Only use multi-word queries when searching for a known
        exact phrase.

        :param query: A single keyword or exact phrase to find in chat titles or messages.
                      Avoid multi-word queries unless the words are known to appear together
                      verbatim (e.g. a specific quote or title). For broad topic searches,
                      use one distinctive word per call.
        :param count: Maximum number of results to return (default: 5)
        :param start_timestamp: Only include chats updated after this Unix timestamp (seconds)
        :param end_timestamp: Only include chats updated before this Unix timestamp (seconds)
        :return: JSON with matching chats containing id, title, updated_at, and content snippet
        """

        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            user_id = __user__.get('id')

            chats = await Chats.get_chats_by_user_id_and_search_text(
                user_id=user_id,
                search_text=query,
                include_archived=False,
                skip=0,
                limit=count * 3,  # Fetch more for filtering
            )

            results = []
            for chat in chats:
                # Skip the current chat to avoid showing it in search results
                if __chat_id__ and chat.id == __chat_id__:
                    continue

                # Apply date filters (updated_at is in seconds)
                if start_timestamp and chat.updated_at < start_timestamp:
                    continue
                if end_timestamp and chat.updated_at > end_timestamp:
                    continue

                # Find a matching message snippet
                snippet = ''
                messages = (getattr(chat, 'chat', None) or {}).get('history', {}).get('messages', {})
                lower_query = query.lower()

                for msg_id, msg in messages.items():
                    content = msg.get('content', '')
                    if isinstance(content, str) and lower_query in content.lower():
                        idx = content.lower().find(lower_query)
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(query) + 100)
                        snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
                        break

                if not snippet and lower_query in chat.title.lower():
                    snippet = f'Title match: {chat.title}'

                results.append(
                    {
                        'id': chat.id,
                        'title': chat.title,
                        'snippet': snippet,
                        'updated_at': chat.updated_at,
                    }
                )

                if len(results) >= count:
                    break

            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            log.exception(f'search_chats error: {e}')
            return json.dumps({'error': str(e)})

    async def view_chat(
        self,
        chat_id: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Get the full conversation history of a chat by its ID.

        :param chat_id: The ID of the chat to retrieve
        :return: JSON with the chat's id, title, and messages
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            user_id = __user__.get('id')

            chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

            if not chat:
                return json.dumps({'error': 'Chat not found or access denied'})

            # Extract messages from history
            messages = []
            history = chat.chat.get('history', {})
            msg_dict = history.get('messages', {})

            # Build message chain from currentId
            current_id = history.get('currentId')
            visited = set()

            while current_id and current_id not in visited:
                visited.add(current_id)
                msg = msg_dict.get(current_id)
                if msg:
                    messages.append(
                        {
                            'role': msg.get('role', ''),
                            'content': msg.get('content', ''),
                        }
                    )
                current_id = msg.get('parentId') if msg else None

            # Reverse to get chronological order
            messages.reverse()

            return json.dumps(
                {
                    'id': chat.id,
                    'title': chat.title,
                    'messages': messages,
                    'updated_at': chat.updated_at,
                    'created_at': chat.created_at,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'view_chat error: {e}')
            return json.dumps({'error': str(e)})
