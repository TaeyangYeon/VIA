# VIA Project Rules

## Project
VIA is a multi-agent AI desktop app for automated computer vision algorithm design.
Stack: FastAPI + Python 3.11 (backend), Electron + React + TypeScript + TailwindCSS (frontend), Ollama + Gemma4 (AI), OpenCV (vision).

## Workflow
- TDD: Write tests FIRST → Red → Green → Refactor
- Never commit to git. Taeyang commits after 3-Gate verification.
- One Step = one commit unit.

## Code Rules
- Backend tests: pytest. Frontend tests: jest + React Testing Library.
- Always verify model field names from agents/models.py before referencing them.
- Always verify interface methods from agents/base_agent.py before implementing.
- Commit message format: English prefix (feat:/fix:/test:) + Korean body.

## MCP Usage
- Use context7 for up-to-date docs on FastAPI, React, Electron, OpenCV, pytest, TailwindCSS.
- Use sequential-thinking for architecture decisions and complex debugging.

## UI Design (Phase 6, Steps 32-40)
- Dark theme ONLY: backgrounds #0a0a0a / #111111 / #1a1a1a
- Glass morphism: bg-white/5 backdrop-blur-sm border border-white/10
- NO blue/purple/green backgrounds
- lucide-react for all icons
- All interactions: transition-all duration-150

## File Structure
- Backend: backend/, agents/, tests/
- Frontend: frontend/src/
- Plans: VIA_MASTER_PLAN.md, progress.md
