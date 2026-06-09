import pytest
from datetime import datetime

from app.db import Database


@pytest.mark.asyncio
async def test_create_and_get_workflow(client, auth_headers):
    payload = {
        "type": "PROJECT_GENERATION",
        "steps": [
            {
                "name": "analyze_requirements",
                "agent_target": "IDEAS_MACHINE",
                "inputs": {"description": "Build a fast API"},
            }
        ],
        "approval_required": False,
        "priority": 7,
    }

    response = await client.post("/api/v1/workflows", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"]
    assert data["status"] == "PENDING"
    workflow_id = data["workflow_id"]

    fetched = await client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
    assert fetched.status_code == 200
    fetched_data = fetched.json()
    assert fetched_data["workflow_id"] == workflow_id
    assert fetched_data["steps"][0]["name"] == "analyze_requirements"


@pytest.mark.asyncio
async def test_pickup_and_complete_step(client, auth_headers, agent_headers):
    # Create a workflow with a JOB_HUNTER step
    create_resp = await client.post(
        "/api/v1/workflows",
        json={
            "type": "JOB_FLOW",
            "steps": [
                {
                    "name": "search_jobs",
                    "agent_target": "JOB_HUNTER",
                    "inputs": {"query": "python developer"},
                }
            ],
        },
        headers=auth_headers,
    )
    workflow = create_resp.json()
    workflow_id = workflow["workflow_id"]

    pickup_body = {"worker_id": "worker-1", "agent_targets": ["JOB_HUNTER"]}
    pickup_resp = await client.post(
        "/api/v1/workflows/steps/pickup",
        json=pickup_body,
        headers=agent_headers("POST", "/api/v1/workflows/steps/pickup", pickup_body),
    )
    assert pickup_resp.status_code == 200
    step = pickup_resp.json()
    assert step
    step_id = step["step_id"]

    # Complete the step
    complete_body = {"status": "COMPLETED", "outputs": {"result": "ok"}}
    complete_resp = await client.patch(
        f"/api/v1/workflows/{workflow_id}/steps/{step_id}",
        json=complete_body,
        headers=agent_headers(
            "PATCH",
            f"/api/v1/workflows/{workflow_id}/steps/{step_id}",
            complete_body,
        ),
    )
    assert complete_resp.status_code == 200

    # Verify workflow is completed
    fetched = await client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_workflow_step_waits_for_approval(client, auth_headers, agent_headers):
    workflows = Database.get_collection("workflows")
    workflow_id = "wf-approval-1"
    step_id = "step-approval-1"

    await workflows.insert_one(
        {
            "_id": workflow_id,
            "workflow_id": workflow_id,
            "type": "JOB_FLOW",
            "status": "PENDING",
            "current_step": 0,
            "steps": [
                {
                    "step_id": step_id,
                    "name": "apply_job",
                    "agent_target": "JOB_HUNTER",
                    "status": "PENDING",
                    "inputs": {"action": "apply"},
                    "approval_required": True,
                    "approval_state": "PENDING",
                }
            ],
            "approval_required": True,
            "approval_state": "PENDING",
            "approval_token": "tok-1",
            "priority": 5,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": "user",
            "metadata": {},
        }
    )

    pickup_body = {"worker_id": "worker-1", "agent_targets": ["JOB_HUNTER"]}
    pickup_resp = await client.post(
        "/api/v1/workflows/steps/pickup",
        json=pickup_body,
        headers=agent_headers("POST", "/api/v1/workflows/steps/pickup", pickup_body),
    )
    assert pickup_resp.status_code == 200
    assert pickup_resp.json() is None

    approve_resp = await client.post(
        f"/api/v1/workflows/{workflow_id}/approve",
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200

    pickup_resp = await client.post(
        "/api/v1/workflows/steps/pickup",
        json=pickup_body,
        headers=agent_headers("POST", "/api/v1/workflows/steps/pickup", pickup_body),
    )
    assert pickup_resp.status_code == 200
    picked = pickup_resp.json()
    assert picked
    assert picked["workflow_id"] == workflow_id
