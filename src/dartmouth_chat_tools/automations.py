"""
title: Automations
version: 0.9.2
"""

import json
import logging
from typing import Optional

from fastapi import Request

log = logging.getLogger(__name__)


class Tools:
    async def list_automations(
        self,
        status: Optional[str] = None,
        count: int = 10,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        List the user's scheduled automations.

        :param status: Filter by status: "active", "paused", or omit for all
        :param count: Maximum number of automations to return (default: 10)
        :return: JSON list of automations with id, name, prompt snippet, schedule, status, and next runs
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.automations import Automations
            from open_webui.models.users import Users
            from open_webui.utils.automations import next_n_runs_ns

            user_id = __user__.get("id")
            user = await Users.get_user_by_id(user_id)

            result = await Automations.search_automations(
                user_id=user_id,
                status=status,
                skip=0,
                limit=count,
            )

            automations = []
            for item in result.items:
                rrule = item.data.get("rrule", "")
                prompt_text = item.data.get("prompt", "")
                snippet = prompt_text[:100] + ("..." if len(prompt_text) > 100 else "")

                automations.append(
                    {
                        "id": item.id,
                        "name": item.name,
                        "prompt_snippet": snippet,
                        "model_id": item.data.get("model_id", ""),
                        "rrule": rrule,
                        "is_active": item.is_active,
                        "last_run_at": item.last_run_at,
                        "next_runs": next_n_runs_ns(
                            rrule, tz=user.timezone if user else None
                        ),
                    }
                )

            return json.dumps(
                {"automations": automations, "total": result.total},
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"list_automations error: {e}")
            return json.dumps({"error": str(e)})

    async def create_automation(
        self,
        name: str,
        prompt: str,
        rrule: str,
        __request__: Request = None,
        __user__: dict = None,
        __metadata__: dict = None,
    ) -> str:
        """
        Create a scheduled automation that runs a prompt on a recurring or one-time schedule.
        Use this when the user wants to schedule a task to run automatically.
        The automation will use the current chat model.

        The rrule parameter must be a valid iCalendar RRULE string. Common examples:
        - Every day at 9am: "DTSTART:20250101T090000\\nRRULE:FREQ=DAILY"
        - Every Monday at 8am: "DTSTART:20250106T080000\\nRRULE:FREQ=WEEKLY;BYDAY=MO"
        - Every hour: "RRULE:FREQ=HOURLY;INTERVAL=1"
        - Every 30 minutes: "RRULE:FREQ=MINUTELY;INTERVAL=30"
        - Once at a specific time: "DTSTART:20250415T140000\\nRRULE:FREQ=DAILY;COUNT=1"
        - First day of every month: "DTSTART:20250101T090000\\nRRULE:FREQ=MONTHLY;BYMONTHDAY=1"

        The DTSTART time should reflect the desired execution time. Use COUNT=1 for one-time automations.

        :param name: A short descriptive name for the automation
        :param prompt: The prompt/instructions to execute on each run
        :param rrule: An iCalendar RRULE string defining the schedule
        :return: JSON with the created automation details including id, next scheduled runs
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.automations import (
                Automations,
                AutomationForm,
                AutomationData,
            )
            from open_webui.models.users import Users
            from open_webui.utils.automations import (
                validate_rrule,
                next_run_ns,
                next_n_runs_ns,
            )

            user_id = __user__.get("id")
            user = await Users.get_user_by_id(user_id)
            if not user:
                return json.dumps({"error": "User not found"})

            # Fall back to model dict ID since __metadata__ may predate model_id assignment
            metadata = __metadata__ or {}
            model_id = metadata.get("model_id") or (
                metadata.get("model", {}).get("id")
                if isinstance(metadata.get("model"), dict)
                else None
            )
            if not model_id:
                return json.dumps({"error": "Could not detect current model"})

            # Validate the RRULE
            try:
                validate_rrule(rrule, tz=user.timezone)
            except ValueError as e:
                return json.dumps({"error": f"Invalid schedule: {e}"})

            tz = user.timezone
            form = AutomationForm(
                name=name,
                data=AutomationData(
                    prompt=prompt,
                    model_id=model_id,
                    rrule=rrule,
                ),
                is_active=True,
            )

            automation = await Automations.insert(
                user_id, form, next_run_ns(rrule, tz=tz)
            )

            return json.dumps(
                {
                    "status": "success",
                    "id": automation.id,
                    "name": automation.name,
                    "model_id": model_id,
                    "is_active": automation.is_active,
                    "next_runs": next_n_runs_ns(rrule, tz=tz),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"create_automation error: {e}")
            return json.dumps({"error": str(e)})

    async def update_automation(
        self,
        automation_id: str,
        name: Optional[str] = None,
        prompt: Optional[str] = None,
        rrule: Optional[str] = None,
        model_id: Optional[str] = None,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Update an existing automation. Only the provided fields are changed; omitted fields stay the same.

        :param automation_id: The ID of the automation to update
        :param name: New name for the automation (optional)
        :param prompt: New prompt/instructions (optional)
        :param rrule: New iCalendar RRULE schedule string (optional). See create_automation for format examples.
        :param model_id: New model ID to use (optional)
        :return: JSON with the updated automation details
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.automations import (
                Automations,
                AutomationForm,
                AutomationData,
            )
            from open_webui.models.users import Users
            from open_webui.utils.automations import (
                validate_rrule,
                next_run_ns,
                next_n_runs_ns,
            )

            user_id = __user__.get("id")
            user = await Users.get_user_by_id(user_id)

            automation = await Automations.get_by_id(automation_id)
            if not automation:
                return json.dumps({"error": "Automation not found"})
            if automation.user_id != user_id:
                return json.dumps({"error": "Access denied"})

            # Merge provided fields with existing values
            new_name = name if name is not None else automation.name
            new_prompt = (
                prompt if prompt is not None else automation.data.get("prompt", "")
            )
            new_model_id = (
                model_id
                if model_id is not None
                else automation.data.get("model_id", "")
            )
            new_rrule = rrule if rrule is not None else automation.data.get("rrule", "")

            # Validate RRULE if changed
            if rrule is not None:
                try:
                    validate_rrule(new_rrule, tz=user.timezone if user else None)
                except ValueError as e:
                    return json.dumps({"error": f"Invalid schedule: {e}"})

            tz = user.timezone if user else None
            form = AutomationForm(
                name=new_name,
                data=AutomationData(
                    prompt=new_prompt,
                    model_id=new_model_id,
                    rrule=new_rrule,
                ),
                is_active=automation.is_active,
            )

            updated = await Automations.update_by_id(
                automation_id, form, next_run_ns(new_rrule, tz=tz)
            )

            return json.dumps(
                {
                    "status": "success",
                    "id": updated.id,
                    "name": updated.name,
                    "model_id": new_model_id,
                    "is_active": updated.is_active,
                    "next_runs": next_n_runs_ns(new_rrule, tz=tz),
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"update_automation error: {e}")
            return json.dumps({"error": str(e)})

    async def toggle_automation(
        self,
        automation_id: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Pause or resume a scheduled automation. If active, it will be paused. If paused, it will be resumed.

        :param automation_id: The ID of the automation to toggle
        :return: JSON with the updated automation status
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.automations import Automations
            from open_webui.models.users import Users
            from open_webui.utils.automations import next_run_ns

            user_id = __user__.get("id")
            user = await Users.get_user_by_id(user_id)

            automation = await Automations.get_by_id(automation_id)
            if not automation:
                return json.dumps({"error": "Automation not found"})
            if automation.user_id != user_id:
                return json.dumps({"error": "Access denied"})

            rrule = automation.data.get("rrule", "")
            toggled = await Automations.toggle(
                automation_id,
                next_run_ns(rrule, tz=user.timezone if user else None),
            )

            return json.dumps(
                {
                    "status": "success",
                    "id": toggled.id,
                    "name": toggled.name,
                    "is_active": toggled.is_active,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"toggle_automation error: {e}")
            return json.dumps({"error": str(e)})

    async def delete_automation(
        self,
        automation_id: str,
        __request__: Request = None,
        __user__: dict = None,
    ) -> str:
        """
        Delete a scheduled automation and all its run history.

        :param automation_id: The ID of the automation to delete
        :return: JSON confirming the automation was deleted
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.automations import Automations, AutomationRuns

            user_id = __user__.get("id")

            automation = await Automations.get_by_id(automation_id)
            if not automation:
                return json.dumps({"error": "Automation not found"})
            if automation.user_id != user_id:
                return json.dumps({"error": "Access denied"})

            name = automation.name
            await AutomationRuns.delete_by_automation(automation_id)
            await Automations.delete(automation_id)

            return json.dumps(
                {
                    "status": "success",
                    "message": f'Automation "{name}" deleted',
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"delete_automation error: {e}")
            return json.dumps({"error": str(e)})
