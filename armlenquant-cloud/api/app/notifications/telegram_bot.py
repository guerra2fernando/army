"""
Telegram Bot Service
Handles sending notifications and receiving commands via Telegram.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable
from uuid import uuid4

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
from loguru import logger

from app.config import get_settings

settings = get_settings()


class TelegramBot:
    """
    Telegram Bot for ArmLenQuant notifications and commands.
    
    Features:
    - Send notifications (alerts, briefs, signals)
    - Process user commands (/status, /agents, /task, etc.)
    - Forward natural language to Orchestrator
    """
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.enabled = settings.telegram_enabled and bool(self.token)
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self._running = False
        self._command_handlers: Dict[str, Callable] = {}
        self._message_handler: Optional[Callable] = None
        self.logger = logger.bind(component="telegram_bot")
        
        if self.enabled:
            self.bot = Bot(token=self.token)
    
    async def start(self):
        """Start the Telegram bot (polling mode)."""
        if not self.enabled:
            self.logger.warning("Telegram bot is disabled")
            return
        
        self.logger.info("Starting Telegram bot...")
        
        # Build application
        self.application = (
            Application.builder()
            .token(self.token)
            .build()
        )
        
        # Register built-in command handlers
        self._register_default_handlers()
        
        # Register custom command handlers
        for command, handler in self._command_handlers.items():
            self.application.add_handler(
                CommandHandler(command, self._wrap_handler(handler))
            )
        
        # Register message handler for natural language
        if self._message_handler:
            self.application.add_handler(
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    self._wrap_handler(self._message_handler)
                )
            )
        
        # Initialize and start polling
        await self.application.initialize()
        await self.application.start()
        
        # Start polling in background
        self._running = True
        asyncio.create_task(self._poll_loop())
        
        self.logger.info("Telegram bot started")
    
    async def stop(self):
        """Stop the Telegram bot."""
        if not self.enabled or not self.application:
            return
        
        self._running = False
        
        try:
            await self.application.stop()
            await self.application.shutdown()
            self.logger.info("Telegram bot stopped")
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
    
    async def _poll_loop(self):
        """Background polling loop."""
        if not self.application:
            return
        
        try:
            await self.application.updater.start_polling(
                drop_pending_updates=True
            )
            
            while self._running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Polling error: {e}")
        finally:
            if self.application and self.application.updater.running:
                await self.application.updater.stop()
    
    def _register_default_handlers(self):
        """Register default command handlers."""
        if not self.application:
            return
        
        # /start - Welcome message
        self.application.add_handler(
            CommandHandler("start", self._cmd_start)
        )
        
        # /help - Show available commands
        self.application.add_handler(
            CommandHandler("help", self._cmd_help)
        )
        
        # /status - System status
        self.application.add_handler(
            CommandHandler("status", self._cmd_status)
        )
        
        # /agents - List agents
        self.application.add_handler(
            CommandHandler("agents", self._cmd_agents)
        )
        
        # /tasks - List recent tasks
        self.application.add_handler(
            CommandHandler("tasks", self._cmd_tasks)
        )
        
        # /crypto - Quick crypto update
        self.application.add_handler(
            CommandHandler("crypto", self._cmd_crypto)
        )
        
        # /jobs - Job search status
        self.application.add_handler(
            CommandHandler("jobs", self._cmd_jobs)
        )
        
        # /brief - Get daily brief
        self.application.add_handler(
            CommandHandler("brief", self._cmd_brief)
        )
        
        # Default message handler (forward to orchestrator)
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message
            )
        )
    
    def _wrap_handler(self, handler: Callable) -> Callable:
        """Wrap a handler with error handling."""
        async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                await handler(update, context)
            except Exception as e:
                self.logger.error(f"Handler error: {e}")
                if update.effective_chat:
                    await update.effective_chat.send_message(
                        f"❌ Error: {str(e)}"
                    )
        return wrapped
    
    # ==========================================================================
    # COMMAND HANDLERS
    # ==========================================================================
    
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        welcome_message = f"""
🤖 *Welcome to ArmLenQuant!*

Hello {user.first_name}! I'm your autonomous agent orchestrator.

Your Chat ID: `{chat_id}`

*Available Commands:*
/status - System status
/agents - List active agents
/tasks - Recent tasks
/crypto - Crypto market update
/jobs - Job search status
/brief - Get daily brief
/help - Show all commands

You can also send me natural language commands, like:
• "Find Python jobs in Berlin"
• "What's the crypto market looking like?"
• "Create a new FastAPI project"

I'll route your request to the right agent! 🚀
        """
        
        await update.message.reply_text(
            welcome_message,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Log the connection
        self.logger.info(f"New Telegram user: {user.username} (chat_id: {chat_id})")
    
    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
🤖 *ArmLenQuant Commands*

*System:*
/status - Check system health
/agents - List registered agents
/tasks - View recent tasks
/brief - Get daily brief

*Crypto:*
/crypto - Market overview & signals

*Jobs:*
/jobs - Job search status

*Natural Language:*
Just type what you want to do!

Examples:
• "Search for React developer jobs"
• "Analyze SOL and ETH"
• "Create a CLI tool for file management"
• "What can you help me with?"
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        # Import here to avoid circular imports
        from app.db import Database
        
        try:
            agents = Database.get_collection("agent_registry")
            tasks = Database.get_collection("task_queue")
            
            agent_count = await agents.count_documents({})
            active_agents = await agents.count_documents({"status": "ACTIVE"})
            pending_tasks = await tasks.count_documents({"status": "PENDING"})
            in_progress = await tasks.count_documents({"status": "IN_PROGRESS"})
            completed_today = await tasks.count_documents({
                "status": "COMPLETED",
                "completed_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
            })
            
            status_text = f"""
📊 *System Status*

🟢 *Status:* Online
🤖 *Agents:* {active_agents}/{agent_count} active

📋 *Tasks:*
• Pending: {pending_tasks}
• In Progress: {in_progress}
• Completed Today: {completed_today}

⏰ *Updated:* {datetime.utcnow().strftime('%H:%M UTC')}
            """
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error getting status: {e}")
    
    async def _cmd_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /agents command."""
        from app.db import Database
        
        try:
            agents = Database.get_collection("agent_registry")
            cursor = agents.find({})
            agent_list = await cursor.to_list(length=20)
            
            if not agent_list:
                await update.message.reply_text("No agents registered yet.")
                return
            
            lines = ["🤖 *Registered Agents*\n"]
            
            status_emoji = {
                "ACTIVE": "🟢",
                "PAUSED": "🟡",
                "FAILED": "🔴",
                "STANDBY": "⚪"
            }
            
            for agent in agent_list:
                emoji = status_emoji.get(agent.get("status", ""), "⚪")
                name = agent.get("agent_name", "Unknown")
                location = agent.get("location", "?")
                version = agent.get("version", "?")
                
                lines.append(f"{emoji} *{name}*")
                lines.append(f"   └ {location} | v{version}")
            
            await update.message.reply_text(
                "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _cmd_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tasks command."""
        from app.db import Database
        
        try:
            tasks = Database.get_collection("task_queue")
            cursor = tasks.find({}).sort("created_at", -1).limit(10)
            task_list = await cursor.to_list(length=10)
            
            if not task_list:
                await update.message.reply_text("No tasks found.")
                return
            
            lines = ["📋 *Recent Tasks*\n"]
            
            status_emoji = {
                "PENDING": "⏳",
                "PICKED_UP": "📥",
                "IN_PROGRESS": "🔄",
                "COMPLETED": "✅",
                "FAILED": "❌"
            }
            
            for task in task_list:
                emoji = status_emoji.get(task.get("status", ""), "❓")
                agent = task.get("agent_target", "?")
                created = task.get("created_at")
                time_str = created.strftime("%H:%M") if created else "?"
                
                lines.append(f"{emoji} *{agent}* - {time_str}")
            
            await update.message.reply_text(
                "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _cmd_crypto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /crypto command."""
        from app.db import Database
        
        try:
            briefs = Database.get_collection("daily_brief")
            brief = await briefs.find_one(
                {},
                sort=[("date", -1)]
            )
            
            if not brief or "crypto" not in brief:
                await update.message.reply_text(
                    "No crypto data available. Run /brief to generate."
                )
                return
            
            crypto = brief["crypto"]
            sentiment = crypto.get("sentiment", "NEUTRAL")
            sentiment_emoji = {"BULLISH": "📈", "BEARISH": "📉", "NEUTRAL": "➡️"}
            
            lines = [
                f"📊 *Crypto Update*\n",
                f"Sentiment: {sentiment_emoji.get(sentiment, '')} {sentiment}\n",
                "*Top Movers:*"
            ]
            
            for mover in crypto.get("top_movers", [])[:5]:
                coin = mover.get("coin", "?")
                change = mover.get("change", 0)
                signal = mover.get("signal", "HOLD")
                conf = mover.get("confidence", 0)
                
                arrow = "🟢" if change > 0 else "🔴"
                lines.append(f"{arrow} *{coin}*: {change:+.1f}% | {signal} ({conf}%)")
            
            await update.message.reply_text(
                "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _cmd_jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /jobs command."""
        from app.db import Database
        
        try:
            briefs = Database.get_collection("daily_brief")
            brief = await briefs.find_one({}, sort=[("date", -1)])
            
            if not brief or "jobs" not in brief:
                await update.message.reply_text("No job data available.")
                return
            
            jobs = brief["jobs"]
            
            text = f"""
💼 *Job Search Status*

📝 Drafts Ready: {jobs.get('drafts_ready', 0)}
🆕 New Matches: {jobs.get('new_matches', 0)}
📤 Applications Sent: {jobs.get('applications_sent', 0)}

Use natural language to search:
"Find senior Python jobs in London"
            """
            
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def _cmd_brief(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /brief command - request daily brief generation."""
        await update.message.reply_text(
            "🔄 Generating daily brief...\n"
            "This may take a moment."
        )
        
        # Create a task for the crypto sentinel to generate brief
        from app.db import Database
        
        try:
            tasks = Database.get_collection("task_queue")
            task_id = str(uuid4())
            
            await tasks.insert_one({
                "_id": task_id,
                "task_id": task_id,
                "agent_target": "CRYPTO_SENTINEL",
                "payload": {"action": "morning_brief"},
                "status": "PENDING",
                "priority": 8,
                "worker_id": None,
                "retry_count": 0,
                "max_retries": 3,
                "error_log": [],
                "result": None,
                "created_by": f"telegram:{update.effective_user.id}",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            await update.message.reply_text(
                f"✅ Task created: `{task_id[:8]}...`\n"
                "I'll send you the brief when it's ready!",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to create task: {e}")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages."""
        text = update.message.text
        user_id = f"telegram:{update.effective_user.id}"
        
        # Show typing indicator
        await update.effective_chat.send_action("typing")
        
        # Process through orchestrator
        from app.orchestrator.agent_00 import get_orchestrator
        
        try:
            orchestrator = get_orchestrator()
            response = await orchestrator.process_command(
                command=text,
                user_id=user_id
            )
            
            # Format response
            if response.requires_clarification:
                reply = f"🤔 {response.clarification_question}"
            elif response.task_created:
                reply = f"✅ {response.message}\n\n📋 Task ID: `{response.task_id[:8]}...`"
            else:
                reply = f"💬 {response.message}"
            
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            self.logger.error(f"Orchestrator error: {e}")
            await update.message.reply_text(
                f"❌ Sorry, I encountered an error: {e}"
            )
    
    # ==========================================================================
    # NOTIFICATION METHODS
    # ==========================================================================
    
    async def send_notification(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = ParseMode.MARKDOWN,
        silent: bool = False
    ) -> bool:
        """
        Send a notification message.
        
        Args:
            message: The message to send
            chat_id: Target chat ID (defaults to configured chat)
            parse_mode: Message format (MARKDOWN or HTML)
            silent: Send without notification sound
            
        Returns:
            True if sent successfully
        """
        if not self.enabled:
            self.logger.debug("Telegram disabled, skipping notification")
            return False
        
        target_chat = chat_id or self.chat_id
        if not target_chat:
            self.logger.warning("No chat ID configured for notification")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=target_chat,
                text=message,
                parse_mode=parse_mode,
                disable_notification=silent
            )
            self.logger.debug(f"Notification sent to {target_chat}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False
    
    async def send_task_notification(
        self,
        task_id: str,
        agent: str,
        status: str,
        message: Optional[str] = None,
        result_summary: Optional[str] = None
    ) -> bool:
        """Send a task status notification."""
        emoji = {
            "COMPLETED": "✅",
            "FAILED": "❌",
            "IN_PROGRESS": "🔄",
            "PENDING": "⏳"
        }
        
        text = f"""
{emoji.get(status, '📋')} *Task Update*

*Agent:* {agent}
*Status:* {status}
*Task ID:* `{task_id[:8]}...`
"""
        
        if message:
            text += f"\n*Message:* {message}"
        
        if result_summary:
            text += f"\n\n📊 *Result:*\n{result_summary}"
        
        return await self.send_notification(text)
    
    async def send_alert(
        self,
        title: str,
        message: str,
        level: str = "info"
    ) -> bool:
        """Send an alert notification."""
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨",
            "success": "✅"
        }
        
        text = f"""
{emoji.get(level, 'ℹ️')} *{title}*

{message}

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
"""
        
        return await self.send_notification(
            text,
            silent=(level == "info")
        )
    
    async def send_crypto_signal(
        self,
        coin: str,
        signal: str,
        confidence: int,
        price: float,
        change_24h: float,
        reason: Optional[str] = None
    ) -> bool:
        """Send a crypto trading signal."""
        signal_emoji = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "🟡"
        }
        
        change_emoji = "📈" if change_24h > 0 else "📉"
        
        text = f"""
{signal_emoji.get(signal, '⚪')} *Crypto Signal: {coin}*

*Signal:* {signal} ({confidence}% confidence)
*Price:* ${price:,.2f}
*24h Change:* {change_emoji} {change_24h:+.2f}%
"""
        
        if reason:
            text += f"\n*Reason:* {reason}"
        
        return await self.send_notification(text)
    
    async def send_job_match(
        self,
        title: str,
        company: str,
        location: str,
        match_score: int,
        url: Optional[str] = None
    ) -> bool:
        """Send a job match notification."""
        text = f"""
💼 *New Job Match!*

*Title:* {title}
*Company:* {company}
*Location:* {location}
*Match Score:* {match_score}%
"""
        
        if url:
            text += f"\n🔗 [View Job]({url})"
        
        return await self.send_notification(text)
    
    async def send_daily_brief(self, brief: Dict[str, Any]) -> bool:
        """Send the daily brief summary."""
        crypto = brief.get("crypto", {})
        jobs = brief.get("jobs", {})
        system = brief.get("system", {})
        
        # Format top movers
        movers_text = ""
        for mover in crypto.get("top_movers", [])[:3]:
            arrow = "🟢" if mover.get("change", 0) > 0 else "🔴"
            movers_text += f"\n  {arrow} {mover.get('coin')}: {mover.get('change', 0):+.1f}%"
        
        # Handle empty movers
        if not movers_text:
            movers_text = "\n  No data"
        
        text = f"""
📰 *Daily Brief - {brief.get('date', 'Today')}*

📊 *Crypto*
Sentiment: {crypto.get('sentiment', 'N/A')}
Top Movers:{movers_text}

💼 *Jobs*
• {jobs.get('new_matches', 0)} new matches
• {jobs.get('drafts_ready', 0)} drafts ready

⚙️ *System*
Status: {system.get('health', 'Unknown')}
Tasks (24h): {system.get('tasks_completed_24h', 0)}

Have a productive day! 🚀
"""
        
        return await self.send_notification(text)


# ==========================================================================
# SINGLETON MANAGEMENT
# ==========================================================================

_telegram_bot: Optional[TelegramBot] = None


def get_telegram_bot() -> TelegramBot:
    """Get or create the Telegram bot singleton."""
    global _telegram_bot
    if _telegram_bot is None:
        _telegram_bot = TelegramBot()
    return _telegram_bot


def reset_telegram_bot():
    """Reset the Telegram bot singleton (for testing)."""
    global _telegram_bot
    _telegram_bot = None


