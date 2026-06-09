"""
Tests for Task Queue Endpoints
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
from uuid import uuid4

from app.db import Database


class TestCreateTask:
    """Tests for task creation."""

    @pytest.mark.asyncio
    async def test_create_task_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test successful task creation."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "JOB_HUNTER",
                "payload": {"action": "search", "query": "python developer"},
                "priority": 7
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["agent_target"] == "JOB_HUNTER"
        assert data["status"] == "PENDING"
        assert data["priority"] == 7

    @pytest.mark.asyncio
    async def test_create_task_default_priority(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test task creation with default priority."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "CRYPTO_SENTINEL",
                "payload": {}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 5  # Default priority

    @pytest.mark.asyncio
    async def test_create_task_invalid_agent_target(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test task creation with invalid agent target."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "INVALID_AGENT",
                "payload": {}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_invalid_priority(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test task creation with invalid priority (out of range)."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "JOB_HUNTER",
                "payload": {},
                "priority": 15  # Out of 1-10 range
            },
            headers=auth_headers
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_without_auth_fails(self, client: AsyncClient):
        """Test task creation without authentication fails."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "JOB_HUNTER",
                "payload": {}
            }
        )
        
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials

    @pytest.mark.asyncio
    async def test_create_task_stores_created_by(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test that created task stores the creating user."""
        response = await client.post(
            "/api/v1/tasks",
            json={
                "agent_target": "JOB_HUNTER",
                "payload": {}
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Verify in database
        tasks = Database.get_collection("task_queue")
        task = await tasks.find_one({"task_id": task_id})
        assert task["created_by"] == test_user["_id"]

    @pytest.mark.asyncio
    async def test_create_task_idempotent_within_window(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Duplicate task requests within the window should return the same task."""
        payload = {"action": "search", "query": "python developer"}
        first = await client.post(
            "/api/v1/tasks",
            json={"agent_target": "JOB_HUNTER", "payload": payload},
            headers=auth_headers,
        )
        second = await client.post(
            "/api/v1/tasks",
            json={"agent_target": "JOB_HUNTER", "payload": payload},
            headers=auth_headers,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["task_id"] == second.json()["task_id"]


class TestListTasks:
    """Tests for listing tasks."""

    @pytest.mark.asyncio
    async def test_list_tasks_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_task: dict
    ):
        """Test listing tasks."""
        response = await client.get("/api/v1/tasks", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_status(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_task: dict
    ):
        """Test filtering tasks by status."""
        response = await client.get(
            "/api/v1/tasks?status=PENDING",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(t["status"] == "PENDING" for t in data)

    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_agent(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_task: dict
    ):
        """Test filtering tasks by agent target."""
        response = await client.get(
            "/api/v1/tasks?agent_target=JOB_HUNTER",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert all(t["agent_target"] == "JOB_HUNTER" for t in data)

    @pytest.mark.asyncio
    async def test_list_tasks_respects_limit(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test that list respects limit parameter."""
        # Create multiple tasks
        tasks_coll = Database.get_collection("task_queue")
        for i in range(5):
            await tasks_coll.insert_one({
                "_id": str(uuid4()),
                "task_id": str(uuid4()),
                "agent_target": "JOB_HUNTER",
                "payload": {},
                "title": f"Test task {i+1}",
                "status": "PENDING",
                "priority": 5,
                "created_by": test_user["_id"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
        
        response = await client.get(
            "/api/v1/tasks?limit=3",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_tasks_without_auth_fails(self, client: AsyncClient):
        """Test listing tasks without authentication fails."""
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 403  # FastAPI returns 403 for missing credentials


class TestGetTask:
    """Tests for getting a specific task."""

    @pytest.mark.asyncio
    async def test_get_task_success(
        self, client: AsyncClient, test_user: dict, auth_headers: dict, test_task: dict
    ):
        """Test getting a specific task."""
        response = await client.get(
            f"/api/v1/tasks/{test_task['task_id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == test_task["task_id"]
        assert data["agent_target"] == test_task["agent_target"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_task_fails(
        self, client: AsyncClient, test_user: dict, auth_headers: dict
    ):
        """Test getting non-existent task returns 404."""
        response = await client.get(
            "/api/v1/tasks/nonexistent-task-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTaskPickup:
    """Tests for task pickup (agent-facing)."""

    @pytest.mark.asyncio
    async def test_pickup_task_success(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Test successful task pickup by agent."""
        response = await client.post(
            "/api/v1/tasks/pickup",
            json={
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["JOB_HUNTER"]
            },
            headers=agent_headers(
                "POST",
                "/api/v1/tasks/pickup",
                {
                    "worker_id": "TEST_WORKER_01",
                    "agent_targets": ["JOB_HUNTER"]
                },
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == test_task["task_id"]
        assert data["agent_target"] == "JOB_HUNTER"
        assert "payload" in data

    @pytest.mark.asyncio
    async def test_pickup_updates_task_status(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Test that pickup updates task status to PICKED_UP."""
        pickup_body = {
            "worker_id": "TEST_WORKER_01",
            "agent_targets": ["JOB_HUNTER"]
        }
        await client.post(
            "/api/v1/tasks/pickup",
            json=pickup_body,
            headers=agent_headers("POST", "/api/v1/tasks/pickup", pickup_body),
        )
        
        # Verify status updated
        tasks = Database.get_collection("task_queue")
        task = await tasks.find_one({"task_id": test_task["task_id"]})
        assert task["status"] == "PICKED_UP"
        assert task["worker_id"] == "TEST_WORKER_01"
        assert task["picked_up_at"] is not None

    @pytest.mark.asyncio
    async def test_pickup_no_tasks_returns_null(
        self, client: AsyncClient, agent_headers
    ):
        """Test pickup when no tasks available returns null."""
        response = await client.post(
            "/api/v1/tasks/pickup",
            json={
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["CRYPTO_SENTINEL"]  # No tasks for this agent
            },
            headers=agent_headers(
                "POST",
                "/api/v1/tasks/pickup",
                {
                    "worker_id": "TEST_WORKER_01",
                    "agent_targets": ["CRYPTO_SENTINEL"]
                },
            ),
        )
        
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_pickup_without_agent_headers_fails(self, client: AsyncClient):
        """Task pickup should reject unsigned requests."""
        response = await client.post(
            "/api/v1/tasks/pickup",
            json={
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["JOB_HUNTER"]
            }
        )
        
        assert response.status_code == 401  # Missing auth headers

    @pytest.mark.asyncio
    async def test_pickup_with_invalid_signature_fails(self, client: AsyncClient, agent_headers):
        """Task pickup should fail when signature is invalid."""
        bad_headers = agent_headers(
            "POST",
            "/api/v1/tasks/pickup",
            {
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["JOB_HUNTER"]
            },
        )
        bad_headers["X-Signature"] = "deadbeef"

        response = await client.post(
            "/api/v1/tasks/pickup",
            json={
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["JOB_HUNTER"]
            },
            headers=bad_headers
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_pickup_respects_priority(
        self, client: AsyncClient, test_user: dict, agent_headers
    ):
        """Test that pickup returns highest priority task first."""
        tasks = Database.get_collection("task_queue")
        
        # Create low priority task
        low_id = str(uuid4())
        await tasks.insert_one({
            "_id": low_id,
            "task_id": low_id,
            "agent_target": "IDEAS_MACHINE",
            "payload": {"type": "low"},
            "title": "Low priority task",
            "status": "PENDING",
            "priority": 3,
            "created_by": test_user["_id"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        # Create high priority task
        high_id = str(uuid4())
        await tasks.insert_one({
            "_id": high_id,
            "task_id": high_id,
            "agent_target": "IDEAS_MACHINE",
            "payload": {"type": "high"},
            "title": "High priority task",
            "status": "PENDING",
            "priority": 9,
            "created_by": test_user["_id"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })
        
        response = await client.post(
            "/api/v1/tasks/pickup",
            json={
                "worker_id": "TEST_WORKER_01",
                "agent_targets": ["IDEAS_MACHINE"]
            },
            headers=agent_headers(
                "POST",
                "/api/v1/tasks/pickup",
                {
                    "worker_id": "TEST_WORKER_01",
                    "agent_targets": ["IDEAS_MACHINE"]
                },
            ),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == 9
        assert data["payload"]["type"] == "high"

    @pytest.mark.asyncio
    async def test_pickup_sets_lease_and_execution_count(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Pickup should set lease and increment execution counter."""
        pickup_body = {
            "worker_id": "TEST_WORKER_01",
            "agent_targets": ["JOB_HUNTER"]
        }
        response = await client.post(
            "/api/v1/tasks/pickup",
            json=pickup_body,
            headers=agent_headers("POST", "/api/v1/tasks/pickup", pickup_body),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lease_until"] is not None

        tasks = Database.get_collection("task_queue")
        task = await tasks.find_one({"task_id": test_task["task_id"]})
        assert task["execution_count"] == 1


class TestUpdateTaskStatus:
    """Tests for updating task status."""

    @pytest.mark.asyncio
    async def test_update_task_completed(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Test marking task as completed."""
        body = {
            "status": "COMPLETED",
            "result": {"findings": ["result1", "result2"]}
        }
        response = await client.patch(
            f"/api/v1/tasks/{test_task['task_id']}/status",
            json=body,
            headers=agent_headers("PATCH", f"/api/v1/tasks/{test_task['task_id']}/status", body),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_update_task_failed_with_retry(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Test that failed task is retried if retries available."""
        body = {
            "status": "FAILED",
            "error_message": "Connection timeout"
        }
        response = await client.patch(
            f"/api/v1/tasks/{test_task['task_id']}/status",
            json=body,
            headers=agent_headers("PATCH", f"/api/v1/tasks/{test_task['task_id']}/status", body),
        )
        
        assert response.status_code == 200
        
        # Verify task was reset to PENDING for retry
        tasks = Database.get_collection("task_queue")
        task = await tasks.find_one({"task_id": test_task["task_id"]})
        assert task["status"] == "PENDING"
        assert task["retry_count"] == 1

    @pytest.mark.asyncio
    async def test_update_nonexistent_task_fails(
        self, client: AsyncClient, agent_headers
    ):
        """Test updating non-existent task returns 404."""
        body = {"status": "COMPLETED"}
        response = await client.patch(
            "/api/v1/tasks/nonexistent-task-id/status",
            json=body,
            headers=agent_headers("PATCH", "/api/v1/tasks/nonexistent-task-id/status", body),
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_stores_completed_at(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Test that completing task stores completed_at timestamp."""
        body = {"status": "COMPLETED", "result": {}}
        await client.patch(
            f"/api/v1/tasks/{test_task['task_id']}/status",
            json=body,
            headers=agent_headers("PATCH", f"/api/v1/tasks/{test_task['task_id']}/status", body),
        )
        
        tasks = Database.get_collection("task_queue")
        task = await tasks.find_one({"task_id": test_task["task_id"]})
        assert task["completed_at"] is not None


class TestLeaseManagement:
    """Tests for lease renewal and recovery."""

    @pytest.mark.asyncio
    async def test_renew_task_lease(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Lease renewal should extend lease for current worker."""
        pickup_body = {
            "worker_id": "TEST_WORKER_01",
            "agent_targets": ["JOB_HUNTER"]
        }
        pickup_headers = agent_headers(
            "POST",
            "/api/v1/tasks/pickup",
            pickup_body,
            extra={"X-Worker-ID": "TEST_WORKER_01"},
        )
        await client.post(
            "/api/v1/tasks/pickup",
            json=pickup_body,
            headers=pickup_headers
        )

        lease_headers = agent_headers(
            "PATCH",
            f"/api/v1/tasks/{test_task['task_id']}/lease",
            "",
            extra={"X-Worker-ID": "TEST_WORKER_01"},
        )
        response = await client.patch(
            f"/api/v1/tasks/{test_task['task_id']}/lease",
            headers=lease_headers
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_recover_expired_leases(
        self, client: AsyncClient, test_task: dict, agent_headers
    ):
        """Expired leases should be reclaimed to PENDING."""
        tasks = Database.get_collection("task_queue")
        await tasks.update_one(
            {"task_id": test_task["task_id"]},
            {
                "$set": {
                    "status": "PICKED_UP",
                    "lease_until": datetime.utcnow() - timedelta(minutes=1),
                    "picked_up_by": "OTHER_WORKER"
                }
            }
        )

        response = await client.post(
            "/api/v1/tasks/recover_leases",
            headers=agent_headers("POST", "/api/v1/tasks/recover_leases", ""),
        )

        assert response.status_code == 200
        recovered = response.json().get("data", {}).get("recovered", 0)
        assert recovered >= 1

        task = await tasks.find_one({"task_id": test_task["task_id"]})
        assert task["status"] == "PENDING"

