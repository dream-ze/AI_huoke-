# Project Guidelines

## Code Style
- Follow existing style in touched files; do not reformat unrelated files.
- Backend Python:
  - Keep business logic in `backend/app/services/` and keep route handlers thin.
  - Keep DB access through SQLAlchemy models/repositories patterns already used in `backend/app/models/` and `backend/app/repositories/`.
- Desktop frontend:
  - Keep React + TypeScript patterns used in `desktop/src/`.
  - Use existing API access conventions before introducing new client wrappers.

## Architecture
- Monorepo with multiple runtime targets:
  - `backend/`: FastAPI + SQLAlchemy + Alembic + Redis/Postgres integrations.
  - `desktop/`: Electron host + React (Vite) renderer.
  - `mobile-h5/`: static mobile entry pages.
  - `browser-extension/`: Manifest v3 extension for content collection.
  - `deploy/`: deployment artifacts and compose-related docs.
- Backend API layering:
  - API routes in `backend/app/api/`
  - business services in `backend/app/services/`
  - schemas in `backend/app/schemas/`
  - models in `backend/app/models/`

## Build and Test
- Prefer running commands from each subproject root.
- Backend:
  - Install: `pip install poetry && poetry install`
  - Run dev server: `uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (in `backend/`)
  - Migrations: `alembic upgrade head` (in `backend/`)
  - Tests: `pytest` (in `backend/`)
- Desktop:
  - Install: `npm install` (in `desktop/`)
  - Web dev: `npm run dev:web`
  - LAN web dev: `npm run dev:web:lan`
  - Electron dev: `npm run dev`
  - Build web: `npm run build:web`
  - Build installer: `npm run dist`
- Mobile H5:
  - Serve locally: `python -m http.server 8081` (in `mobile-h5/`)
- Browser extension:
  - Load unpacked extension from `browser-extension/` in Chrome/Edge developer mode.

## Conventions
- Keep instructions minimal and link to docs for details:
  - root overview: `README.md`
  - backend operations: `backend/README.md`
  - deployment references: `deploy/README.md` and `网页端局域网部署说明.md`
- Auth/security conventions:
  - Use string `sub` in JWT payload handling paths.
  - Keep password hashing compatibility constraints used in backend dependencies (bcrypt < 5).
- Routing convention in FastAPI:
  - Register static routes before dynamic `/{id}` style routes to avoid path capture issues.
- Alembic/env convention:
  - Prefer `DATABASE_URL` env var; avoid migration patterns that import runtime settings at revision top-level.
- For deployment/debug scripts in repo root (`_*.py`, `build.ps1`, `deploy.ps1`):
  - Prefer read/verify-first workflow before applying environment changes.
  - Do not assume scripts are safe for every environment without checking target host/context.
