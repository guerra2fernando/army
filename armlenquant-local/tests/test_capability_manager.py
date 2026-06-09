import pytest
from pathlib import Path

from agents.capability_manager import (
    CapabilityManager,
    CapabilityError,
    QuotaExceededError,
)
from models.capability import CapabilityGrant, CapabilityPolicy, CapabilityLimits


@pytest.mark.asyncio
async def test_file_write_policy_allows_project_paths(tmp_path: Path):
    """Capability manager allows writes to permitted project paths."""
    project_root = Path.home() / "Projects"
    target_dir = project_root / "cap_test"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "sample.txt"

    manager = CapabilityManager()
    manager.register_agent("TEST_AGENT", [CapabilityGrant(capability_id="file_write")])

    allowed = await manager.check_permission(
        "TEST_AGENT",
        "file_write",
        policy_params={
            "path": str(target_file),
            "size_mb": 0.1,
            "extension": ".txt",
        },
    )

    assert allowed is True


@pytest.mark.asyncio
async def test_blocked_path_is_rejected():
    """Blocked paths should raise a capability error."""
    secret_path = Path.home() / "secrets" / "secret.txt"
    manager = CapabilityManager()
    manager.register_agent(
        "TEST_AGENT",
        [
            CapabilityGrant(
                capability_id="file_write",
                policy_override=CapabilityPolicy(
                    allowed_paths=[f"{Path.home()}/**"],
                    blocked_paths=[f"{Path.home()}/secrets/**"],
                ),
            )
        ],
    )

    with pytest.raises(CapabilityError):
        await manager.check_permission(
            "TEST_AGENT",
            "file_write",
            policy_params={
                "path": str(secret_path),
                "size_mb": 0.1,
                "extension": ".txt",
            },
        )


@pytest.mark.asyncio
async def test_quota_enforced():
    """Quota enforcement stops excessive use."""
    project_root = Path.home() / "Projects"
    target_file = project_root / "quota_test" / "file.txt"

    manager = CapabilityManager()
    manager.register_agent(
        "LIMITED",
        [
            CapabilityGrant(
                capability_id="file_write",
                limits_override=CapabilityLimits(daily_quota=1),
            )
        ],
    )

    async def _noop(**kwargs):
        return "ok"

    await manager.execute_with_capability(
        "LIMITED",
        "file_write",
        _noop,
        path=str(target_file),
        size_mb=0.1,
        extension=".txt",
    )

    with pytest.raises(QuotaExceededError):
        await manager.execute_with_capability(
            "LIMITED",
            "file_write",
            _noop,
            path=str(target_file),
            size_mb=0.1,
            extension=".txt",
        )

