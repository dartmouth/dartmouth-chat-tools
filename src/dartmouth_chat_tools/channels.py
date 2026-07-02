"""
title: Channels
version: 0.9.6
"""

import json
import logging
from typing import Optional

from fastapi import Request

from open_webui.models.channels import Channels
from open_webui.models.messages import Messages

log = logging.getLogger(__name__)


class Tools:
    async def search_channels(
        self,
        query: str,
        count: int = 5,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search for channels by name and description that the user has access to.

        :param query: The search query to find matching channels
        :param count: Maximum number of results to return (default: 5)
        :return: JSON with matching channels containing id, name, description, and type
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id") or ""

            # Get all channels the user has access to
            all_channels = await Channels.get_channels_by_user_id(user_id)

            # Filter by query
            lower_query = query.lower()
            matching_channels = []

            for channel in all_channels:
                name_match = (
                    lower_query in channel.name.lower() if channel.name else False
                )
                desc_match = lower_query in (channel.description or "").lower()

                if name_match or desc_match:
                    matching_channels.append(
                        {
                            "id": channel.id,
                            "name": channel.name,
                            "description": channel.description or "",
                            "type": channel.type or "public",
                        }
                    )

                if len(matching_channels) >= count:
                    break

            return json.dumps(matching_channels, ensure_ascii=False)
        except Exception as e:
            log.exception(f"search_channels error: {e}")
            return json.dumps({"error": str(e)})

    async def search_channel_messages(
        self,
        query: str,
        count: int = 10,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search for messages in channels the user is a member of, including thread replies.

        :param query: The search query to find matching messages
        :param count: Maximum number of results to return (default: 10)
        :param start_timestamp: Only include messages created after this Unix timestamp (seconds)
        :param end_timestamp: Only include messages created before this Unix timestamp (seconds)
        :return: JSON with matching messages containing channel info, message content, and thread context
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id") or ""

            # Get all channels the user has access to
            user_channels = await Channels.get_channels_by_user_id(user_id)
            channel_ids = [c.id for c in user_channels]
            channel_map = {c.id: c for c in user_channels}

            if not channel_ids:
                return json.dumps([])

            # Convert timestamps to nanoseconds (Message.created_at is in nanoseconds)
            start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
            end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

            # Search messages using the model method
            matching_messages = await Messages.search_messages_by_channel_ids(
                channel_ids=channel_ids,
                query=query,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                limit=count,
            )

            results = []
            for msg in matching_messages:
                channel = channel_map.get(msg.channel_id or "")

                # Extract snippet around the match
                content = msg.content or ""
                lower_query = query.lower()
                idx = content.lower().find(lower_query)
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 100)
                    snippet = (
                        ("..." if start > 0 else "")
                        + content[start:end]
                        + ("..." if end < len(content) else "")
                    )
                else:
                    snippet = content[:150] + ("..." if len(content) > 150 else "")

                results.append(
                    {
                        "channel_id": msg.channel_id,
                        "channel_name": channel.name if channel else "Unknown",
                        "message_id": msg.id,
                        "content_snippet": snippet,
                        "is_thread_reply": msg.parent_id is not None,
                        "parent_id": msg.parent_id,
                        "created_at": msg.created_at,
                    }
                )

            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            log.exception(f"search_channel_messages error: {e}")
            return json.dumps({"error": str(e)})

    async def view_channel_message(
        self,
        message_id: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Get the full content of a channel message by its ID, including thread replies.

        :param message_id: The ID of the message to retrieve
        :return: JSON with the message content, channel info, and thread replies if any
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id") or ""

            message = await Messages.get_message_by_id(message_id)

            if not message:
                return json.dumps({"error": "Message not found"})

            # Verify user has access to the channel
            channel = await Channels.get_channel_by_id(message.channel_id or "")
            if not channel:
                return json.dumps({"error": "Channel not found"})

            # Check if user has access to the channel
            user_channels = await Channels.get_channels_by_user_id(user_id or "")
            channel_ids = [c.id for c in user_channels]

            if message.channel_id not in channel_ids:
                return json.dumps({"error": "Access denied"})

            # Build response with thread information
            result = {
                "id": message.id,
                "channel_id": message.channel_id,
                "channel_name": channel.name,
                "content": message.content,
                "user_id": message.user_id,
                "is_thread_reply": message.parent_id is not None,
                "parent_id": message.parent_id,
                "reply_count": message.reply_count,
                "created_at": message.created_at,
                "updated_at": message.updated_at,
            }

            # Include user info if available
            if message.user:
                result["user_name"] = message.user.name

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f"view_channel_message error: {e}")
            return json.dumps({"error": str(e)})

    async def view_channel_thread(
        self,
        parent_message_id: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Get all messages in a channel thread, including the parent message and all replies.

        :param parent_message_id: The ID of the parent message that started the thread
        :return: JSON with the parent message and all thread replies in chronological order
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            user_id = __user__.get("id") or ""

            # Get the parent message
            parent_message = await Messages.get_message_by_id(parent_message_id)

            if not parent_message:
                return json.dumps({"error": "Message not found"})

            # Verify user has access to the channel
            channel = await Channels.get_channel_by_id(parent_message.channel_id or "")
            if not channel:
                return json.dumps({"error": "Channel not found"})

            user_channels = await Channels.get_channels_by_user_id(user_id or "")
            channel_ids = [c.id for c in user_channels]

            if parent_message.channel_id not in channel_ids:
                return json.dumps({"error": "Access denied"})

            # Get all thread replies
            thread_replies = await Messages.get_thread_replies_by_message_id(
                parent_message_id
            )

            # Build the response
            messages = []

            # Add parent message first
            messages.append(
                {
                    "id": parent_message.id,
                    "content": parent_message.content,
                    "user_id": parent_message.user_id,
                    "user_name": (
                        parent_message.user.name if parent_message.user else None
                    ),
                    "is_parent": True,
                    "created_at": parent_message.created_at,
                }
            )

            # Add thread replies (reverse to get chronological order)
            for reply in reversed(thread_replies):
                messages.append(
                    {
                        "id": reply.id,
                        "content": reply.content,
                        "user_id": reply.user_id,
                        "user_name": reply.user.name if reply.user else None,
                        "is_parent": False,
                        "reply_to_id": reply.reply_to_id,
                        "created_at": reply.created_at,
                    }
                )

            return json.dumps(
                {
                    "channel_id": parent_message.channel_id,
                    "channel_name": channel.name,
                    "thread_id": parent_message_id,
                    "message_count": len(messages),
                    "messages": messages,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"view_channel_thread error: {e}")
            return json.dumps({"error": str(e)})
