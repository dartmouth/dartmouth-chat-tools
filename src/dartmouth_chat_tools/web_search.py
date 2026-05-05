"""
title: Web Search
version: 0.9.2
"""

import json
import logging
import asyncio
from typing import Optional

from fastapi import Request

from open_webui.models.users import UserModel
from open_webui.routers.retrieval import search_web as _search_web
from open_webui.retrieval.utils import get_content_from_url

log = logging.getLogger(__name__)


class Tools:
    async def search_web(
        self,
        query: str,
        count: Optional[int] = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Search the public web for information. Best for current events, external references,
        or topics not covered in internal documents.

        :param query: The search query to look up
        :param count: Number of results to return (default: admin-configured value)
        :return: JSON with search results containing title, link, and snippet for each result
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        try:
            engine = __request__.app.state.config.WEB_SEARCH_ENGINE
            user = UserModel(**__user__) if __user__ else None

            configured = __request__.app.state.config.WEB_SEARCH_RESULT_COUNT
            max_count = 5 if configured is None else configured
            count = max(1, min(count, max_count)) if count is not None else max_count

            results = await asyncio.to_thread(
                _search_web, __request__, engine, query, user
            )

            # Limit results
            results = results[:count] if results else []

            return json.dumps(
                [
                    {"title": r.title, "link": r.link, "snippet": r.snippet}
                    for r in results
                ],
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"search_web error: {e}")
            return json.dumps({"error": str(e)})

    async def fetch_url(
        self,
        url: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Fetch and extract the main text content from a web page URL.

        :param url: The URL to fetch content from
        :return: The extracted text content from the page
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        try:
            content, _ = await asyncio.to_thread(get_content_from_url, __request__, url)

            # Truncate if configured (WEB_FETCH_MAX_CONTENT_LENGTH)
            # Guard: content may be None if the web loader silently failed
            if content is not None:
                max_length = getattr(
                    __request__.app.state.config, "WEB_FETCH_MAX_CONTENT_LENGTH", None
                )
                if max_length and max_length > 0 and len(content) > max_length:
                    content = content[:max_length] + "\n\n[Content truncated...]"
            else:
                content = ""

            return content
        except Exception as e:
            log.exception(f"fetch_url error: {e}")
            return json.dumps({"error": str(e)})
