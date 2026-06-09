"""
MongoDB Database Connection
"""
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from loguru import logger
from app.config import get_settings

settings = get_settings()


class Database:
    """MongoDB database connection manager."""
    
    client: AsyncIOMotorClient = None
    db = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        logger.info("Connecting to MongoDB...")
        cls.client = AsyncIOMotorClient(settings.mongodb_uri)
        cls.db = cls.client[settings.mongodb_db_name]
        
        # Verify connection
        await cls.client.admin.command('ping')
        logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
        
        # Initialize collections and indexes
        await cls._init_collections()
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    async def _init_collections(cls):
        """Initialize collections with indexes."""
        
        # Users collection
        await cls.db.users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True),
            IndexModel([("created_at", DESCENDING)]),
        ])
        
        # Sessions collection
        await cls.db.sessions.create_indexes([
            IndexModel([("user_id", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ])
        
        # Task Queue collection
        await cls.db.task_queue.create_indexes([
            IndexModel([("status", ASCENDING), ("priority", DESCENDING), ("created_at", ASCENDING)]),
            IndexModel([("agent_target", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("worker_id", ASCENDING)]),
            IndexModel([("idempotency_key", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("lease_until", ASCENDING)]),
            IndexModel([("picked_up_by", ASCENDING), ("status", ASCENDING)]),
        ])
        
        # Agent Registry collection
        await cls.db.agent_registry.create_indexes([
            IndexModel([("agent_name", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("config_version", DESCENDING)]),
            IndexModel([("config_versions.version", DESCENDING)]),
            IndexModel([("config_versions.is_active", ASCENDING)]),
        ])

        # Schema Migrations collection
        await cls.db.schema_migrations.create_indexes([
            IndexModel([("migration_id", ASCENDING)], unique=True),
            IndexModel([("from_version", ASCENDING), ("to_version", ASCENDING)]),
            IndexModel([("applied_at", DESCENDING)]),
        ])
        
        # Logs collection (TTL: 30 days)
        await cls.db.logs.create_indexes([
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("agent", ASCENDING), ("level", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=2592000),
        ])
        
        # Event Stream collection (TTL: 7 days)
        await cls.db.event_stream.create_indexes([
            IndexModel([("timestamp", DESCENDING)]),
            IndexModel([("event_type", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=604800),
        ])

        # Capabilities collection (allowlist registry)
        await cls.db.capabilities.create_indexes([
            IndexModel([("capability_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
        ])

        # Secrets for agent signing keys (TTL on expiry)
        await cls.db.secrets.create_indexes([
            IndexModel([("agent_name", ASCENDING), ("key_version", DESCENDING)], unique=True),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ])

        # Scoped tokens for agents (TTL on expiry)
        await cls.db.access_tokens.create_indexes([
            IndexModel([("token_id", ASCENDING)], unique=True),
            IndexModel([("agent_name", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0),
        ])

        # Spawn budgets (orchestrator safety)
        await cls.db.spawn_budgets.create_indexes([
            IndexModel([("budget_id", ASCENDING)], unique=True),
            IndexModel([("scope_type", ASCENDING)]),
            IndexModel([("agent_type_filter", ASCENDING)]),
            IndexModel([("window_start", DESCENDING)]),
        ])

        # Orchestrator monitoring
        await cls.db.orchestrator_monitoring.create_indexes([
            IndexModel([("change_id", ASCENDING)]),
            IndexModel([("timestamp", DESCENDING)]),
        ])

        # System settings (kill switch flag, etc.)
        await cls.db.system_settings.create_indexes([
            IndexModel([("setting", ASCENDING)], unique=True),
        ])

        # Daily brief collection (immutable snapshots)
        await cls.db.daily_brief.create_indexes([
            IndexModel([("date", ASCENDING)], unique=True),
            IndexModel([("generated_at", DESCENDING)]),
        ])
        
        # Notifications collection (TTL: 30 days)
        await cls.db.notifications.create_indexes([
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("type", ASCENDING)]),
            IndexModel([("delivered", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=2592000),
        ])
        
        # Telegram users collection
        await cls.db.telegram_users.create_indexes([
            IndexModel([("telegram_user_id", ASCENDING)], unique=True),
            IndexModel([("chat_id", ASCENDING)]),
            IndexModel([("user_id", ASCENDING)]),
        ])

        # Task Master Plans collection
        await cls.db.task_master_plans.create_indexes([
            IndexModel([("task_id", ASCENDING)], unique=True),
            IndexModel([("project_name", ASCENDING)]),
            IndexModel([("scope", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            IndexModel([("approved_at", ASCENDING)]),
        ])

        # Task Phase Executions collection
        await cls.db.task_phase_executions.create_indexes([
            IndexModel([("task_id", ASCENDING), ("phase_number", ASCENDING)], unique=True),
            IndexModel([("task_id", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("started_at", DESCENDING)]),
            IndexModel([("completed_at", ASCENDING)]),
        ])

        # Task Execution Controls collection
        await cls.db.task_execution_controls.create_indexes([
            IndexModel([("task_id", ASCENDING), ("action", ASCENDING)]),
            IndexModel([("requested_at", DESCENDING)]),
            IndexModel([("applied_at", ASCENDING)]),
        ])

        # Workflows collection
        await cls.db.workflows.create_indexes([
            IndexModel([("workflow_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("steps.step_id", ASCENDING)]),
            IndexModel([("steps.agent_target", ASCENDING), ("steps.status", ASCENDING)]),
            IndexModel([("approval_state", ASCENDING)]),
            IndexModel([("approval_token", ASCENDING)]),
        ])

        # Scheduled tasks
        await cls.db.scheduled_tasks.create_indexes([
            IndexModel([("task_id", ASCENDING)], unique=True),
            IndexModel([("scheduled_time", ASCENDING), ("executed", ASCENDING)]),
            IndexModel([("agent_target", ASCENDING), ("scheduled_time", ASCENDING)]),
        ])

        # Discovery runs
        await cls.db.discovery_runs.create_indexes([
            IndexModel([("run_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("kind", ASCENDING), ("lane", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("task_id", ASCENDING)]),
            IndexModel([("scheduled_task_id", ASCENDING)]),
        ])

        # Opportunities
        await cls.db.opportunities.create_indexes([
            IndexModel([("opportunity_id", ASCENDING)], unique=True),
            IndexModel([("dedupe_key", ASCENDING)], unique=True),
            IndexModel([("kind", ASCENDING), ("lane", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("business_slug", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("profile_slug", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("source_platform", ASCENDING), ("last_seen_at", DESCENDING)]),
            IndexModel([("recrawl_after", ASCENDING)]),
        ])

        # Opportunity routes
        await cls.db.opportunity_routes.create_indexes([
            IndexModel([("route_id", ASCENDING)], unique=True),
            IndexModel([("opportunity_id", ASCENDING)], unique=True),
            IndexModel([("specialist", ASCENDING), ("lane", ASCENDING)]),
            IndexModel([("profile_binding.business_profile_slug", ASCENDING)]),
            IndexModel([("routing_method", ASCENDING), ("confidence", DESCENDING)]),
        ])

        # Review queue
        await cls.db.review_queue.create_indexes([
            IndexModel([("review_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("review_kind", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("lane", ASCENDING), ("target_persona", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("recommended_channel", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("opportunity_id", ASCENDING)]),
            IndexModel([("followup_plan_id", ASCENDING), ("followup_step", ASCENDING)]),
            IndexModel([("workflow_id", ASCENDING)]),
        ])

        # Send intents
        await cls.db.send_intents.create_indexes([
            IndexModel([("send_intent_id", ASCENDING)], unique=True),
            IndexModel([("idempotency_key", ASCENDING)], unique=True),
            IndexModel([("cooldown_key", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("status", ASCENDING), ("channel", ASCENDING)]),
            IndexModel([("dispatch_task_id", ASCENDING)]),
            IndexModel([("review_id", ASCENDING)]),
        ])

        # Send results
        await cls.db.send_results.create_indexes([
            IndexModel([("send_result_id", ASCENDING)], unique=True),
            IndexModel([("send_intent_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("channel", ASCENDING), ("delivered_at", DESCENDING)]),
        ])

        # Follow-up plans
        await cls.db.followup_plans.create_indexes([
            IndexModel([("followup_id", ASCENDING)], unique=True),
            IndexModel([("review_id", ASCENDING)], unique=True),
            IndexModel([("status", ASCENDING), ("next_action_at", ASCENDING)]),
            IndexModel([("opportunity_id", ASCENDING)]),
        ])

        # Operator profiles
        await cls.db.operator_profiles.create_indexes([
            IndexModel([("profile_id", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("slug", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("is_active", ASCENDING)]),
        ])

        # Business profiles
        await cls.db.business_profiles.create_indexes([
            IndexModel([("profile_id", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("slug", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("is_active", ASCENDING)]),
        ])

        # Commercial policies
        await cls.db.commercial_policies.create_indexes([
            IndexModel([("policy_id", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("slug", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("is_active", ASCENDING)]),
        ])

        # Uploaded profile assets
        await cls.db.profile_assets.create_indexes([
            IndexModel([("asset_id", ASCENDING)], unique=True),
            IndexModel([("owner_user_id", ASCENDING), ("asset_type", ASCENDING)]),
            IndexModel([("owner_user_id", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Intent contracts collection
        await cls.db.intent_contracts.create_indexes([
            IndexModel([("agent_name", ASCENDING), ("version", DESCENDING)], unique=True),
            IndexModel([("agent_name", ASCENDING)]),
        ])

        logger.info("Database collections initialized")

        # Seed default capability definitions (best-effort)
        try:
            from app.services.capability_registry import seed_default_capabilities
            await seed_default_capabilities(cls.db)
        except Exception as exc:  # pragma: no cover - defensive only
            logger.warning(f"Capability registry seed skipped: {exc}")

        # Backfill legacy agents with default config versions if needed
        await cls._backfill_agent_configs()
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name."""
        return cls.db[name]

    @classmethod
    async def _backfill_agent_configs(cls):
        """
        Ensure existing agents have a versioned config structure.
        This runs lightly on startup and skips agents already migrated.
        """
        agents = cls.db.agent_registry
        cursor = agents.find({"$or": [{"config_versions": {"$exists": False}}, {"config_version": {"$exists": False}}]})
        to_migrate = await cursor.to_list(length=None)

        for agent in to_migrate:
            legacy_config = {
                "version": "1.0.0",
                "prompt_template": agent.get("prompt_template", ""),
                "config_params": agent.get("config", {}),
                "schema_version": "1.0.0",
                "created_at": agent.get("created_at"),
                "created_by": agent.get("created_by", "SYSTEM"),
                "performance_baseline": agent.get("performance", {}),
                "is_active": True
            }

            await agents.update_one(
                {"_id": agent["_id"]},
                {
                    "$set": {
                        "config_version": "1.0.0",
                        "config_versions": [legacy_config],
                        "rollback_versions": [],
                        "last_rollback_at": None,
                    },
                    "$unset": {
                        "prompt_template": "",
                        "config": ""
                    }
                }
            )


# Convenience function
def get_db():
    """Get database instance."""
    return Database.db
