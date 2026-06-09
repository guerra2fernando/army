"""
Ideas Machine Agent
Complete project generator with AI-powered phase execution.
"""
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger

from agents.base_agent import BaseAgent, AgentResult
from models.capability import CapabilityGrant, CapabilityPolicy, CapabilityLimits
from .analyzer import IdeaAnalyzer
from .architect import SystemArchitect
from .scaffolder import ProjectScaffolder
from .phase_planner import PhasePlanner
from .code_generator import CodeGenerator
from .code_validator import CodeValidator
from .phase_executor import PhaseExecutor
from .prompt_generator import PromptGenerator
from .doc_generator import DocumentationGenerator
from .context_manager import ContextManager
from .models import IdeaInput


class IdeasMachineAgent(BaseAgent):
    """
    Ideas Machine - Complete Project Generator with AI-Powered Phase Execution

    Transforms raw project ideas into fully functional, production-ready applications
    through sequential AI API calls, each phase generating complete files with proper
    models, APIs, comprehensive tests, and automatic error detection/fixing.
    """

    def __init__(self, project_path: Optional[str] = None, llm_delay_seconds: float = 1.5):
        super().__init__("IDEAS_MACHINE", version="2.0.0")
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.llm_delay_seconds = llm_delay_seconds  # Delay between LLM calls to avoid rate limits
        self.logger.info(f"LLM delay set to {self.llm_delay_seconds}s between calls")

        # Core analysis components
        self.analyzer = IdeaAnalyzer()
        self.architect = SystemArchitect()

        # Complete project generation components
        self.phase_planner = PhasePlanner()
        self.code_generator = CodeGenerator()
        self.code_validator = CodeValidator(project_path=str(self.project_path))
        self.phase_executor = PhaseExecutor(str(self.project_path))
        self.prompt_generator = PromptGenerator()
        self.doc_generator = DocumentationGenerator(str(self.project_path))
        self.context_manager = ContextManager(str(self.project_path))

        # Legacy scaffolding (for backward compatibility)
        self.scaffolder = ProjectScaffolder()

    def get_capability_grants(self) -> list[CapabilityGrant]:
        """Capability allowlist for project scaffolding."""
        projects_root = str(Path.home() / "Projects")
        return [
            CapabilityGrant(
                capability_id="directory_create",
                policy_override=CapabilityPolicy(
                    allowed_paths=[projects_root, f"{projects_root}/**"]
                ),
            ),
            CapabilityGrant(
                capability_id="file_write",
                policy_override=CapabilityPolicy(
                    allowed_paths=[projects_root, f"{projects_root}/**"],
                    blocked_paths=[str(Path.home() / ".ssh/**"), str(Path.home() / "secrets/**")],
                    max_file_size_mb=200,
                ),
                limits_override=CapabilityLimits(daily_quota=200),
            ),
            CapabilityGrant(
                capability_id="command_execute",
                limits_override=CapabilityLimits(daily_quota=100),
            ),
        ]

    async def _delay_between_llm_calls(self):
        """Add configurable delay between LLM calls to prevent rate limiting."""
        if self.llm_delay_seconds > 0:
            self.logger.debug(f"Waiting {self.llm_delay_seconds}s between LLM calls...")
            import asyncio
            await asyncio.sleep(self.llm_delay_seconds)
    
    async def execute(self, payload: Dict[str, Any]) -> AgentResult:
        """Execute Ideas Machine task."""
        action = payload.get("action", "generate")

        self.logger.info(f"Executing action: {action}")

        try:
            if action == "generate":
                return await self._action_generate_complete_project(payload)
            elif action == "generate_plan":
                return await self._action_generate_plan(payload)
            elif action == "scaffold":
                return await self._action_scaffold(payload)  # Legacy
            elif action == "analyze":
                return await self._action_analyze(payload)
            elif action == "recommend_stack":
                return await self._action_recommend_stack(payload)
            elif action == "execute_phases":
                return await self._action_execute_phases(payload)
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
        except Exception as e:
            self.logger.error(f"Action {action} failed: {e}")
            return AgentResult(success=False, error=str(e))
    
    async def _action_scaffold(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Full scaffold action - analyze, architect, and generate project.
        
        Payload:
            description: str - Project idea description
            reference_urls: List[str] - Optional reference URLs
            constraints: Dict[str, str] - Optional constraints (budget, timeline)
            preferences: Dict[str, str] - Optional tech preferences
        """
        # Accept legacy payloads that used "idea" or "name" fields
        description = (
            payload.get("description")
            or payload.get("idea")
            or payload.get("name")
            or ""
        )
        
        if not description:
            return AgentResult(
                success=False,
                error="No project description provided"
            )
        
        # Create idea input
        idea_input = IdeaInput(
            description=description,
            reference_urls=payload.get("reference_urls", []),
            constraints=payload.get("constraints", {}),
            preferences=payload.get("preferences", {})
        )
        
        self.logger.info("Step 1/4: Analyzing idea...")
        analysis = await self.analyzer.analyze(idea_input)
        
        self.logger.info("Step 2/4: Recommending tech stack...")
        tech_stack = await self.architect.recommend_tech_stack(analysis)
        
        self.logger.info("Step 3/4: Designing architecture...")
        architecture = await self.architect.design_architecture(analysis, tech_stack)
        
        self.logger.info("Step 4/4: Scaffolding project...")
        scaffold = self.scaffolder.scaffold(analysis, tech_stack, architecture)
        
        self.logger.info(f"Project scaffolded successfully: {scaffold.project_name}")
        
        return AgentResult(
            success=True,
            data={
                "project_name": scaffold.project_name,
                "project_path": scaffold.project_path,
                "analysis": analysis.model_dump(),
                "tech_stack": tech_stack.model_dump(),
                "files_created": len(scaffold.files),
                "docs_created": len(scaffold.documentation),
                "directories_created": len(scaffold.directories)
            }
        )

    async def _action_generate_complete_project(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Complete project generation with planning approval workflow.

        Payload:
            description: str - Project idea description
            reference_urls: List[str] - Optional reference URLs
            constraints: Dict[str, str] - Optional constraints (budget, timeline)
            preferences: Dict[str, str] - Optional tech preferences
            project_path: str - Optional custom project path
            task_id: str - Task ID for plan association
            execute_phases: bool - Whether to execute phases automatically after approval (default: True)
        """
        # Accept legacy payloads that used "idea" or "name" fields
        description = (
            payload.get("description")
            or payload.get("idea")
            or payload.get("name")
            or ""
        )

        task_id = getattr(self, '_current_task_id', None) or payload.get("task_id", "")
        execute_phases = payload.get("execute_phases", True)

        if not description:
            return AgentResult(
                success=False,
                error="No project description provided"
            )

        self.logger.info("=== PROJECT GENERATION WITH PLANNING APPROVAL STARTED ===")
        self.logger.info(f"Project Description: {description}")
        self.logger.info(f"Task ID: {task_id}")

        try:
            # Always generate plan first - this is the new workflow
            self.logger.info("Step 1/2: Generating master project plan...")

            # Create plan payload with task_id
            plan_payload = {
                "description": description,
                "reference_urls": payload.get("reference_urls", []),
                "constraints": payload.get("constraints", {}),
                "preferences": payload.get("preferences", {}),
                "task_id": task_id
            }

            plan_result = await self._action_generate_plan(plan_payload)

            if not plan_result.success:
                return plan_result

            # If plan was generated successfully, check if we should auto-execute
            if execute_phases:
                self.logger.info("Step 2/2: Auto-executing approved plan...")
                return await self._execute_approved_plan(plan_result.data, payload)
            else:
                self.logger.info("Plan generated successfully - waiting for manual approval")
                return AgentResult(
                    success=True,
                    data={
                        **plan_result.data,
                        "message": "Plan generated and ready for approval. Use the dashboard to review and approve the plan.",
                        "next_action": "await_approval"
                    }
                )

            # Set project path using the analyzed project title (not the description)
            # Sanitize for Windows filesystem (remove invalid chars: \ / : * ? " < > |)
            import re
            project_title = re.sub(r'[\\/:*?"<>|,.]', '', analysis.title).replace(' ', '_').strip('_')
            # Get the directory where this agent.py file is located, then go up to armlenquant-local
            agent_dir = Path(__file__).parent.parent.parent  # Goes from ideas_machine -> agents -> armlenquant-local
            default_projects_dir = agent_dir / "Projects"
            default_project_path = default_projects_dir / project_title
            
            project_path = payload.get("project_path", str(default_project_path))
            self.project_path = Path(project_path).expanduser()
            self.phase_executor = PhaseExecutor(str(self.project_path))
            self.doc_generator = DocumentationGenerator(str(self.project_path))
            self.context_manager = ContextManager(str(self.project_path))

            self.logger.info(f"Project: {analysis.title}")
            self.logger.info(f"Path: {self.project_path}")

            # Step 2: Recommend tech stack
            self.logger.info("Step 2/8: Recommending optimal tech stack...")
            tech_stack = await self.architect.recommend_tech_stack(analysis)

            # Step 3: Design architecture
            self.logger.info("Step 3/8: Designing system architecture...")
            architecture = await self.architect.design_architecture(analysis, tech_stack)

            # Step 4: Plan development phases
            self.logger.info("Step 4/8: Planning development phases...")
            phases = await self.phase_planner.plan_phases(analysis)

            # Step 5: Generate documentation
            self.logger.info("Step 5/8: Generating comprehensive documentation...")
            docs = {}
            docs["docs/00_MASTER_PLAN.md"] = self.doc_generator.generate_master_plan(
                analysis, tech_stack, architecture, phases
            )
            docs["README.md"] = self.doc_generator.generate_readme(analysis, tech_stack, architecture)
            docs["PROJECT_CONTEXT.md"] = self.context_manager.initialize_context(
                analysis, tech_stack, architecture
            )

            # Generate phase docs
            for phase in phases:
                phase_filename = "02d"
                docs[f"docs/{phase_filename}"] = self.doc_generator.generate_phase_specification(
                    phase, analysis, tech_stack, architecture,
                    self.context_manager._context
                )

            # Step 6: Execute phases (if requested)
            execution_results = None
            if execute_phases:
                self.logger.info("Step 6/8: Executing development phases...")
                execution_results = await self.phase_executor.execute_project(
                    analysis, tech_stack, architecture
                )

                # Update documentation with execution results
                if execution_results["success"]:
                    docs["PROJECT_CONTEXT.md"] = self.doc_generator.update_project_context(
                        docs["PROJECT_CONTEXT.md"],
                        {"success": True, "phases_completed": execution_results["phases_executed"]},
                        "Complete Project Execution"
                    )

            # Step 7: Generate Cursor prompts
            self.logger.info("Step 7/8: Generating Cursor AI integration prompts...")
            cursor_prompts = {}
            for phase in phases:
                phase_prompts = await self.prompt_generator.generate_cursor_prompts(
                    phase, analysis, tech_stack, architecture, self.context_manager._context
                )
                cursor_prompts.update(phase_prompts)

            # Step 8: Store successful template for future reuse
            self.logger.info("Step 8/8: Storing successful patterns for future reuse...")
            if execution_results and execution_results["success"]:
                template_data = {
                    "phases_completed": execution_results["phases_executed"],
                    "total_files": execution_results.get("results", [{}])[0].get("generated_files", []),
                    "tech_stack_success": {
                        "frontend": tech_stack.frontend,
                        "backend": tech_stack.backend,
                        "infrastructure": tech_stack.infrastructure
                    },
                    "architecture_patterns": architecture.model_dump(),
                    "development_approach": "phase_based_ai_generation",
                    "quality_gates": "automatic_testing_validation"
                }

                await self.context_manager.store_successful_template(
                    template_data, analysis, tech_stack
                )

            # Create final summary
            summary = {
                "project_name": analysis.title,
                "project_path": str(self.project_path),
                "fullstack": analysis.is_fullstack,
                "project_type": analysis.project_type.value if hasattr(analysis.project_type, 'value') else analysis.project_type,
                "tech_stack": {
                    "frontend": tech_stack.frontend,
                    "backend": tech_stack.backend,
                    "infrastructure": tech_stack.infrastructure
                },
                "phases_planned": len(phases),
                "phases_executed": execution_results["phases_executed"] if execution_results else 0,
                "success": execution_results["success"] if execution_results else False,
                "total_files_generated": execution_results.get("results", [{}])[0].get("generated_files", []) if execution_results else 0,
                "documentation_generated": len(docs),
                "cursor_prompts_generated": len(cursor_prompts)
            }

            self.logger.info("=== COMPLETE PROJECT GENERATION FINISHED ===")
            self.logger.info(f"Success: {summary['success']}")
            self.logger.info(f"Files Generated: {summary['total_files_generated']}")
            self.logger.info(f"Phases Completed: {summary['phases_executed']}/{summary['phases_planned']}")

            return AgentResult(
                success=True,
                data={
                    **summary,
                    "analysis": analysis.model_dump(),
                    "architecture": architecture.model_dump(),
                    "execution_results": execution_results,
                    "next_steps": [
                        f"Open project in Cursor: cursor {self.project_path}",
                        "Read docs/00_MASTER_PLAN.md for project overview",
                        "Run development servers and test the application",
                        "Deploy using the generated deployment configurations"
                    ] if summary["success"] else [
                        "Review error logs and fix issues manually",
                        "Re-run phase execution for failed phases",
                        "Check generated documentation for guidance"
                    ]
                }
            )

        except Exception as e:
            self.logger.error(f"Complete project generation failed: {e}")
            return AgentResult(
                success=False,
                error=f"Project generation failed: {str(e)}",
                data={"partial_results": True}
            )

    async def _action_generate_plan(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Generate master project plan for human approval.

        Payload:
            description: str - Project idea description
            reference_urls: List[str] - Optional reference URLs
            constraints: Dict[str, str] - Optional constraints (budget, timeline)
            preferences: Dict[str, str] - Optional tech preferences
            task_id: str - Task ID for plan association
        """
        # Accept legacy payloads that used "idea" or "name" fields
        description = (
            payload.get("description")
            or payload.get("idea")
            or payload.get("name")
            or ""
        )

        task_id = getattr(self, '_current_task_id', None) or payload.get("task_id", "")

        if not description:
            return AgentResult(
                success=False,
                error="No project description provided"
            )

        if not task_id:
            return AgentResult(
                success=False,
                error="No task_id provided for plan association"
            )

        self.logger.info("=== MASTER PLAN GENERATION STARTED ===")
        self.logger.info(f"Project Description: {description}")
        self.logger.info(f"Task ID: {task_id}")

        try:
            # Step 1: Analyze idea
            self.logger.info("Step 1/5: Analyzing project idea...")
            idea_input = IdeaInput(
                description=description,
                reference_urls=payload.get("reference_urls", []),
                constraints=payload.get("constraints", {}),
                preferences=payload.get("preferences", {})
            )
            analysis = await self.analyzer.analyze(idea_input)

            # Delay between LLM calls to prevent rate limiting
            await self._delay_between_llm_calls()

            # Step 2: Recommend tech stack
            self.logger.info("Step 2/5: Recommending optimal tech stack...")
            tech_stack = await self.architect.recommend_tech_stack(analysis)

            # Delay between LLM calls to prevent rate limiting
            await self._delay_between_llm_calls()

            # Step 3: Design architecture
            self.logger.info("Step 3/5: Designing system architecture...")
            architecture = await self.architect.design_architecture(analysis, tech_stack)

            # Step 4: Plan development phases
            self.logger.info("Step 4/5: Planning development phases...")
            phases = await self.phase_planner.plan_phases(analysis)

            # Step 5: Generate master plan
            self.logger.info("Step 5/5: Creating master plan for approval...")

            # Determine scope based on analysis
            scope = "FULLSTACK"
            if analysis.project_type.value.lower() in ["frontend", "spa", "web_app"]:
                scope = "FRONTEND"
            elif analysis.project_type.value.lower() in ["api", "backend", "microservice"]:
                scope = "BACKEND"

            # Extract explicit preferences
            explicit_prefs = {}
            if payload.get("preferences"):
                explicit_prefs.update(payload.get("preferences", {}))

            # Calculate estimated hours
            estimated_hours = len(phases) * 20  # Rough estimate: 20 hours per phase

            # Create master plan structure
            master_plan = {
                "task_id": task_id,
                "project_name": analysis.title,
                "scope": scope,
                "tech_stack": {
                    "explicit_preferences": explicit_prefs,
                    "recommended_stack": {
                        "frontend": tech_stack.frontend,
                        "backend": tech_stack.backend,
                        "infrastructure": tech_stack.infrastructure
                    },
                    "alternatives": []
                },
                "phases": [
                    {
                        "id": f"phase_{i+1}",
                        "name": phase.name,
                        "description": phase.description,
                        "estimated_duration": f"{phase.estimated_hours or 20} hours",
                        "deliverables": phase.deliverables,
                        "success_criteria": phase.success_criteria,
                        "dependencies": phase.dependencies
                    }
                    for i, phase in enumerate(phases)
                ],
                "estimated_hours": estimated_hours,
                "risks": [
                    "Technology stack compatibility issues",
                    "Third-party API limitations",
                    "Performance requirements may exceed initial estimates",
                    "Security vulnerabilities in dependencies"
                ],
                "assumptions": [
                    "All required third-party services are available",
                    "Development environment matches production",
                    "Stakeholders provide timely feedback",
                    "No major changes to requirements during development"
                ]
            }

            # Store analysis data for later use
            plan_metadata = {
                "analysis": analysis.model_dump(),
                "architecture": architecture.model_dump(),
                "tech_stack": tech_stack.model_dump(),
                "phases": [phase.model_dump() for phase in phases]
            }

            self.logger.info("=== MASTER PLAN GENERATION COMPLETED ===")
            self.logger.info(f"Project: {analysis.title}")
            self.logger.info(f"Scope: {scope}")
            self.logger.info(f"Phases: {len(phases)}")
            self.logger.info(f"Estimated Hours: {estimated_hours}")

            return AgentResult(
                success=True,
                data={
                    **master_plan,
                    "metadata": plan_metadata,
                    "ready_for_approval": True
                }
            )

        except Exception as e:
            self.logger.error(f"Master plan generation failed: {e}")
            return AgentResult(
                success=False,
                error=f"Plan generation failed: {str(e)}"
            )

    async def _execute_approved_plan(self, plan_data: Dict[str, Any], original_payload: Dict[str, Any]) -> AgentResult:
        """
        Execute a plan that has been approved.

        Args:
            plan_data: The plan data from _action_generate_plan
            original_payload: Original payload with execution preferences
        """
        try:
            # Extract analysis data from plan metadata
            metadata = plan_data.get("metadata", {})
            analysis = IdeaAnalysis(**metadata.get("analysis", {}))
            tech_stack = TechStackRecommendation(**metadata.get("tech_stack", {}))
            architecture = ProjectArchitecture(**metadata.get("architecture", {}))
            phases = [PhaseSpec(**phase) for phase in metadata.get("phases", [])]

            self.logger.info(f"Executing approved plan for: {analysis.title}")

            # Set up project paths
            project_title = analysis.title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            agent_dir = Path(__file__).parent.parent.parent
            default_projects_dir = agent_dir / "Projects"
            default_project_path = default_projects_dir / project_title

            project_path = original_payload.get("project_path", str(default_project_path))
            self.project_path = Path(project_path).expanduser()
            self.phase_executor = PhaseExecutor(str(self.project_path), llm_delay_seconds=self.llm_delay_seconds)
            self.doc_generator = DocumentationGenerator(str(self.project_path))
            self.context_manager = ContextManager(str(self.project_path))

            self.logger.info(f"Project Path: {self.project_path}")

            # Generate documentation
            self.logger.info("Generating project documentation...")
            docs = {}
            docs["docs/00_MASTER_PLAN.md"] = self.doc_generator.generate_master_plan(
                analysis, tech_stack, architecture, phases
            )
            docs["README.md"] = self.doc_generator.generate_readme(analysis, tech_stack, architecture)
            docs["PROJECT_CONTEXT.md"] = self.context_manager.initialize_context(
                analysis, tech_stack, architecture
            )

            # Generate phase docs
            for phase in phases:
                phase_filename = "02d"
                docs[f"docs/{phase_filename}"] = self.doc_generator.generate_phase_specification(
                    phase, analysis, tech_stack, architecture,
                    self.context_manager._context
                )

            # Execute phases
            self.logger.info("Executing development phases...")
            execution_results = await self.phase_executor.execute_project(
                analysis, tech_stack, architecture
            )

            # Update documentation with execution results
            if execution_results["success"]:
                docs["PROJECT_CONTEXT.md"] = self.doc_generator.update_project_context(
                    docs["PROJECT_CONTEXT.md"],
                    {"success": True, "phases_completed": execution_results["phases_executed"]},
                    "Complete Project Execution"
                )

            # Generate Cursor prompts
            self.logger.info("Generating Cursor AI integration prompts...")
            cursor_prompts = {}
            for phase in phases:
                phase_prompts = await self.prompt_generator.generate_cursor_prompts(
                    phase, analysis, tech_stack, architecture, self.context_manager._context
                )
                cursor_prompts.update(phase_prompts)

            # Store successful template
            if execution_results["success"]:
                template_data = {
                    "phases_completed": execution_results["phases_executed"],
                    "total_files": execution_results.get("results", [{}])[0].get("generated_files", []),
                    "tech_stack_success": {
                        "frontend": tech_stack.frontend,
                        "backend": tech_stack.backend,
                        "infrastructure": tech_stack.infrastructure
                    },
                    "architecture_patterns": architecture.model_dump(),
                    "development_approach": "phase_based_ai_generation",
                    "quality_gates": "automatic_testing_validation"
                }

                await self.context_manager.store_successful_template(
                    template_data, analysis, tech_stack
                )

            # Create final summary
            summary = {
                "project_name": analysis.title,
                "project_path": str(self.project_path),
                "fullstack": analysis.is_fullstack,
                "project_type": analysis.project_type.value if hasattr(analysis.project_type, 'value') else analysis.project_type,
                "tech_stack": {
                    "frontend": tech_stack.frontend,
                    "backend": tech_stack.backend,
                    "infrastructure": tech_stack.infrastructure
                },
                "phases_planned": len(phases),
                "phases_executed": execution_results["phases_executed"] if execution_results else 0,
                "success": execution_results["success"] if execution_results else False,
                "total_files_generated": execution_results.get("results", [{}])[0].get("generated_files", []) if execution_results else [],
                "documentation_generated": len(docs),
                "cursor_prompts_generated": len(cursor_prompts)
            }

            self.logger.info("=== PROJECT EXECUTION COMPLETED ===")
            self.logger.info(f"Success: {summary['success']}")
            self.logger.info(f"Files Generated: {len(summary['total_files_generated'])}")
            self.logger.info(f"Phases Completed: {summary['phases_executed']}/{summary['phases_planned']}")

            return AgentResult(
                success=True,
                data={
                    **summary,
                    "analysis": analysis.model_dump(),
                    "architecture": architecture.model_dump(),
                    "execution_results": execution_results,
                    "next_steps": [
                        f"Open project in Cursor: cursor {self.project_path}",
                        "Read docs/00_MASTER_PLAN.md for project overview",
                        "Run development servers and test the application",
                        "Deploy using the generated deployment configurations"
                    ] if summary["success"] else [
                        "Review error logs and fix issues manually",
                        "Re-run phase execution for failed phases",
                        "Check generated documentation for guidance"
                    ]
                }
            )

        except Exception as e:
            self.logger.error(f"Approved plan execution failed: {e}")
            return AgentResult(
                success=False,
                error=f"Plan execution failed: {str(e)}",
                data={"partial_results": True}
            )

    async def _action_execute_phases(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Execute phases for an existing project.

        Payload:
            project_path: str - Path to existing project
            analysis: dict - Project analysis data
            tech_stack: dict - Tech stack data
            architecture: dict - Architecture data
            start_phase: int - Phase to start from (optional)
        """
        # This would load existing project data and execute phases
        # Implementation would be similar to the phase execution part above
        return AgentResult(
            success=False,
            error="Phase execution for existing projects not yet implemented"
        )

    async def _action_analyze(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Analyze action - just analyze the idea without scaffolding.
        
        Payload:
            description: str - Project idea description
        """
        description = (
            payload.get("description")
            or payload.get("idea")
            or payload.get("name")
            or ""
        )
        
        if not description:
            # Return with empty analysis for empty description
            return AgentResult(
                success=False,
                error="No project description provided"
            )
        
        idea_input = IdeaInput(description=description)
        
        self.logger.info("Analyzing idea...")
        analysis = await self.analyzer.analyze(idea_input)
        complexity = self.analyzer.estimate_complexity(analysis)
        
        return AgentResult(
            success=True,
            data={
                "analysis": analysis.model_dump(),
                "complexity": complexity
            }
        )
    
    async def _action_recommend_stack(self, payload: Dict[str, Any]) -> AgentResult:
        """
        Recommend stack action - analyze and recommend tech stack only.
        
        Payload:
            description: str - Project idea description
        """
        description = payload.get("description", "")
        
        if not description:
            return AgentResult(
                success=False,
                error="No project description provided"
            )
        
        idea_input = IdeaInput(description=description)
        
        self.logger.info("Analyzing idea...")
        analysis = await self.analyzer.analyze(idea_input)
        
        self.logger.info("Recommending tech stack...")
        tech_stack = await self.architect.recommend_tech_stack(analysis)
        
        return AgentResult(
            success=True,
            data={
                "analysis": analysis.model_dump(),
                "tech_stack": tech_stack.model_dump()
            }
        )
    
    def get_capabilities(self) -> list:
        """Get list of agent capabilities."""
        return [
            "idea_analysis",
            "tech_stack_recommendation",
            "architecture_design",
            "project_scaffolding",
            "documentation_generation",
            "cursor_integration",
            "master_plan_generation"
        ]
