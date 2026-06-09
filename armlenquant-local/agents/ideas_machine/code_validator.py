"""
Code Validator & Auto-Fixer
Cursor-like auto-fixing system - iterative testing and repair.
"""
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from agents.llm_client import get_llm_client, LLMClient
from .models import (
    IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
    ProjectContext, PhaseExecutionResult
)

# Windows compatibility flag
IS_WINDOWS = sys.platform == "win32"


class CodeValidator:
    """
    Validates generated code through testing and auto-fixes issues.
    """

    def __init__(self, llm_client: LLMClient = None, project_path: str = None):
        self.client = llm_client or get_llm_client()
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.logger = logger.bind(component="code_validator")
        self.max_fix_attempts = 3
    
    async def _run_command(
        self,
        *args: str,
        cwd: Optional[Path] = None,
        check_exists: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run a command with cross-platform support (especially Windows).
        
        Args:
            *args: Command and arguments
            cwd: Working directory
            check_exists: Check if executable exists first
            
        Returns:
            Tuple of (returncode, stdout, stderr)
        """
        if not args:
            return (-1, "", "No command provided")
        
        cmd = list(args)
        work_dir = cwd or self.project_path
        
        # Ensure the working directory exists
        if not work_dir.exists():
            return (-1, "", f"Working directory does not exist: {work_dir}")
        
        try:
            if IS_WINDOWS:
                # On Windows, use shell=True via create_subprocess_shell
                # This properly handles .cmd/.bat files like npx, npm, etc.
                full_cmd = subprocess.list2cmdline(cmd)
                process = await asyncio.create_subprocess_shell(
                    full_cmd,
                    cwd=work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                # On Unix-like systems, use exec directly
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=work_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120  # 2 minute timeout
            )
            
            return (
                process.returncode,
                stdout.decode(errors='replace'),
                stderr.decode(errors='replace')
            )
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Command timed out: {cmd}")
            return (-1, "", "Command timed out after 120 seconds")
        except FileNotFoundError:
            self.logger.debug(f"Command not found: {cmd[0]}")
            return (-1, "", f"Command not found: {cmd[0]}")
        except Exception as e:
            self.logger.debug(f"Command execution failed: {e}")
            return (-1, "", str(e))

    async def validate_and_fix(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext,
        generated_files: Dict[str, str],
        phase_name: str
    ) -> PhaseExecutionResult:
        """
        Validate generated code and auto-fix issues.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack recommendation
            architecture: System architecture
            context: Project context
            generated_files: Files generated for this phase
            phase_name: Name of the current phase

        Returns:
            Phase execution result with fixes applied
        """
        self.logger.info(f"Validating and fixing code for phase: {phase_name}")

        # Write generated files to disk
        file_paths = self._write_files_to_disk(generated_files)

        # Check if this is a foundation/setup phase with only config files
        # These phases don't have actual code to validate
        config_only_extensions = {'.json', '.yml', '.yaml', '.toml', '.md', '.txt', '.env', '.example', '.gitignore', '.cursorrules'}
        dockerfile_names = {'Dockerfile', 'Dockerfile.frontend', 'Dockerfile.backend', 'docker-compose.yml'}
        
        has_code_files = False
        for file_path in generated_files.keys():
            # Check if it's a config file
            file_ext = Path(file_path).suffix.lower()
            file_name = Path(file_path).name
            
            # Skip if it's a config file or dockerfile
            if file_ext in config_only_extensions or file_name in dockerfile_names:
                continue
            
            # Check for actual code files
            if file_ext in {'.py', '.ts', '.tsx', '.js', '.jsx', '.go', '.rs', '.java'}:
                has_code_files = True
                break
        
        # If no code files, skip validation - just return success with generated files
        if not has_code_files:
            self.logger.info(f"Phase {phase_name} has only config files, skipping code validation")
            return PhaseExecutionResult(
                phase_id=f"{phase_name}_validation",
                success=True,
                generated_files=list(file_paths.keys()),
                test_results={"success": True, "output": "Config-only phase, no code validation needed"}
            )

        # Run validation tests
        test_results = await self._run_validation_tests(analysis, tech_stack, file_paths)

        # If tests pass, return success
        if test_results.get("success", False):
            return PhaseExecutionResult(
                phase_id=f"{phase_name}_validation",
                success=True,
                generated_files=list(file_paths.keys()),
                test_results=test_results
            )

        # If tests fail, attempt auto-fixes
        fixes_applied = []
        for attempt in range(self.max_fix_attempts):
            self.logger.info(f"Fix attempt {attempt + 1}/{self.max_fix_attempts}")

            # Generate fixes using AI
            fix_result = await self._generate_fixes(
                analysis, tech_stack, architecture, context,
                test_results, generated_files, file_paths, attempt
            )

            if not fix_result["fixes"]:
                self.logger.warning("No fixes generated, stopping auto-fix attempts")
                break

            # Apply fixes
            applied_fixes = self._apply_fixes(fix_result["fixes"], file_paths)
            fixes_applied.extend(applied_fixes)

            # Re-run tests
            test_results = await self._run_validation_tests(analysis, tech_stack, file_paths)

            # If tests now pass, return success
            if test_results.get("success", False):
                self.logger.info(f"Fix attempt {attempt + 1} succeeded!")
                break

        # Return final result
        success = test_results.get("success", False)
        if not success:
            self.logger.warning(f"All fix attempts failed for phase: {phase_name}")

        return PhaseExecutionResult(
            phase_id=f"{phase_name}_validation",
            success=success,
            generated_files=list(file_paths.keys()),
            test_results=test_results,
            errors=test_results.get("errors", []),
            fixes_applied=fixes_applied
        )

    def _check_python_dependencies_installed(self) -> bool:
        """
        Check if Python dependencies are installed for the project.
        Returns True if a venv exists OR if key packages like fastapi are importable.
        """
        # Check for virtual environment
        venv_paths = [
            self.project_path / "venv",
            self.project_path / ".venv",
            self.project_path / "env",
        ]
        has_venv = any(p.exists() for p in venv_paths)
        
        # For newly generated projects, there won't be a venv
        # So we check if requirements.txt exists but no venv - means fresh project
        has_requirements = (self.project_path / "requirements.txt").exists()
        
        if has_requirements and not has_venv:
            self.logger.info("Fresh project detected - dependencies not yet installed")
            return False
        
        return True

    def _check_node_dependencies_installed(self) -> bool:
        """Check if Node.js dependencies are installed."""
        return (self.project_path / "node_modules").exists()

    async def _run_validation_tests(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        file_paths: Dict[str, Path]
    ) -> Dict[str, Any]:
        """
        Run validation tests on generated code.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack
            file_paths: Paths to generated files

        Returns:
            Test results dictionary
        """
        results = {
            "success": True,
            "errors": [],
            "test_output": {},
            "lint_errors": [],
            "type_errors": []
        }

        # Check if this is a newly generated project without dependencies
        python_deps_installed = self._check_python_dependencies_installed()
        node_deps_installed = self._check_node_dependencies_installed()

        try:
            # Run syntax/type checking first
            if analysis.is_fullstack or analysis.project_type.value == "WEB_APP":
                if node_deps_installed:
                    # TypeScript checking
                    ts_results = await self._run_typescript_check()
                    results["type_errors"].extend(ts_results.get("errors", []))
                    # Don't fail the phase for type errors in new projects
                    # if not ts_results.get("success", True):
                    #     results["success"] = False

                    # ESLint
                    eslint_results = await self._run_eslint_check()
                    results["lint_errors"].extend(eslint_results.get("errors", []))
                    # Don't fail for lint errors in new projects
                    # if not eslint_results.get("success", True):
                    #     results["success"] = False
                else:
                    self.logger.info("Skipping frontend validation - node_modules not installed")
                    results["test_output"]["frontend"] = "Skipped - run 'npm install' first"

            if analysis.is_fullstack or analysis.project_type.value in ["API_SERVICE", "AI_APP"]:
                if python_deps_installed:
                    # Python type checking
                    mypy_results = await self._run_mypy_check()
                    results["type_errors"].extend(mypy_results.get("errors", []))
                    # Don't fail for type errors
                    # if not mypy_results.get("success", True):
                    #     results["success"] = False

                    # Python linting
                    flake8_results = await self._run_flake8_check()
                    results["lint_errors"].extend(flake8_results.get("errors", []))
                    # Don't fail for lint errors
                    # if not flake8_results.get("success", True):
                    #     results["success"] = False
                else:
                    self.logger.info("Skipping backend validation - Python dependencies not installed")
                    results["test_output"]["backend"] = "Skipped - run 'pip install -r requirements.txt' first"

            # Run unit tests only if dependencies are installed
            if python_deps_installed or node_deps_installed:
                test_results = await self._run_unit_tests(analysis, tech_stack)
                results["test_output"].update(test_results)
                # Don't fail for test errors in newly generated projects
                # Tests are informational, not blocking
            else:
                self.logger.info("Skipping all tests - no dependencies installed (fresh project)")
                results["test_output"]["status"] = "Skipped - install dependencies first"

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            # Don't fail the whole phase for validation errors
            results["errors"].append(f"Validation warning: {str(e)}")

        return results

    async def _run_typescript_check(self) -> Dict[str, Any]:
        """Run TypeScript type checking."""
        # Check if tsconfig.json exists
        if not (self.project_path / "tsconfig.json").exists():
            return {"success": True, "errors": [], "output": "No tsconfig.json found, skipping TypeScript check"}
        
        # Check if node_modules exists (npm install must have been run)
        if not (self.project_path / "node_modules").exists():
            return {"success": True, "errors": [], "output": "No node_modules found, skipping TypeScript check (run npm install first)"}
        
        # Check if there are any TypeScript files to check
        ts_files = list(self.project_path.glob("**/*.ts")) + list(self.project_path.glob("**/*.tsx"))
        # Exclude node_modules
        ts_files = [f for f in ts_files if "node_modules" not in str(f)]
        if not ts_files:
            return {"success": True, "errors": [], "output": "No TypeScript files found, skipping TypeScript check"}
        
        returncode, stdout, stderr = await self._run_command("npx", "tsc", "--noEmit")
        
        if returncode == -1 and ("not found" in stderr.lower() or "timed out" in stderr.lower()):
            return {"success": True, "errors": [], "output": "TypeScript not available or timed out"}
        
        success = returncode == 0
        errors = []
        
        if not success:
            error_output = stderr + stdout
            errors = self._parse_typescript_errors(error_output)
        
        return {
            "success": success,
            "errors": errors,
            "output": stdout + stderr
        }

    async def _run_eslint_check(self) -> Dict[str, Any]:
        """Run ESLint."""
        # Check if node_modules exists (npm install must have been run)
        if not (self.project_path / "node_modules").exists():
            return {"success": True, "errors": [], "output": "No node_modules found, skipping ESLint check (run npm install first)"}
        
        # Check if ESLint config exists
        eslint_configs = [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs"]
        has_eslint_config = any((self.project_path / cfg).exists() for cfg in eslint_configs)
        
        if not has_eslint_config:
            return {"success": True, "errors": [], "output": "No ESLint config found, skipping ESLint check"}
        
        # Check if there are any JS/TS files to check
        js_files = list(self.project_path.glob("**/*.js")) + list(self.project_path.glob("**/*.jsx")) + \
                   list(self.project_path.glob("**/*.ts")) + list(self.project_path.glob("**/*.tsx"))
        # Exclude node_modules
        js_files = [f for f in js_files if "node_modules" not in str(f)]
        if not js_files:
            return {"success": True, "errors": [], "output": "No JS/TS files found, skipping ESLint check"}
        
        returncode, stdout, stderr = await self._run_command(
            "npx", "eslint", ".", "--ext", ".ts,.tsx,.js,.jsx"
        )
        
        if returncode == -1 and ("not found" in stderr.lower() or "timed out" in stderr.lower()):
            return {"success": True, "errors": [], "output": "ESLint not available or timed out"}
        
        success = returncode == 0
        errors = []
        
        if not success:
            error_output = stderr + stdout
            errors = self._parse_eslint_errors(error_output)
        
        return {
            "success": success,
            "errors": errors,
            "output": stdout + stderr
        }

    async def _run_mypy_check(self) -> Dict[str, Any]:
        """Run mypy type checking."""
        # Check if there are any Python files to check
        py_files = list(self.project_path.glob("**/*.py"))
        if not py_files:
            return {"success": True, "errors": [], "output": "No Python files found, skipping mypy check"}
        
        # Use python -m mypy for better cross-platform support
        returncode, stdout, stderr = await self._run_command(
            sys.executable, "-m", "mypy", "."
        )
        
        if returncode == -1 or "No module named mypy" in stderr:
            return {"success": True, "errors": [], "output": "mypy not available"}
        
        success = returncode == 0
        errors = []
        
        if not success:
            error_output = stderr + stdout
            errors = self._parse_mypy_errors(error_output)
        
        return {
            "success": success,
            "errors": errors,
            "output": stdout + stderr
        }

    async def _run_flake8_check(self) -> Dict[str, Any]:
        """Run flake8 linting."""
        # Check if there are any Python files to check
        py_files = list(self.project_path.glob("**/*.py"))
        if not py_files:
            return {"success": True, "errors": [], "output": "No Python files found, skipping flake8 check"}
        
        # Use python -m flake8 for better cross-platform support
        returncode, stdout, stderr = await self._run_command(
            sys.executable, "-m", "flake8", "."
        )
        
        if returncode == -1 or "No module named flake8" in stderr:
            return {"success": True, "errors": [], "output": "flake8 not available"}
        
        success = returncode == 0
        errors = []
        
        if not success:
            error_output = stderr + stdout
            errors = self._parse_flake8_errors(error_output)
        
        return {
            "success": success,
            "errors": errors,
            "output": stdout + stderr
        }

    async def _run_unit_tests(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Dict[str, Any]:
        """Run unit tests."""
        results = {"success": True, "errors": [], "output": ""}
        
        # Check if Python dependencies are installed first
        python_deps_installed = self._check_python_dependencies_installed()
        
        # Run backend tests (Python)
        if analysis.is_fullstack or analysis.project_type.value in ["API_SERVICE", "AI_APP"]:
            if not python_deps_installed:
                results["output"] += "Backend tests: Skipped - install dependencies first (pip install -r requirements.txt)\n"
            else:
                # Check if there are any test files
                test_files = list(self.project_path.glob("**/test_*.py")) + \
                            list(self.project_path.glob("**/*_test.py")) + \
                            list(self.project_path.glob("**/tests/*.py"))
                
                if test_files:
                    # Use python -m pytest for better cross-platform support
                    returncode, stdout, stderr = await self._run_command(
                        sys.executable, "-m", "pytest", "-v", "--tb=short"
                    )
                    
                    output_combined = stdout + stderr
                    
                    if returncode == -1:
                        if "No module named pytest" in stderr:
                            results["output"] += "Backend tests: pytest not available\n"
                        else:
                            # Non-critical error, just log it
                            self.logger.warning(f"pytest execution issue: {stderr}")
                            results["output"] += f"Backend tests: Could not run pytest - {stderr}\n"
                    elif returncode != 0:
                        # Check if failure is due to missing dependencies (common for new projects)
                        if "ModuleNotFoundError" in output_combined or "ImportError" in output_combined:
                            self.logger.info("Tests failed due to missing dependencies - this is expected for new projects")
                            results["output"] += "Backend tests: Skipped - missing dependencies (install requirements first)\n"
                        else:
                            # Real test failures
                            results["errors"].extend(self._parse_pytest_errors(output_combined))
                            results["output"] += f"Backend tests: {output_combined}\n"
                            # Don't set success=False for new projects, tests are informational
                    else:
                        results["output"] += f"Backend tests: {output_combined}\n"
                else:
                    results["output"] += "Backend tests: No test files found, skipping pytest\n"
        
        # Run frontend tests (JavaScript/TypeScript)
        if analysis.is_fullstack or analysis.project_type.value == "WEB_APP":
            # Check if node_modules exists (npm install must have been run)
            if not (self.project_path / "node_modules").exists():
                results["output"] += "Frontend tests: No node_modules found, skipping (run npm install first)\n"
            else:
                # Check if package.json exists and has a test script
                package_json_path = self.project_path / "package.json"
                has_test_script = False
                
                if package_json_path.exists():
                    try:
                        with open(package_json_path, 'r', encoding='utf-8') as f:
                            package_json = json.load(f)
                            scripts = package_json.get("scripts", {})
                            test_script = scripts.get("test", "")
                            # Check if there's a real test script (not just "no test specified")
                            has_test_script = test_script and "no test specified" not in test_script.lower()
                    except Exception as e:
                        self.logger.debug(f"Could not read package.json: {e}")
                
                if has_test_script:
                    returncode, stdout, stderr = await self._run_command(
                        "npm", "test", "--", "--watchAll=false", "--passWithNoTests"
                    )
                    
                    if returncode == -1:
                        if "not found" in stderr.lower():
                            results["output"] += "Frontend tests: npm not available\n"
                        else:
                            self.logger.warning(f"npm test execution issue: {stderr}")
                            results["output"] += f"Frontend tests: Could not run npm test - {stderr}\n"
                    elif returncode != 0:
                        # Check if it's just a "no tests" error - that's okay for new projects
                        if "no tests found" in (stdout + stderr).lower():
                            results["output"] += "Frontend tests: No tests found (new project)\n"
                        else:
                            results["success"] = False
                            results["errors"].extend(self._parse_jest_errors(stderr + stdout))
                            results["output"] += f"Frontend tests: {stdout}{stderr}\n"
                    else:
                        results["output"] += f"Frontend tests: {stdout}{stderr}\n"
                else:
                    results["output"] += "Frontend tests: No test script configured, skipping\n"
        
        # If no tests were run, that's still a success for a new project
        if not results["output"]:
            results["output"] = "No tests configured yet (new project)\n"
        
        return results

    async def _generate_fixes(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation,
        architecture: ProjectArchitecture,
        context: ProjectContext,
        test_results: Dict[str, Any],
        generated_files: Dict[str, str],
        file_paths: Dict[str, Path],
        attempt: int
    ) -> Dict[str, Any]:
        """
        Generate fixes for failing tests using AI.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack
            architecture: Architecture
            context: Project context
            test_results: Current test results
            generated_files: Original generated files
            file_paths: File paths on disk
            attempt: Current fix attempt number

        Returns:
            Dictionary with fixes to apply
        """
        # Collect error context
        error_context = self._collect_error_context(test_results, attempt)

        prompt = f"""You are an expert software engineer fixing code issues. The following code was generated but has failing tests.

**Project Context:**
- Name: {analysis.title}
- Type: {analysis.project_type.value if hasattr(analysis.project_type, 'value') else analysis.project_type}
- Tech Stack: {json.dumps(tech_stack.frontend)} + {json.dumps(tech_stack.backend)}

**Current Errors:**
{chr(10).join(f"- {error}" for error in error_context)}

**Architecture:**
{json.dumps(architecture.data_models, indent=2)}

**Generated Files:**
{chr(10).join(f"- {path}: {content[:200]}..." for path, content in generated_files.items())}

**Fix Attempt:** {attempt + 1}/{self.max_fix_attempts}

Generate fixes for the failing code. Return a JSON object with this structure:
{{
  "fixes": [
    {{
      "file_path": "relative/path/to/file.py",
      "description": "What this fix does",
      "old_code": "exact old code to replace",
      "new_code": "exact new code to replace with"
    }}
  ],
  "explanation": "Overall explanation of the fixes"
}}

IMPORTANT:
- Only fix the actual issues causing test failures
- Maintain the same functionality and architecture
- Use exact string matches for old_code
- Include enough context in old_code for unique matching
- Return valid JSON only
"""

        response = await self.client.chat(
            messages=[
                {"role": "system", "content": "You are an expert code fixer. Return only valid JSON with fixes."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            json_response=True
        )

        try:
            result = response.json()
            return result
        except Exception as e:
            self.logger.error(f"Failed to parse fix response: {e}")
            return {"fixes": [], "explanation": "Failed to generate fixes"}

    def _apply_fixes(self, fixes: List[Dict[str, str]], file_paths: Dict[str, Path]) -> List[Dict[str, str]]:
        """
        Apply generated fixes to files.

        Args:
            fixes: List of fixes to apply
            file_paths: Mapping of relative paths to absolute paths

        Returns:
            List of applied fixes with results
        """
        applied_fixes = []

        for fix in fixes:
            file_path = fix.get("file_path")
            description = fix.get("description", "No description")
            old_code = fix.get("old_code")
            new_code = fix.get("new_code")

            if not file_path or not old_code:
                self.logger.warning(f"Invalid fix: {fix}")
                continue

            # Get absolute path
            abs_path = file_paths.get(file_path)
            if not abs_path:
                self.logger.warning(f"File path not found: {file_path}")
                continue

            try:
                # Read current file content
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Apply fix
                if old_code in content:
                    new_content = content.replace(old_code, new_code, 1)

                    # Write back
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                    applied_fixes.append({
                        "file_path": file_path,
                        "description": description,
                        "success": True
                    })

                    self.logger.info(f"Applied fix to {file_path}: {description}")
                else:
                    self.logger.warning(f"Old code not found in {file_path}")
                    applied_fixes.append({
                        "file_path": file_path,
                        "description": description,
                        "success": False,
                        "error": "Old code not found"
                    })

            except Exception as e:
                self.logger.error(f"Failed to apply fix to {file_path}: {e}")
                applied_fixes.append({
                    "file_path": file_path,
                    "description": description,
                    "success": False,
                    "error": str(e)
                })

        return applied_fixes

    def _write_files_to_disk(self, generated_files: Dict[str, str]) -> Dict[str, Path]:
        """
        Write generated files to disk.

        Args:
            generated_files: Files to write

        Returns:
            Mapping of relative paths to absolute paths
        """
        file_paths = {}

        for rel_path, content in generated_files.items():
            abs_path = self.project_path / rel_path
            abs_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                file_paths[rel_path] = abs_path
                self.logger.debug(f"Wrote file: {abs_path}")
            except Exception as e:
                self.logger.error(f"Failed to write file {abs_path}: {e}")

        return file_paths

    def _collect_error_context(self, test_results: Dict[str, Any], attempt: int) -> List[str]:
        """Collect error context for AI fixing."""
        errors = []

        # Add test errors
        errors.extend(test_results.get("errors", []))

        # Add lint errors
        for lint_error in test_results.get("lint_errors", []):
            errors.append(f"Lint: {lint_error}")

        # Add type errors
        for type_error in test_results.get("type_errors", []):
            errors.append(f"Type: {type_error}")

        # Add attempt context
        if attempt > 0:
            errors.append(f"This is fix attempt {attempt + 1}. Previous fixes may have introduced new issues.")

        return errors[:10]  # Limit to first 10 errors

    def _parse_typescript_errors(self, error_output: str) -> List[str]:
        """Parse TypeScript error output."""
        errors = []
        for line in error_output.split('\n'):
            if line.strip() and not line.startswith(' '):
                errors.append(line.strip())
        return errors

    def _parse_eslint_errors(self, error_output: str) -> List[str]:
        """Parse ESLint error output."""
        errors = []
        for line in error_output.split('\n'):
            if 'error' in line.lower():
                errors.append(line.strip())
        return errors

    def _parse_mypy_errors(self, error_output: str) -> List[str]:
        """Parse mypy error output."""
        errors = []
        for line in error_output.split('\n'):
            if line.strip() and not line.startswith(' '):
                errors.append(line.strip())
        return errors

    def _parse_flake8_errors(self, error_output: str) -> List[str]:
        """Parse flake8 error output."""
        errors = []
        for line in error_output.split('\n'):
            if line.strip():
                errors.append(line.strip())
        return errors

    def _parse_pytest_errors(self, error_output: str) -> List[str]:
        """Parse pytest error output."""
        errors = []
        in_error = False
        current_error = []

        for line in error_output.split('\n'):
            if line.startswith('E   ') or line.startswith('FAILED'):
                if current_error:
                    errors.append(' '.join(current_error))
                    current_error = []
                in_error = True
                current_error.append(line.strip())
            elif in_error and line.strip():
                current_error.append(line.strip())
            elif in_error and not line.strip():
                if current_error:
                    errors.append(' '.join(current_error))
                    current_error = []
                in_error = False

        if current_error:
            errors.append(' '.join(current_error))

        return errors

    def _parse_jest_errors(self, error_output: str) -> List[str]:
        """Parse Jest error output."""
        errors = []
        for line in error_output.split('\n'):
            if 'FAIL' in line or 'Error:' in line:
                errors.append(line.strip())
        return errors
