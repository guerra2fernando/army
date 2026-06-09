"""
Tests for agent configuration versioning.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_active_config_backfilled(client: AsyncClient, test_agent: dict, agent_headers):
    """Existing agents should expose an active config after backfill."""
    headers = agent_headers(
        "GET",
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        "",
    )
    response = await client.get(
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_create_new_config_version(
    client: AsyncClient, test_agent: dict, auth_headers: dict, agent_headers
):
    """Creating a config version should bump config_version and activate it."""
    response = await client.post(
        f"/api/v1/agents/{test_agent['agent_name']}/config",
        json={
            "prompt_template": "You are a helpful agent.",
            "config_params": {"mode": "test"},
            "reason": "initial update",
        },
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    new_version = data["data"]["version"]
    assert new_version == "1.0.1"

    active_headers = agent_headers(
        "GET",
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        "",
    )
    active = await client.get(
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        headers=active_headers,
    )
    assert active.status_code == 200
    active_data = active.json()
    assert active_data["version"] == "1.0.1"
    assert active_data["is_active"] is True


@pytest.mark.asyncio
async def test_list_config_versions(client: AsyncClient, test_agent: dict, auth_headers: dict):
    """Config versions endpoint should return ordered versions."""
    # Create a new version first
    await client.post(
        f"/api/v1/agents/{test_agent['agent_name']}/config",
        json={
            "prompt_template": "New prompt",
            "config_params": {"foo": "bar"},
            "reason": "testing",
        },
        headers=auth_headers,
    )

    response = await client.get(
        f"/api/v1/agents/{test_agent['agent_name']}/config/versions",
        headers=auth_headers,
    )
    assert response.status_code == 200
    versions = response.json()
    assert isinstance(versions, list)
    assert len(versions) >= 2
    assert versions[0]["is_active"] is True


@pytest.mark.asyncio
async def test_rollback_config_version(
    client: AsyncClient, test_agent: dict, auth_headers: dict, agent_headers
):
    """Rollback should activate previous version and record it."""
    await client.post(
        f"/api/v1/agents/{test_agent['agent_name']}/config",
        json={
            "prompt_template": "Updated prompt",
            "config_params": {"foo": "bar"},
            "reason": "new version",
        },
        headers=auth_headers,
    )

    response = await client.post(
        f"/api/v1/agents/{test_agent['agent_name']}/config/rollback",
        params={"target_version": "1.0.0"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["config_version"] == "1.0.0"

    active_headers = agent_headers(
        "GET",
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        "",
    )
    active = await client.get(
        f"/api/v1/agents/{test_agent['agent_name']}/config/active",
        headers=active_headers,
    )
    assert active.status_code == 200
    assert active.json()["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_test_agent_config_endpoint(
    client: AsyncClient, test_agent: dict, auth_headers: dict
):
    """Test endpoint should validate without saving."""
    response = await client.post(
        f"/api/v1/agents/{test_agent['agent_name']}/config/test",
        json={
            "prompt_template": "You are validating config.",
            "config_params": {"mode": "dry-run"},
            "reason": "dry run",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["safe"] is True

