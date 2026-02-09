import json
import logging
import asyncio

from fastapi import Request

from open_webui.models.users import UserModel
from open_webui.routers.retrieval import search_web as _search_web
from open_webui.retrieval.utils import get_content_from_url

log = logging.getLogger(__name__)


class Tools:
    # =============================================================================
    # WEB SEARCH TOOLS
    # =============================================================================

    async def search_web(
        self,
        query: str,
        count: int = 5,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Search the public web for information. Best for current events, external references,
        or topics not covered in internal documents. If knowledge base tools are available,
        consider checking those first for internal information.

        :param query: The search query to look up
        :param count: Number of results to return (default: 5)
        :return: JSON with search results containing title, link, and snippet for each result
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        try:
            engine = __request__.app.state.config.WEB_SEARCH_ENGINE
            user = UserModel(**__user__) if __user__ else None

            results = _search_web(__request__, engine, query, user)

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

            # Truncate if too long (avoid overwhelming context)
            max_length = 50000
            if len(content) > max_length:
                content = content[:max_length] + "\n\n[Content truncated...]"

            return content
        except Exception as e:
            log.exception(f"fetch_url error: {e}")
            return json.dumps({"error": str(e)})
