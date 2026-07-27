# Contributing to Asila

We welcome contributions to Asila! Whether you're fixing bugs, improving documentation, or proposing new features, your help is appreciated.

## Development Environment Setup

Asila's backend is written in Python (FastAPI). We use `uv` as our package manager and test runner.

### Prerequisites
- Python 3.11+
- `uv` (Install via `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker and Docker Compose

### Getting Started

1. **Fork and Clone:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/asila.git
   cd asila
   ```

2. **Start the Database and Dependencies:**
   ```bash
   # We need PostgreSQL, Redis, Docling, and Ollama running locally.
   docker compose up -d postgres redis docling ollama
   ```

3. **Install Dependencies:**
   ```bash
   cd backend
   uv sync
   ```

4. **Run the Tests:**
   ```bash
   uv run pytest
   ```

## Code Standards

- **Formatting:** We use `black` and `ruff`. Run `uv run ruff check .` before submitting.
- **Typing:** Strict type hints are enforced via `mypy`.
- **Architecture:** The backend strictly follows a Ports and Adapters (Clean Architecture) pattern. Ensure your domain logic does not depend on database or framework specific code.

## Pull Request Process

1. Create a feature branch (`git checkout -b feature/your-feature`).
2. Commit your changes using Conventional Commits formatting (e.g., `feat: add awesome feature`).
3. Ensure all tests pass.
4. Push to your branch and open a PR against `main`.
5. A maintainer will review your code. 

## Reporting Bugs

Please open an issue on GitHub. Include:
- Your operating system and Docker version.
- The exact error output or logs (`docker compose logs`).
- Steps to reproduce the bug.
