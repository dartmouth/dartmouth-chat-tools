"""
title: Tasks
version: 0.11.3
icon_url: TaskList
"""

import json
import logging
from typing import Literal, Optional

from fastapi import Request
from pydantic import BaseModel, Field

from open_webui.models.chats import Chats
from open_webui.utils.chat_id import is_saved_chat_id

log = logging.getLogger(__name__)

VALID_TASK_STATUSES = {'pending', 'in_progress', 'completed', 'cancelled'}


class TaskItem(BaseModel):
    id: Optional[str] = Field(None, description='Unique identifier for the task. Auto-generated if omitted.')
    content: str = Field(..., description='Task description.')
    status: Literal['pending', 'in_progress', 'completed', 'cancelled'] = Field(
        'pending', description='Task status.'
    )


def _task_summary(all_tasks: list[dict]) -> dict:
    """Build summary counts for a task list."""
    pending = sum(1 for t in all_tasks if t['status'] == 'pending')
    in_progress = sum(1 for t in all_tasks if t['status'] == 'in_progress')
    completed = sum(1 for t in all_tasks if t['status'] == 'completed')
    cancelled = sum(1 for t in all_tasks if t['status'] == 'cancelled')
    return {
        'total': len(all_tasks),
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    }


async def _emit_tasks(event_emitter, all_tasks: list[dict]):
    """Persist task state to the UI."""
    if event_emitter:
        await event_emitter(
            {
                'type': 'chat:message:tasks',
                'data': {
                    'tasks': all_tasks,
                },
            }
        )


class Tools:
    async def create_tasks(
        self,
        tasks: list[TaskItem],
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: callable = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Create a task checklist to track progress on multi-step work.
        Call this once at the start to define all steps, then use
        update_task to mark each task as you complete it.

        :param tasks: List of task items. Each item: content (string, required), status (pending|in_progress|completed|cancelled, default pending), id (optional, auto-generated).
        :return: JSON with the full task list and summary counts
        """
        if not is_saved_chat_id(__chat_id__):
            return json.dumps({'error': 'Saved chat context not available'})

        try:
            all_tasks = []
            for idx, task in enumerate(tasks):
                if hasattr(task, 'model_dump'):
                    d = task.model_dump(exclude_none=True)
                elif isinstance(task, dict):
                    d = task
                else:
                    d = dict(task)

                content = str(d.get('content', '')).strip()
                if not content:
                    continue

                item_id = str(d.get('id', '') or '').strip() or str(idx + 1)
                status = str(d.get('status', 'pending')).strip().lower()
                if status not in VALID_TASK_STATUSES:
                    status = 'pending'

                all_tasks.append({'id': item_id, 'content': content, 'status': status})

            await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
            await _emit_tasks(__event_emitter__, all_tasks)

            return json.dumps(
                {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'tasks error: {e}')
            return json.dumps({'error': str(e)})

    async def update_task(
        self,
        id: str,
        status: str = 'completed',
        __chat_id__: str = None,
        __message_id__: str = None,
        __event_emitter__: callable = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Mark a single task as completed, in_progress, pending, or cancelled.
        Call this after finishing each step. You MUST call this for every
        task, including the very last one.

        :param id: The task ID to update
        :param status: New status: completed, in_progress, pending, or cancelled (default: completed)
        :return: JSON with the updated task list and summary counts
        """
        if not is_saved_chat_id(__chat_id__):
            return json.dumps({'error': 'Saved chat context not available'})

        try:
            status = status.strip().lower()
            if status not in VALID_TASK_STATUSES:
                return json.dumps(
                    {'error': f'Invalid status: {status}. Must be one of: {", ".join(sorted(VALID_TASK_STATUSES))}'}
                )

            all_tasks = await Chats.get_chat_tasks_by_id(__chat_id__)

            found = False
            for task in all_tasks:
                if task['id'] == id:
                    task['status'] = status
                    found = True
                    break

            if not found:
                return json.dumps({'error': f'Task with id "{id}" not found'})

            await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
            await _emit_tasks(__event_emitter__, all_tasks)

            return json.dumps(
                {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f'update_task_status error: {e}')
            return json.dumps({'error': str(e)})
