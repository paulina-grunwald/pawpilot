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
pnpm dev
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

**Requirements:**

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (uv installs the pinned Python 3.12 automatically).
- Docker — required for `make test` / `make check`, which spin up an ephemeral Postgres via [testcontainers](https://testcontainers-python.readthedocs.io/). Also required for `make db-up`, which runs the local dev Postgres from `infra/docker-compose.yml`.

```bash
cd backend
cp .env.example .env
uv sync
make db-up
make dev
```

Quality gate (run before committing):

```bash
make check
```

Other targets: `make format` (ruff format + autofix), `make lint`, `make typecheck`, `make test`, `make db-upgrade`, `make db-revision name="describe change"`.

Loading the vet RAG corpus into the deployed backend's private Qdrant: see [`backend/docs/corpus-admin.md`](backend/docs/corpus-admin.md).
