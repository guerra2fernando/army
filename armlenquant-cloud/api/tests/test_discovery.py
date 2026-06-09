from datetime import datetime, timedelta

import pytest

from app.db import Database


@pytest.mark.asyncio
async def test_run_job_discovery_creates_task_and_run(client, auth_headers):
    response = await client.post(
        "/api/v1/discovery/jobs/run",
        json={
            "roles": ["Growth Lead"],
            "locations": ["Remote"],
            "sources": ["lever"],
            "limit": 10,
            "profile_slug": "default",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"]
    assert data["task_id"]

    task = await Database.get_collection("task_queue").find_one({"task_id": data["task_id"]})
    assert task is not None
    assert task["agent_target"] == "JOB_HUNTER"

    run = await Database.get_collection("discovery_runs").find_one({"run_id": data["run_id"]})
    assert run is not None
    assert run["profile_slug"] == "default"


@pytest.mark.asyncio
async def test_completed_job_discovery_persists_opportunities(client, auth_headers, agent_headers):
    create = await client.post(
        "/api/v1/discovery/jobs/run",
        json={
            "roles": ["Growth Lead"],
            "locations": ["Remote"],
            "sources": ["greenhouse"],
            "profile_slug": "default",
        },
        headers=auth_headers,
    )
    task_id = create.json()["task_id"]

    body = {
        "status": "COMPLETED",
        "result": {
            "success": True,
            "data": {
                "jobs": [
                    {
                        "title": "Growth Lead",
                        "company": "Example Inc",
                        "location": "Remote",
                        "source": "greenhouse",
                        "url": "https://boards.greenhouse.io/example/jobs/123",
                    },
                    {
                        "title": "Growth Lead",
                        "company": "Example Inc",
                        "location": "Remote",
                        "source": "greenhouse",
                        "url": "https://boards.greenhouse.io/example/jobs/123?gh_jid=123",
                    },
                ]
            },
        },
    }
    response = await client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json=body,
        headers=agent_headers("PATCH", f"/api/v1/tasks/{task_id}/status", body),
    )
    assert response.status_code == 200

    opportunities = await Database.get_collection("opportunities").find({}).to_list(length=None)
    assert len(opportunities) == 1
    assert opportunities[0]["source_platform"] == "GREENHOUSE"
    assert opportunities[0]["profile_slug"] == "default"

    run = await Database.get_collection("discovery_runs").find_one({"run_id": create.json()["run_id"]})
    assert run["persisted_count"] == 1
    assert run["deduped_count"] == 1


@pytest.mark.asyncio
async def test_schedule_commercial_discovery_creates_scheduled_task(client, auth_headers):
    response = await client.post(
        "/api/v1/discovery/commercial/schedule",
        json={
            "business_slug": "lenquant",
            "personas": ["Founder"],
            "keywords": ["quant trading"],
            "locations": ["London"],
            "scheduled_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "recurring": {"pattern": "weekdays"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["scheduled_task_id"]
    task = await Database.get_collection("scheduled_tasks").find_one({"task_id": data["scheduled_task_id"]})
    assert task is not None
    assert task["agent_target"] == "COMMERCIAL_SCOUT"


@pytest.mark.asyncio
async def test_import_commercial_opportunities_and_list(client, auth_headers):
    imported = await client.post(
        "/api/v1/discovery/opportunities/import",
        json={
            "items": [
                {
                    "kind": "COMMERCIAL",
                    "lane": "LENQUANT",
                    "title": "Founder profile",
                    "person_name": "Jane Doe",
                    "company": "Acme Capital",
                    "location": "London",
                    "source_platform": "LINKEDIN",
                    "source_url": "https://www.linkedin.com/in/jane-doe/",
                    "business_slug": "lenquant",
                    "confidence": 0.82,
                }
            ]
        },
        headers=auth_headers,
    )
    assert imported.status_code == 200

    listed = await client.get(
        "/api/v1/discovery/opportunities?kind=COMMERCIAL&business_slug=lenquant",
        headers=auth_headers,
    )
    assert listed.status_code == 200
    data = listed.json()
    assert len(data) == 1
    assert data[0]["person_name"] == "Jane Doe"
    assert data[0]["lane"] == "LENQUANT"
