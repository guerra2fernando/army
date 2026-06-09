"""
Notification Service
Central service for managing notifications across all channels.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4

from loguru import logger
from telegram.constants import ParseMode

from app.config import get_settings
from app.db import Database
from app.notifications.models import (
    Notification,
    NotificationType,
    NotificationPriority,
    NotificationChannel,
    NotificationCreate,
    NotificationResponse
)
from app.notifications.telegram_bot import get_telegram_bot
from app.utils.data_contracts import contract_logger

settings = get_settings()


class NotificationService:
    """
    Central notification service.
    
    Handles:
    - Routing notifications to appropriate channels
    - Storing notification history
    - Checking user preferences
    - Rate limiting notifications
    """
    
    def __init__(self):
        self.logger = logger.bind(component="notifications")
        self.telegram = get_telegram_bot()
        self.enabled = settings.notifications_enabled
    
    async def send(
        self,
        notification: NotificationCreate,
        user_id: Optional[str] = None
    ) -> NotificationResponse:
        """
        Send a notification through appropriate channels.
        
        Args:
            notification: The notification to send
            user_id: Optional user ID for preferences lookup
            
        Returns:
            NotificationResponse with delivery status
        """
        if not self.enabled:
            return NotificationResponse(
                success=False,
                message="Notifications are disabled"
            )
        
        notification_id = str(uuid4())
        delivered_to: List[str] = []
        
        # Store in database
        await self._store_notification(notification_id, notification)
        
        # Check if we should send based on settings
        if not self._should_send(notification.type):
            return NotificationResponse(
                success=True,
                notification_id=notification_id,
                message="Notification stored but not sent (disabled by settings)",
                delivered_to=[]
            )
        
        # Send to appropriate channels
        if notification.channel in (NotificationChannel.TELEGRAM, NotificationChannel.ALL):
            if await self._send_telegram(notification):
                delivered_to.append("telegram")
        
        if notification.channel in (NotificationChannel.DASHBOARD, NotificationChannel.ALL):
            await self._send_dashboard(notification_id, notification)
            delivered_to.append("dashboard")
        
        # Update delivery status
        await self._update_delivery_status(notification_id, delivered_to)
        
        return NotificationResponse(
            success=len(delivered_to) > 0,
            notification_id=notification_id,
            message=f"Notification delivered to {', '.join(delivered_to)}" if delivered_to else "Failed to deliver",
            delivered_to=delivered_to
        )
    
    def _should_send(self, notification_type: NotificationType) -> bool:
        """Check if notification type should be sent based on settings."""
        type_to_setting = {
            NotificationType.TASK_COMPLETED: settings.notify_on_task_complete,
            NotificationType.TASK_FAILED: settings.notify_on_task_failed,
            NotificationType.AGENT_ALERT: settings.notify_on_agent_alert,
            NotificationType.SYSTEM_ERROR: settings.notify_on_system_error,
        }
        return type_to_setting.get(notification_type, True)
    
    async def _send_telegram(self, notification: NotificationCreate) -> bool:
        """Send notification via Telegram."""
        if not self.telegram.enabled:
            return False
        
        # Format message based on type
        message = self._format_telegram_message(notification)
        
        return await self.telegram.send_notification(
            message=message,
            silent=(notification.priority == NotificationPriority.LOW)
        )
    
    def _format_telegram_message(self, notification: NotificationCreate) -> str:
        """Format notification for Telegram."""
        type_emoji = {
            NotificationType.TASK_COMPLETED: "✅",
            NotificationType.TASK_FAILED: "❌",
            NotificationType.AGENT_ALERT: "⚠️",
            NotificationType.SYSTEM_ERROR: "🚨",
            NotificationType.DAILY_BRIEF: "📰",
            NotificationType.CRYPTO_SIGNAL: "📊",
            NotificationType.JOB_MATCH: "💼",
            NotificationType.CUSTOM: "💬"
        }
        
        priority_indicator = ""
        if notification.priority == NotificationPriority.URGENT:
            priority_indicator = "🔴 URGENT\n\n"
        elif notification.priority == NotificationPriority.HIGH:
            priority_indicator = "🟠 "
        
        emoji = type_emoji.get(notification.type, "📋")
        
        return f"{priority_indicator}{emoji} *{notification.title}*\n\n{notification.message}"
    
    async def _send_dashboard(
        self,
        notification_id: str,
        notification: NotificationCreate
    ):
        """Store notification for dashboard display via event stream."""
        action_url = notification.metadata.get("action_url") if notification.metadata else None
        action_label = notification.metadata.get("action_label") if notification.metadata else None

        await contract_logger.emit_event(
            event_type="NOTIFICATION",
            title=notification.title,
            description=notification.message,
            priority=notification.priority.value,
            action_required=False,
            action_url=action_url,
            action_label=action_label,
            payload={
                "notification_id": notification_id,
                "type": notification.type.value,
                "priority": notification.priority.value,
                "metadata": notification.metadata,
            },
            notify_email=False,
            notify_telegram=notification.channel in (NotificationChannel.TELEGRAM, NotificationChannel.ALL),
        )
    
    async def _store_notification(
        self,
        notification_id: str,
        notification: NotificationCreate
    ):
        """Store notification in database."""
        notifications = Database.get_collection("notifications")
        
        await notifications.insert_one({
            "_id": notification_id,
            "notification_id": notification_id,
            "type": notification.type.value,
            "title": notification.title,
            "message": notification.message,
            "priority": notification.priority.value,
            "channel": notification.channel.value,
            "metadata": notification.metadata,
            "created_at": datetime.utcnow(),
            "delivered": False,
            "delivered_to": [],
            "sent_at": None
        })
    
    async def _update_delivery_status(
        self,
        notification_id: str,
        delivered_to: List[str]
    ):
        """Update notification delivery status."""
        notifications = Database.get_collection("notifications")
        
        await notifications.update_one(
            {"notification_id": notification_id},
            {
                "$set": {
                    "delivered": len(delivered_to) > 0,
                    "delivered_to": delivered_to,
                    "sent_at": datetime.utcnow()
                }
            }
        )
    
    # ==========================================================================
    # CONVENIENCE METHODS
    # ==========================================================================
    
    async def notify_task_completed(
        self,
        task_id: str,
        agent: str,
        result_summary: Optional[str] = None,
        result_data: Optional[dict] = None,
        execution_time_ms: Optional[int] = None
    ) -> NotificationResponse:
        """Send task completion notification."""
        # Generate enhanced summary based on agent type and result data
        enhanced_summary = self._generate_enhanced_task_summary(agent, result_summary, result_data)

        message = f"Task `{task_id[:8]}...` completed by *{agent}*"

        # Add execution time if available
        if execution_time_ms is not None:
            if execution_time_ms < 1000:
                time_str = f"{execution_time_ms}ms"
            elif execution_time_ms < 60000:
                time_str = f"{execution_time_ms/1000:.1f}s"
            else:
                minutes = execution_time_ms // 60000
                seconds = (execution_time_ms % 60000) // 1000
                time_str = f"{minutes}m {seconds}s"
            message += f" in *{time_str}*"

        if enhanced_summary:
            message += f"\n\n📊 *Result:*\n{enhanced_summary}"

        return await self.send(NotificationCreate(
            type=NotificationType.TASK_COMPLETED,
            title="Task Completed",
            message=message,
            priority=NotificationPriority.NORMAL,
            metadata={
                "task_id": task_id,
                "agent": agent,
                "result_summary": result_summary,
                "execution_time_ms": execution_time_ms
            }
        ))
    
    async def notify_task_failed(
        self,
        task_id: str,
        agent: str,
        error: str
    ) -> NotificationResponse:
        """Send task failure notification."""
        return await self.send(NotificationCreate(
            type=NotificationType.TASK_FAILED,
            title="Task Failed",
            message=f"Task `{task_id[:8]}...` failed\n*Agent:* {agent}\n*Error:* {error}",
            priority=NotificationPriority.HIGH,
            metadata={"task_id": task_id, "agent": agent, "error": error}
        ))
    
    async def notify_agent_alert(
        self,
        agent: str,
        alert_message: str,
        level: str = "warning"
    ) -> NotificationResponse:
        """Send agent alert notification."""
        priority = (
            NotificationPriority.URGENT if level == "error"
            else NotificationPriority.HIGH if level == "warning"
            else NotificationPriority.NORMAL
        )
        
        return await self.send(NotificationCreate(
            type=NotificationType.AGENT_ALERT,
            title=f"Agent Alert: {agent}",
            message=alert_message,
            priority=priority,
            metadata={"agent": agent, "level": level}
        ))
    
    async def notify_system_error(
        self,
        error: str,
        context: Optional[Dict[str, Any]] = None
    ) -> NotificationResponse:
        """Send system error notification."""
        message = f"*Error:* {error}"
        if context:
            message += f"\n\n*Context:*\n```\n{context}\n```"
        
        return await self.send(NotificationCreate(
            type=NotificationType.SYSTEM_ERROR,
            title="System Error",
            message=message,
            priority=NotificationPriority.URGENT,
            metadata={"error": error, "context": context or {}}
        ))
    
    async def send_workflow_approval_request(
        self,
        *,
        workflow_id: str,
        approval_token: str,
        approval_config: Dict[str, Any],
        agent: str,
    ) -> bool:
        """Send a lightweight approval prompt via Telegram (best-effort)."""
        if not self.telegram.enabled:
            return False

        context = approval_config.get("approval_context") or {}
        message = f"""
🤖 *Approval Required*

{approval_config.get('approval_message', 'Please review this workflow')}

*Agent:* {agent}
*Workflow:* `{workflow_id}`
*Reason:* {approval_config.get('reason') or 'High-risk action detected'}

Context:
{context}

✅ /approve_{approval_token}
❌ /reject_{approval_token}
👀 /view_{approval_token}
        """

        return await self.telegram.send_notification(message)

    async def notify_crypto_signal(
        self,
        coin: str,
        signal: str,
        confidence: int,
        price: float,
        change_24h: float,
        reason: Optional[str] = None
    ) -> NotificationResponse:
        """Send crypto signal notification."""
        signal_emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
        change_emoji = "📈" if change_24h > 0 else "📉"
        
        message = (
            f"*{coin}*: {signal_emoji.get(signal, '')} {signal} ({confidence}%)\n"
            f"Price: ${price:,.2f}\n"
            f"24h: {change_emoji} {change_24h:+.2f}%"
        )
        
        if reason:
            message += f"\n\n*Reason:* {reason}"
        
        return await self.send(NotificationCreate(
            type=NotificationType.CRYPTO_SIGNAL,
            title=f"Crypto Signal: {coin}",
            message=message,
            priority=NotificationPriority.HIGH if signal != "HOLD" else NotificationPriority.NORMAL,
            metadata={
                "coin": coin,
                "signal": signal,
                "confidence": confidence,
                "price": price,
                "change_24h": change_24h
            }
        ))
    
    async def notify_job_match(
        self,
        title: str,
        company: str,
        location: str,
        match_score: int,
        url: Optional[str] = None
    ) -> NotificationResponse:
        """Send job match notification."""
        message = (
            f"*{title}*\n"
            f"🏢 {company}\n"
            f"📍 {location}\n"
            f"🎯 Match: {match_score}%"
        )
        
        if url:
            message += f"\n\n[View Job]({url})"
        
        return await self.send(NotificationCreate(
            type=NotificationType.JOB_MATCH,
            title="New Job Match",
            message=message,
            priority=NotificationPriority.HIGH if match_score >= 80 else NotificationPriority.NORMAL,
            metadata={
                "job_title": title,
                "company": company,
                "location": location,
                "match_score": match_score,
                "url": url
            }
        ))
    
    async def notify_daily_brief(self, brief: Dict[str, Any]) -> NotificationResponse:
        """Send daily brief notification."""
        # Use telegram's formatted brief method
        if self.telegram.enabled:
            await self.telegram.send_daily_brief(brief)

        return await self.send(NotificationCreate(
            type=NotificationType.DAILY_BRIEF,
            title="Daily Brief",
            message="Your daily brief is ready!",
            priority=NotificationPriority.NORMAL,
            metadata=brief
        ))

    async def send_morning_brief_notification(self, brief_content: str) -> NotificationResponse:
        """Send morning brief content directly to Telegram."""
        if not self.telegram.enabled:
            return NotificationResponse(
                success=False,
                message="Telegram bot not enabled"
            )

        # Send the brief content directly
        success = await self.telegram.send_notification(
            message=f"📰 *Morning Brief*\n\n{brief_content}",
            parse_mode=ParseMode.MARKDOWN
        )

        return NotificationResponse(
            success=success,
            message="Morning brief sent to Telegram" if success else "Failed to send morning brief",
            delivered_to=["telegram"] if success else []
        )
    
    def _generate_enhanced_task_summary(
        self,
        agent: str,
        result_summary: Optional[str] = None,
        result_data: Optional[dict] = None
    ) -> str:
        """
        Generate an enhanced task summary based on agent type and result data.

        Args:
            agent: The agent that completed the task
            result_summary: Existing summary (if any)
            result_data: Raw result data from the task

        Returns:
            Enhanced summary string
        """
        # If we have specific result data, try to generate a meaningful summary
        if result_data:
            if agent == "IDEAS_MACHINE":
                return self._generate_ideas_machine_summary(result_data)
            elif agent == "JOB_HUNTER":
                return self._generate_job_hunter_summary(result_data)
            elif agent == "CRYPTO_SENTINEL":
                return self._generate_crypto_sentinel_summary(result_data)

        # Fallback to basic summary or original result_summary
        if result_summary:
            return result_summary

        return "Task completed successfully"

    def _generate_ideas_machine_summary(self, result_data: dict) -> str:
        """Generate summary for IDEAS_MACHINE tasks."""
        try:
            # Extract main project summary data
            project_name = result_data.get("project_name", "Unknown Project")
            project_type = result_data.get("project_type", "Unknown")
            fullstack = result_data.get("fullstack", False)
            success = result_data.get("success", False)

            # Tech stack info
            tech_stack = result_data.get("tech_stack", {})
            frontend = tech_stack.get("frontend", "Unknown")
            backend = tech_stack.get("backend", "Unknown")
            infrastructure = tech_stack.get("infrastructure", [])

            # Phase and file generation stats
            phases_planned = result_data.get("phases_planned", 0)
            phases_executed = result_data.get("phases_executed", 0)
            total_files = result_data.get("total_files_generated", 0)
            docs_generated = result_data.get("documentation_generated", 0)

            # Project path
            project_path = result_data.get("project_path", "")

            # Build comprehensive summary
            summary = f"🏗️ **{project_name}**\n"
            summary += f"📂 *Type:* {project_type.replace('_', ' ').title()}\n"
            summary += f"🔧 *Tech Stack:*\n"

            if frontend and frontend != "Unknown":
                summary += f"  • Frontend: {frontend}\n"
            if backend and backend != "Unknown":
                summary += f"  • Backend: {backend}\n"
            if infrastructure and len(infrastructure) > 0:
                infra_str = ", ".join(infrastructure[:3])  # Show first 3 infra tools
                if len(infrastructure) > 3:
                    infra_str += f" +{len(infrastructure) - 3} more"
                summary += f"  • Infrastructure: {infra_str}\n"

            # Execution results - show detailed breakdown
            if phases_executed > 0:
                status_emoji = "✅" if success else "⚠️"
                summary += f"{status_emoji} *Phases:* {phases_executed}/{phases_planned} completed\n"

                # Add detailed execution results if available
                execution_results = result_data.get("execution_results")
                if execution_results and isinstance(execution_results, dict):
                    success_rate = execution_results.get("success_rate", 0)
                    if success_rate > 0:
                        success_percentage = int(success_rate * 100)
                        summary += f"🎯 *Success Rate:* {success_percentage}%\n"

                    total_fixes = execution_results.get("total_fixes_applied", 0)
                    if total_fixes > 0:
                        summary += f"🔧 *Auto-fixes:* {total_fixes}\n"

                    completion_status = execution_results.get("completion_status")
                    if completion_status:
                        summary += f"🏁 *Status:* {completion_status}\n"

                if total_files > 0:
                    summary += f"📄 *Files Generated:* {total_files}\n"
                if docs_generated > 0:
                    summary += f"📚 *Documentation:* {docs_generated} files\n"
            else:
                summary += f"📋 *Planning:* {phases_planned} phases planned\n"

            # Add analysis details if available
            if "analysis" in result_data:
                analysis = result_data["analysis"]
                features = analysis.get("core_features", [])
                if features and len(features) > 0:
                    summary += f"\n🎯 *Key Features:*\n"
                    for feature in features[:2]:  # Show first 2 features
                        summary += f"• {feature}\n"
                    if len(features) > 2:
                        summary += f"• ... and {len(features) - 2} more\n"

            # Add project path and key links
            if project_path:
                summary += f"\n📍 *Location:* `{project_path}`"

                # Add helpful links if this is a local development environment
                if "Projects" in project_path or "/home/" in project_path or "C:\\" in project_path:
                    # Try to create relative links to key documentation files
                    docs_path = f"{project_path}/docs"
                    summary += f"\n\n🔗 *Quick Access:*\n"
                    summary += f"• 📖 [Master Plan](docs/00_MASTER_PLAN.md)\n"
                    summary += f"• 📋 [README](README.md)\n"
                    summary += f"• 🖥️ Open in Cursor: `cursor {project_path}`"

            # Add next steps if available
            next_steps = result_data.get("next_steps", [])
            if next_steps and len(next_steps) > 0 and not project_path:
                # Only show next steps if we didn't show the quick access links
                summary += f"\n\n🚀 *Next Steps:*\n"
                for step in next_steps[:2]:  # Show first 2 steps
                    summary += f"• {step}\n"
                if len(next_steps) > 2:
                    summary += f"• ... and {len(next_steps) - 2} more actions\n"

            return summary

        except Exception as e:
            self.logger.warning(f"Failed to generate IDEAS_MACHINE summary: {e}")
            # Provide basic fallback with available data
            project_name = result_data.get("project_name", "Project")
            return f"🏗️ **{project_name}** - Project generation completed"

    def _generate_job_hunter_summary(self, result_data: dict) -> str:
        """Generate summary for JOB_HUNTER tasks."""
        try:
            if "jobs" in result_data and isinstance(result_data["jobs"], list):
                jobs = result_data["jobs"]
                count = len(jobs)
                if count > 0:
                    summary = f"💼 Found {count} job opportunit{'ies' if count != 1 else 'y'}\n"

                    # Show top 2 jobs
                    for i, job in enumerate(jobs[:2]):
                        title = job.get("title", "Position")
                        company = job.get("company", "Company")
                        summary += f"• {title} at {company}\n"

                    if count > 2:
                        summary += f"• ... and {count - 2} more opportunities\n"

                    return summary

            # Check for other job-related data
            if "applications" in result_data:
                apps = result_data["applications"]
                if isinstance(apps, list):
                    count = len(apps)
                    return f"📝 Processed {count} job application{'s' if count != 1 else ''}"

        except Exception as e:
            self.logger.warning(f"Failed to generate JOB_HUNTER summary: {e}")

        return "Job search completed"

    def _generate_crypto_sentinel_summary(self, result_data: dict) -> str:
        """Generate summary for CRYPTO_SENTINEL tasks."""
        try:
            # Handle market analysis
            if "signals" in result_data and isinstance(result_data["signals"], list):
                signals = result_data["signals"]
                count = len(signals)
                if count > 0:
                    summary = f"📈 Generated {count} trading signal{'s' if count != 1 else ''}\n"

                    # Show top signals
                    for signal in signals[:3]:
                        coin = signal.get("coin", "Asset")
                        action = signal.get("signal", "Signal")
                        confidence = signal.get("confidence", 0)
                        summary += f"• {coin}: {action} ({confidence}%)\n"

                    return summary

            # Handle portfolio data
            if "portfolio" in result_data:
                portfolio = result_data["portfolio"]
                if isinstance(portfolio, dict):
                    assets = portfolio.get("assets", [])
                    if isinstance(assets, list):
                        count = len(assets)
                        total_value = portfolio.get("total_value", "Unknown")
                        return f"📊 Portfolio: {count} asset{'s' if count != 1 else ''}, Total: ${total_value}"

            # Handle market brief
            if "brief" in result_data or "market_data" in result_data:
                return "📊 Market analysis completed"

        except Exception as e:
            self.logger.warning(f"Failed to generate CRYPTO_SENTINEL summary: {e}")

        return "Market analysis completed"

    async def get_recent_notifications(
        self,
        limit: int = 50,
        notification_type: Optional[NotificationType] = None
    ) -> List[Dict[str, Any]]:
        """Get recent notifications."""
        notifications = Database.get_collection("notifications")

        query = {}
        if notification_type:
            query["type"] = notification_type.value

        cursor = notifications.find(query).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)


# ==========================================================================
# SINGLETON MANAGEMENT
# ==========================================================================

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def reset_notification_service():
    """Reset the notification service singleton (for testing)."""
    global _notification_service
    _notification_service = None


