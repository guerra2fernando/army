"""
Cloud API Client
Handles all communication with the ArmLenQuant cloud server.
"""
import base64
import hashlib
import hmac
import httpx
import json
import time
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
from loguru import logger
from poller.config import get_settings

settings = get_settings()


class APIError(Exception):
    """API request error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class CloudAPIClient:
    """
    Client for ArmLenQuant Cloud API with HMAC signing and scoped token headers.
    """
    
    def __init__(self):
        self.base_url = settings.api_url.rstrip("/")
        self.agent_name = settings.agent_name
        self.agent_token = settings.agent_token
        self.hmac_key = settings.hmac_key
        self.key_version = settings.hmac_key_version
        self.worker_id = settings.worker_id

        cert = None
        if settings.mtls_cert_path and settings.mtls_key_path:
            cert = (settings.mtls_cert_path, settings.mtls_key_path)

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            verify=settings.ca_cert_path or True,
            cert=cert,
        )
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _sign_request(
        self,
        method: str,
        endpoint: str,
        body: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Create signed headers for a request."""
        timestamp = str(int(time.time()))
        nonce = str(uuid4())
        signing_string = f"{method.upper()}\n{endpoint}\n{timestamp}\n{nonce}\n{body}"
        signature = hmac.new(
            base64.b64decode(self.hmac_key.encode()),
            signing_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Agent": self.agent_name,
            "X-Timestamp": timestamp,
            "X-Nonce": nonce,
            "X-Signature": signature,
            "X-Key-Version": str(self.key_version),
            "X-Agent-Token": self.agent_token,
            "X-Worker-ID": self.worker_id,
        }
        if extra_headers:
            headers.update(extra_headers)
        return headers
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ) -> dict:
        """Make an API request with HMAC signing."""
        try:
            body_str = ""
            if data is not None:
                body_str = json.dumps(data, separators=(",", ":"), sort_keys=True, default=str)

            headers = self._sign_request(
                method=method,
                endpoint=endpoint,
                body=body_str,
                extra_headers=extra_headers,
            )

            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                content=body_str if body_str else None,
                headers=headers,
            )
            
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown error")
                raise APIError(response.status_code, error_detail)
            
            return response.json() if response.content else {}
            
        except httpx.ConnectError as e:
            logger.error(f"Connection error: {e}")
            raise APIError(0, f"Connection failed: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Request timeout: {e}")
            raise APIError(0, f"Request timeout: {e}")
    
    # =========================================================================
    # Task Operations
    # =========================================================================
    
    async def pickup_task(self, agent_targets: List[str]) -> Optional[dict]:
        """
        Pick up the next available task.
        
        Args:
            agent_targets: List of agent types this worker can handle
            
        Returns:
            Task data if available, None otherwise
        """
        try:
            response = await self._request(
                "POST",
                "/api/v1/tasks/pickup",
                data={
                    "worker_id": settings.worker_id,
                    "agent_targets": agent_targets
                }
            )
            
            if response:
                logger.info(f"Picked up task: {response.get('task_id')} for {response.get('agent_target')}")
                return response
            
            return None
            
        except APIError as e:
            if e.status_code == 404:
                return None  # No tasks available
            raise
    
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[dict] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update task status after execution.
        
        Args:
            task_id: Task identifier
            status: New status (IN_PROGRESS, COMPLETED, FAILED)
            result: Result data (for COMPLETED)
            error_message: Error message (for FAILED)
            
        Returns:
            True if update successful
        """
        try:
            await self._request(
                "PATCH",
                f"/api/v1/tasks/{task_id}/status",
                data={
                    "status": status,
                    "result": result,
                    "error_message": error_message
                }
            )
            
            logger.info(f"Updated task {task_id} status to {status}")
            return True
            
        except APIError as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    async def renew_task_lease(self, task_id: str) -> bool:
        """Renew a task lease while executing."""
        try:
            await self._request(
                "PATCH",
                f"/api/v1/tasks/{task_id}/lease",
            )
            logger.debug(f"Lease renewed for task {task_id}")
            return True
        except APIError as e:
            logger.warning(f"Failed to renew lease for {task_id}: {e}")
            return False

    async def recover_expired_leases(self) -> int:
        """Recover tasks with expired leases."""
        try:
            response = await self._request("POST", "/api/v1/tasks/recover_leases")
            return int(response.get("data", {}).get("recovered", 0))
        except APIError as e:
            logger.warning(f"Failed to recover expired leases: {e}")
            return 0

    # =========================================================================
    # Workflow Operations
    # =========================================================================

    async def pickup_workflow_step(self, agent_targets: List[str]) -> Optional[dict]:
        """Pick up the next available workflow step for these agents."""
        try:
            response = await self._request(
                "POST",
                "/api/v1/workflows/steps/pickup",
                data={
                    "worker_id": settings.worker_id,
                    "agent_targets": agent_targets,
                },
            )
            if response:
                logger.info(
                    f"Picked up workflow step {response.get('step_id')} "
                    f"for workflow {response.get('workflow_id')}"
                )
                return response
            return None
        except APIError as e:
            if e.status_code == 404:
                return None
            logger.error(f"Failed to pick up workflow step: {e}")
            return None

    async def update_workflow_step(
        self,
        workflow_id: str,
        step_id: str,
        status: str,
        outputs: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update workflow step status after execution."""
        try:
            await self._request(
                "PATCH",
                f"/api/v1/workflows/{workflow_id}/steps/{step_id}",
                data={"status": status, "outputs": outputs, "error": error},
            )
            logger.info(
                f"Updated workflow {workflow_id} step {step_id} status to {status}"
            )
            return True
        except APIError as e:
            logger.error(f"Failed to update workflow step {step_id}: {e}")
            return False
    
    # =========================================================================
    # Agent Operations
    # =========================================================================
    
    async def register_agent(
        self,
        agent_name: str,
        version: str,
        location: str,
        trigger_type: str,
        capabilities: List[str],
        trigger_config: Optional[dict] = None,
        granted_capabilities: Optional[List[dict]] = None,
    ) -> dict:
        """Register an agent with the cloud."""
        return await self._request(
            "POST",
            "/api/v1/agents/register",
            data={
                "agent_name": agent_name,
                "version": version,
                "location": location,
                "trigger_type": trigger_type,
                "trigger_config": trigger_config,
                "capabilities": capabilities,
                "granted_capabilities": granted_capabilities or [],
            }
        )

    async def get_agent_config(self, agent_name: str) -> dict:
        """Get the currently active config version for an agent."""
        return await self._request(
            "GET",
            f"/api/v1/agents/{agent_name}/config/active",
        )
    
    async def send_heartbeat(
        self,
        agent_name: str,
        status: str = "HEALTHY",
        current_task: Optional[str] = None,
        metrics: Optional[dict] = None
    ) -> bool:
        """Send heartbeat to cloud."""
        try:
            await self._request(
                "POST",
                "/api/v1/agents/heartbeat",
                data={
                    "agent_name": agent_name,
                    "worker_id": settings.worker_id,
                    "status": status,
                    "current_task": current_task,
                    "metrics": metrics
                }
            )
            return True
        except APIError as e:
            logger.warning(f"Heartbeat failed: {e}")
            return False
    
    # =========================================================================
    # Health Check
    # =========================================================================
    
    async def health_check(self) -> bool:
        """Check if cloud API is reachable."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
