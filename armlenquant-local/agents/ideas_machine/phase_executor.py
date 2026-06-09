"""
Sequential Phase Executor
Executes development phases sequentially with quality gates.
"""
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger

from .models import (
    IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
    ProjectContext, PhaseSpec, PhaseExecutionResult, PhaseTask
)
from .phase_planner import PhasePlanner
from .code_generator import CodeGenerator
from .code_validator import CodeValidator
from .context_manager import ContextManager
from .prompt_generator import PromptGenerator


class PhaseExecutor:
    """
    Executes development phases sequentially with quality assurance and execution control.
    """

    def __init__(self, project_path: str = None, llm_delay_seconds: float = 1.5):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = logger.bind(component="phase_executor")
        self.llm_delay_seconds = llm_delay_seconds

        # Initialize components
        self.phase_planner = PhasePlanner()
        self.code_generator = CodeGenerator()
        self.code_validator = CodeValidator(project_path=str(self.project_path))
        self.context_manager = ContextManager(str(self.project_path))
        self.prompt_generator = PromptGenerator()

        # Execution control state
        self.execution_state = "READY"  # READY, RUNNING, PAUSED, CANCELLED
        self.current_phase = None
        self.control_callbacks = {}  # For external control integration

    async def _delay_between_llm_calls(self):
        """Add configurable delay between LLM calls to prevent rate limiting."""
        if self.llm_delay_seconds > 0:
            self.logger.debug(f"Waiting {self.llm_delay_seconds}s between LLM calls...")
            import asyncio
            await asyncio.sleep(self.llm_delay_seconds)

    def pause_execution(self) -> bool:
        """
        Pause execution at the next safe point.

        Returns:
            True if pause was initiated, False if already paused/cancelled
        """
        if self.execution_state in ["READY", "RUNNING"]:
            self.execution_state = "PAUSED"
            self.logger.info("Execution paused")
            return True
        return False

    def resume_execution(self) -> bool:
        """
        Resume paused execution.

        Returns:
            True if resume was initiated, False if not paused
        """
        if self.execution_state == "PAUSED":
            self.execution_state = "RUNNING"
            self.logger.info("Execution resumed")
            return True
        return False

    def cancel_execution(self) -> bool:
        """
        Cancel execution immediately.

        Returns:
            True if cancellation was initiated
        """
        if self.execution_state in ["READY", "RUNNING", "PAUSED"]:
            self.execution_state = "CANCELLED"
            self.logger.info("Execution cancelled")
            return True
        return False

    def get_execution_status(self) -> Dict[str, Any]:
        """
        Get current execution status.

        Returns:
            Dictionary with execution state information
        """
        return {
            "state": self.execution_state,
            "current_phase": self.current_phase,
            "can_pause": self.execution_state in ["READY", "RUNNING"],
            "can_resume": self.execution_state == "PAUSED",
            "can_cancel": self.execution_state in ["READY", "RUNNING", "PAUSED"]
        }

    async def _check_execution_control(self) -> bool:
        """
        Check if execution should continue or if there's a control signal.

        Returns:
            True if execution should continue, False if paused/cancelled
        """
        if self.execution_state == "CANCELLED":
            self.logger.info("Execution cancelled by control signal")
            return False
        elif self.execution_state == "PAUSED":
            self.logger.info("Execution paused, waiting for resume...")
            # In a real implementation, this might wait for external resume signal
            # For now, we'll just return False to stop execution
            return False

        return True

    async def execute_project(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture
    ) -> Dict[str, Any]:
        """
        Execute complete project development through sequential phases.

        Args:
            analysis: Project analysis
            tech_stack: Recommended tech stack
            architecture: System architecture

        Returns:
            Complete execution results
        """
        self.logger.info(f"Starting project execution: {analysis.title}")

        # Initialize project context
        context_md = self.context_manager.initialize_context(analysis, tech_stack, architecture)

        # Plan phases
        phases = await self.phase_planner.plan_phases(analysis)

        # Execute phases sequentially
        results = []
        current_context = ProjectContext(
            architecture={
                "overview": architecture.overview,
                "components": architecture.components,
                "data_flow": architecture.data_flow,
                "diagrams": architecture.diagrams
            },
            models=architecture.data_models,
            endpoints=architecture.api_endpoints,
            components=[],
            test_coverage={}
        )

        for i, phase in enumerate(phases):
            self.current_phase = phase.phase_name
            self.logger.info(f"Executing Phase {i+1}/{len(phases)}: {phase.phase_name}")

            # Check execution control before starting phase
            if not await self._check_execution_control():
                self.logger.info(f"Phase {phase.phase_name} skipped due to execution control")
                break

            self.execution_state = "RUNNING"

            # Execute phase
            phase_result = await self._execute_phase(
                analysis, tech_stack, architecture, current_context, phase
            )

            results.append(phase_result)

            # Update context with phase results
            if phase_result.success:
                self.context_manager.update_context_after_phase(
                    phase.phase_name,
                    {
                        "success": True,
                        "generated_files": phase_result.generated_files,
                        "test_results": phase_result.test_results
                    },
                    phase_result.generated_files,
                    []  # components would be populated from actual implementation
                )

                # Update current context
                current_context.test_coverage[phase.phase_name] = phase_result.test_results
            else:
                # Phase failed - log and continue or stop based on policy
                self.logger.error(f"Phase {phase.phase_name} failed: {phase_result.errors}")
                break

            # Check execution control after phase completion
            # Allow pause between phases for user review
            if not await self._check_execution_control():
                self.logger.info(f"Execution paused after phase {phase.phase_name}")
                break

        # Generate final summary
        summary = self._generate_execution_summary(analysis, results)

        return {
            "success": all(r.success for r in results),
            "phases_executed": len(results),
            "total_phases": len(phases),
            "results": [r.dict() for r in results],
            "summary": summary,
            "project_context": context_md
        }

    async def _execute_phase(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext,
        phase: PhaseSpec
    ) -> PhaseExecutionResult:
        """
        Execute a single development phase.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack
            architecture: Architecture
            context: Current project context
            phase: Phase to execute

        Returns:
            Phase execution result
        """
        try:
            # Generate code for this phase
            generated_files = await self.code_generator.generate_phase_code(
                analysis, tech_stack, architecture, context, phase
            )

            if not generated_files:
                return PhaseExecutionResult(
                    phase_id=f"{phase.phase_name}_empty",
                    success=False,
                    errors=["No code generated for phase"]
                )

            # Delay between LLM calls to prevent rate limiting
            await self._delay_between_llm_calls()

            # Validate and auto-fix generated code
            validation_result = await self.code_validator.validate_and_fix(
                analysis, tech_stack, architecture, context,
                generated_files, phase.phase_name
            )

            return validation_result

        except Exception as e:
            self.logger.error(f"Phase execution failed: {e}")
            return PhaseExecutionResult(
                phase_id=f"{phase.phase_name}_error",
                success=False,
                errors=[str(e)]
            )

    async def execute_single_phase(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext,
        phase: PhaseSpec
    ) -> PhaseExecutionResult:
        """
        Execute a single phase (useful for manual phase execution).

        Args:
            analysis: Project analysis
            tech_stack: Tech stack
            architecture: Architecture
            context: Project context
            phase: Phase to execute

        Returns:
            Phase execution result
        """
        return await self._execute_phase(analysis, tech_stack, architecture, context, phase)

    def _generate_execution_summary(
        self,
        analysis: IdeaAnalysis,
        results: List[PhaseExecutionResult]
    ) -> Dict[str, Any]:
        """
        Generate execution summary.

        Args:
            analysis: Project analysis
            results: Phase execution results

        Returns:
            Summary dictionary
        """
        successful_phases = sum(1 for r in results if r.success)
        total_phases = len(results)

        total_files = sum(len(r.generated_files) for r in results if r.generated_files)
        total_fixes = sum(len(r.fixes_applied) for r in results if r.fixes_applied)

        all_errors = []
        for result in results:
            all_errors.extend(result.errors or [])

        return {
            "project_name": analysis.title,
            "successful_phases": successful_phases,
            "total_phases": total_phases,
            "success_rate": successful_phases / total_phases if total_phases > 0 else 0,
            "total_files_generated": total_files,
            "total_fixes_applied": total_fixes,
            "total_errors": len(all_errors),
            "completion_status": "COMPLETE" if successful_phases == total_phases else "PARTIAL",
            "recommendations": self._generate_recommendations(results)
        }

    def _generate_recommendations(self, results: List[PhaseExecutionResult]) -> List[str]:
        """
        Generate recommendations based on execution results.

        Args:
            results: Phase execution results

        Returns:
            List of recommendations
        """
        recommendations = []

        failed_phases = [r for r in results if not r.success]
        if failed_phases:
            recommendations.append(f"Review and fix {len(failed_phases)} failed phases manually")

        # Check for patterns in fixes applied
        total_fixes = sum(len(r.fixes_applied or []) for r in results)
        if total_fixes > 10:
            recommendations.append("Consider improving code generation prompts to reduce auto-fixes needed")

        # Check test coverage
        phases_with_tests = sum(1 for r in results if r.test_results and r.test_results.get("success"))
        if phases_with_tests < len(results) * 0.8:
            recommendations.append("Improve test generation to ensure higher success rates")

        return recommendations

    async def validate_project_readiness(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext
    ) -> Dict[str, Any]:
        """
        Validate that project is ready for deployment.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack
            architecture: Architecture
            context: Project context

        Returns:
            Validation results
        """
        validation_results = {
            "ready_for_deployment": False,
            "checks": {},
            "issues": [],
            "recommendations": []
        }

        # Check if all phases completed successfully
        # (This would be checked against actual phase results)

        # Check test coverage
        test_coverage = context.test_coverage
        if not test_coverage:
            validation_results["issues"].append("No test coverage information available")
        else:
            total_tests = len(test_coverage)
            passing_tests = sum(1 for result in test_coverage.values()
                              if isinstance(result, dict) and result.get("success"))
            coverage_rate = passing_tests / total_tests if total_tests > 0 else 0

            validation_results["checks"]["test_coverage"] = {
                "rate": coverage_rate,
                "passing": passing_tests,
                "total": total_tests
            }

            if coverage_rate < 0.8:
                validation_results["issues"].append(f"Test coverage too low: {coverage_rate:.1%}")

        # Check API completeness
        if analysis.is_fullstack:
            api_endpoints = len(context.endpoints)
            validation_results["checks"]["api_completeness"] = {
                "endpoints_defined": api_endpoints
            }

            if api_endpoints < 3:  # Arbitrary minimum
                validation_results["issues"].append("Too few API endpoints defined")

        # Check component completeness
        components = len(context.components or [])
        validation_results["checks"]["component_completeness"] = {
            "components_implemented": components
        }

        # Determine readiness
        critical_issues = [issue for issue in validation_results["issues"]
                          if any(keyword in issue.lower()
                                for keyword in ["test coverage", "api", "security"])]

        validation_results["ready_for_deployment"] = len(critical_issues) == 0

        if validation_results["ready_for_deployment"]:
            validation_results["recommendations"].append("Project is ready for deployment")
        else:
            validation_results["recommendations"].extend([
                "Address critical issues before deployment",
                "Consider manual code review",
                "Run integration tests in staging environment"
            ])

        return validation_results
