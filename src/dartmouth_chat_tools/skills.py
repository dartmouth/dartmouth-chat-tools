from fastapi import Request

from open_webui.models.groups import Groups

import json
import logging
from typing import Optional


log = logging.getLogger(__name__)


class Tools:
    async def view_skill(
        self,
        name: str,
        __request__: Optional[Request] = None,
        __user__: Optional[dict] = None,
    ) -> str:
        """
        Load the full instructions of a skill by its name from the available skills manifest.
        Use this when you need detailed instructions for a skill listed in <available_skills>.

        :param name: The name of the skill to load (as shown in the manifest)
        :return: The full skill instructions as markdown content
        """
        if __request__ is None:
            return json.dumps({"error": "Request context not available"})

        if not __user__:
            return json.dumps({"error": "User context not available"})

        try:
            from open_webui.models.skills import Skills
            from open_webui.models.access_grants import AccessGrants

            user_id = __user__.get("id")

            # Direct DB lookup by unique name
            skill = Skills.get_skill_by_name(name)

            if not skill or not skill.is_active:
                return json.dumps({"error": f"Skill '{name}' not found"})

            # Check user access
            user_role = __user__.get("role", "user")
            if user_role != "admin" and skill.user_id != user_id:
                user_group_ids = [
                    group.id for group in Groups.get_groups_by_member_id(user_id)
                ]
                if not AccessGrants.has_access(
                    user_id=user_id,
                    resource_type="skill",
                    resource_id=skill.id,
                    permission="read",
                    user_group_ids=set(user_group_ids),
                ):
                    return json.dumps({"error": "Access denied"})

            return json.dumps(
                {
                    "name": skill.name,
                    "content": skill.content,
                },
                ensure_ascii=False,
            )
        except Exception as e:
            log.exception(f"view_skill error: {e}")
            return json.dumps({"error": str(e)})
