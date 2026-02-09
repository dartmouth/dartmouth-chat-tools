import json
import logging
from typing import Optional

from fastapi import Request

from open_webui.models.groups import Groups

log = logging.getLogger(__name__)

MAX_KNOWLEDGE_BASE_SEARCH_ITEMS = 10_000


class Tools:
    # =============================================================================
    # KNOWLEDGE BASE TOOLS
    # =============================================================================

    async def list_knowledge_bases(
        self,
        count: int = 10,
        skip: int = 0,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        List the user's accessible knowledge bases.

        :param count: Maximum number of KBs to return (default: 10)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with KBs containing id, name, description, and file_count
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.knowledge import Knowledges

            user_id = __user__.get("id")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]

            result = Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    "query": "",
                    "user_id": user_id,
                    "group_ids": user_group_ids,
                },
                skip=skip,
                limit=count,
            )

            knowledge_bases = []
            for knowledge_base in result.items:
                files = Knowledges.get_files_by_id(knowledge_base.id)
                file_count = len(files) if files else 0

                knowledge_bases.append(
                    {
                        "id": knowledge_base.id,
                        "name": knowledge_base.name,
                        "description": knowledge_base.description or "",
                        "file_count": file_count,
                        "updated_at": knowledge_base.updated_at,
                    }
                )

            return json.dumps(knowledge_bases, ensure_ascii=False)
        except Exception as e:
            log.exception(f"list_knowledge_bases error: {e}")
            return json.dumps({"error": str(e)})

    async def search_knowledge_bases(
        self,
        query: str,
        count: int = 5,
        skip: int = 0,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search the user's accessible knowledge bases by name and description.

        :param query: The search query to find matching knowledge bases
        :param count: Maximum number of results to return (default: 5)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with matching KBs containing id, name, description, and file_count
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.knowledge import Knowledges

            user_id = __user__.get("id")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]

            result = Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    "query": query,
                    "user_id": user_id,
                    "group_ids": user_group_ids,
                },
                skip=skip,
                limit=count,
            )

            knowledge_bases = []
            for knowledge_base in result.items:
                files = Knowledges.get_files_by_id(knowledge_base.id)
                file_count = len(files) if files else 0

                knowledge_bases.append(
                    {
                        "id": knowledge_base.id,
                        "name": knowledge_base.name,
                        "description": knowledge_base.description or "",
                        "file_count": file_count,
                        "updated_at": knowledge_base.updated_at,
                    }
                )

            return json.dumps(knowledge_bases, ensure_ascii=False)
        except Exception as e:
            log.exception(f"search_knowledge_bases error: {e}")
            return json.dumps({"error": str(e)})

    async def search_knowledge_files(
        self,
        query: str,
        knowledge_id: Optional[str] = None,
        count: int = 5,
        skip: int = 0,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search files across knowledge bases the user has access to.

        :param query: The search query to find matching files by filename
        :param knowledge_id: Optional KB id to limit search to a specific knowledge base
        :param count: Maximum number of results to return (default: 5)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with matching files containing id, filename, and updated_at
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.knowledge import Knowledges

            user_id = __user__.get("id")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]

            if knowledge_id:
                result = Knowledges.search_files_by_id(
                    knowledge_id=knowledge_id,
                    user_id=user_id,
                    filter={"query": query},
                    skip=skip,
                    limit=count,
                )
            else:
                result = Knowledges.search_knowledge_files(
                    filter={
                        "query": query,
                        "user_id": user_id,
                        "group_ids": user_group_ids,
                    },
                    skip=skip,
                    limit=count,
                )

            files = []
            for file in result.items:
                file_info = {
                    "id": file.id,
                    "filename": file.filename,
                    "updated_at": file.updated_at,
                }
                if hasattr(file, "collection") and file.collection:
                    file_info["knowledge_id"] = file.collection.get("id", "")
                    file_info["knowledge_name"] = file.collection.get("name", "")
                files.append(file_info)

            return json.dumps(files, ensure_ascii=False)
        except Exception as e:
            log.exception(f"search_knowledge_files error: {e}")
            return json.dumps({"error": str(e)})

    async def view_knowledge_file(
        self,
        file_id: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Get the full content of a file from a knowledge base.

        :param file_id: The ID of the file to retrieve
        :return: JSON with the file's id, filename, and full text content
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.files import Files
            from open_webui.models.knowledge import Knowledges
            from open_webui.utils.access_control import has_access

            user_id = __user__.get("id")
            user_role = __user__.get("role", "user")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]

            file = Files.get_file_by_id(file_id)
            if not file:
                return json.dumps({"error": "File not found"})

            # Check access via any KB containing this file
            knowledges = Knowledges.get_knowledges_by_file_id(file_id)
            has_knowledge_access = False
            knowledge_info = None

            for knowledge_base in knowledges:
                if (
                    user_role == "admin"
                    or knowledge_base.user_id == user_id
                    or has_access(
                        user_id, "read", knowledge_base.access_control, user_group_ids
                    )
                ):
                    has_knowledge_access = True
                    knowledge_info = {
                        "id": knowledge_base.id,
                        "name": knowledge_base.name,
                    }
                    break

            if not has_knowledge_access:
                if file.user_id != user_id and user_role != "admin":
                    return json.dumps({"error": "Access denied"})

            content = ""
            if file.data:
                content = file.data.get("content", "")

            result = {
                "id": file.id,
                "filename": file.filename,
                "content": content,
                "updated_at": file.updated_at,
                "created_at": file.created_at,
            }
            if knowledge_info:
                result["knowledge_id"] = knowledge_info["id"]
                result["knowledge_name"] = knowledge_info["name"]

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f"view_knowledge_file error: {e}")
            return json.dumps({"error": str(e)})

    async def query_knowledge_files(
        self,
        query: str,
        knowledge_ids: Optional[list[str]] = None,
        count: int = 5,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
        __model_knowledge__: Optional[list[dict]] = None,
    ) -> str:
        """
        Search knowledge base files using semantic/vector search. This should be your first
        choice for finding information before searching the web. Searches across collections (KBs),
        individual files, and notes that the user has access to.

        :param query: The search query to find semantically relevant content
        :param knowledge_ids: Optional list of KB ids to limit search to specific knowledge bases
        :param count: Maximum number of results to return (default: 5)
        :return: JSON with relevant chunks containing content, source filename, and relevance score
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.knowledge import Knowledges
            from open_webui.models.files import Files
            from open_webui.models.notes import Notes
            from open_webui.retrieval.utils import query_collection
            from open_webui.utils.access_control import has_access

            user_id = __user__.get("id")
            user_role = __user__.get("role", "user")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]

            embedding_function = __request__.app.state.EMBEDDING_FUNCTION
            if not embedding_function:
                return json.dumps({"error": "Embedding function not configured"})

            collection_names = []
            note_results = []  # Notes aren't vectorized, handle separately

            # If model has attached knowledge, use those
            if __model_knowledge__:
                for item in __model_knowledge__:
                    item_type = item.get("type")
                    item_id = item.get("id")

                    if item_type == "collection":
                        # Knowledge base - use KB ID as collection name
                        knowledge = Knowledges.get_knowledge_by_id(item_id)
                        if knowledge and (
                            user_role == "admin"
                            or knowledge.user_id == user_id
                            or has_access(
                                user_id,
                                "read",
                                knowledge.access_control,
                                user_group_ids,
                            )
                        ):
                            collection_names.append(item_id)

                    elif item_type == "file":
                        # Individual file - use file-{id} as collection name
                        file = Files.get_file_by_id(item_id)
                        if file and (user_role == "admin" or file.user_id == user_id):
                            collection_names.append(f"file-{item_id}")

                    elif item_type == "note":
                        # Note - always return full content as context
                        note = Notes.get_note_by_id(item_id)
                        if note and (
                            user_role == "admin"
                            or note.user_id == user_id
                            or has_access(user_id, "read", note.access_control)
                        ):
                            content = note.data.get("content", {}).get("md", "")
                            note_results.append(
                                {
                                    "content": content,
                                    "source": note.title,
                                    "note_id": note.id,
                                    "type": "note",
                                }
                            )

            elif knowledge_ids:
                # User specified specific KBs
                for knowledge_id in knowledge_ids:
                    knowledge = Knowledges.get_knowledge_by_id(knowledge_id)
                    if knowledge and (
                        user_role == "admin"
                        or knowledge.user_id == user_id
                        or has_access(
                            user_id, "read", knowledge.access_control, user_group_ids
                        )
                    ):
                        collection_names.append(knowledge_id)
            else:
                # No model knowledge and no specific IDs - search all accessible KBs
                result = Knowledges.search_knowledge_bases(
                    user_id,
                    filter={
                        "query": "",
                        "user_id": user_id,
                        "group_ids": user_group_ids,
                    },
                    skip=0,
                    limit=50,
                )
                collection_names = [
                    knowledge_base.id for knowledge_base in result.items
                ]

            chunks = []

            # Add note results first
            chunks.extend(note_results)

            # Query vector collections if any
            if collection_names:
                query_results = await query_collection(
                    collection_names=collection_names,
                    queries=[query],
                    embedding_function=embedding_function,
                    k=count,
                )

                if query_results and "documents" in query_results:
                    documents = query_results.get("documents", [[]])[0]
                    metadatas = query_results.get("metadatas", [[]])[0]
                    distances = query_results.get("distances", [[]])[0]

                    for idx, doc in enumerate(documents):
                        chunk_info = {
                            "content": doc,
                            "source": metadatas[idx].get(
                                "source", metadatas[idx].get("name", "Unknown")
                            ),
                            "file_id": metadatas[idx].get("file_id", ""),
                        }
                        if idx < len(distances):
                            chunk_info["distance"] = distances[idx]
                        chunks.append(chunk_info)

            # Limit to requested count
            chunks = chunks[:count]

            return json.dumps(chunks, ensure_ascii=False)
        except Exception as e:
            log.exception(f"query_knowledge_files error: {e}")
            return json.dumps({"error": str(e)})

    async def query_knowledge_bases(
        self,
        query: str,
        count: int = 5,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Search knowledge bases by semantic similarity to query.
        Finds KBs whose name/description match the meaning of your query.
        Use this to discover relevant knowledge bases before querying their files.

        :param query: Natural language query describing what you're looking for
        :param count: Maximum results (default: 5)
        :return: JSON with matching KBs (id, name, description, similarity)
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            import heapq
            from open_webui.models.knowledge import Knowledges
            from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION
            from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

            user_id = __user__.get("id")
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id)
            ]
            query_embedding = await __request__.app.state.EMBEDDING_FUNCTION(query)

            # Min-heap of (distance, knowledge_base_id) - only holds top `count` results
            top_results_heap = []
            seen_ids = set()
            page_offset = 0
            page_size = 100

            while True:
                accessible_knowledge_bases = Knowledges.search_knowledge_bases(
                    user_id,
                    filter={"user_id": user_id, "group_ids": user_group_ids},
                    skip=page_offset,
                    limit=page_size,
                )

                if not accessible_knowledge_bases.items:
                    break

                accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]

                search_results = VECTOR_DB_CLIENT.search(
                    collection_name=KNOWLEDGE_BASES_COLLECTION,
                    vectors=[query_embedding],
                    filter={"knowledge_base_id": {"$in": accessible_ids}},
                    limit=count,
                )

                if search_results and search_results.ids and search_results.ids[0]:
                    result_ids = search_results.ids[0]
                    result_distances = (
                        search_results.distances[0]
                        if search_results.distances
                        else [0] * len(result_ids)
                    )

                    for knowledge_base_id, distance in zip(
                        result_ids, result_distances
                    ):
                        if knowledge_base_id in seen_ids:
                            continue
                        seen_ids.add(knowledge_base_id)

                        if len(top_results_heap) < count:
                            heapq.heappush(
                                top_results_heap, (distance, knowledge_base_id)
                            )
                        elif distance > top_results_heap[0][0]:
                            heapq.heapreplace(
                                top_results_heap, (distance, knowledge_base_id)
                            )

                page_offset += page_size
                if len(accessible_knowledge_bases.items) < page_size:
                    break
                if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
                    break

            # Sort by distance descending (best first) and fetch KB details
            sorted_results = sorted(top_results_heap, key=lambda x: x[0], reverse=True)

            matching_knowledge_bases = []
            for distance, knowledge_base_id in sorted_results:
                knowledge_base = Knowledges.get_knowledge_by_id(knowledge_base_id)
                if knowledge_base:
                    matching_knowledge_bases.append(
                        {
                            "id": knowledge_base.id,
                            "name": knowledge_base.name,
                            "description": knowledge_base.description or "",
                            "similarity": round(distance, 4),
                        }
                    )

            return json.dumps(matching_knowledge_bases, ensure_ascii=False)

        except Exception as e:
            log.exception(f"query_knowledge_bases error: {e}")
            return json.dumps({"error": str(e)})
