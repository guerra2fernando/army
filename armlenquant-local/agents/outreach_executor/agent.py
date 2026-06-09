"""
Conservative outreach executor for approved send intents.
"""
import asyncio
import json
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict

from agents.base_agent import AgentResult, BaseAgent
from models.capability import CapabilityGrant, CapabilityPolicy
from poller.config import get_settings
from poller.profile_loader import load_operator_profile


settings = get_settings()


class OutreachExecutorAgent(BaseAgent):
    """Execute approved outreach actions conservatively."""

    def __init__(self):
        super().__init__("OUTREACH_EXECUTOR", version="1.0.0")

    def get_capability_grants(self) -> list[CapabilityGrant]:
        return [
            CapabilityGrant(
                capability_id="file_write",
                policy_override=CapabilityPolicy(
                    allowed_paths=[str(settings.outreach_exports_path), str(settings.outreach_exports_path / "**")],
                    blocked_paths=[],
                    max_file_size_mb=25,
                ),
            ),
            CapabilityGrant(
                capability_id="browser_navigate",
                policy_override=CapabilityPolicy(allowed_domains=["*.linkedin.com"]),
            ),
        ]

    def get_capabilities(self) -> list:
        return [
            "send_email",
            "linkedin_connect",
            "linkedin_dm",
            "manual_export",
        ]

    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        action = payload.get("action", "manual_export")
        try:
            if action == "send_email":
                result = await self._send_email(payload)
            elif action == "linkedin_connect":
                result = await self._export_linkedin_action(payload, "linkedin_connect")
            elif action == "linkedin_dm":
                result = await self._export_linkedin_action(payload, "linkedin_dm")
            elif action == "manual_export":
                result = await self._manual_export(payload)
            else:
                return AgentResult(success=False, error=f"Unknown action: {action}")
            return AgentResult(success=True, data={"send_result": result})
        except Exception as exc:
            return AgentResult(success=False, error=str(exc))

    async def _send_email(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        draft = payload.get("draft", {})
        recipient = self._resolve_recipient(payload)
        if not recipient:
            return await self._manual_export(payload, channel="EMAIL", reason="No recipient email available")

        operator_profile = load_operator_profile()
        sender = settings.smtp_from_email or (operator_profile.email_identity if operator_profile else None)
        if not sender:
            return await self._manual_export(payload, channel="EMAIL", reason="No sender identity configured")

        if not settings.smtp_host or not settings.smtp_username or not settings.smtp_password:
            return await self._manual_export(payload, channel="EMAIL", reason="SMTP not configured")

        message = EmailMessage()
        message["Subject"] = draft.get("subject") or payload.get("title") or "Approved outreach"
        message["From"] = sender
        message["To"] = recipient
        message.set_content(draft.get("body", ""))

        await asyncio.to_thread(self._deliver_email, message)
        return {
            "status": "SENT",
            "channel": "EMAIL",
            "provider": "smtp",
            "detail": {
                "to": recipient,
                "from": sender,
                "is_followup": bool(payload.get("is_followup")),
                "followup_plan_id": payload.get("followup_plan_id"),
                "followup_step": payload.get("followup_step"),
            },
        }

    def _deliver_email(self, message: EmailMessage):
        if settings.smtp_use_tls:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(message)

    async def _export_linkedin_action(self, payload: Dict[str, Any], action: str) -> Dict[str, Any]:
        return await self._manual_export(
            payload,
            channel="LINKEDIN_CONNECT" if action == "linkedin_connect" else "LINKEDIN_DM",
            reason="Conservative LinkedIn executor exported the approved action for local execution.",
        )

    async def _manual_export(self, payload: Dict[str, Any], channel: str = "MANUAL", reason: str = "Manual export requested") -> Dict[str, Any]:
        send_intent_id = payload.get("send_intent_id", "unknown")
        target_dir = settings.outreach_exports_path / datetime.utcnow().strftime("%Y-%m-%d")
        artifact_path = target_dir / f"{send_intent_id}_{channel.lower()}.json"
        export_payload = {
            "exported_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "channel": channel,
            "send_intent_id": send_intent_id,
            "is_followup": bool(payload.get("is_followup")),
            "followup_plan_id": payload.get("followup_plan_id"),
            "followup_step": payload.get("followup_step"),
            "payload": payload,
        }
        await self.write_file_safe(str(artifact_path), json.dumps(export_payload, indent=2))
        return {
            "status": "MANUAL",
            "channel": channel,
            "provider": "local_export",
            "artifact_path": str(artifact_path),
            "detail": {
                "reason": reason,
                "is_followup": bool(payload.get("is_followup")),
                "followup_plan_id": payload.get("followup_plan_id"),
                "followup_step": payload.get("followup_step"),
            },
        }

    def _resolve_recipient(self, payload: Dict[str, Any]) -> str:
        metadata = payload.get("draft_metadata", {})
        return (
            payload.get("to_email")
            or metadata.get("email")
            or metadata.get("contact_email")
            or ""
        )
