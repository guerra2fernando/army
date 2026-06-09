"""
Test Generator
Generates comprehensive test suites for all generated code.
"""
import json
from typing import Dict, Any, List
from loguru import logger

from .models import IdeaAnalysis, TechStackRecommendation, ProjectArchitecture, ProjectContext


class TestGenerator:
    """
    Generates comprehensive test suites for all project components.
    """

    def __init__(self):
        self.logger = logger.bind(component="test_generator")

    def generate_test_infrastructure(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Dict[str, str]:
        """
        Generate test infrastructure files.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack recommendation

        Returns:
            Dictionary of test infrastructure files
        """
        files = {}

        # Generate pytest.ini for Python backend
        if analysis.is_fullstack or analysis.project_type.value in ["API_SERVICE", "AI_APP"]:
            files["pytest.ini"] = self._generate_pytest_config()
            files["tests/__init__.py"] = '"""Test package."""'
            files["tests/conftest.py"] = self._generate_backend_conftest()

        # Generate Jest config for frontend
        if analysis.is_fullstack or analysis.project_type.value == "WEB_APP":
            files["jest.config.js"] = self._generate_jest_config()
            files["jest.setup.js"] = self._generate_jest_setup()
            files["tests/__init__.py"] = '"""Test package."""'

        return files

    def generate_model_tests(
        self,
        architecture: ProjectArchitecture,
        context: ProjectContext
    ) -> Dict[str, str]:
        """
        Generate tests for database models.

        Args:
            architecture: System architecture
            context: Project context

        Returns:
            Dictionary of model test files
        """
        files = {}

        for model in architecture.data_models:
            model_name = model.get('name', 'Unknown')
            fields = model.get('fields', '')

            files[f"tests/test_models_{model_name.lower()}.py"] = f'''"""
Tests for {model_name} model.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.{model_name.lower()} import {model_name}
from app.database import Base


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    Base.metadata.drop_all(engine)


def test_{model_name.lower()}_creation(db_session):
    """Test {model_name} model creation."""
    # Create test data
    test_data = {{
        # Add test data based on model fields
        # {fields}
    }}

    model_instance = {model_name}(**test_data)
    db_session.add(model_instance)
    db_session.commit()

    # Verify creation
    assert model_instance.id is not None
    # Add more assertions based on model fields


def test_{model_name.lower()}_relationships(db_session):
    """Test {model_name} model relationships."""
    # Test relationships defined in model
    # Add relationship tests here
    pass


def test_{model_name.lower()}_validation(db_session):
    """Test {model_name} model validation."""
    # Test field validations
    # Add validation tests here
    pass
'''

        return files

    def generate_api_tests(
        self,
        architecture: ProjectArchitecture,
        context: ProjectContext
    ) -> Dict[str, str]:
        """
        Generate API endpoint tests.

        Args:
            architecture: System architecture
            context: Project context

        Returns:
            Dictionary of API test files
        """
        files = {}

        for endpoint in architecture.api_endpoints:
            method = endpoint.get('method', 'GET').lower()
            path = endpoint.get('path', '/unknown')
            description = endpoint.get('description', 'No description')

            # Extract resource name from path
            path_parts = path.strip('/').split('/')
            resource = path_parts[0] if path_parts[0] else 'root'

            files[f"tests/test_api_{resource}.py"] = f'''"""
Tests for {resource} API endpoints.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


class Test{resource.title()}API:
    """Test {resource} API endpoints."""

    def test_get_{resource}s(self, client):
        """Test GET /{resource} endpoint."""
        response = client.get(f"/{resource}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_{resource}(self, client):
        """Test POST /{resource} endpoint."""
        test_data = {{
            # Add test data based on endpoint requirements
            "name": "Test {resource.title()}",
        }}

        response = client.post(f"/{resource}", json=test_data)
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == test_data["name"]
        assert "id" in data

    def test_get_{resource}(self, client):
        """Test GET /{resource}/{{id}} endpoint."""
        # First create a resource
        test_data = {{"name": "Test {resource.title()}"}}
        create_response = client.post(f"/{resource}", json=test_data)
        resource_id = create_response.json()["id"]

        # Then get it
        response = client.get(f"/{resource}/{{resource_id}}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == resource_id
        assert data["name"] == test_data["name"]

    def test_update_{resource}(self, client):
        """Test PUT /{resource}/{{id}} endpoint."""
        # First create a resource
        test_data = {{"name": "Test {resource.title()}"}}
        create_response = client.post(f"/{resource}", json=test_data)
        resource_id = create_response.json()["id"]

        # Update it
        update_data = {{"name": "Updated {resource.title()}"}}
        response = client.put(f"/{resource}/{{resource_id}}", json=update_data)
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == update_data["name"]

    def test_delete_{resource}(self, client):
        """Test DELETE /{resource}/{{id}} endpoint."""
        # First create a resource
        test_data = {{"name": "Test {resource.title()}"}}
        create_response = client.post(f"/{resource}", json=test_data)
        resource_id = create_response.json()["id"]

        # Delete it
        response = client.delete(f"/{resource}/{{resource_id}}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/{resource}/{{resource_id}}")
        assert get_response.status_code == 404

    def test_create_{resource}_validation_error(self, client):
        """Test POST /{resource} with invalid data."""
        invalid_data = {{
            # Invalid data that should trigger validation errors
            "name": "",  # Empty name
        }}

        response = client.post(f"/{resource}", json=invalid_data)
        assert response.status_code == 422  # Validation error

    def test_get_nonexistent_{resource}(self, client):
        """Test GET /{resource}/{{id}} with non-existent ID."""
        response = client.get(f"/{resource}/99999")
        assert response.status_code == 404
'''

        return files

    def generate_component_tests(
        self,
        analysis: IdeaAnalysis,
        tech_stack: TechStackRecommendation
    ) -> Dict[str, str]:
        """
        Generate frontend component tests.

        Args:
            analysis: Project analysis
            tech_stack: Tech stack recommendation

        Returns:
            Dictionary of component test files
        """
        files = {}

        # Generate basic component test template
        files["src/components/__tests__/Button.test.tsx"] = '''/**
 * @jest-environment jsdom
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../Button';

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click me</Button>);

    fireEvent.click(screen.getByText('Click me'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Click me</Button>);
    expect(screen.getByText('Click me')).toBeDisabled();
  });

  it('applies correct variant classes', () => {
    const { container } = render(<Button variant="secondary">Click me</Button>);
    expect(container.firstChild).toHaveClass('bg-secondary');
  });
});
'''

        # Generate API client tests
        files["src/lib/__tests__/api.test.ts"] = '''/**
 * @jest-environment jsdom
 */
import { getUsers, createUser } from '../api';

// Mock fetch
global.fetch = jest.fn();

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getUsers', () => {
    it('fetches users successfully', async () => {
      const mockUsers = [
        { id: 1, name: 'John Doe' },
        { id: 2, name: 'Jane Doe' }
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockUsers,
      });

      const users = await getUsers();
      expect(users).toEqual(mockUsers);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users',
        expect.objectContaining({
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    });

    it('throws error on failed request', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      });

      await expect(getUsers()).rejects.toThrow('Internal Server Error');
    });
  });

  describe('createUser', () => {
    it('creates user successfully', async () => {
      const newUser = { name: 'John Doe', email: 'john@example.com' };
      const createdUser = { id: 1, ...newUser };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => createdUser,
      });

      const result = await createUser(newUser);
      expect(result).toEqual(createdUser);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newUser),
        })
      );
    });
  });
});
'''

        return files

    def generate_e2e_tests(
        self,
        analysis: IdeaAnalysis,
        context: ProjectContext
    ) -> Dict[str, str]:
        """
        Generate end-to-end tests.

        Args:
            analysis: Project analysis
            context: Project context

        Returns:
            Dictionary of E2E test files
        """
        files = {}

        files["e2e/tests/auth.spec.ts"] = '''/**
 * @jest-environment jsdom
 */
import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('user can sign up', async ({ page }) => {
    await page.goto('/signup');

    // Fill out signup form
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.fill('[data-testid="confirm-password-input"]', 'password123');

    // Submit form
    await page.click('[data-testid="signup-button"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
  });

  test('user can log in', async ({ page }) => {
    await page.goto('/login');

    // Fill out login form
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');

    // Submit form
    await page.click('[data-testid="login-button"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
  });

  test('user can log out', async ({ page }) => {
    // Assume user is logged in
    await page.goto('/dashboard');

    // Click logout button
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });
});
'''

        files["e2e/tests/crud.spec.ts"] = f'''/**
 * @jest-environment jsdom
 */
import {{ test, expect }} from '@playwright/test';

test.describe('CRUD Operations', () => {{
  test.beforeEach(async ({{ page }}) => {{
    // Log in before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'password123');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  }});

  test('user can create, read, update, and delete items', async ({{ page }}) => {{
    // Navigate to items page
    await page.goto('/items');

    // Create new item
    await page.click('[data-testid="create-item-button"]');
    await page.fill('[data-testid="item-name-input"]', 'Test Item');
    await page.fill('[data-testid="item-description-input"]', 'Test Description');
    await page.click('[data-testid="save-item-button"]');

    // Verify item was created
    await expect(page.locator('[data-testid="item-name"]')).toContainText('Test Item');

    // Update item
    await page.click('[data-testid="edit-item-button"]');
    await page.fill('[data-testid="item-name-input"]', 'Updated Test Item');
    await page.click('[data-testid="save-item-button"]');

    // Verify item was updated
    await expect(page.locator('[data-testid="item-name"]')).toContainText('Updated Test Item');

    // Delete item
    await page.click('[data-testid="delete-item-button"]');
    await page.click('[data-testid="confirm-delete-button"]');

    // Verify item was deleted
    await expect(page.locator('[data-testid="item-name"]')).not.toBeVisible();
  }});
}});
'''

        return files

    def _generate_pytest_config(self) -> str:
        """Generate pytest configuration."""
        return """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=app
    --cov-report=html
    --cov-report=term-missing
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
"""

    def _generate_backend_conftest(self) -> str:
        """Generate pytest conftest.py for backend."""
        return '''"""
Pytest configuration and fixtures.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db


@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
    """Create test database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client():
    """Create test client."""
    from fastapi.testclient import TestClient
    from main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def run_migrations(db_engine):
    """Run database migrations before tests."""
    Base.metadata.create_all(bind=db_engine)
'''

    def _generate_jest_config(self) -> str:
        """Generate Jest configuration for frontend."""
        return """const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Provide the path to your Next.js app to load next.config.js and .env files
  dir: './',
})

// Add any custom config to be passed to Jest
const customJestConfig = {
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    // Handle module aliases (this will be automatically configured for you based on your tsconfig.json paths)
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testEnvironment: 'jest-environment-jsdom',
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '!src/**/*.d.ts',
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70,
    },
  },
}

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
module.exports = createJestConfig(customJestConfig)
"""

    def _generate_jest_setup(self) -> str:
        """Generate Jest setup file."""
        return """// Optional: configure or set up a testing framework before each test.
// If you delete this file, remove `setupFilesAfterEnv` from `jest.config.js`

// Learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom'
"""
