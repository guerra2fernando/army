"""
Heartbeat Manager
Sends periodic health signals to the cloud.
"""
import asyncio
import psutil
from datetime import datetime
from typing import Optional
from loguru import logger

from poller.api_client import CloudAPIClient
from poller.task_router import TaskRouter
from poller.config import get_settings

settings = get_settings()


class HeartbeatManager:
    """
    Manages heartbeat signals to the cloud.
    """
    
    def __init__(
        self,
        api_client: CloudAPIClient,
        task_router: TaskRouter
    ):
        self.api_client = api_client
        self.task_router = task_router
        self.logger = logger.bind(component="heartbeat")
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the heartbeat loop."""
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        self.logger.info("Heartbeat manager started")
    
    async def stop(self):
        """Stop the heartbeat loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("Heartbeat manager stopped")
    
    async def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._send_heartbeat()
            except Exception as e:
                self.logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(settings.heartbeat_interval_seconds)
    
    async def _send_heartbeat(self):
        """Send heartbeat to cloud."""
        # Collect metrics
        metrics = self._collect_metrics()
        
        # Get current task if any
        statuses = self.task_router.get_all_statuses()
        current_task = None
        for agent_type, status in statuses.items():
            if status.get("is_running"):
                current_task = status.get("current_task")
                break
        
        # Determine overall status
        overall_status = "HEALTHY"
        if metrics["cpu_percent"] > 90 or metrics["memory_percent"] > 90:
            overall_status = "DEGRADED"
        
        # Send heartbeat for the poller itself
        success = await self.api_client.send_heartbeat(
            agent_name="LOCAL_POLLER",
            status=overall_status,
            current_task=current_task,
            metrics=metrics
        )
        
        if success:
            self.logger.debug(f"Heartbeat sent: {overall_status}")
        else:
            self.logger.warning("Failed to send heartbeat")
    
    def _collect_metrics(self) -> dict:
        """Collect system metrics."""
        try:
            disk_percent = psutil.disk_usage('/').percent
        except Exception:
            try:
                disk_percent = psutil.disk_usage('C:\\').percent
            except Exception:
                disk_percent = 0.0
        
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": disk_percent,
            "timestamp": datetime.utcnow().isoformat()
        }

