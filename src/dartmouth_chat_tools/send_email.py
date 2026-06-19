"""
title: Send Email
version: 0.1.0
"""

import json
import logging
from typing import Literal

import httpx
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

# Microsoft endpoints
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_SEND_MAIL_URL = (
    "https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail"
)


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
) -> dict:
    """Construct the Microsoft Graph sendMail JSON payload."""
    content_type = "HTML" if body_type == "html" else "Text"
    return {
        "message": {
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
        },
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
        __user__: dict = None,
    ) -> str:
        """Send an email to the current user.

        The email is sent from the Dartmouth Chat service account to the
        logged-in user's email address. A disclaimer footer is appended
        automatically.

        :param subject: Email subject line (a prefix will be added automatically).
        :param body: Email body content.
        :param body_type: Body format — "text" for plain text, "html" for HTML.
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
        footer = _build_footer(to_name or to_email, body_type)
        full_body = f"{body}{footer}"

        payload = _build_payload(
            subject=full_subject,
            body=full_body,
            body_type=body_type,
            to_email=to_email,
            to_name=to_name,
            sender_email=self.valves.sender_email,
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
        return json.dumps(
            {
                "status": "sent",
                "to": to_email,
                "subject": full_subject,
            }
        )
