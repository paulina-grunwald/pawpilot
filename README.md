# PawPilot

An agentic RAG assistant that knows _your specific dog_ — breed, weight, vaccination record, chronic conditions, and activity history — and uses that context to triage symptoms in real time.

Connects to your dog's Tractive GPS collar to proactively alert you when activity or sleep patterns deviate from their personal baseline. A multi-agent debate (Researcher + Skeptic + Synthesizer) returns cited, urgency-classified answers grounded.

---

## Frontend

Next.js (App Router) + TypeScript + Tailwind, tested with Vitest and Playwright. Lives in `frontend/`.

**Requirements:** Node 20+, pnpm 10+.

```bash
cd frontend
pnpm install
pnpm dev              # http://localhost:3000
```

Quality gate (run before committing):

```bash
pnpm check            # lint + typecheck + unit tests
pnpm build            # production build
pnpm test:e2e         # Playwright smoke tests (boots dev server)
```

Other scripts: `pnpm format` (Prettier write), `pnpm format:check`, `pnpm test:watch`.

---

## Backend

FastAPI + Python 3.12, managed with [uv](https://docs.astral.sh/uv/), tested with pytest. Lives in `backend/`.

**Requirements:** [uv](https://docs.astral.sh/uv/getting-started/installation/) (uv installs the pinned Python 3.12 automatically).

```bash
cd backend
uv sync
make dev              # http://localhost:8000  →  GET /health → {"status":"ok"}
```

Quality gate (run before committing):

```bash
make check            # ruff lint + mypy strict + pytest
```

Other targets: `make format` (ruff format + autofix), `make lint`, `make typecheck`, `make test`.
