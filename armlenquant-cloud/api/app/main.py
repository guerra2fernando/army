"""
ArmLenQuant API - Main Entry Point
Phase 10: Integration & Polish
Phase 11: Telegram Bot & Notifications
"""
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from typing import Dict, Any
import traceback
import asyncio
import pytz

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import get_settings
from app.db import Database
from app.routes import (
    auth,
    tasks,
    agents,
    health,
    orchestrator,
    knowledge,
    crypto,
    notifications,
    master_plans,
    phase_executions,
    workflows,
    safety,
    profiles,
    discovery,
    commercial_ops,
)
from app.logging_config import setup_logging
from app.middleware import rate_limit_middleware, SecurityHeaders, mtls_middleware
from app.utils.data_contracts import contract_logger
from app.services.commercial_ops_service import get_commercial_ops_service

settings = get_settings()

# Configure logging using the new logging config
setup_logging(debug=settings.debug)


async def task_scheduler():
    """Background scheduler for checking and executing scheduled tasks."""
    logger.info("Task scheduler started")

    while True:
        try:
            # Check for tasks that should run now
            await check_and_execute_scheduled_tasks()

            # Sleep for 30 seconds before checking again
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Task scheduler error: {e}")
            await asyncio.sleep(30)


def _calculate_next_run(current_time: datetime, recurring: Dict[str, Any], original_command: str = "") -> datetime:
    """Calculate the next run time for a recurring task."""
    import pytz
    from app.utils.time_parser import parse_time_from_text

    # Get Tbilisi timezone
    tbilisi_tz = pytz.timezone("Asia/Tbilisi")

    # Convert to Tbilisi time for calculation
    current_tbilisi = current_time.astimezone(tbilisi_tz)

    pattern = recurring.get("pattern", "")

    if pattern == "weekdays":
        # Parse the desired time from the original command
        scheduled_time = parse_time_from_text(original_command, timezone="Asia/Tbilisi")

        if scheduled_time:
            # Extract hour and minute from the parsed time
            target_hour = scheduled_time.hour
            target_minute = scheduled_time.minute
        else:
            # Fallback to 09:00 if no time found
            target_hour = 9
            target_minute = 0

        # Next weekday at the target time in Tbilisi time
        next_run = current_tbilisi.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        # If it's Saturday or Sunday, move to next Monday
        if current_tbilisi.weekday() >= 5:  # Saturday = 5, Sunday = 6
            days_ahead = 7 - current_tbilisi.weekday()
            next_run = next_run + timedelta(days=days_ahead)
        elif current_tbilisi.time() >= time(target_hour, target_minute):  # Already passed target time today
            if current_tbilisi.weekday() == 4:  # Friday, next is Monday
                next_run = next_run + timedelta(days=3)
            else:
                next_run = next_run + timedelta(days=1)

        # Convert back to UTC
        return next_run.astimezone(pytz.utc)

    # Default: don't recur
    return current_time + timedelta(days=1)


async def check_and_execute_scheduled_tasks():
    """Check for scheduled tasks that should run now and execute them."""
    try:
        due_followups = await get_commercial_ops_service().process_due_followups()
        if due_followups:
            logger.info(f"Created {due_followups} due follow-up review item(s)")

        scheduled_tasks = Database.get_collection("scheduled_tasks")
        now = datetime.utcnow()

        # Find tasks that should run now (within the last minute to account for timing)
        cutoff_time = now.replace(second=0, microsecond=0)

        # Look for tasks scheduled to run at this time
        query = {
            "scheduled_time": {"$lte": now, "$gte": cutoff_time.replace(minute=cutoff_time.minute - 1)},
            "executed": False,
            "cancelled": {"$ne": True}
        }

        cursor = scheduled_tasks.find(query)
        tasks_to_run = await cursor.to_list(length=None)

        for scheduled_task in tasks_to_run:
            try:
                logger.info(f"Executing scheduled task: {scheduled_task['_id']} - {scheduled_task.get('title', 'Unknown')}")

                # Create the actual task in the task queue
                from uuid import uuid4
                tasks = Database.get_collection("task_queue")
                task_id = str(uuid4())

                await tasks.insert_one({
                    "_id": task_id,
                    "task_id": task_id,
                    "agent_target": scheduled_task["agent_target"],
                    "payload": scheduled_task["payload"],
                    "title": scheduled_task.get("title", f"Scheduled task"),
                    "status": "PENDING",
                    "priority": scheduled_task.get("priority", 5),
                    "worker_id": None,
                    "retry_count": 0,
                    "max_retries": 3,
                    "error_log": [],
                    "result": None,
                    "created_by": scheduled_task.get("created_by", "scheduler"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })

                # Handle recurring tasks vs one-time tasks
                recurring = scheduled_task.get("recurring")
                if recurring:
                    # Reschedule for next occurrence
                    original_command = scheduled_task.get("original_command", "")
                    next_run = _calculate_next_run(scheduled_task["scheduled_time"], recurring, original_command)
                    await scheduled_tasks.update_one(
                        {"_id": scheduled_task["_id"]},
                        {"$set": {
                            "executed": False,
                            "executed_at": datetime.utcnow(),
                            "scheduled_time": next_run,
                            "last_scheduled": scheduled_task["scheduled_time"],
                            "task_id": task_id
                        }}
                    )
                    logger.info(f"Rescheduled recurring task {scheduled_task['_id']} for next run: {next_run}")
                else:
                    # Mark one-time task as executed
                    await scheduled_tasks.update_one(
                        {"_id": scheduled_task["_id"]},
                        {"$set": {"executed": True, "executed_at": datetime.utcnow(), "task_id": task_id}}
                    )
                    logger.info(f"Executed one-time scheduled task {scheduled_task['_id']}")

                logger.info(f"Created task {task_id} from scheduled task {scheduled_task['_id']}")

            except Exception as e:
                logger.error(f"Failed to execute scheduled task {scheduled_task['_id']}: {e}")

    except Exception as e:
        logger.error(f"Error checking scheduled tasks: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await Database.connect()

    # Start Telegram bot if enabled
    if settings.telegram_enabled:
        try:
            from app.notifications.telegram_bot import get_telegram_bot
            telegram_bot = get_telegram_bot()
            await telegram_bot.start()
            logger.info("Telegram bot started")
        except Exception as e:
            logger.error(f"Failed to start Telegram bot: {e}")

    # Start task scheduler
    scheduler_task = asyncio.create_task(task_scheduler())
    logger.info("Task scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Cancel scheduler
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("Task scheduler stopped")

    # Stop Telegram bot
    if settings.telegram_enabled:
        try:
            from app.notifications.telegram_bot import get_telegram_bot
            telegram_bot = get_telegram_bot()
            await telegram_bot.stop()
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    await Database.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Autonomous Agent Orchestration System API",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# GLOBAL ERROR HANDLER (Phase 10)
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions.
    
    Logs the error to the event stream and returns a standardized error response.
    """
    # Log the full traceback
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    
    # Log to event stream for monitoring
    try:
        await contract_logger.log_internal(
            "ERROR",
            "UNHANDLED_ERROR",
            agent="API",
            message=str(exc),
            details={
                "path": str(request.url.path),
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
        )
        await contract_logger.emit_event(
            "UNHANDLED_ERROR",
            "Unhandled API exception",
            description=str(exc),
            priority="HIGH",
            agent_name="API",
            payload={
                "path": str(request.url.path),
                "method": request.method,
                "traceback": traceback.format_exc(),
            },
        )
    except Exception as log_error:
        logger.error(f"Failed to log error to event stream: {log_error}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred"
        }
    )


# Add security headers middleware
@app.middleware("http")
async def enforce_mtls(request: Request, call_next):
    """Validate client certificate when mTLS is enabled."""
    return await mtls_middleware(request, call_next)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    return await SecurityHeaders.add_headers(request, call_next)


# Include routers
# Health router is included twice: once at root level for basic health check,
# and once under /api/v1 for detailed health (requires auth)
app.include_router(health.router)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(crypto.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(master_plans.router, prefix="/api/v1")
app.include_router(phase_executions.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(safety.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(discovery.router, prefix="/api/v1")
app.include_router(commercial_ops.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
