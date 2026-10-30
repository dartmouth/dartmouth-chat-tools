"""
title: DISC Risk Gate
author: Simon Stone
version: 0.11.4
description: Classify the DISC level of the contents of outgoing messages and warn about potential disclosure of sensitive data.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Questions asked of the classifier for every message, and how each answer
# maps to a finding. Wording and thresholds come from the prototype in #16.
THRESHOLD = 0.5
DISC_LEVEL_THRESHOLD = 2.5


def _noul(instructions: str, false: Optional[str] = None) -> dict:
    question: dict = {"type": "noul", "instructions": instructions}
    if false:
        question["criteria"] = {"true": "Yes", "false": false}
    return question


QUESTIONS = {
    "government_id": _noul(
        "Does the content contain a government-issued ID number, such as a "
        "Social Security number, passport number or driver's license number?"
    ),
    "personal_details": _noul(
        "Does the content contain personal details about an identifiable person "
        "beyond directory information, such as a birth date, home address or "
        "personal phone number?",
        false="Only names, work email, NetID, job title, or no personal data.",
    ),
    "ferpa": _noul(
        "Does the content contain education records about an identifiable "
        "student, such as grades, enrollment or academic standing?"
    ),
    "hipaa": _noul(
        "Does the content contain health information about an identifiable "
        "person, such as a diagnosis, treatment or medication?"
    ),
    "pci": _noul(
        "Does the content contain payment card data, such as a card number, "
        "expiry date or CVV?"
    ),
    "glba": _noul(
        "Does the content contain non-public personal financial information, "
        "such as a bank account, loan, tax or financial aid details?"
    ),
    "cui": _noul("Does the content contain Controlled Unclassified Information?"),
    "disc_level": {
        "type": "score",
        "instructions": (
            "Rate the content on the Dartmouth Information Security "
            "Classification (DISC)."
        ),
        "criteria": [
            "DISC 0 (Public): information anyone may see.",
            "DISC 1 (Internal Use Only): ordinary Dartmouth business "
            "information, including directory information (name, Dartmouth "
            "email, NetID, title).",
            "DISC 2 (Confidential): information whose disclosure would harm "
            "Dartmouth or individuals, but which is not highly confidential.",
            "DISC 3 (Highly Confidential): regulated data (FERPA, HIPAA, PCI, "
            "GLBA, CUI) or PII (personal data beyond directory information).",
        ],
    },
}

# (answer key, finding label, regulated)
CATEGORIES = [
    ("ferpa", "FERPA student record", True),
    ("hipaa", "Health information (HIPAA)", True),
    ("pci", "Payment card data (PCI)", True),
    ("glba", "Financial information (GLBA)", True),
    ("cui", "Controlled Unclassified Information", True),
    ("government_id", "Government ID (e.g. SSN)", False),
    ("personal_details", "PII (e.g. birth date, home address)", False),
]
OTHER_DISC3 = "Other highly confidential data"

COULDNT_CHECK = (
    "The DISC Risk Gate couldn't check this request for highly confidential "
    "data, so it was sent unchecked."
)
TOO_LONG_MESSAGE = (
    "Some messages in this conversation are too long to be checked for "
    "highly confidential data, so nothing was sent to the model. To continue, "
    "switch off the DISC Risk Gate for this chat."
)

# Bump when QUESTIONS or the thresholds change, so cached verdicts are dropped.
QUESTIONS_VERSION = "1"
MAX_PARALLEL_CALLS = 8
CACHE_SIZE = 1024

# Builtin tools whose results are the content of a file attached to the chat.
ATTACHMENT_TOOLS = {"view_attachment", "view_file"}


@dataclass(frozen=True)
class Finding:
    """A category of DISC 3 data found in one message. Never holds the value."""

    label: str
    regulated: bool
    location: str
    disc_level: int = 3


class ClassifierUnavailable(Exception):
    """The classifier couldn't be reached or gave an unusable answer."""


class MessageTooLong(Exception):
    """A message doesn't fit in the classifier's input, so it can't be checked."""


# The classifier's answers for one message: {question key: probability or score}.
Verdict = dict[str, float]
# Cached in place of a verdict for a message that is too long to check.
TOO_LONG = None


class Filter:
    class Valves(BaseModel):
        classifier_model: str = Field(
            default="cloudflare.clef",
            description="System One model used to classify messages.",
        )
        classifier_timeout: float = Field(
            default=10.0,
            description="Seconds to wait for the classifier to check a whole "
            "request before letting it through unchecked. 10 s is about 3x the "
            "slowest call measured on preprod (#16).",
        )
        classifier_max_input_tokens: int = Field(
            default=16384,
            description="The classifier's input limit (Clef's --max-model-len). "
            "Messages that don't fit block the request.",
        )

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.valves = self.Valves()
        self.toggle = True
        # Lucide "shield-question-mark": it asks, it doesn't guarantee protection.
        self.icon = """data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwYXRoIGQ9Ik0yMCAxM2MwIDUtMy41IDcuNS03LjY2IDguOTVhMSAxIDAgMCAxLS42Ny0uMDFDNy41IDIwLjUgNCAxOCA0IDEzVjZhMSAxIDAgMCAxIDEtMWMyIDAgNC41LTEuMiA2LjI0LTIuNzJhMS4xNyAxLjE3IDAgMCAxIDEuNTIgMEMxNC41MSAzLjgxIDE3IDUgMTkgNWExIDEgMCAwIDEgMSAxeiIvPjxwYXRoIGQ9Ik05LjEgOWEzIDMgMCAwIDEgNS44MiAxYzAgMi0zIDMtMyAzIi8+PHBhdGggZD0iTTEyIDE3aC4wMSIvPjwvc3ZnPg=="""
        # Tests inject an in-memory transport; Open WebUI uses the default.
        self._transport = transport
        # Verdicts by content hash, so each pass through the tool loop only
        # classifies new messages. Decisions are never cached.
        self._verdicts: OrderedDict[str, Optional[Verdict]] = OrderedDict()

    async def request(
        self,
        body: dict,
        __model__: Optional[dict] = None,
        __request__=None,
        __event_emitter__=None,
        __event_call__=None,
    ) -> dict:
        # Automations and API calls have nobody to ask, so they pass unchecked.
        if __event_call__ is None:
            return body

        messages = body.get("messages", [])
        tool_names = _tool_names(messages)
        checked = [
            (message, text)
            for message in messages
            if (text := _text(message.get("content"))).strip()
        ]

        if any(self._known_too_long(text) for _, text in checked):
            raise Exception(TOO_LONG_MESSAGE)

        try:
            verdicts = await asyncio.wait_for(
                self._classify_all([text for _, text in checked]),
                timeout=self.valves.classifier_timeout,
            )
        except MessageTooLong:
            # Unlike an unavailable classifier, this blocks: we know we can't check it.
            raise Exception(TOO_LONG_MESSAGE) from None
        except (ClassifierUnavailable, asyncio.TimeoutError) as e:
            if isinstance(e, asyncio.TimeoutError):
                log.warning("DISC Risk Gate: classifier timed out")
            await _notify(__event_emitter__, COULDNT_CHECK)
            return body

        findings: list[Finding] = []
        for (message, text), verdict in zip(checked, verdicts):
            findings.extend(_findings(verdict, _location(message, text, tool_names)))

        local = _is_local(__model__, __request__)
        regulated = _unique(f for f in findings if f.regulated)
        disc3 = [] if local else _unique(f for f in findings if not f.regulated)
        if not regulated and not disc3:
            return body

        confirmed = await __event_call__(
            {
                "type": "confirmation",
                "data": {
                    "title": "This may contain highly confidential data",
                    "message": _dialog(regulated, disc3, local),
                },
            }
        )
        # Closing the dialog, a disconnect or a timeout all count as cancel.
        if confirmed is not True:
            raise Exception(_cancelled(regulated, disc3))
        return body

    async def _classify_all(self, texts: list[str]) -> list[Verdict]:
        base_url = os.environ.get("LITELLM_PROXY_BASE_URL")
        api_key = os.environ.get("LITELLM_PROXY_API_KEY")
        if not base_url or not api_key:
            log.warning("DISC Risk Gate: LiteLLM proxy is not configured")
            raise ClassifierUnavailable()

        semaphore = asyncio.Semaphore(MAX_PARALLEL_CALLS)
        async with httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=self.valves.classifier_timeout,
            transport=self._transport,
        ) as client:

            async def classify(text: str) -> Verdict:
                async with semaphore:
                    return await self._classify(client, text)

            results = await asyncio.gather(
                *(classify(text) for text in texts), return_exceptions=True
            )

        # A message that is too long blocks the request even if others failed.
        if any(isinstance(r, MessageTooLong) for r in results):
            raise MessageTooLong()
        verdicts = []
        for r in results:
            if isinstance(r, BaseException):
                raise ClassifierUnavailable() from r
            verdicts.append(r)
        return verdicts

    def _cache_key(self, text: str) -> str:
        return hashlib.sha256(
            f"{QUESTIONS_VERSION}|{self.valves.classifier_model}|"
            f"{self.valves.classifier_max_input_tokens}|{text}".encode()
        ).hexdigest()

    def _known_too_long(self, text: str) -> bool:
        """Whether we already know, without calling the classifier, that it can't check this."""
        # Don't upload megabytes the classifier would cut short anyway.
        if len(text) > 8 * self.valves.classifier_max_input_tokens:
            return True
        key = self._cache_key(text)
        return key in self._verdicts and self._verdicts[key] is TOO_LONG

    async def _classify(self, client: httpx.AsyncClient, text: str) -> Verdict:
        key = self._cache_key(text)
        if key in self._verdicts:
            self._verdicts.move_to_end(key)
            verdict = self._verdicts[key]
        else:
            verdict = await self._call_classifier(client, text)

        self._verdicts[key] = verdict
        if len(self._verdicts) > CACHE_SIZE:
            self._verdicts.popitem(last=False)
        if verdict is TOO_LONG:
            raise MessageTooLong()
        return verdict

    async def _call_classifier(
        self, client: httpx.AsyncClient, text: str
    ) -> Optional[Verdict]:
        started = time.monotonic()
        try:
            response = await client.post(
                "/v1/systemone",
                json={
                    "model": self.valves.classifier_model,
                    "state": text,
                    "questions": QUESTIONS,
                },
            )
        except httpx.HTTPError as e:
            log.warning("DISC Risk Gate: classifier unreachable (%s)", type(e).__name__)
            raise ClassifierUnavailable() from None

        latency = time.monotonic() - started
        try:
            result = response.json()
        except ValueError:
            result = None

        if response.status_code != 200:
            # Error bodies can echo the request content: log only the error type.
            error = result.get("error") if isinstance(result, dict) else None
            error_type = error.get("type") if isinstance(error, dict) else None
            log.warning(
                "DISC Risk Gate: classifier returned %s (%s) after %.2fs",
                response.status_code,
                error_type,
                latency,
            )
            raise ClassifierUnavailable()

        try:
            answers = result["answers"]
            verdict = {key: float(answers[key]["noul"]) for key, _, _ in CATEGORIES}
            verdict["disc_level"] = float(answers["disc_level"]["score"])
            input_tokens = int(result["usage"]["input_tokens"])
        except (TypeError, KeyError, ValueError):
            log.warning(
                "DISC Risk Gate: unusable classifier response after %.2fs", latency
            )
            raise ClassifierUnavailable() from None

        # Clef silently cuts longer input down to exactly the limit.
        if input_tokens >= self.valves.classifier_max_input_tokens:
            return TOO_LONG
        return verdict


async def _notify(event_emitter, description: str) -> None:
    if event_emitter is not None:
        await event_emitter(
            {"type": "status", "data": {"description": description, "done": True}}
        )


def _text(content) -> str:
    """The text of a message's content, which may be a string or a list of parts."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    return ""


def _tool_names(messages: list[dict]) -> dict[str, str]:
    """Tool call ID → tool name, from the assistant messages that made the calls."""
    names = {}
    for message in messages:
        for call in message.get("tool_calls") or []:
            names[call.get("id")] = call.get("function", {}).get("name", "")
    return names


def _location(message: dict, text: str, tool_names: dict[str, str]) -> str:
    """Where a message's content came from, in words the user recognises."""
    role = message.get("role")
    if role == "tool":
        tool = message.get("name") or tool_names.get(
            message.get("tool_call_id") or "", ""
        )
        if tool in ATTACHMENT_TOOLS:
            filename = _attachment_filename(text)
            return f"attached file {filename}" if filename else "an attached file"
        return f"the result of tool {tool}" if tool else "a tool result"
    # RAG and web search results are added to a message inside <source> tags.
    if "<source" in text:
        if role == "user":
            return "your message or the retrieved context added to it"
        return "retrieved context"
    if role == "user":
        return "your message"
    if role == "assistant":
        return "an earlier reply"
    return "the system prompt"


def _attachment_filename(text: str) -> Optional[str]:
    try:
        result = json.loads(text)
    except ValueError:
        return None
    if not isinstance(result, dict):
        return None
    # File attachments carry `filename`; text and chat attachments carry `name`.
    return result.get("filename") or result.get("name")


def _findings(verdict: dict[str, float], location: str) -> list[Finding]:
    findings = [
        Finding(label, regulated, location)
        for key, label, regulated in CATEGORIES
        if verdict[key] >= THRESHOLD
    ]
    if not findings and verdict["disc_level"] >= DISC_LEVEL_THRESHOLD:
        findings.append(Finding(OTHER_DISC3, False, location))
    return findings


def _unique(findings) -> list[Finding]:
    return list(dict.fromkeys(findings))


def _is_local(model: Optional[dict], request) -> bool:
    """Whether the model is tagged `local`. Anything else counts as cloud.

    A workspace model doesn't inherit its base model's tags, and its own tags
    are user-editable, so we use the tags of the base model it runs on.
    """
    model = model or {}
    base_model_id = (model.get("info") or {}).get("base_model_id")
    if base_model_id:
        registry = getattr(getattr(request, "app", None), "state", None)
        model = (getattr(registry, "MODELS", None) or {}).get(base_model_id) or {}
    return "local" in _tag_names(model)


def _tag_names(model: dict) -> set[str]:
    """The model's own tags merged with its meta tags, as the models endpoint does.

    Lowercased, because deployments tag models `Local` as well as `local`.
    """
    meta = (model.get("info") or {}).get("meta") or {}
    tags = (meta.get("tags") or []) + (model.get("tags") or [])
    names = (t.get("name") if isinstance(t, dict) else t for t in tags)
    return {n.strip().lower() for n in names if isinstance(n, str)}


def _dialog(regulated: list[Finding], disc3: list[Finding], local: bool) -> str:
    sections = []
    if regulated:
        advice = (
            "Contact Information Security before using this data with any AI model."
            if local
            else "Regulated data is not allowed on cloud models. Contact "
            "Information Security before using it with any AI model."
        )
        sections.append(_section("Regulated data", advice, regulated))
    if disc3:
        sections.append(
            _section(
                "Highly confidential data (DISC 3) on a cloud model",
                "This model is only approved for data up to DISC 2. Switch to a "
                "local model, or remove this data from the conversation.",
                disc3,
            )
        )
    sections.append("Do you want to send it anyway?")
    return "\n\n".join(sections)


def _cancelled(regulated: list[Finding], disc3: list[Finding]) -> str:
    advice = []
    if regulated:
        advice.append(
            "Contact Information Security before using regulated data with any "
            "AI model."
        )
    if disc3:
        advice.append(
            "Switch to a local model, or remove the highly confidential data "
            "from the conversation."
        )
    return (
        "Cancelled by the DISC Risk Gate. Nothing was sent to the model. "
        + " ".join(advice)
        + " If you've checked that this use is approved, switch off the DISC "
        "Risk Gate for this chat and send your message again."
    )


def _section(heading: str, advice: str, findings: list[Finding]) -> str:
    lines = [f"- {f.label} in {f.location}" for f in findings]
    return f"**{heading}**\n\n{advice}\n\n" + "\n".join(lines)
