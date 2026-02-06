"""
title: Inject User ID
author: Simon Stone
version: 0.4
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:

    class Valves(BaseModel):
        team_prefixes: list[str] = Field(
            default=[], description="Prefixes for all connected Team keys."
        )
        bypass_models: list[str] = Field(
            default=[],
            description="Models that should bypass user ID injection for other reasons (e.g., Responses API pipe).",
        )

    def __init__(self):
        self.valves = self.Valves()

    def inlet(self, body: dict, __user__: dict, __metadata__: dict) -> dict:
        model = (
            __metadata__.get("model", {}).get("info", {}).get("base_model_id")
            or body["model"]
        )
        if model in self.valves.bypass_models or any(
            model.startswith(prefix + ".") for prefix in self.valves.team_prefixes
        ):
            return body

        body["user"] = __user__["id"]

        return body
