# Contributing to Database Architecture Layers

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 🎯 Ways to Contribute

- **Report Bugs**: Submit detailed bug reports
- **Suggest Features**: Propose new features or improvements
- **Fix Issues**: Pick up existing issues and submit PRs
- **Improve Documentation**: Enhance READMEs, comments, or examples
- **Add Tests**: Increase test coverage
- **Share Knowledge**: Write blog posts or tutorials

## 🚀 Getting Started

### 1. Fork the Repository

```bash
# Fork on GitHub, then clone your fork
git clone https://github.com/rohansen856/database-layering.git
cd database-layering
```

### 2. Set Up Development Environment

```bash
# Install Python dependencies for any layer
cd l<N>-<name>/
pip install -r requirements.txt

# Or use Docker
docker-compose up -d
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

## 📋 Guidelines

### Code Style

- **Python**: Follow PEP 8
- **Type Hints**: Use type hints where appropriate
- **Docstrings**: Document functions and classes
- **Comments**: Explain "why", not "what"

### Testing

- **Add Tests**: All new features must include tests
- **Run Tests**: Ensure all tests pass before submitting

```bash
# Run tests for a layer
cd l<N>-<name>/
pytest -v

# Or with Docker
docker-compose exec api pytest -v
```

- **Test Coverage**: Aim for >80% coverage
- **Test Types**: Include unit, integration, and end-to-end tests

### Documentation

- **README Updates**: Update README.md if adding features
- **Code Comments**: Add comments for complex logic
- **Architecture Diagrams**: Update ASCII diagrams if architecture changes
- **Examples**: Provide usage examples for new features

### Commit Messages

Use conventional commits:

```
feat: add rate limiting to Layer 10
fix: resolve cache invalidation bug in Layer 5
docs: update Layer 7 architecture diagram
test: add integration tests for sharding
refactor: improve connection pool management
```

### Pull Request Process

1. **Update Documentation**: Ensure READMEs are current
2. **Add Tests**: Include comprehensive tests
3. **Run Tests**: All tests must pass
4. **Update CHANGELOG** (if applicable)
5. **Describe Changes**: Provide clear PR description

## 🏗️ Project Structure

```
database-layering/
├── l0-single-db/          # Layer 0 implementation
│   ├── app/               # Application code
│   ├── tests/             # Tests
│   ├── docker-compose.yml # Docker configuration
│   ├── README.md          # Layer documentation
│   └── requirements.txt   # Python dependencies
├── l1-connection-pooling/ # Layer 1 implementation
...
├── LAYERS.md             # Architecture specifications
├── README.md             # Project README
└── CONTRIBUTING.md       # This file
```

### Each Layer Contains:

- `app/` - Application code
  - `main.py` - FastAPI application
  - `config.py` - Configuration
  - `database.py` - Database layer
  - `models.py` - Pydantic models
- `tests/` - Test suite
  - `conftest.py` - Pytest fixtures
  - `test_*.py` - Test files
- `docker-compose.yml` - Docker services
- `Dockerfile` - API container
- `README.md` - Layer documentation
- `requirements.txt` - Dependencies
- `.env.example` - Configuration template

## 🐛 Reporting Bugs

When reporting bugs, please include:

- **Description**: Clear description of the bug
- **Layer**: Which layer(s) are affected
- **Steps to Reproduce**: Detailed steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, Docker version
- **Logs**: Relevant error messages or logs

### Bug Report Template

```markdown
**Layer**: L5 - Multi-Tier Cache

**Description**: Cache invalidation not working after write

**Steps to Reproduce**:
1. Start layer 5: `docker-compose up -d`
2. Write data: `curl -X POST http://localhost:8005/write -d '{"key":"test","value":"value"}'`
3. Read data: `curl http://localhost:8005/read/test`
4. Write again with different value
5. Read again - old value still returned

**Expected**: New value should be returned
**Actual**: Old cached value is returned

**Environment**:
- OS: Ubuntu 22.04
- Python: 3.11.5
- Docker: 24.0.6
```

## 💡 Suggesting Features

When suggesting features:

- **Use Case**: Explain why this feature is needed
- **Proposed Solution**: Describe your idea
- **Alternatives**: Other approaches considered
- **Impact**: Which layers would be affected

## 🔍 Code Review Process

1. **Automated Checks**: CI runs tests automatically
2. **Maintainer Review**: A maintainer reviews the PR
3. **Feedback**: Address any requested changes
4. **Approval**: PR is approved and merged
5. **Release**: Changes included in next release

## 📦 Adding a New Layer

If proposing a new layer (beyond L10):

1. **Specification**: Create detailed architecture spec
2. **Implementation**: Follow existing layer structure
3. **Tests**: Comprehensive test coverage
4. **Documentation**: Complete README with diagrams
5. **Docker Support**: Full Docker Compose setup
6. **Examples**: Usage examples and API docs

## 🧪 Testing Guidelines

### Test Categories

1. **Unit Tests**: Test individual functions
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Test scalability (optional)

### Writing Tests

```python
def test_feature_name(test_client, api_headers):
    """Test description"""
    # Arrange
    test_data = {"key": "test", "value": "value"}

    # Act
    response = test_client.post("/write", json=test_data, headers=api_headers)

    # Assert
    assert response.status_code == 200
    assert response.json()["success"] is True
```

## 📝 Documentation Standards

### README Structure

Each layer README should include:

1. **Overview**: Brief description
2. **Architecture**: Diagram and explanation
3. **Features**: Key capabilities
4. **Performance**: Characteristics
5. **Trade-offs**: Advantages and disadvantages
6. **Use Cases**: When to use this layer
7. **Running**: Docker and local instructions
8. **API Examples**: Request/response examples
9. **Testing**: How to run tests
10. **Configuration**: Environment variables

### Code Documentation

```python
def function_name(param: str) -> dict:
    """
    Brief description of what the function does.

    Args:
        param: Description of parameter

    Returns:
        dict: Description of return value

    Raises:
        ValueError: When parameter is invalid
    """
    # Implementation
    pass
```

## 🌟 Recognition

Contributors will be:
- Listed in project contributors
- Mentioned in release notes (for significant contributions)
- Credited in documentation (if applicable)

## ❓ Questions?

- Open a Discussion on GitHub
- Check existing Issues
- Review documentation in each layer's README

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## 🎓 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Docker Documentation](https://docs.docker.com/)
- [pytest Documentation](https://docs.pytest.org/)

---

Thank you for contributing to Database Architecture Layers! 🚀
