"""
title: Knowledge
version: 0.10.2
icon_url: BookOpen
"""

import json
import logging
from typing import Optional

from fastapi import Request

from open_webui.models.groups import Groups
from open_webui.models.users import UserModel

log = logging.getLogger(__name__)

MAX_KNOWLEDGE_BASE_SEARCH_ITEMS = 10_000
DEFAULT_VIEW_FILE_MAX_CHARS = 10_000
MAX_VIEW_FILE_CHARS = 100_000

class Tools:
    async def list_knowledge_bases(
        self,
        count: int = 10,
        skip: int = 0,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        List the user's accessible knowledge bases.

        :param count: Maximum number of KBs to return (default: 10)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with KBs containing id, name, description, and file_count
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            from open_webui.models.knowledge import Knowledges

            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            result = await Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    'query': '',
                    'user_id': user_id,
                    'group_ids': user_group_ids,
                },
                skip=skip,
                limit=count,
            )

            knowledge_bases = []
            for knowledge_base in result.items:
                files = await Knowledges.get_files_by_id(knowledge_base.id)
                file_count = len(files) if files else 0

                knowledge_bases.append(
                    {
                        'id': knowledge_base.id,
                        'name': knowledge_base.name,
                        'description': knowledge_base.description or '',
                        'file_count': file_count,
                        'updated_at': knowledge_base.updated_at,
                    }
                )

            return json.dumps(knowledge_bases, ensure_ascii=False)
        except Exception as e:
            log.exception(f'list_knowledge_bases error: {e}')
            return json.dumps({'error': str(e)})


    async def search_knowledge_bases(
        self,
        query: str,
        count: int = 5,
        skip: int = 0,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Search the user's accessible knowledge bases by name and description.

        :param query: The search query to find matching knowledge bases
        :param count: Maximum number of results to return (default: 5)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with matching KBs containing id, name, description, and file_count
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            from open_webui.models.knowledge import Knowledges

            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            result = await Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    'query': query,
                    'user_id': user_id,
                    'group_ids': user_group_ids,
                },
                skip=skip,
                limit=count,
            )

            knowledge_bases = []
            for knowledge_base in result.items:
                files = await Knowledges.get_files_by_id(knowledge_base.id)
                file_count = len(files) if files else 0

                knowledge_bases.append(
                    {
                        'id': knowledge_base.id,
                        'name': knowledge_base.name,
                        'description': knowledge_base.description or '',
                        'file_count': file_count,
                        'updated_at': knowledge_base.updated_at,
                    }
                )

            return json.dumps(knowledge_bases, ensure_ascii=False)
        except Exception as e:
            log.exception(f'search_knowledge_bases error: {e}')
            return json.dumps({'error': str(e)})


    async def search_knowledge_files(
        self,
        query: str,
        knowledge_id: Optional[str] = None,
        count: int = 5,
        skip: int = 0,
        __request__: Request = None,
        __user__: dict = None,
        __model_knowledge__: Optional[list[dict]] = None,
    ) -> str:
        """
        Search files by filename across knowledge bases the user has access to.
        When the model has attached knowledge, searches only within attached KBs and files.

        :param query: The search query to find matching files by filename
        :param knowledge_id: Optional KB id to limit search to a specific knowledge base
        :param count: Maximum number of results to return (default: 5)
        :param skip: Number of results to skip for pagination (default: 0)
        :return: JSON with matching files containing id, filename, and updated_at
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            from open_webui.models.knowledge import Knowledges
            from open_webui.models.files import Files
            from open_webui.models.access_grants import AccessGrants

            user_id = __user__.get('id')
            user_role = __user__.get('role', 'user')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            # When model has attached knowledge, scope to attached KBs/files only
            if __model_knowledge__:
                attached_kb_ids = set()
                attached_file_ids = set()

                for item in __model_knowledge__:
                    item_type = item.get('type')
                    item_id = item.get('id')
                    if item_type == 'collection':
                        attached_kb_ids.add(item_id)
                    elif item_type == 'file':
                        attached_file_ids.add(item_id)

                # If knowledge_id specified, verify it's in the attached set
                if knowledge_id:
                    if knowledge_id not in attached_kb_ids:
                        return json.dumps({'error': f'Knowledge base {knowledge_id} is not attached to this model'})
                    attached_kb_ids = {knowledge_id}

                all_files = []

                # Search within attached KBs
                for kb_id in attached_kb_ids:
                    knowledge = await Knowledges.get_knowledge_by_id(kb_id)
                    if not knowledge:
                        continue

                    if not (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        continue

                    result = await Knowledges.search_files_by_id(
                        knowledge_id=kb_id,
                        user_id=user_id,
                        filter={'query': query},
                        skip=0,
                        limit=count + skip,
                    )

                    for file in result.items:
                        all_files.append(
                            {
                                'id': file.id,
                                'filename': file.filename,
                                'knowledge_id': knowledge.id,
                                'knowledge_name': knowledge.name,
                                'updated_at': file.updated_at,
                            }
                        )

                # Search within directly attached files (filename match)
                if not knowledge_id and attached_file_ids:
                    query_lower = query.lower() if query else ''
                    for file_id in attached_file_ids:
                        file = await Files.get_file_by_id(file_id)
                        if file and (not query_lower or query_lower in file.filename.lower()):
                            all_files.append(
                                {
                                    'id': file.id,
                                    'filename': file.filename,
                                    'updated_at': file.updated_at,
                                }
                            )

                # Apply pagination across combined results
                all_files = all_files[skip : skip + count]
                return json.dumps(all_files, ensure_ascii=False)

            # No attached knowledge - search all accessible KBs
            if knowledge_id:
                result = await Knowledges.search_files_by_id(
                    knowledge_id=knowledge_id,
                    user_id=user_id,
                    filter={'query': query},
                    skip=skip,
                    limit=count,
                )
            else:
                result = await Knowledges.search_knowledge_files(
                    filter={
                        'query': query,
                        'user_id': user_id,
                        'group_ids': user_group_ids,
                    },
                    skip=skip,
                    limit=count,
                )

            files = []
            for file in result.items:
                file_info = {
                    'id': file.id,
                    'filename': file.filename,
                    'updated_at': file.updated_at,
                }
                if hasattr(file, 'collection') and file.collection:
                    file_info['knowledge_id'] = file.collection.get('id', '')
                    file_info['knowledge_name'] = file.collection.get('name', '')
                files.append(file_info)

            return json.dumps(files, ensure_ascii=False)
        except Exception as e:
            log.exception(f'search_knowledge_files error: {e}')
            return json.dumps({'error': str(e)})


    async def view_file(
        self,
        file_id: str,
        offset: int = 0,
        max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
        __request__: Request = None,
        __user__: dict = None,
        __model_knowledge__: Optional[list[dict]] = None,
    ) -> str:
        """
        Get the content of a file by its ID. Supports pagination for large files.

        :param file_id: The ID of the file to retrieve
        :param offset: Character offset to start reading from (default: 0)
        :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
        :return: JSON with the file's id, filename, content, and pagination metadata if truncated
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        # Coerce parameters from LLM tool calls (may come as strings)
        if isinstance(offset, str):
            try:
                offset = int(offset)
            except ValueError:
                offset = 0
        if isinstance(max_chars, str):
            try:
                max_chars = int(max_chars)
            except ValueError:
                max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

        # Enforce hard cap
        max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
        offset = max(offset, 0)

        try:
            from open_webui.models.files import Files
            from open_webui.utils.access_control.files import has_access_to_file

            user_id = __user__.get('id')
            user_role = __user__.get('role', 'user')

            file = await Files.get_file_by_id(file_id)
            if not file:
                return json.dumps({'error': 'File not found'})

            if (
                file.user_id != user_id
                and user_role != 'admin'
                and not any(
                    item.get('type') == 'file' and item.get('id') == file_id for item in (__model_knowledge__ or [])
                )
                and not await has_access_to_file(
                    file_id=file_id,
                    access_type='read',
                    user=UserModel(**__user__),
                )
            ):
                return json.dumps({'error': 'File not found'})

            content = ''
            if file.data:
                content = file.data.get('content', '')

            total_chars = len(content)
            sliced = content[offset : offset + max_chars]
            is_truncated = (offset + len(sliced)) < total_chars

            result = {
                'id': file.id,
                'filename': file.filename,
                'content': sliced,
                'updated_at': file.updated_at,
                'created_at': file.created_at,
            }

            if is_truncated or offset > 0:
                result['truncated'] = is_truncated
                result['total_chars'] = total_chars
                result['returned_chars'] = len(sliced)
                result['offset'] = offset
                if is_truncated:
                    result['next_offset'] = offset + len(sliced)

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f'view_file error: {e}')
            return json.dumps({'error': str(e)})


    async def view_knowledge_file(
        self,
        file_id: str,
        offset: int = 0,
        max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Get the content of a file from a knowledge base. Supports pagination for large files.

        :param file_id: The ID of the file to retrieve
        :param offset: Character offset to start reading from (default: 0)
        :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
        :return: JSON with the file's id, filename, content, and pagination metadata if truncated
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        # Coerce parameters from LLM tool calls (may come as strings)
        if isinstance(offset, str):
            try:
                offset = int(offset)
            except ValueError:
                offset = 0
        if isinstance(max_chars, str):
            try:
                max_chars = int(max_chars)
            except ValueError:
                max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

        # Enforce hard cap
        max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
        offset = max(offset, 0)

        try:
            from open_webui.models.files import Files
            from open_webui.models.knowledge import Knowledges
            from open_webui.models.access_grants import AccessGrants

            user_id = __user__.get('id')
            user_role = __user__.get('role', 'user')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            file = await Files.get_file_by_id(file_id)
            if not file:
                return json.dumps({'error': 'File not found'})

            # Check access via any KB containing this file
            knowledges = await Knowledges.get_knowledges_by_file_id(file_id)
            has_knowledge_access = False
            knowledge_info = None

            for knowledge_base in knowledges:
                if (
                    user_role == 'admin'
                    or knowledge_base.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge_base.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    has_knowledge_access = True
                    knowledge_info = {'id': knowledge_base.id, 'name': knowledge_base.name}
                    break

            if not has_knowledge_access:
                if file.user_id != user_id and user_role != 'admin':
                    return json.dumps({'error': 'Access denied'})

            content = ''
            if file.data:
                content = file.data.get('content', '')

            total_chars = len(content)
            sliced = content[offset : offset + max_chars]
            is_truncated = (offset + len(sliced)) < total_chars

            result = {
                'id': file.id,
                'filename': file.filename,
                'content': sliced,
                'updated_at': file.updated_at,
                'created_at': file.created_at,
            }
            if knowledge_info:
                result['knowledge_id'] = knowledge_info['id']
                result['knowledge_name'] = knowledge_info['name']

            if is_truncated or offset > 0:
                result['truncated'] = is_truncated
                result['total_chars'] = total_chars
                result['returned_chars'] = len(sliced)
                result['offset'] = offset
                if is_truncated:
                    result['next_offset'] = offset + len(sliced)

            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            log.exception(f'view_knowledge_file error: {e}')
            return json.dumps({'error': str(e)})


    async def list_knowledge(
        self,
        __request__: Request = None,
        __user__: dict = None,
        __model_knowledge__: Optional[list[dict]] = None,
    ) -> str:
        """
        List all knowledge bases, files, and notes attached to the current model.
        Use this first to discover what knowledge is available before querying or reading files.

        :return: JSON with knowledge_bases, files, and notes attached to this model
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        if not __model_knowledge__:
            return json.dumps({'knowledge_bases': [], 'files': [], 'notes': []})

        try:
            from open_webui.models.knowledge import Knowledges
            from open_webui.models.files import Files
            from open_webui.models.notes import Notes
            from open_webui.models.access_grants import AccessGrants

            user_id = __user__.get('id')
            user_role = __user__.get('role', 'user')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            knowledge_bases = []
            files = []
            notes = []

            for item in __model_knowledge__:
                item_type = item.get('type')
                item_id = item.get('id')

                if item_type == 'collection':
                    knowledge = await Knowledges.get_knowledge_by_id(item_id)
                    if knowledge and (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        kb_files = await Knowledges.get_files_by_id(knowledge.id)
                        file_count = len(kb_files) if kb_files else 0

                        kb_entry = {
                            'id': knowledge.id,
                            'name': knowledge.name,
                            'description': knowledge.description or '',
                            'file_count': file_count,
                        }

                        # Include file listing for each KB
                        if kb_files:
                            kb_entry['files'] = [{'id': f.id, 'filename': f.filename} for f in kb_files]

                        knowledge_bases.append(kb_entry)

                elif item_type == 'file':
                    file = await Files.get_file_by_id(item_id)
                    if file:
                        files.append(
                            {
                                'id': file.id,
                                'filename': file.filename,
                                'updated_at': file.updated_at,
                            }
                        )

                elif item_type == 'note':
                    note = await Notes.get_note_by_id(item_id)
                    if note and (
                        user_role == 'admin'
                        or note.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='note',
                            resource_id=note.id,
                            permission='read',
                        )
                    ):
                        notes.append(
                            {
                                'id': note.id,
                                'title': note.title,
                            }
                        )

            return json.dumps(
                {
                    'knowledge_bases': knowledge_bases,
                    'files': files,
                    'notes': notes,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'list_knowledge error: {e}')
            return json.dumps({'error': str(e)})


    async def query_knowledge_files(
        self,
        query: str,
        knowledge_ids: Optional[list[str]] = None,
        count: int = 5,
        __request__: Request = None,
        __user__: dict = None,
        __model_knowledge__: list[dict] = None,
    ) -> str:
        """
        Search knowledge base files using semantic/vector search. Searches across collections (KBs),
        individual files, and notes that the user has access to.

        :param query: The search query to find semantically relevant content
        :param knowledge_ids: Optional list of KB ids to limit search to specific knowledge bases
        :param count: Maximum number of results to return (default: 5)
        :return: JSON with relevant chunks containing content, source filename, and relevance score
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        # Coerce parameters from LLM tool calls (may come as strings)
        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 5  # Default fallback

        # Handle knowledge_ids being string "None", "null", or empty
        if isinstance(knowledge_ids, str):
            if knowledge_ids.lower() in ('none', 'null', ''):
                knowledge_ids = None
            else:
                # Try to parse as JSON array if it looks like one
                try:
                    knowledge_ids = json.loads(knowledge_ids)
                except json.JSONDecodeError:
                    # Treat as single ID
                    knowledge_ids = [knowledge_ids]

        try:
            from open_webui.models.knowledge import Knowledges
            from open_webui.models.files import Files
            from open_webui.models.notes import Notes
            from open_webui.retrieval.external import retrieve_external_knowledge
            from open_webui.retrieval.utils import query_collection
            from open_webui.models.access_grants import AccessGrants

            user_id = __user__.get('id')
            user_role = __user__.get('role', 'user')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            embedding_function = __request__.app.state.EMBEDDING_FUNCTION
            if not embedding_function:
                return json.dumps({'error': 'Embedding function not configured'})

            collection_names = []
            external_knowledges = []
            note_results = []  # Notes aren't vectorized, handle separately

            # If model has attached knowledge, use those
            if __model_knowledge__:
                for item in __model_knowledge__:
                    item_type = item.get('type')
                    item_id = item.get('id')

                    if item_type == 'collection':
                        # Knowledge base - use KB ID as collection name
                        knowledge = await Knowledges.get_knowledge_by_id(item_id)
                        if knowledge and (
                            user_role == 'admin'
                            or knowledge.user_id == user_id
                            or await AccessGrants.has_access(
                                user_id=user_id,
                                resource_type='knowledge',
                                resource_id=knowledge.id,
                                permission='read',
                                user_group_ids=set(user_group_ids),
                            )
                        ):
                            if (knowledge.meta or {}).get('source') == 'external':
                                external_knowledges.append(knowledge)
                            else:
                                collection_names.append(item_id)

                    elif item_type == 'file':
                        # Individual file - use file-{id} as collection name
                        file = await Files.get_file_by_id(item_id)
                        if file:
                            collection_names.append(f'file-{item_id}')

                    elif item_type == 'note':
                        # Note - always return full content as context
                        note = await Notes.get_note_by_id(item_id)
                        if note and (
                            user_role == 'admin'
                            or note.user_id == user_id
                            or await AccessGrants.has_access(
                                user_id=user_id,
                                resource_type='note',
                                resource_id=note.id,
                                permission='read',
                            )
                        ):
                            content = note.data.get('content', {}).get('md', '')
                            note_results.append(
                                {
                                    'content': content,
                                    'source': note.title,
                                    'note_id': note.id,
                                    'type': 'note',
                                }
                            )

            elif knowledge_ids:
                # User specified specific KBs
                for knowledge_id in knowledge_ids:
                    knowledge = await Knowledges.get_knowledge_by_id(knowledge_id)
                    if knowledge and (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        if (knowledge.meta or {}).get('source') == 'external':
                            external_knowledges.append(knowledge)
                        else:
                            collection_names.append(knowledge_id)
            else:
                # No model knowledge and no specific IDs - search all accessible KBs
                result = await Knowledges.search_knowledge_bases(
                    user_id,
                    filter={
                        'query': '',
                        'user_id': user_id,
                        'group_ids': user_group_ids,
                    },
                    skip=0,
                    limit=50,
                )
                for knowledge_base in result.items:
                    if (knowledge_base.meta or {}).get('source') == 'external':
                        external_knowledges.append(knowledge_base)
                    else:
                        collection_names.append(knowledge_base.id)

            chunks = []

            # Add note results first
            chunks.extend(note_results)

            # Query vector collections if any
            if collection_names:
                query_results = await query_collection(
                    __request__,
                    collection_names=collection_names,
                    queries=[query],
                    embedding_function=embedding_function,
                    k=count,
                )

                if query_results and 'documents' in query_results:
                    documents = query_results.get('documents', [[]])[0]
                    metadatas = query_results.get('metadatas', [[]])[0]
                    distances = query_results.get('distances', [[]])[0]

                    for idx, doc in enumerate(documents):
                        chunk_info = {
                            'content': doc,
                            'source': metadatas[idx].get('source', metadatas[idx].get('name', 'Unknown')),
                            'file_id': metadatas[idx].get('file_id', ''),
                        }
                        if idx < len(distances):
                            chunk_info['distance'] = distances[idx]
                        chunks.append(chunk_info)

            for knowledge in external_knowledges:
                query_results = await retrieve_external_knowledge(
                    __request__,
                    knowledge,
                    queries=[query],
                    count=count,
                    user=type('UserContext', (), {'id': user_id, 'role': user_role})(),
                )
                documents = query_results.get('documents', [[]])[0]
                metadatas = query_results.get('metadatas', [[]])[0]
                distances = query_results.get('distances', [[]])[0]

                for idx, doc in enumerate(documents):
                    metadata = metadatas[idx] if idx < len(metadatas) else {}
                    chunk_info = {
                        'content': doc,
                        'source': metadata.get('source', metadata.get('name', knowledge.name)),
                        'file_id': metadata.get('file_id', f'external-{knowledge.id}'),
                        'type': 'external',
                        'knowledge_id': knowledge.id,
                    }
                    if idx < len(distances):
                        chunk_info['distance'] = distances[idx]
                    chunks.append(chunk_info)

            # Limit to requested count
            chunks = chunks[:count]

            return json.dumps(chunks, ensure_ascii=False)
        except Exception as e:
            log.exception(f'query_knowledge_files error: {e}')
            return json.dumps({'error': str(e)})


    async def query_knowledge_bases(
        self,
        query: str,
        count: int = 5,
        __request__: Request = None,
        __user__: dict = None,
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
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            import heapq
            from open_webui.models.knowledge import Knowledges
            from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION
            from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT

            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
            query_embedding = await __request__.app.state.EMBEDDING_FUNCTION(query)

            # Min-heap of (distance, knowledge_base_id) - only holds top `count` results
            top_results_heap = []
            seen_ids = set()
            page_offset = 0
            page_size = 100

            while True:
                accessible_knowledge_bases = await Knowledges.search_knowledge_bases(
                    user_id,
                    filter={'user_id': user_id, 'group_ids': user_group_ids},
                    skip=page_offset,
                    limit=page_size,
                )

                if not accessible_knowledge_bases.items:
                    break

                accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]

                search_results = await ASYNC_VECTOR_DB_CLIENT.search(
                    collection_name=KNOWLEDGE_BASES_COLLECTION,
                    vectors=[query_embedding],
                    filter={'knowledge_base_id': {'$in': accessible_ids}},
                    limit=count,
                )

                if search_results and search_results.ids and search_results.ids[0]:
                    result_ids = search_results.ids[0]
                    result_distances = search_results.distances[0] if search_results.distances else [0] * len(result_ids)

                    for knowledge_base_id, distance in zip(result_ids, result_distances):
                        if knowledge_base_id in seen_ids:
                            continue
                        seen_ids.add(knowledge_base_id)

                        if len(top_results_heap) < count:
                            heapq.heappush(top_results_heap, (distance, knowledge_base_id))
                        elif distance > top_results_heap[0][0]:
                            heapq.heapreplace(top_results_heap, (distance, knowledge_base_id))

                page_offset += page_size
                if len(accessible_knowledge_bases.items) < page_size:
                    break
                if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
                    break

            # Sort by distance descending (best first) and fetch KB details
            sorted_results = sorted(top_results_heap, key=lambda x: x[0], reverse=True)

            matching_knowledge_bases = []
            for distance, knowledge_base_id in sorted_results:
                knowledge_base = await Knowledges.get_knowledge_by_id(knowledge_base_id)
                if knowledge_base:
                    matching_knowledge_bases.append(
                        {
                            'id': knowledge_base.id,
                            'name': knowledge_base.name,
                            'description': knowledge_base.description or '',
                            'similarity': round(distance, 4),
                        }
                    )

            return json.dumps(matching_knowledge_bases, ensure_ascii=False)

        except Exception as e:
            log.exception(f'query_knowledge_bases error: {e}')
            return json.dumps({'error': str(e)})
