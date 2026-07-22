"""
title: Ask User Question
description: Workspace Tool that lets an LLM present structured questions to the user (MCQ,
             multi-select, or rank). Questions render as native UI widgets in the chat; the
             user's answer becomes the next message. The UI always allows skip, cancel, and
             write-in answers — these do not need to be configured by the model.
             Supports single questions or multiple questions paged one at a time, collected
             into a single combined answer.
author: Dartmouth
author_url: https://dartmouth.edu
version: 0.10.2
license: MIT
"""

from pydantic import BaseModel
from typing import Optional

# Sentinel value that signals the middleware to short-circuit
# (skip the follow-up LLM call after tool execution).
QUESTION_PENDING_SENTINEL = "__QUESTION_PENDING__"


class Tools:
    class Valves(BaseModel):
        pass

    def __init__(self):
        self.valves = self.Valves()

    async def ask_user_question(
        self,
        question: str,
        options: list[str],
        type: Optional[str] = "mcq",
        rank_instruction: Optional[str] = "best first",
        __event_emitter__=None,
    ) -> str:
        """
        Present a single structured question to the user with clickable options.
        The current assistant response will end, and the user's selected answer
        will appear as the next user message in the conversation.

        The UI always allows the user to skip the question, cancel the questionnaire,
        or write in their own answer — there is no need to configure these.

        To present multiple questions in sequence, use ask_user_questions instead.

        :param question: The question to display to the user.
        :param options: A list of answer options for the user to choose from.
        :param type: Question type — "mcq" (single choice), "multi_select" (multiple choices), or "rank" (drag to reorder). Defaults to "mcq".
        :param rank_instruction: Short label shown next to "Drag to reorder" for rank questions (e.g. "most important first", "earliest to latest"). Defaults to "best first".
        :return: A sentinel value indicating the question was presented.
        """
        if not __event_emitter__:
            return "Error: event emitter not available."

        if not options or len(options) < 2:
            return "Error: at least two options are required."

        valid_types = ("mcq", "multi_select", "rank")
        if type not in valid_types:
            return f"Error: type must be one of {valid_types}, got '{type}'."

        await __event_emitter__(
            {
                "type": "chat:message:question",
                "data": {
                    "questions": [
                        {
                            "type": type,
                            "question": question,
                            "options": options,
                            "rank_instruction": rank_instruction,
                        }
                    ]
                },
            }
        )

        return QUESTION_PENDING_SENTINEL

    async def ask_user_questions(
        self,
        questions: list[dict],
        __event_emitter__=None,
    ) -> str:
        """
        Present multiple structured questions to the user in sequence, one at a time.
        The user pages through each question, can skip individual questions or cancel
        the entire batch. All answers are collected and submitted as a single combined
        user message when the final question is answered or skipped.

        Each question dict must contain:
          - question (str): The question text.
          - options (list[str]): Answer options, minimum 2.

        Each question dict may optionally contain:
          - type (str): "mcq" (default), "multi_select", or "rank".
          - rank_instruction (str): Label for rank questions. Defaults to "best first".

        The UI always allows skip, cancel, and write-in — no need to configure these.

        :param questions: List of question dicts.
        :return: A sentinel value indicating the questions were presented.
        """
        if not __event_emitter__:
            return "Error: event emitter not available."

        if not questions or len(questions) < 1:
            return "Error: at least one question is required."

        valid_types = ("mcq", "multi_select", "rank")
        normalized = []
        for i, q in enumerate(questions):
            if not isinstance(q, dict):
                return f"Error: question {i + 1} must be a dict."
            if not q.get("question"):
                return f"Error: question {i + 1} is missing 'question' text."
            if not q.get("options") or len(q["options"]) < 2:
                return f"Error: question {i + 1} must have at least two options."
            qtype = q.get("type", "mcq")
            if qtype not in valid_types:
                return f"Error: question {i + 1} has invalid type '{qtype}'. Must be one of {valid_types}."
            normalized.append(
                {
                    "type": qtype,
                    "question": q["question"],
                    "options": q["options"],
                    "rank_instruction": q.get("rank_instruction", "best first"),
                }
            )

        await __event_emitter__(
            {
                "type": "chat:message:question",
                "data": {
                    "questions": normalized,
                },
            }
        )

        return QUESTION_PENDING_SENTINEL
