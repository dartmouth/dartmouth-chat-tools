"""
title: Notes
version: 0.11.3
icon_url: Note
"""

import json
import logging
import time
import asyncio
from typing import Optional

from fastapi import Request

from open_webui.models.notes import Notes
from open_webui.models.groups import Groups
from open_webui.socket.main import sio
from open_webui.events import EVENTS, publish_event
from open_webui.tasks import stop_item_tasks

log = logging.getLogger(__name__)


async def _has_write_access_to_note(note, user_id: str) -> bool:
    if note.user_id == user_id:
        return True

    from open_webui.models.access_grants import AccessGrants

    user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
    return await AccessGrants.has_access(
        user_id=user_id,
        resource_type='note',
        resource_id=note.id,
        permission='write',
        user_group_ids=set(user_group_ids),
    )


async def _emit_note_updated(request: Request, user: dict, note) -> None:
    await sio.emit('events:note', note.model_dump(), to=f'note:{note.id}')
    await publish_event(
        request,
        EVENTS.NOTE_UPDATED,
        actor=user,
        subject_id=note.id,
        data={'title': note.title},
    )


class Tools:
    async def search_notes(
        self,
        query: str,
        count: int = 5,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Search the user's notes by title and content.

        :param query: The search query to find matching notes
        :param count: Maximum number of results to return (default: 5)
        :param start_timestamp: Only include notes updated after this Unix timestamp (seconds)
        :param end_timestamp: Only include notes updated before this Unix timestamp (seconds)
        :return: JSON with matching notes containing id, title, and content snippet
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            result = await Notes.search_notes(
                user_id=user_id,
                filter={
                    'query': query,
                    'user_id': user_id,
                    'group_ids': user_group_ids,
                    'permission': 'read',
                },
                skip=0,
                limit=count * 3,  # Fetch more for filtering
            )

            # Convert timestamps to nanoseconds for comparison
            start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
            end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

            notes = []
            for note in result.items:
                # Apply date filters (updated_at is in nanoseconds)
                if start_ts and note.updated_at < start_ts:
                    continue
                if end_ts and note.updated_at > end_ts:
                    continue

                # Extract a snippet from the markdown content
                content_snippet = ''
                if note.data and note.data.get('content', {}).get('md'):
                    md_content = note.data['content']['md']
                    content_lower = md_content.lower()

                    # Find the first matching word to center the snippet around.
                    search_words = query.lower().split()
                    match_pos = -1
                    match_len = len(query)
                    for word in search_words:
                        found_pos = content_lower.find(word)
                        if found_pos != -1:
                            match_pos = found_pos
                            match_len = len(word)
                            break

                    if match_pos != -1:
                        snippet_start = max(0, match_pos - 50)
                        snippet_end = min(len(md_content), match_pos + match_len + 100)
                        content_snippet = (
                            ('...' if snippet_start > 0 else '')
                            + md_content[snippet_start:snippet_end]
                            + ('...' if snippet_end < len(md_content) else '')
                        )
                    else:
                        content_snippet = md_content[:150] + ('...' if len(md_content) > 150 else '')

                notes.append(
                    {
                        'id': note.id,
                        'title': note.title,
                        'snippet': content_snippet,
                        'updated_at': note.updated_at,
                    }
                )

                if len(notes) >= count:
                    break

            return json.dumps(notes, ensure_ascii=False)
        except Exception as e:
            log.exception(f'search_notes error: {e}')
            return json.dumps({'error': str(e)})


    async def view_note(
        self,
        note_id: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Get the full content of a note by its ID.

        :param note_id: The ID of the note to retrieve
        :return: JSON with the note's id, title, and full markdown content
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            note = await Notes.get_note_by_id(note_id)

            if not note:
                return json.dumps({'error': 'Note not found'})

            # Check access permission
            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            from open_webui.models.access_grants import AccessGrants

            if (
                __user__.get('role') != 'admin'
                and note.user_id != user_id
                and not await AccessGrants.has_access(
                    user_id=user_id,
                    resource_type='note',
                    resource_id=note.id,
                    permission='read',
                    user_group_ids=set(user_group_ids),
                )
            ):
                return json.dumps({'error': 'Access denied'})

            # Extract markdown content
            content = ''
            if note.data and note.data.get('content', {}).get('md'):
                content = note.data['content']['md']

            return json.dumps(
                {
                    'id': note.id,
                    'title': note.title,
                    'content': content,
                    'updated_at': note.updated_at,
                    'created_at': note.created_at,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'view_note error: {e}')
            return json.dumps({'error': str(e)})


    async def write_note(
        self,
        title: str,
        content: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Create a new note with the given title and content.

        :param title: The title of the new note
        :param content: The markdown content for the note
        :return: JSON with success status and new note id
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            from open_webui.models.notes import NoteForm

            user_id = __user__.get('id')

            form = NoteForm(
                title=title,
                data={'content': {'md': content}},
                access_grants=[],  # Private by default - only owner can access
            )

            new_note = await Notes.insert_new_note(user_id, form)

            if not new_note:
                return json.dumps({'error': 'Failed to create note'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': new_note.id,
                    'title': new_note.title,
                    'created_at': new_note.created_at,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'write_note error: {e}')
            return json.dumps({'error': str(e)})


    async def replace_note_content(
        self,
        note_id: str,
        content: Optional[str] = None,
        operations: Optional[list[dict]] = None,
        title: Optional[str] = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Update an existing note by replacing the whole markdown content or applying range operations.

        :param note_id: The ID of the note to update
        :param content: The new markdown content for a whole-note update
        :param operations: Optional note operations:
        - {"action": "replace", "content": "..."}
        - {"action": "replace_range", "start": 0, "end": 10, "content": "...", "expected": "..."}
        :param title: Optional new title for the note
        :return: JSON with success status and updated note info
        """
        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        if not __user__:
            return json.dumps({'error': 'User context not available'})

        try:
            from open_webui.models.notes import NoteUpdateForm

            note = await Notes.get_note_by_id(note_id)

            if not note:
                return json.dumps({'error': 'Note not found', 'code': 'not_found'})

            user_id = __user__.get('id')
            if __user__.get('role') != 'admin' and not await _has_write_access_to_note(note, user_id):
                return json.dumps({'error': 'Write access denied', 'code': 'write_access_denied'})

            current_content = ((note.data or {}).get('content') or {}).get('md') or ''
            applied_operation_count = 0
            if operations is not None:
                if not isinstance(operations, list) or len(operations) == 0:
                    return json.dumps({'error': 'operations must be a non-empty list', 'code': 'invalid_operations'})

                range_operations = []
                for idx, operation in enumerate(operations):
                    if not isinstance(operation, dict):
                        return json.dumps(
                            {'error': 'each operation must be an object', 'code': 'invalid_operation', 'index': idx}
                        )

                    action = operation.get('action')
                    replacement = operation.get('content')

                    if action == 'replace':
                        if len(operations) != 1:
                            return json.dumps(
                                {
                                    'error': 'replace operation must be the only operation',
                                    'code': 'invalid_operations',
                                    'index': idx,
                                }
                            )
                        if not isinstance(replacement, str):
                            return json.dumps(
                                {
                                    'error': 'replace operation content must be a string',
                                    'code': 'invalid_content',
                                    'index': idx,
                                }
                            )
                        content = replacement
                        applied_operation_count = 1
                        break

                    if action != 'replace_range':
                        return json.dumps(
                            {'error': 'unknown operation action', 'code': 'invalid_action', 'index': idx, 'action': action}
                        )

                    start = operation.get('start')
                    end = operation.get('end')
                    expected = operation.get('expected')
                    if not isinstance(start, int) or not isinstance(end, int):
                        return json.dumps(
                            {'error': 'operation start and end must be integers', 'code': 'invalid_range', 'index': idx}
                        )
                    if not isinstance(replacement, str):
                        return json.dumps(
                            {'error': 'operation content must be a string', 'code': 'invalid_content', 'index': idx}
                        )
                    if start < 0 or end < start or end > len(current_content):
                        return json.dumps(
                            {'error': 'operation range is out of bounds', 'code': 'range_out_of_bounds', 'index': idx}
                        )
                    if expected is not None and current_content[start:end] != expected:
                        return json.dumps(
                            {
                                'error': 'operation expected text does not match current content',
                                'code': 'expected_mismatch',
                                'index': idx,
                            }
                        )

                    range_operations.append({'start': start, 'end': end, 'content': replacement})

                range_operations.sort(key=lambda operation: operation['start'])
                previous_end = 0
                for idx, operation in enumerate(range_operations):
                    if operation['start'] < previous_end:
                        return json.dumps(
                            {'error': 'operation ranges must not overlap', 'code': 'overlapping_operations', 'index': idx}
                        )
                    previous_end = operation['end']

                if range_operations:
                    content = current_content
                    for operation in reversed(range_operations):
                        content = content[: operation['start']] + operation['content'] + content[operation['end'] :]
                    applied_operation_count = len(range_operations)
            elif content is None:
                return json.dumps({'error': 'content or operations is required', 'code': 'content_required'})

            try:
                await stop_item_tasks(__request__.app.state.redis, f'note:{note_id}')
            except Exception:
                pass

            update_data = {
                'data': {
                    **(note.data or {}),
                    'content': {
                        **((note.data or {}).get('content') or {}),
                        'json': None,
                        'html': '',
                        'md': content,
                    },
                }
            }
            if title:
                update_data['title'] = title

            form = NoteUpdateForm(**update_data)
            updated_note = await Notes.update_note_by_id(note_id, form)

            if not updated_note:
                return json.dumps({'error': 'Failed to update note', 'code': 'update_failed'})

            await _emit_note_updated(__request__, __user__, updated_note)

            return json.dumps(
                {
                    'status': 'success',
                    'id': updated_note.id,
                    'title': updated_note.title,
                    'updated_at': updated_note.updated_at,
                    'applied_operation_count': applied_operation_count,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'replace_note_content error: {e}')
            return json.dumps({'error': str(e), 'code': 'unexpected_error'})
