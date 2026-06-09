# Data Contracts (Logs, Events, Briefs)

Phase 5 introduces strict data contracts to prevent noisy dashboards and mixed content across collections.

## Collections

- **logs** – Internal-only audit trail. High volume, 30‑day TTL via `created_at`.
- **event_stream** – User-visible events for dashboard/notifications. 7‑day TTL via `created_at`.
- **daily_brief** – Immutable daily snapshots (no TTL).

## Schemas

### Logs (`logs`)
```json
{
  "log_id": "uuid-v4",
  "timestamp": "ISODate",
  "created_at": "ISODate",
  "level": "DEBUG|INFO|WARN|ERROR",
  "agent": "ORCHESTRATOR",
  "action": "TASK_ROUTED",
  "entity_type": "task|agent|workflow|capability",
  "entity_id": "uuid",
  "message": "...",
  "details": {},
  "request_id": "uuid",
  "duration_ms": 120,
  "error_stack": null,
  "internal_only": true
}
```

### Events (`event_stream`)
```json
{
  "event_id": "uuid-v4",
  "timestamp": "ISODate",
  "created_at": "ISODate",
  "event_type": "TASK_COMPLETED",
  "priority": "LOW|NORMAL|HIGH|URGENT",
  "title": "Job application submitted",
  "description": "Successfully applied...",
  "icon": "✅",
  "action_required": false,
  "action_url": "/tasks/123",
  "action_label": "View Details",
  "agent_name": "Job Hunter",
  "entity_type": "task",
  "entity_id": "uuid",
  "metadata": {},
  "notify_telegram": true,
  "notify_email": false,
  "broadcast": true,
  "payload": {}  // legacy dashboard payload
}
```

### Briefs (`daily_brief`)
```json
{
  "date": "2025-12-12",
  "version": "1.0",
  "crypto": { ... },
  "jobs": { ... },
  "projects": { ... },
  "system": { ... },
  "generated_at": "ISODate",
  "generation_duration_ms": 2500,
  "data_freshness": { "crypto": "ISODate" },
  "immutable": true
}
```

## Enforcement

- `app/utils/data_contracts.py` provides `DataContractLogger` with:
  - `log_internal()` – writes compliant audit logs.
  - `emit_event()` – user-facing events (broadcast-only).
  - `record_brief()` – upserts immutable daily briefs with required sections.
- Contract validation runs on every write; violations raise before persistence.

## Usage

- Orchestrator, workflow routes, notifications, and global exception handler now emit events through `DataContractLogger`.
- Crypto Sentinel writes briefs through `record_brief()` and emits `BRIEF_GENERATED`.
- Dashboard/Telegram read from `daily_brief` to avoid mixing with logs.









