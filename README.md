# PawPilot

A dog-health assistant that answers questions about *your specific dog*. It combines three things most chatbots do not have: your dog's profile (breed, weight, age, conditions), the daily activity and vitals recorded by a Tractive GPS collar, and a retrieval corpus of about 200 open-access veterinary documents. Answers come back with citations to the passages they were drawn from.

Built as a full-stack project: Next.js frontend, FastAPI backend, Postgres, Qdrant, and a LangGraph tool-calling agent.

## What it does today

**Pet profiles.** Create a dog, set breed, birthday, weight, and photo. Breed data drives the baseline comparisons.

**Tractive data ingest.** Upload the GDPR-export zip Tractive gives you and the backend parses it into daily records: sleep architecture (night sleep, day sleep, longest bout, bout count, fragmentation), activity (active time, moderate and low intensity minutes, no-signal time), vitals (resting heart rate, resting respiratory rate split by day and night), and outings (count, total time, walking distance). Ingest is file-based, not a live API connection to Tractive.

**Dashboard.** Charts for each metric family over a chosen window, with tooltips explaining what each reading is derived from and how much of the window actually has data.

**Journal.** Free-text entries with optional photos, stored per dog. Entries are flagged as a concern based on their content so they surface differently in the timeline.

**Ask PawPilot.** A conversational agent over all of the above.

## The agent

A LangGraph tool-calling loop (`backend/app/agent/`) with a bounded tool-call budget. Its tools:

| Tool | What it does |
| --- | --- |
| `retrieve_vet_corpus` | Dense vector search over the vet corpus in Qdrant, with an optional rerank stage. Returns passages tagged `[1]`, `[2]`, … for the model to cite. |
| `web_search` | Tavily search for things the corpus cannot cover, such as product recalls. Results tagged `[W1]`, `[W2]`, … |
| `get_dog_metric` | Owner-scoped read of one metric from Postgres, aggregated as average, daily series, min/max, or a single date. |
| `get_dog_health_snapshot` | Multi-metric summary over a window. |
| `pet_food_lookup` | Open Pet Food Facts lookup by name or barcode, returning the nutrient panel. |
| `save_dog_memory` / `list_dog_memories` / `delete_dog_memory` | Long-term per-dog facts in a LangGraph store, capped per dog. |
| `get_current_date` | Grounds the model in today's date so relative questions ("last week") resolve correctly. |

Conversation state and long-term memory persist to Postgres through LangGraph's Postgres checkpointer and store. Thread ids are namespaced by user id so one owner's history is never reachable from another account.

The response path also runs red-flag detection over the answer text, so symptom descriptions that warrant an actual vet get marked as urgent rather than answered casually.

## Evaluation

The RAG stack is measured, not assumed. Harness lives in `backend/evals/rag/`, and runs push to LangSmith as datasets and experiments.

Retrieval, against a hand-curated golden set:

| recall@5 | recall@8 | recall@10 | recall@20 |
| --- | --- | --- | --- |
| 0.74 | 0.84 | 0.89 | 0.95 |

Generation, RAGAS metrics over 18 curated cases, comparing dense retrieval against dense plus rerank:

| Metric | dense | rerank |
| --- | --- | --- |
| faithfulness | 0.61 | 0.64 |
| answer accuracy | 0.64 | 0.61 |
| answer relevancy | 0.82 | 0.80 |
| noise sensitivity (lower is better) | 0.24 | 0.23 |

Eighteen cases is a small set, and the dense-versus-rerank differences here are inside the noise. Treat these as a working baseline to move, not a claim that the system is solved.

Targets: `make retrieval-report`, `make rag-eval`, `make agent-eval`, `make langsmith-experiments`.

## Stack

**Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind v4, Vitest, Playwright. Deployed on Vercel, with a same-origin `/api` proxy so the auth cookie stays first-party.

**Backend:** FastAPI, Python 3.12 managed with [uv](https://docs.astral.sh/uv/), SQLAlchemy 2 async, Alembic, fastapi-users for auth, pytest with testcontainers.

**Data:** Postgres for profiles, metrics, journal, and agent state. Qdrant for the vet corpus. S3-compatible object storage for photos.

**AI:** OpenAI models through the Vercel AI Gateway for embeddings, generation, reranking, and the eval judge. Tavily for web search. LangSmith for tracing and experiments.

## Repo layout

```
frontend/          Next.js app
backend/app/       FastAPI app
  agent/           LangGraph agent, tools, memory, prompts
  rag/             chunking, embeddings, Qdrant store, retrieval, ingest
  integrations/    Tractive GDPR export parsing and metric consolidation
  journal/         journal entries and photos
  pets/  auth/  media/
backend/evals/rag/ retrieval and generation eval harness
infra/             docker-compose for local Postgres
```

## Running it

### Frontend

Requires Node 20+ and pnpm 10+.

```bash
cd frontend
pnpm install
pnpm dev
```

Quality gate before committing:

```bash
pnpm check && pnpm build
```

`pnpm check` runs lint, typecheck, and unit tests. `pnpm test:e2e` runs the Playwright smoke tests and boots its own dev server. Other scripts: `pnpm format`, `pnpm format:check`, `pnpm test:watch`.

### Backend

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs the pinned Python 3.12 itself, and Docker. Docker is needed for `make test` and `make check`, which start an ephemeral Postgres via testcontainers, and for `make db-up`, which runs the local dev Postgres from `infra/docker-compose.yml`.

```bash
cd backend
cp .env.example .env
uv sync
make db-up
make dev
```

Quality gate before committing:

```bash
make check
```

Other targets: `make format`, `make lint`, `make typecheck`, `make test`, `make db-upgrade`, `make db-revision name="describe change"`, `make corpus-ingest`.

Loading the vet corpus into a deployed backend's private Qdrant: see [backend/docs/corpus-admin.md](backend/docs/corpus-admin.md).

## Known limits

- Tractive data arrives by uploading a GDPR export zip. There is no live collar sync, so the dashboard is as fresh as your last upload.
- Nothing pushes alerts. The agent will tell you a metric has drifted if you ask, but it does not watch for drift on its own.
- The corpus is open-access veterinary literature. Coverage is uneven, and retrieval recall on the golden set tops out around 0.95 at k=20.
- PawPilot is not a veterinarian and does not diagnose. It surfaces cited literature, your dog's own numbers, and a red-flag warning when a described symptom needs a real clinic.
