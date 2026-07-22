"""
title: Notes
version: 0.10.2
"""

import json
import logging
import time
import asyncio
from typing import Optional

from fastapi import Request

from open_webui.models.notes import Notes
from open_webui.models.groups import Groups

log = logging.getLogger(__name__)


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

            if note.user_id != user_id and not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='note',
                resource_id=note.id,
                permission='read',
                user_group_ids=set(user_group_ids),
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
        content: str,
        title: Optional[str] = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Update the content of a note. Use this to modify task lists, add notes, or update content.

        :param note_id: The ID of the note to update
        :param content: The new markdown content for the note
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
                return json.dumps({'error': 'Note not found'})

            # Check write permission
            user_id = __user__.get('id')
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

            from open_webui.models.access_grants import AccessGrants

            if note.user_id != user_id and not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='note',
                resource_id=note.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Write access denied'})

            # Build update form
            update_data = {'data': {'content': {'md': content}}}
            if title:
                update_data['title'] = title

            form = NoteUpdateForm(**update_data)
            updated_note = await Notes.update_note_by_id(note_id, form)

            if not updated_note:
                return json.dumps({'error': 'Failed to update note'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': updated_note.id,
                    'title': updated_note.title,
                    'updated_at': updated_note.updated_at,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'replace_note_content error: {e}')
            return json.dumps({'error': str(e)})
