"""
Ideas Machine Agent Tests
Comprehensive tests for the Ideas Machine agent components.
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import json
import tempfile
import shutil


# ============================================================================
# MODEL TESTS
# ============================================================================

class TestIdeasMachineModels:
    """Tests for Ideas Machine data models."""
    
    def test_project_size_enum(self):
        """Test ProjectSize enum values."""
        from agents.ideas_machine.models import ProjectSize
        
        assert ProjectSize.MICRO == "MICRO"
        assert ProjectSize.SMALL == "SMALL"
        assert ProjectSize.MEDIUM == "MEDIUM"
        assert ProjectSize.LARGE == "LARGE"
    
    def test_project_type_enum(self):
        """Test ProjectType enum values."""
        from agents.ideas_machine.models import ProjectType
        
        assert ProjectType.WEB_APP == "WEB_APP"
        assert ProjectType.API_SERVICE == "API_SERVICE"
        assert ProjectType.CLI_TOOL == "CLI_TOOL"
        assert ProjectType.MOBILE_APP == "MOBILE_APP"
        assert ProjectType.CHROME_EXTENSION == "CHROME_EXTENSION"
        assert ProjectType.DATA_PIPELINE == "DATA_PIPELINE"
        assert ProjectType.AI_APP == "AI_APP"
    
    def test_idea_input_creation(self):
        """Test IdeaInput model creation."""
        from agents.ideas_machine.models import IdeaInput
        
        idea = IdeaInput(
            description="Build a task management app with AI prioritization",
            reference_urls=["https://todoist.com", "https://notion.so"],
            constraints={"budget": "low", "timeline": "2 weeks"},
            preferences={"tech": "Python"}
        )
        
        assert "task management" in idea.description
        assert len(idea.reference_urls) == 2
        assert idea.constraints["budget"] == "low"
        assert idea.preferences["tech"] == "Python"
    
    def test_idea_input_defaults(self):
        """Test IdeaInput default values."""
        from agents.ideas_machine.models import IdeaInput
        
        idea = IdeaInput(description="Simple idea")
        
        assert idea.description == "Simple idea"
        assert idea.reference_urls == []
        assert idea.constraints == {}
        assert idea.preferences == {}
    
    def test_idea_analysis_creation(self):
        """Test IdeaAnalysis model creation."""
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analysis = IdeaAnalysis(
            title="TaskAI",
            description="AI-powered task management",
            problem_statement="People struggle to prioritize tasks",
            target_user="Busy professionals",
            value_proposition="Automatic task prioritization",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=80,
            core_features=["Task creation", "AI prioritization", "Calendar view"],
            mvp_features=["Task creation", "Basic AI sorting"],
            future_features=["Team collaboration", "Integrations"],
            risks=["AI accuracy may vary"],
            assumptions=["Users have internet access"]
        )
        
        assert analysis.title == "TaskAI"
        assert analysis.project_type == ProjectType.WEB_APP
        assert analysis.project_size == ProjectSize.SMALL
        assert analysis.estimated_hours == 80
        assert len(analysis.core_features) == 3
        assert len(analysis.mvp_features) == 2
    
    def test_tech_stack_recommendation_creation(self):
        """Test TechStackRecommendation model creation."""
        from agents.ideas_machine.models import TechStackRecommendation
        
        stack = TechStackRecommendation(
            frontend={"framework": "Next.js", "styling": "Tailwind"},
            backend={"framework": "FastAPI", "database": "PostgreSQL"},
            infrastructure={"hosting": "Vercel", "ci_cd": "GitHub Actions"},
            reasoning="Modern stack for rapid development",
            alternatives=[{"framework": "SvelteKit"}]
        )
        
        assert stack.frontend["framework"] == "Next.js"
        assert stack.backend["database"] == "PostgreSQL"
        assert stack.infrastructure["hosting"] == "Vercel"
        assert "rapid development" in stack.reasoning
    
    def test_project_architecture_creation(self):
        """Test ProjectArchitecture model creation."""
        from agents.ideas_machine.models import ProjectArchitecture
        
        arch = ProjectArchitecture(
            overview="Three-tier web application",
            components=[
                {"name": "Frontend", "purpose": "User interface", "technology": "Next.js"},
                {"name": "API", "purpose": "Business logic", "technology": "FastAPI"}
            ],
            data_flow="User -> Frontend -> API -> Database",
            api_endpoints=[
                {"method": "GET", "path": "/api/tasks", "description": "List tasks"},
                {"method": "POST", "path": "/api/tasks", "description": "Create task"}
            ],
            data_models=[
                {"name": "Task", "fields": "id, title, priority", "relationships": "belongs to User"}
            ],
            diagrams={"system": "ASCII diagram here"}
        )
        
        assert "Three-tier" in arch.overview
        assert len(arch.components) == 2
        assert len(arch.api_endpoints) == 2
        assert len(arch.data_models) == 1
    
    def test_project_scaffold_creation(self):
        """Test ProjectScaffold model creation."""
        from agents.ideas_machine.models import ProjectScaffold
        
        scaffold = ProjectScaffold(
            project_name="taskai",
            project_path="/projects/taskai",
            directories=["src", "tests", "docs"],
            files=[{"path": "README.md", "content": "# TaskAI"}],
            documentation={"master_plan": "# Master Plan"},
            prompts=[{"filename": "setup.md", "content": "Setup prompt"}],
            created_at=datetime.utcnow()
        )
        
        assert scaffold.project_name == "taskai"
        assert len(scaffold.directories) == 3
        assert len(scaffold.files) == 1
        assert scaffold.created_at is not None
    
    def test_phase_spec_creation(self):
        """Test PhaseSpec model creation."""
        from agents.ideas_machine.models import PhaseSpec
        
        phase = PhaseSpec(
            phase_number=1,
            phase_name="MVP",
            goal="Build core functionality",
            duration="2 weeks",
            features=["Task creation", "Task list"],
            user_stories=["As a user, I can create tasks"],
            technical_tasks=["Set up database", "Create API"],
            success_criteria=["Users can create and view tasks"]
        )
        
        assert phase.phase_number == 1
        assert phase.phase_name == "MVP"
        assert len(phase.features) == 2
        assert len(phase.success_criteria) == 1


# ============================================================================
# ANALYZER TESTS
# ============================================================================

class TestIdeaAnalyzer:
    """Tests for IdeaAnalyzer component."""
    
    def test_analyzer_initialization(self):
        """Test IdeaAnalyzer initialization."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        
        analyzer = IdeaAnalyzer()
        
        assert analyzer.client is not None
    
    def test_estimate_complexity_micro(self):
        """Test complexity estimation for micro project."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analyzer = IdeaAnalyzer()
        
        analysis = IdeaAnalysis(
            title="Simple Tool",
            description="A simple CLI tool",
            problem_statement="Need automation",
            target_user="Developers",
            value_proposition="Saves time",
            project_type=ProjectType.CLI_TOOL,
            project_size=ProjectSize.MICRO,
            estimated_hours=10,
            core_features=["Feature 1"],
            mvp_features=["Feature 1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        complexity = analyzer.estimate_complexity(analysis)
        
        assert complexity["classification"] == "MICRO"
        assert complexity["overall"] <= 5
    
    def test_estimate_complexity_large(self):
        """Test complexity estimation for large project."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analyzer = IdeaAnalyzer()
        
        analysis = IdeaAnalysis(
            title="Enterprise App",
            description="Full enterprise solution",
            problem_statement="Complex business needs",
            target_user="Enterprises",
            value_proposition="Complete solution",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.LARGE,
            estimated_hours=500,
            core_features=["F1", "F2", "F3", "F4", "F5", "F6", "F7"],
            mvp_features=["F1", "F2", "F3", "F4", "F5", "F6", "F7"],
            future_features=["F8", "F9"],
            risks=["Complex"],
            assumptions=[]
        )
        
        complexity = analyzer.estimate_complexity(analysis)
        
        assert complexity["classification"] == "LARGE"
        assert complexity["overall"] >= 5
    
    def test_estimate_complexity_frontend_score(self):
        """Test frontend complexity scoring based on feature count."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analyzer = IdeaAnalyzer()
        
        # Few features
        small_analysis = IdeaAnalysis(
            title="Small",
            description="Small app",
            problem_statement="Simple",
            target_user="Users",
            value_proposition="Basic",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1", "F2"],
            mvp_features=["F1", "F2"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        small_complexity = analyzer.estimate_complexity(small_analysis)
        assert small_complexity["frontend"] == 3  # <= 3 features
    
    def test_estimate_complexity_backend_by_type(self):
        """Test backend complexity scoring by project type."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analyzer = IdeaAnalyzer()
        
        # CLI tool (simpler)
        cli_analysis = IdeaAnalysis(
            title="CLI",
            description="CLI tool",
            problem_statement="Automation",
            target_user="Devs",
            value_proposition="Fast",
            project_type=ProjectType.CLI_TOOL,
            project_size=ProjectSize.SMALL,
            estimated_hours=20,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        # AI App (more complex)
        ai_analysis = IdeaAnalysis(
            title="AI App",
            description="AI application",
            problem_statement="ML needs",
            target_user="Data scientists",
            value_proposition="AI power",
            project_type=ProjectType.AI_APP,
            project_size=ProjectSize.MEDIUM,
            estimated_hours=200,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        cli_complexity = analyzer.estimate_complexity(cli_analysis)
        ai_complexity = analyzer.estimate_complexity(ai_analysis)
        
        assert cli_complexity["backend"] < ai_complexity["backend"]
    
    @pytest.mark.asyncio
    async def test_analyze_returns_idea_analysis(self):
        """Test that analyze returns IdeaAnalysis."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaInput, IdeaAnalysis
        from agents.llm_client import LLMResponse
        
        analyzer = IdeaAnalyzer()
        
        # Mock the LLM response
        mock_response = LLMResponse(content=json.dumps({
            "title": "TestApp",
            "description": "A test application",
            "problem_statement": "Testing problem",
            "target_user": "Testers",
            "value_proposition": "Testing value",
            "project_type": "WEB_APP",
            "project_size": "SMALL",
            "estimated_hours": 40,
            "core_features": ["Feature 1"],
            "mvp_features": ["Feature 1"],
            "future_features": ["Feature 2"],
            "risks": ["Risk 1"],
            "assumptions": ["Assumption 1"]
        }))
        
        with patch.object(analyzer.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            
            idea_input = IdeaInput(description="Build a test app")
            result = await analyzer.analyze(idea_input)
            
            assert isinstance(result, IdeaAnalysis)
            assert result.title == "TestApp"


# ============================================================================
# ARCHITECT TESTS
# ============================================================================

class TestSystemArchitect:
    """Tests for SystemArchitect component."""
    
    def test_architect_initialization(self):
        """Test SystemArchitect initialization."""
        from agents.ideas_machine.architect import SystemArchitect
        
        architect = SystemArchitect()
        
        assert architect.client is not None
        assert len(architect.STACK_PRESETS) > 0
    
    def test_stack_presets_exist_for_web_app(self):
        """Test that stack presets exist for WEB_APP."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import ProjectType
        
        architect = SystemArchitect()
        
        assert ProjectType.WEB_APP in architect.STACK_PRESETS
        preset = architect.STACK_PRESETS[ProjectType.WEB_APP]
        
        assert "frontend" in preset
        assert "backend" in preset
        assert "infrastructure" in preset
    
    def test_stack_presets_exist_for_api_service(self):
        """Test that stack presets exist for API_SERVICE."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import ProjectType
        
        architect = SystemArchitect()
        
        assert ProjectType.API_SERVICE in architect.STACK_PRESETS
        preset = architect.STACK_PRESETS[ProjectType.API_SERVICE]
        
        assert "backend" in preset
        assert "infrastructure" in preset
    
    def test_stack_presets_exist_for_cli_tool(self):
        """Test that stack presets exist for CLI_TOOL."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import ProjectType
        
        architect = SystemArchitect()
        
        assert ProjectType.CLI_TOOL in architect.STACK_PRESETS
        preset = architect.STACK_PRESETS[ProjectType.CLI_TOOL]
        
        assert "backend" in preset
    
    def test_generate_system_diagram(self):
        """Test system diagram generation."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        architect = SystemArchitect()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="Test app",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js"},
            backend={"framework": "FastAPI", "database": "PostgreSQL"},
            infrastructure={"hosting": "Vercel"},
            reasoning="Good stack",
            alternatives=[]
        )
        
        diagram = architect._generate_system_diagram(analysis, tech_stack)
        
        assert "TESTAPP" in diagram
        assert "Next.js" in diagram or "Frontend" in diagram
        assert "Database" in diagram
    
    def test_generate_data_flow_diagram(self):
        """Test data flow diagram generation."""
        from agents.ideas_machine.architect import SystemArchitect
        
        architect = SystemArchitect()
        
        data_flow = "User submits form, API validates, stores in DB"
        diagram = architect._generate_data_flow_diagram(data_flow)
        
        assert "DATA FLOW" in diagram
        assert "User Action" in diagram
    
    @pytest.mark.asyncio
    async def test_recommend_tech_stack_returns_recommendation(self):
        """Test that recommend_tech_stack returns TechStackRecommendation."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        from agents.llm_client import LLMResponse
        
        architect = SystemArchitect()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="Test app",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["Feature 1"],
            mvp_features=["Feature 1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        mock_response = LLMResponse(content=json.dumps({
            "frontend": {"framework": "Next.js"},
            "backend": {"framework": "FastAPI"},
            "infrastructure": {"hosting": "Vercel"},
            "reasoning": "Good for this project",
            "alternatives": []
        }))
        
        with patch.object(architect.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await architect.recommend_tech_stack(analysis)
            
            assert isinstance(result, TechStackRecommendation)
    
    @pytest.mark.asyncio
    async def test_design_architecture_returns_architecture(self):
        """Test that design_architecture returns ProjectArchitecture."""
        from agents.ideas_machine.architect import SystemArchitect
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
            ProjectSize, ProjectType
        )
        from agents.llm_client import LLMResponse
        
        architect = SystemArchitect()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="Test app",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["Feature 1"],
            mvp_features=["Feature 1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js"},
            backend={"framework": "FastAPI"},
            infrastructure={"hosting": "Vercel"},
            reasoning="Good stack",
            alternatives=[]
        )
        
        mock_response = LLMResponse(content=json.dumps({
            "overview": "System overview",
            "components": [{"name": "API", "purpose": "Handle requests", "technology": "FastAPI"}],
            "data_flow": "User -> API -> DB",
            "api_endpoints": [{"method": "GET", "path": "/api/items", "description": "List items"}],
            "data_models": [{"name": "Item", "fields": "id, name", "relationships": "none"}]
        }))
        
        with patch.object(architect.client, 'chat', new_callable=AsyncMock) as mock_chat:
            mock_chat.return_value = mock_response
            
            result = await architect.design_architecture(analysis, tech_stack)
            
            assert isinstance(result, ProjectArchitecture)
            assert result.overview == "System overview"


# ============================================================================
# SCAFFOLDER TESTS
# ============================================================================

class TestProjectScaffolder:
    """Tests for ProjectScaffolder component."""
    
    def test_scaffolder_initialization(self):
        """Test ProjectScaffolder initialization."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        assert scaffolder.output_path is not None
    
    def test_sanitize_name_basic(self):
        """Test name sanitization for basic names."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        assert scaffolder._sanitize_name("My Project") == "my_project"
        assert scaffolder._sanitize_name("TestApp") == "testapp"
    
    def test_sanitize_name_special_chars(self):
        """Test name sanitization with special characters."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        assert scaffolder._sanitize_name("My Project! @#$") == "my_project"
        assert scaffolder._sanitize_name("Test (1.0)") == "test_10"
    
    def test_sanitize_name_multiple_spaces(self):
        """Test name sanitization with multiple spaces."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        result = scaffolder._sanitize_name("My   Cool   Project")
        assert "___" not in result  # No triple underscores
    
    def test_generate_package_json(self):
        """Test package.json generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="A test application",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        package_json = scaffolder._generate_package_json(analysis)
        parsed = json.loads(package_json)
        
        assert parsed["name"] == "testapp"
        assert "next" in parsed["dependencies"]
        assert "dev" in parsed["scripts"]
    
    def test_generate_tsconfig(self):
        """Test tsconfig.json generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        tsconfig = scaffolder._generate_tsconfig()
        parsed = json.loads(tsconfig)
        
        assert parsed["compilerOptions"]["strict"] is True
        assert "src" in parsed["include"]
    
    def test_generate_gitignore(self):
        """Test .gitignore generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        
        scaffolder = ProjectScaffolder()
        
        gitignore = scaffolder._generate_gitignore()
        
        assert "node_modules" in gitignore
        assert ".env" in gitignore
        assert "__pycache__" in gitignore
    
    def test_generate_env_example_with_supabase(self):
        """Test .env.example generation with Supabase."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import TechStackRecommendation
        
        scaffolder = ProjectScaffolder()
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js"},
            backend={"database": "Supabase"},
            infrastructure={"hosting": "Vercel"},
            reasoning="Good",
            alternatives=[]
        )
        
        env = scaffolder._generate_env_example(tech_stack)
        
        assert "SUPABASE_URL" in env
        assert "SUPABASE_ANON_KEY" in env
    
    def test_generate_layout(self):
        """Test Next.js layout generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="A test application for testing purposes",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        layout = scaffolder._generate_layout(analysis)
        
        assert "TestApp" in layout
        assert "Metadata" in layout
        assert "RootLayout" in layout
    
    def test_generate_homepage(self):
        """Test Next.js homepage generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="A test application",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        homepage = scaffolder._generate_homepage(analysis)
        
        assert "TestApp" in homepage
        assert "export default function Home" in homepage
    
    def test_generate_fastapi_main(self):
        """Test FastAPI main.py generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestAPI",
            description="A test API",
            problem_statement="Test",
            target_user="Developers",
            value_proposition="Value",
            project_type=ProjectType.API_SERVICE,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        main_py = scaffolder._generate_fastapi_main(analysis)
        
        assert "FastAPI" in main_py
        assert "TestAPI" in main_py
        assert "@app.get" in main_py
    
    def test_generate_cli_main(self):
        """Test CLI main.py generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestCLI",
            description="A test CLI tool",
            problem_statement="Test",
            target_user="Developers",
            value_proposition="Value",
            project_type=ProjectType.CLI_TOOL,
            project_size=ProjectSize.MICRO,
            estimated_hours=10,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        main_py = scaffolder._generate_cli_main(analysis)
        
        assert "typer" in main_py
        assert "TestCLI" in main_py
    
    def test_generate_pyproject(self):
        """Test pyproject.toml generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestCLI",
            description="A test CLI tool",
            problem_statement="Test",
            target_user="Developers",
            value_proposition="Value",
            project_type=ProjectType.CLI_TOOL,
            project_size=ProjectSize.MICRO,
            estimated_hours=10,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        pyproject = scaffolder._generate_pyproject(analysis)
        
        assert "testcli" in pyproject
        assert "typer" in pyproject
        assert "poetry" in pyproject
    
    def test_generate_cursorrules(self):
        """Test .cursorrules generation."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="A test application",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["Feature 1"],
            mvp_features=["MVP Feature 1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js"},
            backend={"framework": "FastAPI"},
            infrastructure={"hosting": "Vercel"},
            reasoning="Good",
            alternatives=[]
        )
        
        cursorrules = scaffolder._generate_cursorrules(analysis, tech_stack)
        
        assert "TestApp" in cursorrules
        assert "WEB_APP" in cursorrules
        assert "MVP Feature 1" in cursorrules
    
    def test_format_tech_stack(self):
        """Test tech stack formatting."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import TechStackRecommendation
        
        scaffolder = ProjectScaffolder()
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js", "styling": "Tailwind"},
            backend={"framework": "FastAPI", "database": "PostgreSQL"},
            infrastructure={},
            reasoning="Good",
            alternatives=[]
        )
        
        formatted = scaffolder._format_tech_stack(tech_stack)
        
        assert "Frontend" in formatted
        assert "Next.js" in formatted
        assert "Backend" in formatted
        assert "FastAPI" in formatted
    
    def test_scaffold_nextjs_structure(self):
        """Test Next.js project structure scaffolding."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestApp",
            description="Test",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={"framework": "Next.js"},
            backend={},
            infrastructure={},
            reasoning="Good",
            alternatives=[]
        )
        
        directories, files = scaffolder._scaffold_nextjs(analysis, tech_stack)
        
        assert "src/app" in directories
        assert "src/components/ui" in directories
        assert any(f["path"] == "package.json" for f in files)
    
    def test_scaffold_fastapi_structure(self):
        """Test FastAPI project structure scaffolding."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestAPI",
            description="Test API",
            problem_statement="Test",
            target_user="Developers",
            value_proposition="Value",
            project_type=ProjectType.API_SERVICE,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={},
            backend={"framework": "FastAPI"},
            infrastructure={},
            reasoning="Good",
            alternatives=[]
        )
        
        directories, files = scaffolder._scaffold_fastapi(analysis, tech_stack)
        
        assert "app/routes" in directories
        assert "app/services" in directories
        assert any(f["path"] == "requirements.txt" for f in files)
    
    def test_scaffold_cli_structure(self):
        """Test CLI project structure scaffolding."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        scaffolder = ProjectScaffolder()
        
        analysis = IdeaAnalysis(
            title="TestCLI",
            description="Test CLI",
            problem_statement="Test",
            target_user="Developers",
            value_proposition="Value",
            project_type=ProjectType.CLI_TOOL,
            project_size=ProjectSize.MICRO,
            estimated_hours=10,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        tech_stack = TechStackRecommendation(
            frontend={},
            backend={"language": "Python"},
            infrastructure={},
            reasoning="Good",
            alternatives=[]
        )
        
        directories, files = scaffolder._scaffold_cli(analysis, tech_stack)
        
        assert "testcli" in directories
        assert "tests" in directories
        assert any(f["path"] == "pyproject.toml" for f in files)


# ============================================================================
# MAIN AGENT TESTS
# ============================================================================

class TestIdeasMachineAgent:
    """Tests for the main IdeasMachineAgent class."""
    
    def test_agent_initialization(self):
        """Test IdeasMachineAgent initialization."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        assert agent.name == "IDEAS_MACHINE"
        assert agent.version == "2.0.0"
        assert agent.analyzer is not None
        assert agent.architect is not None
        assert agent.scaffolder is not None
    
    def test_agent_capabilities(self):
        """Test IdeasMachineAgent capabilities list."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        capabilities = agent.get_capabilities()
        
        assert "idea_analysis" in capabilities
        assert "tech_stack_recommendation" in capabilities
        assert "architecture_design" in capabilities
        assert "project_scaffolding" in capabilities
        assert "documentation_generation" in capabilities
        assert "cursor_integration" in capabilities
    
    @pytest.mark.asyncio
    async def test_execute_unknown_action(self):
        """Test execute with unknown action."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        result = await agent.execute({"action": "unknown_action"})
        
        assert result.success is False
        assert "Unknown action" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_scaffold_no_description(self):
        """Test scaffold action without description."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        result = await agent.execute({"action": "scaffold"})
        
        assert result.success is False
        assert "No project description" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_analyze_no_description(self):
        """Test analyze action without description."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        result = await agent.execute({"action": "analyze", "description": ""})
        
        # Empty description should still work (will fail at API call level)
        # or succeed with empty analysis
        assert result is not None
    
    def test_agent_status(self):
        """Test agent status reporting."""
        from agents.ideas_machine.agent import IdeasMachineAgent
        
        agent = IdeasMachineAgent()
        
        status = agent.get_status()
        
        assert status["name"] == "IDEAS_MACHINE"
        assert status["version"] == "2.0.0"
        assert status["is_running"] is False
        assert "idea_analysis" in status["capabilities"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIdeasMachineIntegration:
    """Integration tests for Ideas Machine components working together."""
    
    def test_models_serialization(self):
        """Test that models can be serialized to JSON."""
        from agents.ideas_machine.models import (
            IdeaInput, IdeaAnalysis, TechStackRecommendation,
            ProjectArchitecture, ProjectScaffold, ProjectSize, ProjectType
        )
        
        analysis = IdeaAnalysis(
            title="Test",
            description="Test project",
            problem_statement="Problem",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.SMALL,
            estimated_hours=40,
            core_features=["F1"],
            mvp_features=["F1"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        # Should not raise
        analysis_dict = analysis.model_dump()
        analysis_json = json.dumps(analysis_dict, default=str)
        
        assert "Test" in analysis_json
        assert "WEB_APP" in analysis_json
    
    def test_full_scaffold_flow_structure(self):
        """Test that scaffold creates correct structure."""
        from agents.ideas_machine.scaffolder import ProjectScaffolder
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectArchitecture,
            ProjectSize, ProjectType
        )
        import tempfile
        import shutil
        
        # Create temp directory for test
        temp_dir = tempfile.mkdtemp()
        
        try:
            scaffolder = ProjectScaffolder()
            # Override output path for test
            scaffolder.output_path = Path(temp_dir)
            
            analysis = IdeaAnalysis(
                title="IntegrationTest",
                description="Integration test project",
                problem_statement="Testing",
                target_user="Testers",
                value_proposition="Tests",
                project_type=ProjectType.WEB_APP,
                project_size=ProjectSize.SMALL,
                estimated_hours=40,
                core_features=["Feature 1"],
                mvp_features=["Feature 1"],
                future_features=[],
                risks=[],
                assumptions=[]
            )
            
            tech_stack = TechStackRecommendation(
                frontend={"framework": "Next.js"},
                backend={"api": "Next.js API Routes"},
                infrastructure={"hosting": "Vercel"},
                reasoning="Standard Next.js stack",
                alternatives=[]
            )
            
            architecture = ProjectArchitecture(
                overview="Test architecture",
                components=[],
                data_flow="User -> App -> DB",
                api_endpoints=[],
                data_models=[],
                diagrams={"system": "Diagram"}
            )
            
            result = scaffolder.scaffold(analysis, tech_stack, architecture)
            
            # Verify structure
            assert result.project_name == "integrationtest"
            assert Path(result.project_path).exists()
            assert (Path(result.project_path) / "README.md").exists()
            assert (Path(result.project_path) / ".cursorrules").exists()
            
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_complexity_calculation_consistency(self):
        """Test complexity calculation is consistent."""
        from agents.ideas_machine.analyzer import IdeaAnalyzer
        from agents.ideas_machine.models import IdeaAnalysis, ProjectSize, ProjectType
        
        analyzer = IdeaAnalyzer()
        
        analysis = IdeaAnalysis(
            title="Test",
            description="Test",
            problem_statement="Test",
            target_user="Users",
            value_proposition="Value",
            project_type=ProjectType.WEB_APP,
            project_size=ProjectSize.MEDIUM,
            estimated_hours=100,
            core_features=["F1", "F2", "F3", "F4", "F5"],
            mvp_features=["F1", "F2", "F3", "F4", "F5"],
            future_features=[],
            risks=[],
            assumptions=[]
        )
        
        # Run multiple times
        c1 = analyzer.estimate_complexity(analysis)
        c2 = analyzer.estimate_complexity(analysis)
        
        # Should be consistent
        assert c1["overall"] == c2["overall"]
        assert c1["frontend"] == c2["frontend"]
        assert c1["backend"] == c2["backend"]


# ============================================================================
# CODE VALIDATOR TESTS
# ============================================================================

class TestCodeValidator:
    """Tests for the CodeValidator component with Windows compatibility."""
    
    def test_code_validator_initialization(self):
        """Test CodeValidator initialization."""
        from agents.ideas_machine.code_validator import CodeValidator
        
        validator = CodeValidator()
        
        assert validator.client is not None
        assert validator.max_fix_attempts == 3
    
    @pytest.mark.asyncio
    async def test_run_command_missing_directory(self):
        """Test _run_command with non-existent working directory."""
        from agents.ideas_machine.code_validator import CodeValidator
        
        validator = CodeValidator(project_path="/nonexistent/path")
        
        returncode, stdout, stderr = await validator._run_command("echo", "test")
        
        assert returncode == -1
        assert "does not exist" in stderr
    
    @pytest.mark.asyncio
    async def test_run_command_no_command(self):
        """Test _run_command with no command."""
        from agents.ideas_machine.code_validator import CodeValidator
        
        validator = CodeValidator(project_path=str(Path.cwd()))
        
        returncode, stdout, stderr = await validator._run_command()
        
        assert returncode == -1
        assert "No command provided" in stderr
    
    @pytest.mark.asyncio
    async def test_run_command_successful(self):
        """Test _run_command with a valid simple command."""
        from agents.ideas_machine.code_validator import CodeValidator
        import sys
        
        validator = CodeValidator(project_path=str(Path.cwd()))
        
        # Use Python to print something, works on all platforms
        returncode, stdout, stderr = await validator._run_command(
            sys.executable, "-c", "print('hello')"
        )
        
        assert returncode == 0
        assert "hello" in stdout
    
    @pytest.mark.asyncio
    async def test_run_validation_tests_skips_missing_files(self):
        """Test that validation tests skip gracefully when test files are missing."""
        from agents.ideas_machine.code_validator import CodeValidator
        from agents.ideas_machine.models import (
            IdeaAnalysis, TechStackRecommendation, ProjectSize, ProjectType
        )
        
        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = CodeValidator(project_path=temp_dir)
            
            analysis = IdeaAnalysis(
                title="TestApp",
                description="Test",
                problem_statement="Test",
                target_user="Users",
                value_proposition="Value",
                project_type=ProjectType.WEB_APP,
                project_size=ProjectSize.SMALL,
                estimated_hours=40,
                core_features=["F1"],
                mvp_features=["F1"],
                future_features=[],
                risks=[],
                assumptions=[]
            )
            
            tech_stack = TechStackRecommendation(
                frontend={"framework": "Next.js"},
                backend={"framework": "FastAPI"},
                infrastructure={},
                reasoning="Good",
                alternatives=[]
            )
            
            # Should not raise and should skip gracefully
            results = await validator._run_validation_tests(analysis, tech_stack, {})
            
            # Result should still be structured correctly
            assert "success" in results
            assert "errors" in results
            assert "test_output" in results


