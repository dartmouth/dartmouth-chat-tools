"""
title: Send Email
version: 0.10.2
"""

import base64
import html
import json
import logging
import mimetypes
import os
from typing import Literal

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Microsoft endpoints
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_SEND_MAIL_URL = (
    "https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
)

# Microsoft Graph caps a single sendMail request at ~4 MB. Base64 inflates
# bytes by ~33%, and the message also carries the body and headers, so we keep
# a conservative budget for the combined *encoded* attachment payload.
_MAX_TOTAL_ATTACHMENT_BYTES = 4 * 1024 * 1024  # 4 MB of base64 text

# Placeholder the AI uses to reference Dartmouth Chat resources by relative path.
_BASE_URL_PLACEHOLDER = "{dartmouth_chat_url}"


def _resolve_base_url() -> str:
    """Return the configured Dartmouth Chat base URL without a trailing slash.

    The live value is held in Open WebUI's ``WEBUI_URL`` config var. We coerce
    it to ``str`` so it works whether it resolves to a plain string or a
    config wrapper.
    """
    try:
        from open_webui.config import WEBUI_URL

        return str(WEBUI_URL).rstrip("/")
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Could not resolve Dartmouth Chat base URL: %s", exc)
        return ""


def _expand_links(body: str) -> str:
    """Replace ``{dartmouth_chat_url}`` placeholders with the base URL.

    The AI specifies links using relative paths prefixed by the placeholder,
    e.g. ``{dartmouth_chat_url}/api/v1/files/<id>/content``. This expands the
    placeholder to the configured base URL, normalising the joining slash.

    Because the placeholder already stands in for a full URL (including the
    scheme), the AI sometimes mistakenly prefixes it with ``http://`` or
    ``https://``. We strip any such redundant scheme before expanding so the
    resulting link is well formed.
    """
    if _BASE_URL_PLACEHOLDER not in body:
        return body

    base_url = _resolve_base_url()

    # Strip a redundant scheme the AI may have added in front of the
    # placeholder (e.g. "https://{dartmouth_chat_url}").
    for scheme in ("https://", "http://"):
        body = body.replace(
            f"{scheme}{_BASE_URL_PLACEHOLDER}", _BASE_URL_PLACEHOLDER
        )

    # Collapse "<base>/" + "/path" or "<base>" + "path" into a single slash.
    body = body.replace(f"{_BASE_URL_PLACEHOLDER}/", f"{base_url}/")
    body = body.replace(_BASE_URL_PLACEHOLDER, base_url)
    return body


def _text_to_html(body: str) -> str:
    """Convert a plain-text body into HTML.

    Escapes HTML-special characters and preserves line breaks so the text
    reads the same once promoted to an HTML email. Used when inline images
    force a text body to be sent as HTML (``cid:`` references only render in
    HTML messages).
    """
    return html.escape(body).replace("\n", "<br>")


def _guess_content_type(filename: str, declared: str | None) -> str:
    """Best-effort MIME type for an attachment."""
    if declared:
        return declared
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def _read_file_bytes(file_path: str | None) -> bytes:
    """Read raw bytes for a stored file via the Open WebUI storage provider.

    ``Storage.get_file`` returns a local filesystem path for every backend
    (local returns directly; S3/GCS/Azure download to a temp file first), so we
    can read uniformly.
    """
    if not file_path:
        raise FileNotFoundError("File has no storage path")

    from open_webui.storage.provider import Storage

    local_path = Storage.get_file(file_path)
    with open(local_path, "rb") as fh:
        return fh.read()


async def _build_attachments(
    file_ids: list[str], user_id: str, body: str, body_type: str
) -> tuple[list[dict], str, str, list[dict]]:
    """Resolve file IDs into Graph attachments.

    Returns ``(attachments, body, body_type, skipped)`` where:
      - ``attachments`` is the Graph ``attachments`` array. Image files are
        marked inline (``isInline`` + ``contentId``) and a ``cid:`` reference is
        appended to the HTML body; other files become regular attachments.
      - ``body`` is the (possibly augmented) email body.
      - ``body_type`` is the (possibly promoted) body type. Inline images use
        ``cid:`` references which only render in HTML messages, so if any inline
        image is added to a plain-text body we promote it to ``"html"`` (escaping
        the original text and preserving line breaks).
      - ``skipped`` is a list of ``{"id", "reason"}`` for files that could not be
        attached (not found, unreadable, or over the size budget). The caller can
        surface these and/or fall back to a link.

    Only files owned by ``user_id`` are eligible, preventing exfiltration of
    other users' files.
    """
    from open_webui.models.files import Files

    attachments: list[dict] = []
    skipped: list[dict] = []
    inline_html_parts: list[str] = []
    encoded_budget = 0

    for file_id in file_ids:
        try:
            file = await Files.get_file_by_id_and_user_id(file_id, user_id)
        except Exception as exc:  # pragma: no cover - defensive
            log.exception("Failed to load file %s: %s", file_id, exc)
            file = None

        if not file:
            skipped.append(
                {"id": file_id, "reason": "not found or not owned by you"}
            )
            continue

        try:
            raw = _read_file_bytes(file.path)
        except Exception as exc:
            log.exception("Failed to read file %s: %s", file_id, exc)
            skipped.append({"id": file_id, "reason": f"unreadable: {exc}"})
            continue

        encoded = base64.b64encode(raw).decode("ascii")
        if encoded_budget + len(encoded) > _MAX_TOTAL_ATTACHMENT_BYTES:
            skipped.append(
                {"id": file_id, "reason": "too large to attach"}
            )
            continue
        encoded_budget += len(encoded)

        meta = file.meta or {}
        content_type = _guess_content_type(
            file.filename, meta.get("content_type")
        )

        attachment = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": file.filename,
            "contentType": content_type,
            "contentBytes": encoded,
        }

        if content_type.startswith("image/"):
            # Embed inline so it renders within the message body.
            content_id = f"att-{file_id}"
            attachment["isInline"] = True
            attachment["contentId"] = content_id
            inline_html_parts.append(
                f'<div style="margin-top:12px;">'
                f'<img src="cid:{content_id}" '
                f'alt="{file.filename}" '
                f'style="max-width:100%;height:auto;"></div>'
            )

        attachments.append(attachment)

    if inline_html_parts:
        # cid: references only render in HTML. If the body is plain text,
        # promote it to HTML (escaping and preserving line breaks) before
        # appending the inline image markup.
        if body_type != "html":
            body = _text_to_html(body)
            body_type = "html"
        body = f"{body}{''.join(inline_html_parts)}"

    return attachments, body, body_type, skipped


async def _acquire_token(
    tenant_id: str, client_id: str, client_secret: str
) -> str:
    """Fetch an OAuth2 access token using the client-credentials flow."""
    url = _TOKEN_URL.format(tenant_id=tenant_id)
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, data=data)
        resp.raise_for_status()
        return resp.json()["access_token"]


def _build_footer(user_name: str, body_type: str) -> str:
    """Return a disclaimer footer appropriate for the body type."""
    disclaimer = (
        f"This email was sent by Dartmouth Chat on behalf of {user_name}."
    )
    if body_type == "html":
        return (
            '<p style="color:#707070;font-size:12px;margin-top:24px;">'
            f"{disclaimer}</p>"
        )
    return f"\n\n---\n{disclaimer}"


def _build_payload(
    subject: str,
    body: str,
    body_type: str,
    to_email: str,
    to_name: str,
    sender_email: str,
    attachments: list[dict] | None = None,
) -> dict:
    """Construct the Microsoft Graph sendMail JSON payload."""
    content_type = "HTML" if body_type == "html" else "Text"
    message: dict = {
        "subject": subject,
        "body": {
            "contentType": content_type,
            "content": body,
        },
        "from": {
            "emailAddress": {
                "address": sender_email,
            }
        },
        "toRecipients": [
            {
                "emailAddress": {
                    "address": to_email,
                    "name": to_name,
                }
            }
        ],
    }
    if attachments:
        message["attachments"] = attachments
    return {
        "message": message,
        "saveToSentItems": True,
    }


class Tools:
    class Valves(BaseModel):
        tenant_id: str = Field(
            default="",
            description="Azure AD tenant ID for the app registration.",
        )
        client_id: str = Field(
            default="",
            description="Azure AD application (client) ID.",
        )
        client_secret: str = Field(
            default="",
            description="Azure AD client secret value.",
        )
        sender_email: str = Field(
            default="dartmouth.chat@dartmouth.edu",
            description="Email address to send from (must match the service account).",
        )
        subject_prefix: str = Field(
            default="[Dartmouth Chat] ",
            description="Prefix added to all outgoing email subjects.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def send_email(
        self,
        subject: str,
        body: str,
        body_type: Literal["text", "html"] = "text",
        attachment_file_ids: list[str] = None,
        __user__: dict = None,
    ) -> str:
        """Send an email to the current user.

        The email is sent from the Dartmouth Chat service account to the
        logged-in user's email address. A disclaimer footer is appended
        automatically.

        ATTACHING DARTMOUTH CHAT FILES:
        To attach a file the user has in Dartmouth Chat, pass its file ID in
        ``attachment_file_ids`` (the ``<id>`` from an ``api/v1/files/<id>/...``
        path). Image files are embedded inline in the email body; other files
        are attached normally. Only files owned by the current user can be
        attached. Files that are too large (the email has a ~4 MB total limit)
        are skipped; for those, fall back to a link using the token below.
        Prefer ``body_type="html"`` when attaching images so they render inline.

        LINKING TO DARTMOUTH CHAT RESOURCES (IMPORTANT):
        You only know the relative path of a Dartmouth Chat resource (such as
        a file), like ``api/v1/files/<id>/content``. You do NOT know the site's
        full domain. To create a working link, you MUST write the literal token
        ``{dartmouth_chat_url}`` followed by the relative path. The tool
        replaces that token with the correct base URL automatically.

        Follow these rules exactly:
        - ALWAYS prefix every Dartmouth Chat resource link with the literal
          token ``{dartmouth_chat_url}``. Never omit it and never write a bare
          relative path.
        - NEVER add ``http://`` or ``https://`` before the token. The token
          already expands to a full URL including the scheme.
        - Do NOT guess, invent, or hardcode a domain such as
          ``https://chat.dartmouth.edu``.

        Correct examples:
            Plain text:
              Download it here: {dartmouth_chat_url}/api/v1/files/<id>/content
            HTML:
              <a href="{dartmouth_chat_url}/api/v1/files/<id>/content">file</a>

        Incorrect (do NOT do this):
            api/v1/files/<id>/content                       (missing token)
            https://{dartmouth_chat_url}/api/v1/files/...    (redundant scheme)
            https://chat.dartmouth.edu/api/v1/files/...      (hardcoded domain)

        :param subject: Email subject line (a prefix will be added automatically).
        :param body: Email body content. Use the ``{dartmouth_chat_url}`` token
            (see above) for any link to a Dartmouth Chat resource.
        :param body_type: Body format — "text" for plain text, "html" for HTML.
        :param attachment_file_ids: Optional list of Dartmouth Chat file IDs to
            attach. Images are embedded inline; other files are attached.
        :return: JSON confirming the send or describing an error.
        """

        # --- validate context -------------------------------------------------
        if not __user__:
            return json.dumps({"error": "User context not available"})

        user_id = __user__.get("id")
        if not user_id:
            return json.dumps({"error": "User ID not available"})

        # --- validate valve configuration -------------------------------------
        if not all(
            [
                self.valves.tenant_id,
                self.valves.client_id,
                self.valves.client_secret,
            ]
        ):
            return json.dumps(
                {
                    "error": (
                        "Email sending is not configured. "
                        "An administrator must set the tenant_id, client_id, "
                        "and client_secret Valves."
                    )
                }
            )

        # --- resolve recipient ------------------------------------------------
        try:
            from open_webui.models.users import Users

            user = await Users.get_user_by_id(user_id)
            if not user:
                return json.dumps({"error": "User not found"})

            to_email = user.email
            to_name = user.name or ""
            if not to_email:
                return json.dumps(
                    {"error": "No email address on your profile."}
                )
        except Exception as exc:
            log.exception("Failed to resolve user email: %s", exc)
            return json.dumps(
                {"error": f"Failed to resolve user email: {exc}"}
            )

        # --- build the message ------------------------------------------------
        full_subject = f"{self.valves.subject_prefix}{subject}"
        body = _expand_links(body)

        # --- resolve attachments ----------------------------------------------
        attachments: list[dict] = []
        skipped: list[dict] = []
        if attachment_file_ids:
            try:
                attachments, body, body_type, skipped = (
                    await _build_attachments(
                        attachment_file_ids, user_id, body, body_type
                    )
                )
            except Exception as exc:
                log.exception("Failed to build attachments: %s", exc)
                # Don't fail the whole send; report and continue without them.
                skipped = [
                    {"id": fid, "reason": f"error: {exc}"}
                    for fid in attachment_file_ids
                ]

        footer = _build_footer(to_name or to_email, body_type)
        full_body = f"{body}{footer}"

        payload = _build_payload(
            subject=full_subject,
            body=full_body,
            body_type=body_type,
            to_email=to_email,
            to_name=to_name,
            sender_email=self.valves.sender_email,
            attachments=attachments,
        )

        # --- acquire token & send ---------------------------------------------
        try:
            token = await _acquire_token(
                tenant_id=self.valves.tenant_id,
                client_id=self.valves.client_id,
                client_secret=self.valves.client_secret,
            )
        except httpx.HTTPStatusError as exc:
            log.exception("Token acquisition failed: %s", exc)
            return json.dumps(
                {
                    "error": (
                        "Failed to authenticate with Azure AD. "
                        "Check the tenant_id, client_id, and client_secret Valves."
                    )
                }
            )
        except Exception as exc:
            log.exception("Token acquisition failed: %s", exc)
            return json.dumps(
                {"error": f"Token acquisition failed: {exc}"}
            )

        try:
            send_url = _SEND_MAIL_URL.format(
                sender_email=self.valves.sender_email
            )
            async with httpx.AsyncClient() as http:
                resp = await http.post(
                    send_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            detail = exc.response.text[:500]
            log.exception("Graph sendMail failed (%s): %s", status, detail)
            return json.dumps(
                {"error": f"Email send failed (HTTP {status}): {detail}"}
            )
        except Exception as exc:
            log.exception("Email send failed: %s", exc)
            return json.dumps({"error": f"Email send failed: {exc}"})

        log.info(
            "Email sent to %s with subject '%s'", to_email, full_subject
        )
        result = {
            "status": "sent",
            "to": to_email,
            "subject": full_subject,
            "attached_count": len(attachments),
        }
        if skipped:
            result["skipped_attachments"] = skipped
            result["note"] = (
                "Some files could not be attached. Consider including a "
                "{dartmouth_chat_url} link to them in the body."
            )
        return json.dumps(result)
