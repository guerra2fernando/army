# Contributing to ArmLenQuant

Thank you for your interest in contributing to ArmLenQuant! This document provides guidelines and instructions for contributing to the project.

## 🎯 Project Status

ArmLenQuant is currently in **active development** by a solo developer. The project has completed Phases 1-10 (MVP) and is preparing for Phase 11 (Cloud Deployment).

### Current Focus Areas:
- **Phase 11**: Cloud deployment and production readiness
- **Integration Testing**: End-to-end system validation
- **Documentation**: Improving setup guides and API documentation

## 📋 Contribution Guidelines

### Before You Start
1. Check the [Issues](https://github.com/armlenquant-cloud/armlenquant/issues) to see if your idea is already being worked on
2. For major changes, please open an issue first to discuss what you would like to change
3. Ensure your changes align with the project's architecture and philosophy

### Development Workflow
1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. **Make your changes** following the coding standards
5. **Test your changes** thoroughly
6. **Commit your changes** with descriptive commit messages
7. **Push to your fork**
8. **Open a Pull Request**

## 🏗️ Architecture Compliance

All contributions must respect the **split-brain architecture**:

### Cloud Components (The Tower)
- **Location**: Runs on cloud servers (DigitalOcean, AWS, etc.)
- **Responsibilities**: Task orchestration, authentication, database, API
- **Technologies**: FastAPI (Python), MongoDB, JWT authentication
- **Constraints**: No browser automation, no local file access

### Local Components (Field Ops)
- **Location**: Runs on user's Windows machine
- **Responsibilities**: Task execution, browser automation, file generation
- **Technologies**: Python, Playwright, local file system access
- **Constraints**: Requires Windows, residential IP for web scraping

## 🔧 Development Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- MongoDB (local or Atlas)
- Git

### Local Development
1. Clone the repository
2. Set up environment variables (see `.env.example` files)
3. Install dependencies:
   ```bash
   # Cloud API
   cd armlenquant-cloud/api
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   
   # Dashboard
   cd armlenquant-cloud/dashboard
   npm install
   
   # Local Poller
   cd armlenquant-local
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
4. Run the services (see README.md for details)

## 🧪 Testing

### Running Tests
```bash
# Local Poller tests
cd armlenquant-local
python -m pytest tests/ -v

# Cloud API tests
cd armlenquant-cloud/api
python -m pytest tests/ -v
```

### Test Coverage
- All new features must include tests
- Maintain at least 80% test coverage
- Include integration tests for agent workflows

## 📝 Code Standards

### Python Code
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints for all function signatures
- Document complex functions with docstrings
- Use `black` for code formatting
- Use `isort` for import sorting

### TypeScript/JavaScript Code
- Follow ESLint configuration
- Use TypeScript strict mode
- Document public APIs
- Follow React best practices

### Commit Messages
Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add new crypto market analysis agent
fix: resolve job hunter timeout issue
docs: update getting started guide
```

## 🔒 Security Guidelines

### Never Commit Secrets
- **NEVER** commit `.env` files
- Use `.env.example` files as templates
- Generate secure random strings for secrets:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

### API Keys & Credentials
- Store API keys in environment variables only
- Use different keys for development and production
- Rotate compromised keys immediately

### Input Validation
- Validate all user inputs
- Sanitize file paths and system commands
- Implement rate limiting for API endpoints

## 📚 Documentation

### Required Documentation
1. **API Documentation**: Document all endpoints with examples
2. **Agent Documentation**: Document each agent's capabilities and configuration
3. **Setup Guides**: Keep installation instructions up to date
4. **Troubleshooting**: Common issues and solutions

### Documentation Format
- Use Markdown format
- Include code examples
- Add diagrams for complex workflows
- Keep documentation in sync with code changes

## 🚀 Pull Request Process

1. **Ensure** your code follows all guidelines
2. **Update** documentation for any changes
3. **Add** tests for new functionality
4. **Verify** all tests pass
5. **Update** the CHANGELOG.md if applicable
6. **Request review** from maintainers

### PR Review Checklist
- [ ] Code follows project standards
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] No secrets are exposed
- [ ] Changes are backward compatible
- [ ] Security considerations addressed

## 🐛 Reporting Issues

### Bug Reports
When reporting bugs, include:
1. Clear description of the issue
2. Steps to reproduce
3. Expected vs actual behavior
4. Environment details (OS, Python version, etc.)
5. Error messages and logs

### Feature Requests
For feature requests, describe:
1. The problem you're trying to solve
2. Proposed solution
3. Use cases and examples
4. Potential implementation approach

## 📞 Getting Help

- **Issues**: [GitHub Issues](https://github.com/armlenquant-cloud/armlenquant/issues)
- **Documentation**: Check the README.md and GETTING_STARTED.md first
- **Community**: Join the discussion in issues

## 📄 License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

*Thank you for contributing to ArmLenQuant! Together we're building the future of autonomous agent systems.*