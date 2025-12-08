"""
requirements: tavily-python
"""

import logging
from typing import Callable, Literal, Union
from tavily import AsyncTavilyClient


from pydantic import BaseModel, Field


log = logging.getLogger(__name__)


class Tools:
    class Valves(BaseModel):
        tavily_api_key: str = "tvly-YOUR_API_KEY"

    class UserValves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()
        self.citation = False

    async def web_search(
        self,
        query: str,
        __event_emitter__: Callable | None = None,
        search_depth: Literal["basic", "advanced"] = "basic",
        topic: Literal["general", "news", "finance"] = "general",
        time_range: Literal["day", "week", "month", "year"] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        max_results: int = 5,
        chunks_per_source: int = 3,
        include_images: bool = False,
        include_image_descriptions: bool = False,
        include_answer: Union[bool, Literal["basic", "advanced"]] = False,
        include_raw_content: Union[bool, Literal["markdown", "text"]] = False,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        country: str | None = None,
    ):
        """
        Search the web for information using Tavily. You must use `include_raw_content = True` to get more detailed results from each source instead of just a brief summary.

        When presenting the results, include inline citations using [id] (e.g., [1], [2]).

        ### Parameters

        | Parameter                    | Type            | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Default     |   |
        | :--------------------------- | :-------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------- | - |
        | `query` **(required)**       | `str`           | The query to run a search on.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | —           |   |
        | `search_depth`               | `str`           | The depth of the search. It can be `"basic"` or `"advanced"`. `"advanced"` search is tailored to retrieve the most relevant sources and `content` snippets for your query, while `"basic"` search provides generic content snippets from each source.                                                                                                                                                                                                                                                                                                                                               | `"basic"`   |   |
        | `topic`                      | `str`           | The category of the search. Determines which agent will be used. Supported values are `"general"`, `"news"` and `"finance"`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `"general"` |   |
        | `time_range`                 | `str`           | The time range back from the current date based on publish date or last updated date. Accepted values include `"day"`, `"week"`, `"month"`, `"year"` or shorthand values `"d"`, `"w"`, `"m"`, `"y"`.                                                                                                                                                                                                                                                                                                                                                                                                | —           |   |
        | `start_date`                 | `str`           | Will return all results after the specified start date based on publish date or last updated date. Required to be written in the format YYYY-MM-DD                                                                                                                                                                                                                                                                                                                                                                                                                                                  | —           |   |
        | `end_date`                   | `str`           | Will return all results before the specified end date based on publish date or last updated date. Required to be written in the format YYYY-MM-DD.                                                                                                                                                                                                                                                                                                                                                                                                                                                  | —           |   |
        | `max_results`                | `int`           | The maximum number of search results to return. It must be between `0` and `20`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | `5`         |   |
        | `include_images`             | `bool`          | Include a list of query-related images in the response.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | `False`     |   |
        | `include_image_descriptions` | `bool`          | Include a list of query-related images and their descriptions in the response.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `False`     |   |
        | `include_answer`             | `bool` or `str` | Include an answer to the query generated by an LLM based on search results. A `"basic"` (or `True`) answer is quick but less detailed; an `"advanced"` answer is more detailed.                                                                                                                                                                                                                                                                                                                                                                                                                     | `False`     |   |
        | `include_raw_content`        | `bool` or `str` | Include the cleaned and parsed HTML content of each search result. `"markdown"` or `True` returns search result content in markdown format. `"text"` returns the plain text from the results and may increase latency.                                                                                                                                                                                                                                                                                                                                                                              | `False`     |   |
        | `include_domains`            | `list[str]`     | A list of domains to specifically include in the search results. Maximum 300 domains.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               | `[]`        |   |
        | `exclude_domains`            | `list[str]`     | A list of domains to specifically exclude from the search results. Maximum 150 domains.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | `[]`        |   |
        | `country`                    | `str`           | Boost search results from a specific country. This will prioritize content from the selected country in the search results. Available only if topic is `general`.                                                                                                                                                                                                                                                                                                                                                                                                                                   | —           |   |

        ### Response format

        The response object you receive will be in the following format:

        | Key                 | Type                               | Description                                                                                                                                                                             |
        | :------------------ | :--------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
        | `results`           | `list[Result]`                     | A list of sorted search results ranked by relevancy.                                                                                                                                    |
        | `query`             | `str`                              | Your search query.                                                                                                                                                                      |
        | `response_time`     | `float`                            | Your search result response time.                                                                                                                                                       |
        | `answer` (optional) | `str`                              | The answer to your search query, generated by an LLM based on Tavily's search results. This is only available if `include_answer` is set to `True`.                                     |
        | `images` (optional) | `list[str]` or `list[ImageResult]` | This is only available if `include_images` is set to `True`. A list of query-related image URLs. If `include_image_descriptions` is set to `True`, each entry will be an `ImageResult`. |
        | `request_id`        | `str`                              | A unique request identifier you can share with customer support to help resolve issues with specific requests.                                                                          |

        ### Results

        | `Key`                       | `Type`  | Description                                                                                                                                             |
        | :-------------------------- | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------ |
        | `title`                     | `str`   | The title of the search result.                                                                                                                         |
        | `url`                       | `str`   | The URL of the search result.                                                                                                                           |
        | `content`                   | `str`   | The most query-related content from the scraped URL. Tavily uses proprietary AI to extract the most relevant content based on context quality and size. |
        | `score`                     | `float` | The relevance score of the search result.                                                                                                               |
        | `raw_content` (optional)    | `str`   | The parsed and cleaned HTML content of the site. This is only available if `include_raw_content` is set to `True`.                                      |
        | `published_date` (optional) | `str`   | The publication date of the source. This is only available if the search `topic` is set to `"news"`.                                                    |
        | `favicon` (optional)        | `str`   | The favicon URL for the search result.                                                                                                                  |

        #### Image Results

        If `includeImageDescriptions` is set to `true`, each image in the `images` list will be in the following `ImageResult` format:

        | Key           | Type     | Description                                |
        | :------------ | :------- | :----------------------------------------- |
        | `url`         | `string` | The URL of the image.                      |
        | `description` | `string` | An LLM-generated description of the image. |
        """

        if __event_emitter__ is not None:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search_queries_generated",
                        "queries": [query],
                        "done": True,
                        "hidden": False,
                    },
                }
            )

        client = self.get_client()

        response = await client.search(
            query=query,
            search_depth=search_depth,
            topic=topic,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            include_images=include_images,
            country=country,
            include_favicon=True,
            chunks_per_source=chunks_per_source,
            include_image_descriptions=include_image_descriptions,
        )

        if __event_emitter__ is not None:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "action": "web_search",
                        "description": "Searched {{count}} sites",
                        "urls": [result["url"] for result in response["results"]],
                        "items": [
                            {
                                "link": result["url"],
                                "title": result["title"],
                                "snippet": result["content"],
                            }
                            for result in response["results"]
                        ],
                        "done": True,
                    },
                }
            )

            sources = [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "content": result["content"],
                }
                for result in response["results"]
            ]

            # Emit citations for each source
            for source in sources:
                await __event_emitter__(
                    {
                        "type": "citation",
                        "data": {
                            "document": [source["content"]],
                            "metadata": [
                                {
                                    "source": source["title"],
                                    "url": source["url"],
                                }
                            ],
                            "source": {"name": source["title"], "url": source["url"]},
                        },
                    }
                )

        return response["results"]

    def get_client(self) -> AsyncTavilyClient:
        return AsyncTavilyClient(self.valves.tavily_api_key)
