# Corpus admin API

Load the vet RAG corpus into the deployed backend's **private** Qdrant without ever
exposing Qdrant publicly. An operator embeds the corpus locally (via Vercel AI
Gateway) and POSTs the resulting vector points to the backend, which upserts them
over its private network.

The endpoints live under `POST /admin/rag/*` and are gated by a shared admin token
(`X-Admin-Token` header):

- `POST /admin/rag/collection` — create or recreate the collection.
- `POST /admin/rag/upsert` — write a source's points and prune its now-stale chunks.

Auth behaviour:

- **401** — missing or wrong token.
- **503** — `admin_ingest_token` is unset on the backend (endpoint disabled).

## Testing

### Automated

```bash
cd backend
uv run pytest tests/rag/test_admin_router.py -v   # uses in-memory Qdrant
make check                                         # full lint + typecheck + test suite
```

### Manual / end-to-end (against the deployed backend)

```bash
cd backend
PAWPILOT_API_URL=https://<backend-host> \
ADMIN_INGEST_TOKEN=<admin-token> \
  uv run python -m scripts.corpus_push --limit 5   # smoke test: first 5 sources
# full load: drop --limit and add --recreate
```

Requires `admin_ingest_token` set on the backend and `VERCEL_AI_GATEWAY` in your local
environment for embedding.

`corpus_push` flags:

- `--recreate` — drop and rebuild the whole collection (cannot be combined with the two below).
- `--source-id <id>` — push only one source.
- `--limit <n>` — push at most `n` sources (smoke test).

Per-source failures are isolated and reported at the end; the script exits non-zero
if any source fails.
