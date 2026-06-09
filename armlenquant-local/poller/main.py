"""
ArmLenQuant Local Poller
Main entry point for the local agent execution service.
Phase 10: Integration & Polish - Error Recovery Added
"""
import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional
from loguru import logger

# Monkey patch for Python 3.9 compatibility with importlib.metadata
# The google-api-core library tries to use packages_distributions() which doesn't exist in Python 3.9
try:
    import importlib.metadata
    if not hasattr(importlib.metadata, 'packages_distributions'):
        import importlib_metadata
        importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
except ImportError:
    pass

from poller.config import get_settings
from poller.api_client import CloudAPIClient
from poller.task_router import TaskRouter
from poller.heartbeat import HeartbeatManager
from poller.error_recovery import ErrorRecovery, error_recovery

# Import agents
from agents.job_hunter.agent import JobHunterAgent
from agents.commercial_scout.agent import CommercialScoutAgent
from agents.outreach_executor.agent import OutreachExecutorAgent
from agents.ideas_machine.agent import IdeasMachineAgent
from agents.meta_builder.agent import MetaBuilderAgent
from agents.crypto_sentinel.agent import CryptoSentinelAgent

settings = get_settings()

# Configure logging
logger.remove()
# Provide a default component so logs without explicit binding don't break
logger.configure(extra={"component": "core"})
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[component]}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    settings.logs_path / "poller_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="7 days",
    level="DEBUG"
)


class LocalPoller:
    """
    Main poller service that coordinates task execution.
    Phase 10: Enhanced with error recovery system.
    """
    
    def __init__(self):
        self.logger = logger.bind(component="poller")
        self.api_client = CloudAPIClient()
        self.task_router = TaskRouter()
        self.heartbeat_manager = HeartbeatManager(self.api_client, self.task_router)
        self.error_recovery = error_recovery  # Use singleton for error tracking
        self._running = False
        self._current_task = None
        self._agent_configs: dict = {}
        self._idle_cycles = 0
    
    async def initialize(self):
        """Initialize the poller and register agents."""
        self.logger.info("Initializing Local Poller...")
        
        # Check cloud connectivity
        if not await self.api_client.health_check():
            self.logger.error("Cannot connect to cloud API!")
            raise ConnectionError("Cloud API unreachable")
        
        self.logger.info("Connected to cloud API")
        
        # Initialize and register agents
        await self._register_agents()
        
        # Start heartbeat
        await self.heartbeat_manager.start()
        
        self.logger.info("Local Poller initialized")
    
    async def _register_agents(self):
        """Initialize and register all local agents."""
        
        # Job Hunter
        job_hunter = JobHunterAgent()
        self.task_router.register_agent("JOB_HUNTER", job_hunter)
        await self.api_client.register_agent(
            agent_name="JOB_HUNTER",
            version=job_hunter.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=job_hunter.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in job_hunter.get_capability_grants()],
        )

        # Commercial Scout
        commercial_scout = CommercialScoutAgent()
        self.task_router.register_agent("COMMERCIAL_SCOUT", commercial_scout)
        await self.api_client.register_agent(
            agent_name="COMMERCIAL_SCOUT",
            version=commercial_scout.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=commercial_scout.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in commercial_scout.get_capability_grants()],
        )

        # Outreach Executor
        outreach_executor = OutreachExecutorAgent()
        self.task_router.register_agent("OUTREACH_EXECUTOR", outreach_executor)
        await self.api_client.register_agent(
            agent_name="OUTREACH_EXECUTOR",
            version=outreach_executor.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=outreach_executor.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in outreach_executor.get_capability_grants()],
        )
        
        # Ideas Machine
        ideas_machine = IdeasMachineAgent(llm_delay_seconds=settings.llm_delay_seconds)
        self.task_router.register_agent("IDEAS_MACHINE", ideas_machine)
        await self.api_client.register_agent(
            agent_name="IDEAS_MACHINE",
            version=ideas_machine.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=ideas_machine.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in ideas_machine.get_capability_grants()],
        )
        
        # Meta Builder
        meta_builder = MetaBuilderAgent()
        self.task_router.register_agent("META_BUILDER", meta_builder)
        await self.api_client.register_agent(
            agent_name="META_BUILDER",
            version=meta_builder.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=meta_builder.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in meta_builder.get_capability_grants()],
        )

        # Crypto Sentinel
        crypto_sentinel = CryptoSentinelAgent()
        self.task_router.register_agent("CRYPTO_SENTINEL", crypto_sentinel)
        await self.api_client.register_agent(
            agent_name="CRYPTO_SENTINEL",
            version=crypto_sentinel.version,
            location="LOCAL",
            trigger_type="TASK_QUEUE",
            capabilities=crypto_sentinel.get_capabilities(),
            granted_capabilities=[g.model_dump() for g in crypto_sentinel.get_capability_grants()],
        )
        
        self.logger.info(f"Registered {len(self.task_router.get_registered_types())} agents")
    
    async def run(self):
        """Main polling loop."""
        self._running = True
        self.logger.info("Starting poll loop...")
        
        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                self.logger.error(f"Poll cycle error: {e}")
            
            # Wait before next poll
            await asyncio.sleep(settings.poll_interval_seconds)
    
    async def _poll_cycle(self):
        """Single polling cycle."""
        # Get supported agent types
        agent_types = self.task_router.get_registered_types()

        # Attempt to reclaim expired leases before picking up new work
        recovered = await self.api_client.recover_expired_leases()
        if recovered:
            self.logger.info(f"Recovered {recovered} expired leased tasks")

        # First try workflow steps
        workflow_step = await self.api_client.pickup_workflow_step(agent_types)
        if workflow_step:
            self._reset_idle_cycles(
                work_type="workflow step",
                work_id=f"{workflow_step.get('workflow_id')}:{workflow_step.get('step_id')}",
            )
            await self._execute_workflow_step(workflow_step)
            return
        
        # Try to pick up a task
        task = await self.api_client.pickup_task(agent_types)
        if task:
            self._reset_idle_cycles(
                work_type="task",
                work_id=task.get("task_id"),
            )
        
        if not task:
            self._record_idle_cycle()
            return
        
        # Execute task
        await self._execute_task(task)

    def _record_idle_cycle(self):
        """Track idle polling cycles and surface periodic health at INFO."""
        self._idle_cycles += 1
        self.logger.debug("No tasks available")

        if self._idle_cycles == 1 or self._idle_cycles % 5 == 0:
            self.logger.info(
                "Poller idle: no workflow steps or tasks available "
                f"(idle cycles: {self._idle_cycles}). Heartbeat is still active."
            )

    def _reset_idle_cycles(self, work_type: str, work_id: Optional[str]):
        """Reset idle tracking once new work arrives."""
        if self._idle_cycles:
            identifier = f" {work_id}" if work_id else ""
            self.logger.info(
                f"Received {work_type}{identifier} after {self._idle_cycles} idle cycle(s)"
            )
        self._idle_cycles = 0
    
    async def _execute_task(self, task: dict):
        """
        Execute a picked up task with error recovery.
        
        Phase 10: Enhanced with error recovery tracking.
        """
        task_id = task["task_id"]
        agent_target = task["agent_target"]
        payload = task["payload"]

        # Fetch and attach latest agent config (version-aware)
        agent_config = None
        try:
            agent_config = await self.api_client.get_agent_config(agent_target)
            previous_version = self._agent_configs.get(agent_target, {}).get("version")
            current_version = agent_config.get("version")
            if previous_version and current_version != previous_version:
                self.logger.info(
                    f"Reloading config for {agent_target}: {previous_version} -> {current_version}"
                )
            self._agent_configs[agent_target] = agent_config
            payload = {**payload, "agent_config": agent_config}
        except Exception as e:
            self.logger.warning(f"Could not fetch config for {agent_target}: {e}")
        
        self._current_task = task_id
        
        # Check if we should even try (error recovery)
        if not self.error_recovery.should_retry(agent_target):
            self.logger.warning(
                f"Skipping task {task_id} for {agent_target} - "
                f"max consecutive failures reached"
            )
            await self.api_client.update_task_status(
                task_id,
                "FAILED",
                error_message=f"Agent {agent_target} is temporarily disabled due to consecutive failures"
            )
            return

        lease_task = asyncio.create_task(self._renew_lease_loop(task_id))
        try:
            # Update status to IN_PROGRESS
            await self.api_client.update_task_status(task_id, "IN_PROGRESS")
            
            # Route and execute
            result = await asyncio.wait_for(
                self.task_router.route_task(task_id, agent_target, payload),
                timeout=settings.task_timeout_seconds
            )
            
            # Update status based on result
            if result.success:
                await self.api_client.update_task_status(
                    task_id,
                    "COMPLETED",
                    result=result.to_dict()
                )
                # Record success (resets failure count)
                self.error_recovery.record_success(agent_target)
            else:
                await self.api_client.update_task_status(
                    task_id,
                    "FAILED",
                    error_message=result.error
                )
                # Record failure
                self.error_recovery.record_failure(agent_target, result.error or "Unknown error")
                
        except asyncio.TimeoutError:
            error_msg = "Task execution timed out"
            self.logger.error(f"Task {task_id} timed out")
            await self.api_client.update_task_status(
                task_id,
                "FAILED",
                error_message=error_msg
            )
            # Record timeout as failure
            self.error_recovery.record_failure(agent_target, error_msg)
            
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Task {task_id} failed: {error_msg}")
            await self.api_client.update_task_status(
                task_id,
                "FAILED",
                error_message=error_msg
            )
            # Record exception as failure
            self.error_recovery.record_failure(agent_target, error_msg)
        
        finally:
            lease_task.cancel()
            try:
                await lease_task
            except asyncio.CancelledError:
                pass
            self._current_task = None

    async def _renew_lease_loop(self, task_id: str):
        """Renew task lease periodically during execution."""
        interval = max(1, settings.lease_renewal_interval_seconds)
        while True:
            await asyncio.sleep(interval)
            success = await self.api_client.renew_task_lease(task_id)
            if not success:
                self.logger.warning(f"Lease renewal failed for task {task_id}")

    async def _execute_workflow_step(self, step: dict):
        """Execute a workflow step and update its status."""
        workflow_id = step["workflow_id"]
        step_id = step["step_id"]
        agent_target = step["agent_target"]
        payload = {
            "inputs": step.get("inputs", {}),
            "step_id": step_id,
            "workflow_id": workflow_id,
        }

        self._current_task = f"{workflow_id}:{step_id}"

        if not self.error_recovery.should_retry(agent_target):
            self.logger.warning(
                f"Skipping workflow step {step_id} for {agent_target} - "
                f"max consecutive failures reached"
            )
            await self.api_client.update_workflow_step(
                workflow_id,
                step_id,
                "FAILED",
                error=f"Agent {agent_target} is temporarily disabled due to consecutive failures",
            )
            return

        try:
            await self.api_client.update_workflow_step(workflow_id, step_id, "RUNNING")

            result = await asyncio.wait_for(
                self.task_router.route_workflow_step(workflow_id, {**step, **payload}),
                timeout=settings.task_timeout_seconds,
            )

            if result.success:
                await self.api_client.update_workflow_step(
                    workflow_id,
                    step_id,
                    "COMPLETED",
                    outputs=result.to_dict(),
                )
                self.error_recovery.record_success(agent_target)
            else:
                await self.api_client.update_workflow_step(
                    workflow_id,
                    step_id,
                    "FAILED",
                    error=result.error,
                )
                self.error_recovery.record_failure(agent_target, result.error or "Unknown error")

        except asyncio.TimeoutError:
            error_msg = "Workflow step execution timed out"
            self.logger.error(f"Workflow step {step_id} timed out")
            await self.api_client.update_workflow_step(
                workflow_id,
                step_id,
                "FAILED",
                error=error_msg,
            )
            self.error_recovery.record_failure(agent_target, error_msg)
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Workflow step {step_id} failed: {error_msg}")
            await self.api_client.update_workflow_step(
                workflow_id,
                step_id,
                "FAILED",
                error=error_msg,
            )
            self.error_recovery.record_failure(agent_target, error_msg)
        finally:
            self._current_task = None
    
    async def shutdown(self):
        """Graceful shutdown."""
        self.logger.info("Shutting down...")
        self._running = False
        
        await self.heartbeat_manager.stop()
        await self.api_client.close()
        
        self.logger.info("Shutdown complete")


async def main():
    """Main entry point."""
    poller = LocalPoller()
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        asyncio.create_task(poller.shutdown())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass
    
    try:
        await poller.initialize()
        await poller.run()
    except KeyboardInterrupt:
        await poller.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await poller.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
