"""
Phase Planner
Breaks projects into logical development phases with dependencies.
"""
from typing import List, Dict, Any
from loguru import logger

from agents.llm_client import get_llm_client, LLMClient
from .models import IdeaAnalysis, PhaseSpec, PhaseTask, ProjectType


class PhasePlanner:
    """
    Plans development phases for projects.
    """

    def __init__(self, llm_client: LLMClient = None):
        self.client = llm_client or get_llm_client()
        self.logger = logger.bind(component="phase_planner")

    def determine_phase_count(self, scope: str, complexity: str, size: str) -> int:
        """
        Determine the number of phases based on project scope, complexity, and size.

        Args:
            scope: "FRONTEND", "BACKEND", or "FULLSTACK"
            complexity: Project complexity level
            size: Project size (MICRO, SMALL, MEDIUM, LARGE)

        Returns:
            Number of development phases
        """
        base_phases = {
            "FRONTEND": 3,    # Setup, Core UI, Integration
            "BACKEND": 4,     # Setup, API Core, Database, Integration
            "FULLSTACK": 6    # Foundation, Backend Core, Frontend Core, Integration, Testing, Deployment
        }

        # Adjust based on project size
        size_multipliers = {
            "MICRO": 0.5,    # Reduce phases for micro projects
            "SMALL": 0.75,   # Slight reduction for small projects
            "MEDIUM": 1.0,   # Standard phase count
            "LARGE": 1.25    # Increase phases for large projects
        }

        base_count = base_phases.get(scope, 4)
        size_multiplier = size_multipliers.get(size, 1.0)

        # Calculate final count and ensure it's at least 2, at most 8
        final_count = max(2, min(8, int(base_count * size_multiplier)))

        self.logger.info(f"Determined {final_count} phases for {scope} project (size: {size})")
        return final_count

    async def plan_phases(self, analysis: IdeaAnalysis) -> List[PhaseSpec]:
        """
        Plan development phases for a project.

        Args:
            analysis: Analyzed project idea

        Returns:
            List of phase specifications with dependencies
        """
        self.logger.info(f"Planning phases for {analysis.title}")

        # Determine project scope
        scope = self._determine_scope(analysis)

        # Get complexity estimate
        complexity = self._estimate_complexity(analysis)

        # Determine phase count
        phase_count = self.determine_phase_count(
            scope,
            complexity,
            analysis.project_size.value if hasattr(analysis.project_size, 'value') else str(analysis.project_size)
        )

        # Plan phases based on scope and count
        if scope == "FRONTEND":
            return await self._plan_frontend_phases(analysis, phase_count)
        elif scope == "BACKEND":
            return await self._plan_backend_phases(analysis, phase_count)
        else:  # FULLSTACK
            return await self._plan_fullstack_phases(analysis, phase_count)

    def _determine_scope(self, analysis: IdeaAnalysis) -> str:
        """Determine project scope from analysis."""
        # Check explicit fullstack flag first
        if analysis.is_fullstack:
            return "FULLSTACK"

        # Check project type for scope hints
        project_type = analysis.project_type.value.lower() if hasattr(analysis.project_type, 'value') else str(analysis.project_type).lower()

        if project_type in ["frontend", "spa", "web_app", "mobile_app", "chrome_extension"]:
            return "FRONTEND"
        elif project_type in ["api", "backend", "microservice", "data_pipeline", "cli_tool"]:
            return "BACKEND"

        # Check description for scope indicators
        description_lower = analysis.description.lower()
        if any(word in description_lower for word in ["frontend only", "client-side", "ui only", "interface only"]):
            return "FRONTEND"
        if any(word in description_lower for word in ["backend only", "api only", "server-side", "data only"]):
            return "BACKEND"

        # Default to fullstack
        return "FULLSTACK"

    def _estimate_complexity(self, analysis: IdeaAnalysis) -> str:
        """Estimate project complexity."""
        # Simple heuristic based on features and size
        feature_count = len(analysis.core_features) + len(analysis.mvp_features)

        if feature_count <= 3:
            return "LOW"
        elif feature_count <= 7:
            return "MEDIUM"
        else:
            return "HIGH"

    async def _plan_frontend_phases(self, analysis: IdeaAnalysis, phase_count: int) -> List[PhaseSpec]:
        """Plan phases for frontend-only projects."""
        phases = []

        if phase_count >= 3:
            # Phase 1: Setup
            phase1 = PhaseSpec(
                phase_number=1,
                phase_name="Frontend Setup",
                goal="Set up frontend development environment and basic structure",
                duration="1-2 days",
                features=[
                    "Next.js/React app with TypeScript setup",
                    "UI framework and styling configuration",
                    "Development environment configuration",
                    "Basic project structure"
                ],
                user_stories=[
                    "As a developer, I can clone the repo and install dependencies",
                    "As a developer, I can run the development server",
                    "As a developer, I can see the basic app structure"
                ],
                technical_tasks=[
                    "Set up Next.js/React with TypeScript",
                    "Configure Tailwind CSS or chosen styling framework",
                    "Set up development tools and linting",
                    "Create basic folder structure and components"
                ],
                success_criteria=[
                    "Development server starts successfully",
                    "Basic routing and navigation work",
                    "UI framework is properly configured",
                    "TypeScript compilation works without errors"
                ],
                ai_prompt="Set up a complete frontend development environment with React/Next.js, TypeScript, and modern tooling.",
                test_commands=[
                    "npm run dev starts successfully",
                    "npm run build completes without errors",
                    "Basic page renders correctly"
                ]
            )
            phases.append(phase1)

            # Phase 2: Core UI
            phase2 = PhaseSpec(
                phase_number=2,
                phase_name="Core UI Development",
                goal="Build the core user interface and user experience",
                duration="2-3 days",
                features=[
                    "Complete component library",
                    "Main application pages and layouts",
                    "State management implementation",
                    "Responsive design implementation"
                ],
                user_stories=[
                    "As a user, I can navigate through the application",
                    "As a user, I can see all main UI components",
                    "As a user, the interface works on mobile and desktop",
                    "As a user, I can interact with form elements"
                ],
                technical_tasks=[
                    "Create reusable component library",
                    "Implement main application pages",
                    "Set up state management (Zustand/Redux)",
                    "Implement responsive layouts and styling",
                    "Add form validation and error handling"
                ],
                success_criteria=[
                    "All main UI components are implemented",
                    "Application is fully responsive",
                    "State management works correctly",
                    "User interactions are smooth and intuitive"
                ],
                ai_prompt="Build a complete frontend application with modern UI components, state management, and responsive design.",
                test_commands=[
                    "All pages render correctly",
                    "Responsive design works on mobile/desktop",
                    "Component interactions work properly",
                    "State updates correctly"
                ]
            )
            phases.append(phase2)

            # Phase 3: Integration & Polish (if phase_count >= 3)
            if phase_count >= 3:
                phase3 = PhaseSpec(
                    phase_number=3,
                    phase_name="Integration & Testing",
                    goal="Integrate all components and prepare for deployment",
                    duration="1-2 days",
                    features=[
                        "Component integration and testing",
                        "Performance optimization",
                        "Error handling and edge cases",
                        "Production build configuration"
                    ],
                    user_stories=[
                        "As a user, I can complete full workflows without errors",
                        "As a user, the application performs well",
                        "As a developer, I can deploy the application"
                    ],
                    technical_tasks=[
                        "Integrate all components and features",
                        "Implement error boundaries and error pages",
                        "Performance optimization and bundle analysis",
                        "Configure production builds and deployment"
                    ],
                    success_criteria=[
                        "All user workflows work end-to-end",
                        "Application performance is optimized",
                        "Error handling is comprehensive",
                        "Production build is ready for deployment"
                    ],
                    ai_prompt="Complete the frontend application with comprehensive testing, error handling, and production readiness.",
                    test_commands=[
                        "End-to-end user flows work correctly",
                        "Performance metrics are within acceptable ranges",
                        "Error scenarios are handled gracefully",
                        "Production build succeeds"
                    ]
                )
                phases.append(phase3)

        return phases

    async def _plan_backend_phases(self, analysis: IdeaAnalysis, phase_count: int) -> List[PhaseSpec]:
        """Plan phases for backend-only projects."""
        phases = []

        if phase_count >= 4:
            # Phase 1: Backend Setup
            phase1 = PhaseSpec(
                phase_number=1,
                phase_name="Backend Foundation",
                goal="Set up backend development environment and basic structure",
                duration="1-2 days",
                features=[
                    "API framework setup (FastAPI/Flask)",
                    "Database configuration and models",
                    "Basic project structure and dependencies",
                    "Development environment setup"
                ],
                user_stories=[
                    "As a developer, I can clone the repo and install dependencies",
                    "As a developer, I can run the development server",
                    "As a developer, I can connect to the database"
                ],
                technical_tasks=[
                    "Set up FastAPI/Flask with proper structure",
                    "Configure database connection and ORM",
                    "Create basic data models",
                    "Set up development tools and testing framework"
                ],
                success_criteria=[
                    "API server starts successfully",
                    "Database connection works",
                    "Basic data models are defined",
                    "Development environment is properly configured"
                ],
                ai_prompt="Set up a complete backend development environment with API framework, database, and modern tooling.",
                test_commands=[
                    "API server starts successfully",
                    "Database migrations run without errors",
                    "Basic API endpoints respond"
                ]
            )
            phases.append(phase1)

            # Phase 2: API Core
            phase2 = PhaseSpec(
                phase_number=2,
                phase_name="API Development",
                goal="Build the core API endpoints and business logic",
                duration="2-3 days",
                features=[
                    "Complete REST API endpoints",
                    "Input validation and error handling",
                    "Business logic implementation",
                    "API documentation generation"
                ],
                user_stories=[
                    "As a frontend developer, I can call API endpoints",
                    "As a user, I can perform CRUD operations through API",
                    "As a developer, I can see comprehensive API documentation"
                ],
                technical_tasks=[
                    "Implement all CRUD operations for entities",
                    "Add comprehensive input validation",
                    "Implement business logic and data processing",
                    "Generate OpenAPI/Swagger documentation"
                ],
                success_criteria=[
                    "All core API endpoints are implemented",
                    "Input validation works correctly",
                    "Error responses are proper and informative",
                    "API documentation is automatically generated"
                ],
                ai_prompt="Build a complete REST API with proper validation, error handling, business logic, and documentation.",
                test_commands=[
                    "All API endpoints return correct responses",
                    "Input validation rejects invalid data",
                    "API documentation generates correctly",
                    "Error scenarios return appropriate status codes"
                ]
            )
            phases.append(phase2)

            # Phase 3: Database & Integration
            phase3 = PhaseSpec(
                phase_number=3,
                phase_name="Database & Integration",
                goal="Complete database integration and system integration",
                duration="1-2 days",
                features=[
                    "Complete database schema and relationships",
                    "Data migration and seeding",
                    "Integration testing",
                    "Performance optimization"
                ],
                user_stories=[
                    "As a developer, I can run database migrations",
                    "As a system, all components work together",
                    "As a user, data operations are fast and reliable"
                ],
                technical_tasks=[
                    "Complete database schema with relationships",
                    "Implement data migrations and seeding",
                    "Set up integration testing",
                    "Optimize database queries and performance"
                ],
                success_criteria=[
                    "Database schema is complete and normalized",
                    "All data relationships work correctly",
                    "Integration tests pass",
                    "Database performance is optimized"
                ],
                ai_prompt="Complete the database integration with proper schema, migrations, testing, and performance optimization.",
                test_commands=[
                    "Database migrations run successfully",
                    "Integration tests pass",
                    "Database queries are optimized",
                    "Data integrity is maintained"
                ]
            )
            phases.append(phase3)

            # Phase 4: Production Readiness (if phase_count >= 4)
            if phase_count >= 4:
                phase4 = PhaseSpec(
                    phase_number=4,
                    phase_name="Production Readiness",
                    goal="Prepare backend for production deployment",
                    duration="1 day",
                    features=[
                        "Production configuration",
                        "Security hardening",
                        "Monitoring and logging setup",
                        "Deployment preparation"
                    ],
                    user_stories=[
                        "As a developer, I can deploy the API to production",
                        "As a system, security best practices are implemented",
                        "As a developer, I can monitor API performance"
                    ],
                    technical_tasks=[
                        "Configure production environment settings",
                        "Implement security best practices",
                        "Set up monitoring and logging",
                        "Prepare deployment configurations"
                    ],
                    success_criteria=[
                        "Production configuration is complete",
                        "Security vulnerabilities are addressed",
                        "Monitoring and logging are configured",
                        "Deployment is ready"
                    ],
                    ai_prompt="Prepare the backend API for production with security, monitoring, and deployment configurations.",
                    test_commands=[
                        "Production configuration loads correctly",
                        "Security headers are properly set",
                        "Monitoring endpoints work",
                        "Deployment scripts are ready"
                    ]
                )
                phases.append(phase4)

        return phases

    async def _plan_fullstack_phases(self, analysis: IdeaAnalysis, phase_count: int = 4) -> List[PhaseSpec]:
        """Plan phases for full-stack projects."""
        phases = []

        # Phase 1: Setup & Foundation
        phase1 = PhaseSpec(
            phase_number=1,
            phase_name="Foundation",
            goal="Set up development environment and basic project structure",
            duration="2-3 days",
            features=[
                "Project scaffolding with proper folder structure",
                "Package.json/requirements.txt with all dependencies",
                "Environment configuration (.env, config files)",
                "Basic linting and formatting setup",
                "Database connection and basic schema setup"
            ],
            user_stories=[
                "As a developer, I can clone the repo and install dependencies",
                "As a developer, I can run the development servers",
                "As a developer, I can connect to the database"
            ],
            technical_tasks=[
                "Create Next.js/React app with TypeScript",
                "Set up FastAPI/Flask backend with proper structure",
                "Configure database models and migrations",
                "Set up authentication system",
                "Create basic CI/CD pipeline",
                "Set up testing infrastructure"
            ],
            tasks=[
                PhaseTask(
                    task_id="setup_frontend",
                    description="Set up frontend framework and basic structure",
                    deliverables=["Frontend package.json", "Basic component structure", "TypeScript config"],
                    dependencies=[],
                    test_requirements=["Frontend builds successfully", "Dev server starts"]
                ),
                PhaseTask(
                    task_id="setup_backend",
                    description="Set up backend framework and basic structure",
                    deliverables=["Backend requirements.txt", "Basic API structure", "Database models"],
                    dependencies=[],
                    test_requirements=["Backend server starts", "Database connection works"]
                ),
                PhaseTask(
                    task_id="setup_database",
                    description="Set up database schema and initial migrations",
                    deliverables=["Database schema", "Initial migration files", "Seed data"],
                    dependencies=["setup_backend"],
                    test_requirements=["Migrations run successfully", "Basic CRUD operations work"]
                ),
                PhaseTask(
                    task_id="setup_auth",
                    description="Set up authentication system",
                    deliverables=["Auth endpoints", "JWT handling", "User model"],
                    dependencies=["setup_backend", "setup_database"],
                    test_requirements=["User registration works", "Login/logout works"]
                )
            ],
            success_criteria=[
                "Both frontend and backend development servers start successfully",
                "Database connection established and migrations run",
                "Basic authentication flow works",
                "All dependencies installed and configured",
                "Code formatting and linting configured"
            ],
            ai_prompt="Set up a complete full-stack development environment with Next.js frontend, FastAPI backend, database integration, and authentication. Include proper TypeScript types, environment configuration, and testing setup.",
            test_commands=[
                "npm run dev (frontend)",
                "python main.py (backend)",
                "Database migrations run",
                "Basic API endpoints respond"
            ]
        )
        phases.append(phase1)

        # Phase 2: Core Backend API
        phase2 = PhaseSpec(
            phase_number=2,
            phase_name="Core API",
            goal="Build the core backend API with data models and business logic",
            duration="3-4 days",
            features=[
                "Complete data models with proper relationships",
                "REST API endpoints for all core entities",
                "Input validation and error handling",
                "Basic business logic implementation",
                "API documentation with OpenAPI/Swagger"
            ],
            user_stories=[
                "As a frontend developer, I can call API endpoints to manage data",
                "As a user, I can perform CRUD operations through the API",
                "As a developer, I can see comprehensive API documentation"
            ],
            technical_tasks=[
                "Design and implement database schema",
                "Create Pydantic models for API validation",
                "Implement CRUD operations for all entities",
                "Add proper error handling and validation",
                "Write comprehensive API tests",
                "Generate OpenAPI documentation"
            ],
            tasks=[
                PhaseTask(
                    task_id="design_schema",
                    description="Design complete database schema with relationships",
                    deliverables=["Entity relationship diagram", "SQL schema files", "Model definitions"],
                    dependencies=["setup_database"],
                    test_requirements=["Schema validates correctly", "Relationships work properly"]
                ),
                PhaseTask(
                    task_id="implement_models",
                    description="Implement database models and relationships",
                    deliverables=["SQLAlchemy/FastAPI models", "Migration files", "Model tests"],
                    dependencies=["design_schema"],
                    test_requirements=["Models create successfully", "Relationships work", "Migrations run"]
                ),
                PhaseTask(
                    task_id="create_endpoints",
                    description="Create REST API endpoints for all entities",
                    deliverables=["API route handlers", "Request/response models", "Endpoint tests"],
                    dependencies=["implement_models"],
                    test_requirements=["All endpoints return correct responses", "Validation works", "Error handling proper"]
                ),
                PhaseTask(
                    task_id="add_validation",
                    description="Add comprehensive input validation and error handling",
                    deliverables=["Pydantic validators", "Error response models", "Validation tests"],
                    dependencies=["create_endpoints"],
                    test_requirements=["Invalid inputs rejected", "Proper error messages", "Edge cases handled"]
                )
            ],
            success_criteria=[
                "All core API endpoints implemented and tested",
                "Database schema properly designed with relationships",
                "Input validation and error handling complete",
                "API documentation automatically generated",
                "All API tests pass",
                "Postman/collection for testing API endpoints"
            ],
            ai_prompt="Build a complete REST API with proper data models, validation, error handling, and documentation. Include all CRUD operations, relationships, and comprehensive testing.",
            test_commands=[
                "API tests pass (pytest)",
                "OpenAPI documentation generates",
                "All endpoints return 200 for valid requests",
                "Invalid requests return proper error codes"
            ]
        )
        phases.append(phase2)

        # Phase 3: Frontend Core
        phase3 = PhaseSpec(
            phase_number=3,
            phase_name="Frontend Core",
            goal="Build the core frontend application with state management and API integration",
            duration="4-5 days",
            features=[
                "Complete UI component library",
                "State management for all data entities",
                "API client with error handling",
                "Authentication UI and flow",
                "Responsive design implementation",
                "Basic routing and navigation"
            ],
            user_stories=[
                "As a user, I can navigate through the application",
                "As a user, I can log in and see my data",
                "As a user, I can perform basic CRUD operations through the UI",
                "As a user, the interface works on mobile and desktop"
            ],
            technical_tasks=[
                "Set up React/Next.js with TypeScript",
                "Create reusable component library",
                "Implement state management (Zustand/Redux)",
                "Build API client with error handling",
                "Create authentication pages and components",
                "Implement responsive layouts",
                "Add form validation and error display",
                "Write component tests"
            ],
            tasks=[
                PhaseTask(
                    task_id="setup_state",
                    description="Set up state management system",
                    deliverables=["State store configuration", "State types", "Basic state tests"],
                    dependencies=["setup_frontend"],
                    test_requirements=["State updates correctly", "State persists properly"]
                ),
                PhaseTask(
                    task_id="create_api_client",
                    description="Create API client for backend communication",
                    deliverables=["API client functions", "Error handling", "TypeScript types", "API client tests"],
                    dependencies=["setup_state"],
                    test_requirements=["API calls work", "Error handling proper", "Types match backend"]
                ),
                PhaseTask(
                    task_id="build_auth_ui",
                    description="Build authentication UI components",
                    deliverables=["Login/signup forms", "Auth state management", "Protected routes", "Auth tests"],
                    dependencies=["create_api_client"],
                    test_requirements=["Login flow works", "Protected routes function", "Auth state persists"]
                ),
                PhaseTask(
                    task_id="create_components",
                    description="Create core UI components and layouts",
                    deliverables=["Component library", "Layout components", "Form components", "Component tests"],
                    dependencies=["build_auth_ui"],
                    test_requirements=["Components render correctly", "Props work properly", "Accessibility good"]
                )
            ],
            success_criteria=[
                "All core UI components implemented and tested",
                "State management working for all data entities",
                "API integration complete with error handling",
                "Authentication flow fully functional",
                "Responsive design implemented",
                "All component tests pass",
                "Basic CRUD operations work through UI"
            ],
            ai_prompt="Build a complete frontend application with TypeScript, state management, API integration, authentication, and responsive design. Include comprehensive component library and testing.",
            test_commands=[
                "Component tests pass (Jest)",
                "E2E tests for auth flow pass",
                "API integration tests pass",
                "Responsive design works on mobile/desktop",
                "All form validations work"
            ]
        )
        phases.append(phase3)

        # Phase 4: Integration & Testing
        phase4 = PhaseSpec(
            phase_number=4,
            phase_name="Integration",
            goal="Integrate frontend and backend, add comprehensive testing, and prepare for deployment",
            duration="2-3 days",
            features=[
                "End-to-end API integration testing",
                "Complete user workflows tested",
                "Performance optimization",
                "Error boundary implementation",
                "Production build configuration",
                "Deployment preparation"
            ],
            user_stories=[
                "As a user, I can complete full workflows without errors",
                "As a developer, I can deploy the application to production",
                "As a user, the application performs well and handles errors gracefully"
            ],
            technical_tasks=[
                "Set up end-to-end testing (Playwright/Cypress)",
                "Test complete user journeys",
                "Implement error boundaries and error pages",
                "Add loading states and optimistic updates",
                "Configure production builds",
                "Set up monitoring and logging",
                "Performance optimization",
                "Security hardening"
            ],
            tasks=[
                PhaseTask(
                    task_id="e2e_testing",
                    description="Set up and implement end-to-end testing",
                    deliverables=["E2E test suite", "Test scenarios", "CI integration", "Test reports"],
                    dependencies=["create_components", "create_endpoints"],
                    test_requirements=["All user journeys work", "No critical bugs", "Performance acceptable"]
                ),
                PhaseTask(
                    task_id="error_handling",
                    description="Implement comprehensive error handling and boundaries",
                    deliverables=["Error boundaries", "Error pages", "Global error handling", "Error tests"],
                    dependencies=["e2e_testing"],
                    test_requirements=["Errors handled gracefully", "Users see helpful messages", "App doesn't crash"]
                ),
                PhaseTask(
                    task_id="performance",
                    description="Optimize performance and user experience",
                    deliverables=["Performance optimizations", "Loading states", "Caching strategy", "Performance tests"],
                    dependencies=["error_handling"],
                    test_requirements=["Load times acceptable", "No performance regressions", "Bundle size optimized"]
                ),
                PhaseTask(
                    task_id="production_prep",
                    description="Prepare for production deployment",
                    deliverables=["Production config", "Environment setup", "Deployment scripts", "Monitoring setup"],
                    dependencies=["performance"],
                    test_requirements=["Production build works", "Deployment succeeds", "Monitoring active"]
                )
            ],
            success_criteria=[
                "End-to-end tests pass for all critical user journeys",
                "Error handling comprehensive and user-friendly",
                "Performance optimized and monitored",
                "Production deployment ready",
                "Security best practices implemented",
                "Monitoring and logging configured",
                "All integration tests pass"
            ],
            ai_prompt="Complete the full-stack integration with comprehensive testing, error handling, performance optimization, and production readiness. Ensure seamless frontend-backend communication.",
            test_commands=[
                "E2E tests pass (Playwright/Cypress)",
                "Integration tests pass",
                "Performance tests pass",
                "Production build succeeds",
                "Deployment scripts work"
            ]
        )
        phases.append(phase4)

        return phases

    async def _plan_simple_phases(self, analysis: IdeaAnalysis) -> List[PhaseSpec]:
        """Plan phases for simpler projects (CLI tools, APIs, etc.)."""

        # Determine phase count for simple projects
        complexity = self._estimate_complexity(analysis)
        phase_count = max(1, min(3, self.determine_phase_count("BACKEND", complexity, analysis.project_size.value)))

        phases = []

        if phase_count >= 1:
            phase1 = PhaseSpec(
                phase_number=1,
                phase_name="Core Implementation",
                goal="Implement the core functionality",
                duration=f"{analysis.estimated_hours // phase_count} hours",
                features=analysis.mvp_features[:max(3, len(analysis.mvp_features) // phase_count)],
                user_stories=[],
                technical_tasks=analysis.mvp_features[:max(3, len(analysis.mvp_features) // phase_count)],
                tasks=[],
                success_criteria=[
                    "Core functionality works",
                    "Basic tests pass",
                    "Code is documented"
                ],
                ai_prompt=f"Implement {analysis.title} with {analysis.project_type.value if hasattr(analysis.project_type, 'value') else analysis.project_type} architecture. Focus on clean code and proper testing.",
                test_commands=["Basic functionality tests pass"]
            )
            phases.append(phase1)

        if phase_count >= 2:
            phase2 = PhaseSpec(
                phase_number=2,
                phase_name="Testing & Refinement",
                goal="Add comprehensive testing and refine implementation",
                duration=f"{analysis.estimated_hours // phase_count} hours",
                features=["Unit tests", "Integration tests", "Error handling"],
                user_stories=[],
                technical_tasks=["Write comprehensive tests", "Add error handling", "Performance optimization"],
                tasks=[],
                success_criteria=[
                    "All tests pass",
                    "Error handling is comprehensive",
                    "Performance is acceptable"
                ],
                ai_prompt="Add comprehensive testing, error handling, and performance optimization to the implementation.",
                test_commands=["All tests pass", "Error scenarios handled", "Performance benchmarks met"]
            )
            phases.append(phase2)

        if phase_count >= 3:
            phase3 = PhaseSpec(
                phase_number=3,
                phase_name="Production Readiness",
                goal="Prepare for production deployment",
                duration=f"{analysis.estimated_hours // phase_count} hours",
                features=["Documentation", "Deployment config", "Monitoring setup"],
                user_stories=[],
                technical_tasks=["Write documentation", "Configure deployment", "Set up monitoring"],
                tasks=[],
                success_criteria=[
                    "Documentation is complete",
                    "Deployment configuration ready",
                    "Monitoring is configured"
                ],
                ai_prompt="Complete documentation, deployment configuration, and monitoring setup for production.",
                test_commands=["Documentation builds", "Deployment config works", "Monitoring active"]
            )
            phases.append(phase3)

        return phases

    def get_phase_dependencies(self, phases: List[PhaseSpec]) -> Dict[str, List[str]]:
        """
        Extract phase dependencies from task dependencies.

        Args:
            phases: List of phase specifications

        Returns:
            Dict mapping phase names to lists of prerequisite phase names
        """
        dependencies = {}

        for phase in phases:
            phase_deps = set()
            for task in phase.tasks:
                # Find which phases contain the prerequisite tasks
                for other_phase in phases:
                    if other_phase.phase_number != phase.phase_number:
                        if any(t.task_id in task.dependencies for t in other_phase.tasks):
                            phase_deps.add(other_phase.phase_name)

            dependencies[phase.phase_name] = list(phase_deps)

        return dependencies
