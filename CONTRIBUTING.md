# Contributing to My Workspace

Thank you for your interest in contributing to this personal development monorepo! While this is primarily a personal workspace, contributions and feedback are welcome.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Adding New Projects](#adding-new-projects)

## Getting Started

1. **Fork the repository** (if external contributor)
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/My-Workspace-TB-.git
   cd My-Workspace-TB-
   ```

3. **Install dependencies**:
   ```bash
   # Install root dependencies
   npm install

   # Install MCP server dependencies
   cd servers/todoist-mcp-server && npm install && cd ../..
   cd servers/ynab-mcp-server && npm install && cd ../..
   cd servers/gmail-mcp-server && npm install && cd ../..

   # Install Python dependencies
   cd apps/love-brittany-tracker && pip install -r requirements.txt && cd ../..
   ```

4. **Set up pre-commit hooks**:
   ```bash
   # For Python projects
   pip install pre-commit
   pre-commit install

   # For JavaScript/TypeScript (handled by npm install)
   npm run prepare
   ```

## Development Setup

### Prerequisites

- **Node.js** 18+ and npm 9+
- **Python** 3.9+ (3.11 recommended)
- **Git** 2.x
- **pre-commit** (optional but recommended)

### Environment Variables

Each project has its own `.env.example` file. Copy and configure:

```bash
# MCP servers
cp servers/todoist-mcp-server/.env.example servers/todoist-mcp-server/.env
cp servers/ynab-mcp-server/.env.example servers/ynab-mcp-server/.env

# Applications
cp apps/love-brittany-tracker/.env.example apps/love-brittany-tracker/.env
```

## Project Structure

```
My-Workspace-TB-/
├── apps/              # Full applications
├── servers/           # MCP server implementations
├── utils/             # Standalone utilities
├── docs/              # Documentation
├── .github/           # GitHub Actions workflows
└── CLAUDE.md          # AI assistant documentation
```

### Adding Files to Projects

- **Applications**: `apps/<app-name>/`
- **MCP Servers**: `servers/<server-name>/`
- **Utilities**: `utils/`
- **Documentation**: `docs/`

## Coding Standards

### TypeScript/JavaScript (MCP Servers)

- **Style**: Follow Prettier configuration (`.prettierrc.json`)
- **Linting**: ESLint (if configured)
- **Formatting**: Run `npm run format` before committing
- **Build**: Ensure `npm run build` succeeds

### Python (Apps & Utils)

- **Formatting**: Use Black with line length 127
  ```bash
  black apps/ utils/
  ```

- **Import Sorting**: Use isort with Black profile
  ```bash
  isort --profile black apps/ utils/
  ```

- **Linting**: Pass flake8 checks
  ```bash
  flake8 apps/ utils/ --max-line-length=127 --extend-ignore=E203
  ```

- **Type Hints**: Use type hints where appropriate

### Documentation

- **Markdown**: Follow markdownlint rules
- **Comments**: Write clear, concise comments
- **README**: Each project should have a comprehensive README.md
- **CLAUDE.md**: Update hierarchical documentation when adding features

## Testing

### MCP Servers (TypeScript)

```bash
# Run tests for all servers
npm run test

# Run tests for specific server
cd servers/todoist-mcp-server
npm test

# Run with coverage
npm run test:coverage
```

### Python Applications

```bash
# Run tests
cd apps/love-brittany-tracker
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Requirements

- **Unit tests** for new functions/methods
- **Integration tests** for API interactions
- **Minimum 70% code coverage** for new code
- **All tests must pass** before merging

## Commit Guidelines

### Commit Message Format

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks, dependencies

### Examples

```bash
feat(todoist): add support for subtask creation

Add new tool for creating subtasks under existing tasks.
Includes validation and error handling.

Closes #123

---

fix(ynab): handle missing budget categories gracefully

Prevent crashes when budget categories are undefined.
Add fallback behavior and logging.

---

docs(readme): update installation instructions

Clarify Node.js version requirements and add troubleshooting section.
```

### Commit Hook Validation

Pre-commit hooks will:
- Format code automatically
- Run linters
- Check for secrets
- Validate commit message length

## Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes**:
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests and linting**:
   ```bash
   # TypeScript
   npm run build
   npm run test
   npm run format:check

   # Python
   pytest
   black --check apps/ utils/
   flake8 apps/ utils/
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**:
   - Use a descriptive title
   - Explain what changed and why
   - Reference related issues
   - Ensure all CI checks pass

### PR Requirements

- ✅ All tests passing
- ✅ Code coverage maintained/improved
- ✅ Documentation updated
- ✅ No merge conflicts
- ✅ Pre-commit hooks passing
- ✅ Reviewed and approved

## Adding New Projects

### New MCP Server

1. Create directory: `servers/<server-name>/`
2. Initialize with `package.json`:
   ```json
   {
     "name": "<server-name>-mcp-server",
     "type": "module",
     "scripts": {
       "build": "tsc",
       "test": "vitest run"
     }
   }
   ```
3. Add TypeScript configuration
4. Create `README.md` with setup instructions
5. Add `.env.example`
6. Update root `.mcp.json`
7. Update root `README.md`

### New Application

1. Create directory: `apps/<app-name>/`
2. Add `requirements.txt` or `package.json`
3. Create directory structure:
   ```
   apps/<app-name>/
   ├── src/
   ├── tests/
   ├── docs/
   ├── README.md
   ├── .env.example
   └── LICENSE
   ```
4. Update root `README.md`

### New Utility

1. Add script to `utils/`
2. Include docstrings/comments
3. Add usage examples in file header
4. Update `utils/CLAUDE.md`

## Questions or Issues?

- **Bug Reports**: Open an issue with detailed description
- **Feature Requests**: Open an issue explaining the use case
- **Questions**: Check CLAUDE.md or open a discussion

## Code of Conduct

- Be respectful and professional
- Provide constructive feedback
- Focus on the code, not the person
- Help maintain a welcoming environment

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!**
