import json
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_outreach_executor_manual_export(tmp_path):
    from agents.outreach_executor.agent import OutreachExecutorAgent

    agent = OutreachExecutorAgent()
    with patch("agents.outreach_executor.agent.settings.outreach_exports_path", tmp_path):
        result = await agent.execute(
            {
                "action": "manual_export",
                "send_intent_id": "intent-1",
                "draft": {"body": "Hello"},
            }
        )

    assert result.success is True
    send_result = result.data["send_result"]
    assert send_result["status"] == "MANUAL"
    assert Path(send_result["artifact_path"]).exists()


@pytest.mark.asyncio
async def test_outreach_executor_email_uses_smtp_when_configured():
    from agents.outreach_executor.agent import OutreachExecutorAgent

    sent_messages = []

    class StubSMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            self.username = username
            self.password = password

        def send_message(self, message):
            sent_messages.append(message)

    agent = OutreachExecutorAgent()
    with patch("agents.outreach_executor.agent.settings.smtp_host", "smtp.example.com"):
        with patch("agents.outreach_executor.agent.settings.smtp_port", 587):
            with patch("agents.outreach_executor.agent.settings.smtp_username", "user"):
                with patch("agents.outreach_executor.agent.settings.smtp_password", "pass"):
                    with patch("agents.outreach_executor.agent.settings.smtp_from_email", "ops@example.com"):
                        with patch("agents.outreach_executor.agent.smtplib.SMTP", StubSMTP):
                            result = await agent.execute(
                                {
                                    "action": "send_email",
                                    "draft": {"subject": "Hello", "body": "Approved copy"},
                                    "draft_metadata": {"email": "lead@example.com"},
                                    "send_intent_id": "intent-2",
                                }
                            )

    assert result.success is True
    assert result.data["send_result"]["status"] == "SENT"
    assert len(sent_messages) == 1


@pytest.mark.asyncio
async def test_outreach_executor_linkedin_dm_exports_conservative_artifact(tmp_path):
    from agents.outreach_executor.agent import OutreachExecutorAgent

    agent = OutreachExecutorAgent()
    with patch("agents.outreach_executor.agent.settings.outreach_exports_path", tmp_path):
        result = await agent.execute(
            {
                "action": "linkedin_dm",
                "send_intent_id": "intent-3",
                "source_url": "https://linkedin.com/in/jane",
                "draft": {"body": "Hello on LinkedIn"},
            }
        )

    assert result.success is True
    payload = json.loads(Path(result.data["send_result"]["artifact_path"]).read_text(encoding="utf-8"))
    assert payload["channel"] == "LINKEDIN_DM"


@pytest.mark.asyncio
async def test_outreach_executor_preserves_followup_metadata(tmp_path):
    from agents.outreach_executor.agent import OutreachExecutorAgent

    agent = OutreachExecutorAgent()
    with patch("agents.outreach_executor.agent.settings.outreach_exports_path", tmp_path):
        result = await agent.execute(
            {
                "action": "manual_export",
                "send_intent_id": "intent-4",
                "is_followup": True,
                "followup_plan_id": "plan-1",
                "followup_step": 2,
                "draft": {"body": "Following up"},
            }
        )

    payload = json.loads(Path(result.data["send_result"]["artifact_path"]).read_text(encoding="utf-8"))
    assert payload["is_followup"] is True
    assert payload["followup_plan_id"] == "plan-1"
    assert payload["followup_step"] == 2
