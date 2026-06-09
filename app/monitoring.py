"""
System Monitoring
Phase 10: Integration & Polish
"""
from datetime import datetime, timedelta
from typing import Dict, List
from loguru import logger

from app.db import Database


class SystemMonitor:
    """Monitors system health and performance."""
    
    ALERT_THRESHOLDS = {
        "task_queue_depth": 100,
        "task_stuck_minutes": 30,
        "agent_failure_rate": 0.2,
        "api_error_rate": 0.05
    }
    
    async def check_health(self) -> Dict:
        """
        Run health checks and return status.
        
        Returns:
            Dictionary with health status for each component
        """
        checks = {}
        
        # Database connectivity
        try:
            await Database.client.admin.command('ping')
            checks["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            checks["database"] = "unhealthy"
        
        # Task queue health
        try:
            tasks = Database.get_collection("task_queue")
            pending = await tasks.count_documents({"status": "PENDING"})
            stuck = await tasks.count_documents({
                "status": "IN_PROGRESS",
                "picked_up_at": {"$lt": datetime.utcnow() - timedelta(minutes=30)}
            })
            
            queue_status = "healthy"
            if pending >= self.ALERT_THRESHOLDS["task_queue_depth"]:
                queue_status = "degraded"
            if stuck > 0:
                queue_status = "degraded"
            
            checks["task_queue"] = {
                "pending": pending,
                "stuck": stuck,
                "status": queue_status
            }
        except Exception as e:
            logger.error(f"Task queue health check failed: {e}")
            checks["task_queue"] = {
                "pending": 0,
                "stuck": 0,
                "status": "unhealthy"
            }
        
        # Agent health
        try:
            agents = Database.get_collection("agent_registry")
            active = await agents.count_documents({"status": "ACTIVE"})
            failed = await agents.count_documents({"status": "FAILED"})
            
            agent_status = "healthy"
            if failed > 0:
                agent_status = "degraded"
            
            checks["agents"] = {
                "active": active,
                "failed": failed,
                "status": agent_status
            }
        except Exception as e:
            logger.error(f"Agent health check failed: {e}")
            checks["agents"] = {
                "active": 0,
                "failed": 0,
                "status": "unhealthy"
            }
        
        # Calculate overall status
        statuses = [
            checks["database"],
            checks["task_queue"]["status"],
            checks["agents"]["status"]
        ]
        
        if all(s == "healthy" for s in statuses):
            checks["overall"] = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            checks["overall"] = "unhealthy"
        else:
            checks["overall"] = "degraded"
        
        return checks
    
    async def generate_alerts(self) -> List[Dict]:
        """
        Generate alerts for system issues.
        
        Returns:
            List of alert dictionaries with severity and message
        """
        alerts = []
        health = await self.check_health()
        
        # Check for stuck tasks
        if health["task_queue"]["stuck"] > 0:
            alerts.append({
                "severity": "warning",
                "message": f"{health['task_queue']['stuck']} stuck tasks detected",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check for high queue depth
        if health["task_queue"]["pending"] > self.ALERT_THRESHOLDS["task_queue_depth"]:
            alerts.append({
                "severity": "warning",
                "message": f"High task queue depth: {health['task_queue']['pending']}",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check for failed agents
        if health["agents"]["failed"] > 0:
            alerts.append({
                "severity": "error",
                "message": f"{health['agents']['failed']} agents in failed state",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Check database health
        if health["database"] != "healthy":
            alerts.append({
                "severity": "critical",
                "message": "Database connection unhealthy",
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return alerts
    
    async def get_metrics(self) -> Dict:
        """
        Get system metrics for monitoring.
        
        Returns:
            Dictionary with system metrics
        """
        health = await self.check_health()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": health,
            "task_queue": {
                "pending": health["task_queue"]["pending"],
                "stuck": health["task_queue"]["stuck"]
            },
            "agents": {
                "active": health["agents"]["active"],
                "failed": health["agents"]["failed"]
            }
        }


# Singleton instance
system_monitor = SystemMonitor()

