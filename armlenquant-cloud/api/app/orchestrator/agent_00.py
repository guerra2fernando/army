"""
Agent 00: The Orchestrator
Central intelligence for the ArmLenQuant system.
"""
import json
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from uuid import uuid4
from loguru import logger

from app.config import get_settings
from app.db import Database
from app.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, TASK_GENERATION_PROMPT
from app.orchestrator.intent_parser import IntentParser, EntityExtractor
from app.orchestrator.task_router import TaskRouter
from app.models.workflow import WorkflowStatus, WorkflowStepStatus

# Import unified LLM client from cloud API agents
from app.agents.llm_client import get_llm_client
from app.utils.time_parser import parse_time_from_text
from app.utils.data_contracts import contract_logger
from app.utils.intent_contracts import IntentContractService, ClarificationQuestion

settings = get_settings()


class OrchestratorResponse:
    """Structured response from the Orchestrator."""
    
    def __init__(
        self,
        success: bool,
        message: str,
        task_created: bool = False,
        task_id: Optional[str] = None,
        agent_target: Optional[str] = None,
        requires_clarification: bool = False,
        clarification_question: Optional[str] = None,
        data: Optional[dict] = None,
        workflow_id: Optional[str] = None,
        workflow_created: bool = False,
    ):
        self.success = success
        self.message = message
        self.task_created = task_created
        self.task_id = task_id
        self.agent_target = agent_target
        self.requires_clarification = requires_clarification
        self.clarification_question = clarification_question
        self.data = data or {}
        self.workflow_id = workflow_id
        self.workflow_created = workflow_created
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "task_created": self.task_created,
            "task_id": self.task_id,
            "agent_target": self.agent_target,
            "requires_clarification": self.requires_clarification,
            "clarification_question": self.clarification_question,
            "data": self.data,
            "workflow_id": self.workflow_id,
            "workflow_created": self.workflow_created,
        }


class Orchestrator:
    """
    Agent 00: The central orchestration intelligence.
    
    Responsibilities:
    - Parse user commands
    - Route to appropriate agents
    - Create and manage tasks
    - Provide system status
    - Coordinate multi-agent workflows
    """
    
    def __init__(
        self,
        llm_client = None,
        intent_parser: Optional[IntentParser] = None,
        task_router: Optional[TaskRouter] = None
    ):
        self.llm_client = llm_client or get_llm_client()
        self.intent_parser = intent_parser or IntentParser(llm_client=self.llm_client)
        self.task_router = task_router or TaskRouter()
        self.entity_extractor = EntityExtractor()
        self.logger = logger.bind(agent="ORCHESTRATOR")
        self.intent_contracts = IntentContractService()
    
    async def process_command(
        self,
        command: str,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> OrchestratorResponse:
        """
        Process a user command and route appropriately.
        
        Args:
            command: User's natural language command
            user_id: ID of the requesting user
            context: Optional additional context
            
        Returns:
            OrchestratorResponse with result
        """
        self.logger.info(f"Processing command: {command[:100]}...")
        
        try:
            # Step 1: Check for scheduling commands first
            scheduled_time = self._parse_scheduled_time(command)
            if scheduled_time:
                return await self._handle_scheduled_command(command, scheduled_time, user_id)

            # Step 2: Get relevant context from RAG
            rag_context = await self._get_rag_context(command, user_id)

            # Step 3: Parse intent
            intent = await self.intent_parser.parse(command, rag_context)
            
            # Step 3: Extract additional entities
            extracted_entities = self.entity_extractor.extract_all(command)
            intent["entities"] = {
                **intent.get("entities", {}),
                **extracted_entities
            }
            
            # Step 4: Check if clarification needed
            if intent.get("requires_clarification"):
                return OrchestratorResponse(
                    success=True,
                    message="I need more information.",
                    requires_clarification=True,
                    clarification_question=intent.get("clarification_question")
                )
            
            # Step 5: Route to agent
            routing = self.task_router.route(intent, command)
            
            # Step 6: Handle internal queries or create task
            if routing.get("internal"):
                return await self._handle_internal_action(routing, user_id)
            
            if not routing.get("target_agent"):
                return OrchestratorResponse(
                    success=False,
                    message="I couldn't determine how to handle that request.",
                    requires_clarification=True,
                    clarification_question="Could you be more specific about what you'd like me to do?"
                )
            
            # Step 7: Enforce intent contracts & collect clarifications/approvals
            parameters = routing.get("parameters", {})
            contract_result = await self.intent_contracts.validate(
                routing["target_agent"], parameters
            )

            if contract_result.get("errors"):
                return OrchestratorResponse(
                    success=False,
                    message=f"Invalid request: {contract_result['errors'][0]}",
                    requires_clarification=True,
                    clarification_question=contract_result["errors"][0],
                    data={"errors": contract_result["errors"]},
                )

            clarifications: List[ClarificationQuestion] = contract_result.get("clarifications", [])
            if clarifications:
                return OrchestratorResponse(
                    success=True,
                    message="I need a bit more information before proceeding.",
                    requires_clarification=True,
                    clarification_question=clarifications[0].question if clarifications else None,
                    data={
                        "clarifications": [
                            {
                                "question": q.question,
                                "options": q.options,
                                "required": q.required,
                            }
                            for q in clarifications
                        ],
                        "errors": contract_result.get("errors", []),
                    },
                )

            approval_required = bool(contract_result.get("needs_approval"))
            approval_reason = contract_result.get("approval_reason")
            if approval_required:
                parameters["requires_approval"] = True
                if approval_reason:
                    parameters["approval_reason"] = approval_reason
                parameters.setdefault(
                    "approval_context", contract_result.get("approval_context") or parameters
                )

            # Step 8: Decide workflow vs single task
            requires_workflow = (
                parameters.get("execute_phases")
                or parameters.get("workflow_steps")
                or intent.get("intent_category") == "PROJECTS"
                or approval_required
            )

            if requires_workflow:
                actions_split = contract_result.get("actions") or {"reversible": [], "irreversible": []}
                steps = parameters.get("workflow_steps") or self._build_steps_from_actions(
                    routing,
                    parameters,
                    actions_split,
                    approval_required,
                )
                workflow_id, approval_token = await self._create_workflow(
                    workflow_type=intent.get("intent_category", "CUSTOM"),
                    steps=steps,
                    user_id=user_id,
                    priority=parameters.get("priority", 5),
                    approval_required=bool(parameters.get("requires_approval", False)),
                    original_command=command,
                    approval_config=self._build_approval_config(parameters, approval_reason),
                    approval_reason=approval_reason,
                )

                if approval_required:
                    await self._notify_approval_needed(
                        workflow_id,
                        approval_token,
                        routing.get("target_agent"),
                        parameters,
                    )

                await self._log_event(
                    event_type="WORKFLOW_CREATED",
                    payload={
                        "workflow_id": workflow_id,
                        "command": command,
                        "user_id": user_id,
                        "steps": len(steps),
                    },
                )

                response_message = self._generate_response_message(
                    routing["target_agent"],
                    routing.get("action"),
                    parameters,
                )

                return OrchestratorResponse(
                    success=True,
                    message=f"{response_message} Workflow created.",
                    task_created=False,
                    workflow_created=True,
                    workflow_id=workflow_id,
                    agent_target=routing["target_agent"],
                    data={
                        "action": routing.get("action"),
                        "parameters": parameters,
                        "workflow_id": workflow_id,
                        "confidence": routing.get("confidence"),
                        "approval_required": approval_required,
                    },
                )

            # Step 8: Create single task
            task_id = await self._create_task(
                agent_target=routing["target_agent"],
                parameters=parameters,
                user_id=user_id,
                original_command=command
            )
            
            # Step 9: Log event
            await self._log_event(
                event_type="COMMAND_PROCESSED",
                payload={
                    "command": command,
                    "user_id": user_id,
                    "task_id": task_id,
                    "agent_target": routing["target_agent"],
                    "confidence": routing.get("confidence", 0)
                }
            )
            
            # Step 10: Generate user response
            response_message = self._generate_response_message(
                routing["target_agent"],
                routing["action"],
                parameters
            )
            
            return OrchestratorResponse(
                success=True,
                message=response_message,
                task_created=True,
                task_id=task_id,
                agent_target=routing["target_agent"],
                data={
                    "action": routing.get("action"),
                    "parameters": parameters,
                    "confidence": routing.get("confidence")
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            await self._log_event(
                event_type="COMMAND_ERROR",
                payload={
                    "command": command,
                    "user_id": user_id,
                    "error": str(e)
                }
            )
            return OrchestratorResponse(
                success=False,
                message=f"An error occurred: {str(e)}"
            )
    
    async def _get_rag_context(self, query: str, user_id: str = None) -> str:
        """Retrieve relevant context from knowledge base using semantic search."""
        try:
            # Use the full RAG knowledge base service
            from app.rag.knowledge_base import get_knowledge_base

            kb = get_knowledge_base()
            context = await kb.get_context(
                query=query,
                user_id=user_id,
                max_tokens=2000
            )

            self.logger.debug(f"RAG context retrieved: {len(context)} characters")
            return context

        except ImportError:
            self.logger.warning("RAG knowledge base not available, falling back to basic search")
            return await self._get_basic_rag_context(query)
        except Exception as e:
            self.logger.warning(f"RAG retrieval failed: {e}")
            return ""

    async def _get_basic_rag_context(self, query: str) -> str:
        """Fallback basic text search when full RAG is not available."""
        try:
            kb = Database.get_collection("knowledge_base")
            if kb is None:
                return ""

            # Ensure a text index exists before querying
            index_info = await kb.index_information()
            has_text_index = any(
                any(field_type == "text" for _, field_type in idx.get("key", []))
                for idx in index_info.values()
            )
            if not has_text_index:
                try:
                    await kb.create_index(
                        [("content", "text"), ("title", "text")],
                        name="knowledge_text_index"
                    )
                    has_text_index = True
                except Exception as index_error:
                    self.logger.warning(f"Text search disabled; index missing: {index_error}")
                    return ""

            # Simple text search as fallback
            cursor = kb.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(3)

            results = await cursor.to_list(length=3)
            if results:
                return "\n".join([r.get("content", "") for r in results])
            return ""
        except Exception as e:
            self.logger.warning(f"Basic RAG retrieval failed: {e}")
            return ""
    
    async def _create_task(
        self,
        agent_target: str,
        parameters: dict,
        user_id: str,
        original_command: str
    ) -> str:
        """Create a task in the queue."""
        tasks = Database.get_collection("task_queue")
        
        task_id = str(uuid4())

        def _summarize_title(text: str) -> str:
            TITLE_MAX_LEN = 35
            if not isinstance(text, str):
                return f"{agent_target.title()} Task"
            import re
            tokens = re.findall(r"[A-Za-z0-9@#\+\-&']+", text.strip())
            if not tokens:
                return f"{agent_target.title()} Task"
            candidate = " ".join(tokens[:8]).title()
            if len(candidate) > TITLE_MAX_LEN:
                candidate = candidate[: TITLE_MAX_LEN - 3].rstrip() + "..."
            return candidate or f"{agent_target.title()} Task"

        title_source = (
            parameters.get("instruction")
            or parameters.get("description")
            or parameters.get("query")
            or original_command
            or f"{agent_target.title()} Task"
        )
        title = _summarize_title(title_source)
        task_doc = {
            "_id": task_id,
            "task_id": task_id,
            "agent_target": agent_target,
            "payload": {
                **parameters,
                "original_command": original_command
            },
            "title": title,
            "status": "PENDING",
            "priority": 5,
            "worker_id": None,
            "retry_count": 0,
            "max_retries": 3,
            "error_log": [],
            "result": None,
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await tasks.insert_one(task_doc)
        self.logger.info(f"Created task {task_id} for {agent_target}")
        
        return task_id

    def _build_steps_from_actions(
        self,
        routing: dict,
        parameters: dict,
        actions_split: dict,
        approval_required: bool,
    ) -> List[dict]:
        """Build workflow steps ensuring reversible actions run before approvals."""
        steps: List[dict] = []

        for action in actions_split.get("reversible", []):
            steps.append(
                {
                    "name": action.get("name") or routing.get("action") or "reversible_action",
                    "agent_target": routing["target_agent"],
                    "inputs": {**parameters, **action.get("inputs", {})},
                    "approval_required": False,
                }
            )

        irreversible_actions = actions_split.get("irreversible") or []
        for action in irreversible_actions:
            steps.append(
                {
                    "name": action.get("name") or routing.get("action") or "execute",
                    "agent_target": routing["target_agent"],
                    "inputs": {**parameters, **action.get("inputs", {})},
                    "approval_required": True,
                }
            )

        if not steps:
            steps.append(
                {
                    "name": routing.get("action") or "execute",
                    "agent_target": routing["target_agent"],
                    "inputs": parameters,
                    "approval_required": approval_required,
                }
            )

        return steps

    def _build_approval_config(self, parameters: dict, reason: Optional[str]) -> dict:
        """Assemble a lightweight approval config block."""
        approval_context = parameters.get("approval_context") or {}
        return {
            "approval_type": "HUMAN",
            "approver_roles": ["user"],
            "timeout_hours": 24,
            "approval_message": parameters.get("approval_message")
            or "Please review this request before execution.",
            "approval_context": approval_context,
            "reason": reason,
        }

    async def _notify_approval_needed(
        self,
        workflow_id: str,
        approval_token: Optional[str],
        agent: Optional[str],
        parameters: dict,
    ) -> None:
        """Send optional approval prompts via Telegram/Dashboard."""
        if not approval_token:
            return
        try:
            from app.notifications.service import get_notification_service

            service = get_notification_service()
            await service.send_workflow_approval_request(
                workflow_id=workflow_id,
                approval_token=approval_token,
                approval_config=self._build_approval_config(parameters, parameters.get("approval_reason")),
                agent=agent or "UNKNOWN",
            )
        except Exception as exc:  # pragma: no cover - best effort
            self.logger.warning(f"Approval notification failed: {exc}")

    async def _create_workflow(
        self,
        workflow_type: str,
        steps: List[dict],
        user_id: str,
        priority: int,
        approval_required: bool,
        original_command: str,
        approval_config: Optional[dict] = None,
        approval_reason: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """Create a workflow document with step definitions."""
        workflows = Database.get_collection("workflows")
        workflow_id = str(uuid4())

        step_docs = []
        for step in steps:
            step_docs.append(
                {
                    "step_id": str(uuid4()),
                    "name": step.get("name") or "execute",
                    "agent_target": step.get("agent_target"),
                    "status": WorkflowStepStatus.PENDING.value,
                    "task_id": step.get("task_id"),
                    "inputs": step.get("inputs", {}),
                    "outputs": None,
                    "started_at": None,
                    "completed_at": None,
                    "error": None,
                    "worker_id": None,
                    "approval_required": bool(step.get("approval_required", False)),
                    "approval_state": "PENDING" if step.get("approval_required") else "APPROVED",
                    "approval_context": step.get("inputs", {}),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )

        needs_approval = approval_required or any(s.get("approval_required") for s in steps)
        approval_token = str(uuid4()) if needs_approval else None
        approval_state = "PENDING" if approval_token else "APPROVED"

        workflow_doc = {
            "_id": workflow_id,
            "workflow_id": workflow_id,
            "type": workflow_type or "CUSTOM",
            "status": WorkflowStatus.PENDING.value,
            "current_step": 0,
            "steps": step_docs,
            "approval_required": approval_required,
            "approved_by": None,
            "approval_state": approval_state,
            "approval_token": approval_token,
            "approval_config": approval_config or self._build_approval_config({}, approval_reason),
            "approval_reason": approval_reason,
            "approval_requested_at": datetime.utcnow() if approval_token else None,
            "resume_token": None,
            "created_by": user_id,
            "priority": priority,
            "related_tasks": [],
            "parent_workflow": None,
            "metadata": {"original_command": original_command},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        await workflows.insert_one(workflow_doc)
        self.logger.info(f"Created workflow {workflow_id} with {len(step_docs)} step(s)")
        return workflow_id, approval_token
    
    async def _handle_internal_action(
        self,
        routing: dict,
        user_id: str
    ) -> OrchestratorResponse:
        """Handle system-level queries internally."""
        action = routing.get("action")
        
        if action == "system_status":
            status = await self._get_system_status()
            return OrchestratorResponse(
                success=True,
                message="Here's the current system status.",
                data=status
            )
        
        if action == "show_capabilities":
            return OrchestratorResponse(
                success=True,
                message=self._get_capabilities_message(),
                data={"capabilities": self.task_router.AGENT_ACTIONS}
            )
        
        if action == "list_agents":
            agents = await self._get_agents_list()
            return OrchestratorResponse(
                success=True,
                message="Here are the registered agents.",
                data={"agents": agents}
            )
        
        return OrchestratorResponse(
            success=False,
            message="I'm not sure how to handle that system request."
        )
    
    async def _get_system_status(self) -> dict:
        """Get current system status."""
        try:
            agents = Database.get_collection("agent_registry")
            tasks = Database.get_collection("task_queue")
            
            agent_count = await agents.count_documents({})
            active_agents = await agents.count_documents({"status": "ACTIVE"})
            pending_tasks = await tasks.count_documents({"status": "PENDING"})
            in_progress = await tasks.count_documents({"status": "IN_PROGRESS"})
            
            return {
                "status": "HEALTHY",
                "agents": {
                    "total": agent_count,
                    "active": active_agents
                },
                "tasks": {
                    "pending": pending_tasks,
                    "in_progress": in_progress
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"status": "ERROR", "error": str(e)}
    
    async def _get_agents_list(self) -> list:
        """Get list of registered agents."""
        try:
            agents = Database.get_collection("agent_registry")
            cursor = agents.find({})
            results = await cursor.to_list(length=100)
            return [
                {
                    "name": a.get("agent_name"),
                    "status": a.get("status"),
                    "location": a.get("location"),
                    "version": a.get("version"),
                    "config_version": a.get("config_version")
                }
                for a in results
            ]
        except Exception as e:
            self.logger.error(f"Failed to get agents list: {e}")
            return []
    
    # =====================================================================
    # Configuration versioning helpers
    # =====================================================================

    async def get_agent_config(self, agent_name: str) -> dict:
        """Return the active configuration for an agent."""
        agents = Database.get_collection("agent_registry")
        agent = await agents.find_one({"agent_name": agent_name})
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        config_versions = agent.get("config_versions", [])
        active = next((v for v in config_versions if v.get("is_active")), None)
        if active:
            return active

        # Fallback legacy shape
        return {
            "prompt_template": agent.get("prompt_template", ""),
            "config_params": agent.get("config", {}),
            "version": agent.get("config_version", "legacy"),
            "schema_version": "1.0.0",
        }

    async def improve_agent_prompt(self, agent_name: str, improvement: str) -> dict:
        """
        Create a new config version for an agent with safety validation.
        This mirrors the API behavior for orchestrated prompt evolution.
        """
        agents = Database.get_collection("agent_registry")
        agent = await agents.find_one({"agent_name": agent_name})
        if not agent:
            return {"error": f"Agent {agent_name} not found"}

        current_config = await self.get_agent_config(agent_name)
        new_version = self._increment_version(current_config.get("version") or agent.get("config_version") or "0.0.0")
        new_prompt = await self._generate_improved_prompt(
            current_config.get("prompt_template", ""),
            improvement
        )

        test_result = await self._test_config_safety(
            agent_name,
            new_prompt,
            current_config.get("config_params", {})
        )

        if not test_result.get("safe"):
            return {"error": "Config change failed safety test", "details": test_result}

        new_config_version = {
            "version": new_version,
            "prompt_template": new_prompt,
            "config_params": current_config.get("config_params", {}),
            "schema_version": current_config.get("schema_version", "1.0.0"),
            "created_at": datetime.utcnow(),
            "created_by": "ORCHESTRATOR",
            "performance_baseline": await self._measure_performance_baseline(agent_name),
            "is_active": False
        }

        await agents.update_one(
            {"agent_name": agent_name},
            {
                "$push": {"config_versions": new_config_version},
                "$set": {"config_version": new_version}
            }
        )

        await self._activate_config_version(agent_name, new_version)

        return {"new_version": new_version, "status": "ACTIVATED"}

    async def _activate_config_version(self, agent_name: str, version: str) -> None:
        """Activate a specific config version."""
        agents = Database.get_collection("agent_registry")
        agent = await agents.find_one({"agent_name": agent_name})
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")

        updated_versions = []
        for v in agent.get("config_versions", []):
            v["is_active"] = v.get("version") == version
            updated_versions.append(v)

        await agents.update_one(
            {"agent_name": agent_name},
            {"$set": {"config_versions": updated_versions, "config_version": version}}
        )

    async def _generate_improved_prompt(self, current_prompt: str, improvement: str) -> str:
        """
        Generate an improved prompt. Currently a simple concatenation plus cleanup;
        can be replaced with LLM-driven improvement later.
        """
        base = current_prompt.strip()
        improvement = improvement.strip()
        if not base:
            return improvement or "You are an ArmLenQuant agent."
        if not improvement:
            return base
        return f"{base}\n\n# Improvement\n{improvement}"

    async def _test_config_safety(self, agent_name: str, prompt: str, config_params: dict) -> dict:
        """Basic safety test for a candidate config."""
        if not prompt.strip():
            return {"safe": False, "reason": "Prompt cannot be empty"}
        if not isinstance(config_params, dict):
            return {"safe": False, "reason": "config_params must be an object"}
        return {"safe": True, "agent": agent_name}

    async def _measure_performance_baseline(self, agent_name: str) -> dict:
        """Placeholder for performance baseline calculation."""
        return {"measured_at": datetime.utcnow(), "agent": agent_name}

    def _increment_version(self, version: str) -> str:
        """Increment semantic version (patch)."""
        try:
            major, minor, patch = [int(x) for x in (version or "0.0.0").split(".")]
            patch += 1
            return f"{major}.{minor}.{patch}"
        except Exception:
            return "1.0.0"
    
    def _get_capabilities_message(self) -> str:
        """Generate capabilities description."""
        return """Here's what I can help you with:

**📈 Crypto Intelligence** (via Crypto Sentinel)
- Get market overview and trading signals
- Analyze specific cryptocurrencies
- Generate morning briefs

**💼 Job Hunting** (via Job Hunter)
- Search for job opportunities
- Generate tailored resumes
- Create cover letters
- Research companies

**🛠️ Project Development** (via Ideas Machine)
- Analyze project ideas
- Scaffold new projects
- Recommend tech stacks
- Generate documentation

**🔧 System Operations**
- Check system status
- View agent health
- Manage tasks

Just tell me what you'd like to do!"""
    
    def _generate_response_message(
        self,
        agent: str,
        action: str,
        parameters: dict
    ) -> str:
        """Generate a user-friendly response message."""
        
        messages = {
            "JOB_HUNTER": {
                "search_jobs": "🔍 Starting job search. I'll look for opportunities matching your criteria.",
                "generate_resume": "📝 Generating a tailored resume for you.",
                "generate_cover_letter": "✍️ Creating a personalized cover letter.",
                "research_company": "🏢 Researching the company for you.",
                "default": "💼 Job Hunter is on it!"
            },
            "CRYPTO_SENTINEL": {
                "morning_brief": "📊 Generating your crypto morning brief.",
                "analyze_asset": "🔎 Analyzing the requested assets.",
                "get_signals": "📈 Fetching the latest trading signals.",
                "market_overview": "📉 Getting market overview for you.",
                "default": "🎯 Crypto Sentinel is analyzing the markets."
            },
            "IDEAS_MACHINE": {
                "scaffold": "🏗️ Scaffolding your new project.",
                "analyze": "💡 Analyzing your project idea.",
                "recommend_stack": "🔧 Recommending tech stack for your project.",
                "default": "🛠️ Ideas Machine is working on it!"
            },
            "META_BUILDER": {
                "create_agent": "🤖 Creating a new agent for you.",
                "modify_agent": "🔧 Modifying the agent as requested.",
                "default": "🤖 Meta Builder is generating code."
            }
        }
        
        agent_messages = messages.get(agent, {})
        return agent_messages.get(action, agent_messages.get("default", "Task created successfully."))
    
    async def _log_event(self, event_type: str, payload: dict):
        """Log an event to the event stream."""
        try:
            title = payload.get("title") if isinstance(payload, dict) else None
            await contract_logger.emit_event(
                event_type=event_type,
                title=title or event_type.replace("_", " ").title(),
                description=payload.get("description") if isinstance(payload, dict) else None,
                priority=payload.get("priority", "NORMAL") if isinstance(payload, dict) else "NORMAL",
                agent_name=payload.get("agent_target") if isinstance(payload, dict) else None,
                entity_type=payload.get("entity_type") if isinstance(payload, dict) else None,
                entity_id=payload.get("task_id") if isinstance(payload, dict) else None,
                payload=payload if isinstance(payload, dict) else {"data": payload},
            )
        except Exception as e:
            self.logger.warning(f"Failed to log event: {e}")

    def _parse_scheduled_time(self, command: str) -> Optional[datetime]:
        """Parse scheduled time from command if present."""
        return parse_time_from_text(command, timezone="Asia/Tbilisi")

    def _parse_recurring_pattern(self, command: str) -> Optional[Dict[str, Any]]:
        """Parse recurring patterns from command (e.g., 'every weekday')."""
        command_lower = command.lower()

        # Check for weekday patterns
        weekday_patterns = [
            r'\bevery\s+(weekday|business\s+day|work\s+day)',
            r'\bweekdays?\s+at\b',
            r'\bdaily\s+(except\s+weekends?|on\s+weekdays?)',
            r'\bmonday\s+through\s+friday\b',
            r'\bmon-fri\b'
        ]

        for pattern in weekday_patterns:
            if re.search(pattern, command_lower):
                return {"pattern": "weekdays"}

        return None

    async def _handle_scheduled_command(
        self,
        command: str,
        scheduled_time: datetime,
        user_id: str
    ) -> OrchestratorResponse:
        """Handle commands that should be scheduled for later execution."""
        try:
            # Extract the actual command without the time part
            # Remove time-related phrases from the command
            cleaned_command = re.sub(
                r'\b(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|in\s+\d+\s+(?:minute|hour|min|hr)s?|today\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|tomorrow\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2}(?::\d{2})?\s*(?:am|pm))\b',
                '',
                command,
                flags=re.IGNORECASE
            ).strip()

            # Check for recurring patterns
            recurring = self._parse_recurring_pattern(command)

            # If the cleaned command is too short, use the original
            if len(cleaned_command) < 10:
                cleaned_command = command

            # Parse the cleaned command to determine what to do
            rag_context = await self._get_rag_context(cleaned_command, user_id)
            intent = await self.intent_parser.parse(cleaned_command, rag_context)
            routing = self.task_router.route(intent, cleaned_command)

            if not routing.get("target_agent"):
                return OrchestratorResponse(
                    success=False,
                    message="I understood you want to schedule something, but I couldn't determine what to do."
                )

            # Create scheduled task
            scheduled_task_id = await self._create_scheduled_task(
                agent_target=routing["target_agent"],
                parameters=routing["parameters"],
                scheduled_time=scheduled_time,
                user_id=user_id,
                original_command=command,
                title=f"Scheduled: {cleaned_command[:50]}..." + (" (Recurring)" if recurring else ""),
                recurring=recurring
            )

            # Format the scheduled time for display
            time_str = scheduled_time.strftime("%H:%M")

            # Add recurring info to message
            recurring_info = " (recurring on weekdays)" if recurring else ""

            return OrchestratorResponse(
                success=True,
                message=f"✅ Scheduled task for {time_str}{recurring_info}: {routing['target_agent']} will {routing.get('action', 'execute')} your request.",
                task_created=True,
                task_id=scheduled_task_id,
                data={
                    "scheduled_time": scheduled_time.isoformat(),
                    "action": routing.get("action"),
                    "agent": routing.get("target_agent"),
                    "recurring": recurring
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling scheduled command: {e}")
            return OrchestratorResponse(
                success=False,
                message="Sorry, I had trouble scheduling that task."
            )

    async def _create_scheduled_task(
        self,
        agent_target: str,
        parameters: Dict[str, Any],
        scheduled_time: datetime,
        user_id: str,
        original_command: str,
        title: str,
        recurring: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a scheduled task in the database."""
        scheduled_tasks = Database.get_collection("scheduled_tasks")

        task_id = str(uuid4())

        await scheduled_tasks.insert_one({
            "_id": task_id,
            "task_id": task_id,
            "agent_target": agent_target,
            "payload": parameters,
            "scheduled_time": scheduled_time,
            "title": title,
            "original_command": original_command,
            "created_by": user_id,
            "created_at": datetime.utcnow(),
            "executed": False,
            "cancelled": False,
            "executed_at": None,
            "priority": 5,
            "recurring": recurring,  # {"pattern": "weekdays", "next_run": datetime}
            "last_scheduled": None
        })

        self.logger.info(f"Created scheduled task: {task_id} for {scheduled_time}")
        return task_id


# Singleton instance
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def reset_orchestrator():
    """Reset the orchestrator singleton (for testing)."""
    global _orchestrator
    _orchestrator = None

