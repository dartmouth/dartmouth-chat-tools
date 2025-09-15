"""
title: Inject User ID
author: Simon Stone
version: 0.1
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    def __init__(self):
        pass

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:

        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{__user__}")

        body["user"] = __user__["id"]

        return body
