# VIA (Vision Intelligence Agent)

Multi-agent AI desktop application for automated computer vision algorithm design. VIA analyzes images and user intent to automatically design vision inspection algorithms, running entirely offline on local hardware with Ollama + Gemma4 multimodal AI.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| Frontend | Electron + React + TypeScript + TailwindCSS + Redux Toolkit |
| AI Engine | Ollama + Gemma4 (gemma4:e4b) — local multimodal |
| Vision | OpenCV + NumPy |
| Testing | pytest (backend), jest + React Testing Library (frontend) |

## Project Status

**Phase 1 in progress** (Environment Setup — Steps 1-4 of 50)

## Features (Planned)

- **Inspection Mode**: OK/NG binary classification algorithm design
- **Align Mode**: X/Y coordinate detection algorithm design
- **Agent Directives**: Per-agent direction input for fine-grained control
- **Vision Judge**: Multimodal AI evaluates processed images against inspection purpose
- **Decision Agent**: Automatic rule-based / Edge Learning / Deep Learning recommendation

## Getting Started

### Prerequisites

- **Python 3.11** (managed via pyenv)
- **Ollama** installed and running
- **gemma4:e4b** model pulled (`ollama pull gemma4:e4b`)
- macOS (Intel Mac x86_64 verified)

### Setup

```bash
# 1. Clone and enter project
git clone <repository-url>
cd via

# 2. Create Python virtual environment
pyenv install 3.11.15
pyenv local 3.11.15
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Ollama and pull model
./scripts/start_ollama.sh

# 5. Run tests
python -m pytest tests/ -v
```

## Project Structure

```
via/
├── backend/          # FastAPI server
│   ├── routers/      # API route handlers
│   ├── services/     # Business logic services
│   └── models/       # Pydantic data models
├── agents/           # Multi-agent system
│   └── prompts/      # LLM prompt templates
├── frontend/         # Electron + React UI (Phase 6)
├── tests/            # Test suites
│   ├── e2e/          # End-to-end tests
│   └── fixtures/     # Test data and sample images
├── scripts/          # Utility scripts
└── docs/             # Documentation
```

## License

All rights reserved.
