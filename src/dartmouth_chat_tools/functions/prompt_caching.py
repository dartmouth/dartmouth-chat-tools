"""
title: Prompt Caching
author: Simon Stone
version: 0.11.3
description: >
  Adds `cache_control: {type: ephemeral}` to the payload,
  enabling prompt caching.
"""

from pydantic import BaseModel


class Filter:
    class Valves(BaseModel):
        enabled: bool = True
        model_id_pattern: str = (
            "anthropic"  # only apply to models whose ID contains this
        )

    def __init__(self):
        self.valves = self.Valves()

    def inlet(self, body: dict, __metadata__: dict):
        if not self.valves.enabled:
            return body

        model_id = __metadata__.get("model", {}).get("info", {}).get(
            "base_model_id"
        ) or body.get("model")

        if self.valves.model_id_pattern.lower() not in model_id.lower():
            return body

        body["cache_control"] = {"type": "ephemeral"}
        return body
