# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClearCode is a build-in-public project to reverse-engineering a production-grade autonomous coding agent from scratch, using Python, LangChain, and MCP. Each layer is built incrementally and documented publicly at [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode).

## Current State

The context layer and initial agent layer are implemented and wired together into a working RAG-powered code assistant REPL. Both ChromaDB and Qdrant are supported as vector store backends, switchable via config.

```
clearcode/
├── config.py                          # Loads config.yaml via Path(__file__).parent
├── config.yaml                        # LLM, embeddings, vector store config
├── main.py                            # REPL entry point — auto-indexes CWD on first run
├── llm/
│   └── factory.py                     # Provider-dispatched LLM and embedder factories
├── context/
│   ├── indexers/
│   │   ├── factory.py                 # get_indexer() / get_index_inspector() — dispatches by provider
│   │   ├── code_parser.py             # AST chunking (tree-sitter) + sliding window fallback
│   │   ├── semantic_chroma.py         # Embeds chunks and upserts into ChromaDB
│   │   └── semantic_qdrant.py         # Embeds chunks and upserts into Qdrant
│   └── retrievers/
│       ├── factory.py                 # get_retriever() — dispatches by provider
│       ├── semantic_chroma.py         # Embeds query, returns top-k chunks from ChromaDB
│       └── semantic_qdrant.py         # Embeds query, returns top-k chunks from Qdrant
├── agent/
│   ├── factory.py                     # Builds tool-calling LangChain agent
│   ├── orchestrator.py                # handle_query() entry point
│   └── tools.py                       # search_codebase LangChain tool
└── observability/
    └── logger.py                      # Root logger at WARNING, clearcode loggers at DEBUG
```

Layers not yet built: `memory/`, `mcp/`, `skills/`, `safety/`, `freshness/`, `eval/`.

## Development Setup

```bash
# Install dependencies
poetry install

# Run the REPL (auto-indexes current directory on first run)
poetry run clearcode

# Activate the venv in your shell
source $(poetry env info --path)/bin/activate
```

Python 3.12 is required (`tree-sitter-languages` has no wheels for 3.14+).

## Key Config

`clearcode/config.yaml` controls the active providers:

```yaml
llm:
  provider: openai   # openai | anthropic
  model: gpt-4o

embeddings:
  provider: openai   # openai | huggingface
  model: text-embedding-3-small

vector_store:
  provider: chromadb  # chromadb | qdrant

chromadb:
  persist_dir: .chromadb/
  collection_name: codebase

qdrant:
  collection_name: codebase
```

API keys go in `.env` at the repo root (gitignored). `load_dotenv()` in `main.py` uses an explicit path relative to `__file__` so it works correctly under both `poetry run` and an activated venv. Qdrant requires `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.

Switching `vector_store.provider` or `embeddings.model` requires a full re-index:
- ChromaDB: delete `.chromadb/`
- Qdrant: delete the collection via the Qdrant client or dashboard

## REPL Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about the codebase |
| `/show_semantic_index` | Dump all indexed chunks |
| `/exit` | Quit |

## Architecture Notes

- **Chunking**: `code_parser.py` uses tree-sitter for AST-aware chunking across 15 languages. Falls back to a sliding window (50 lines, 10-line overlap) for text/config files and files with no extractable AST blocks. tree-sitter returns byte offsets — all slicing is done on `source_bytes` (not the decoded `str`) to avoid truncation with multi-byte characters.
- **Indexing**: ChromaDB uses stable chunk IDs (`source::name::start_line`) for idempotent upserts. Qdrant uses `QdrantVectorStore.from_documents()` and checks `points_count` to skip re-indexing.
- **Retrieval**: Both backends embed the query with the same model used at index time. The active backend is selected at call time via `retrievers/factory.py`.
- **Agent**: `factory.py` builds a `create_agent` + tool-calling chain with a single `search_codebase` tool. The system prompt instructs the LLM to always search before answering.
- **Vector store abstraction**: `indexers/factory.py` and `retrievers/factory.py` dispatch to the right backend based on `config["vector_store"]["provider"]`. Adding a new backend only requires a new `semantic_<backend>.py` pair and a branch in each factory.

## Known Flaws (not yet fixed)

- Agent and LLM client are rebuilt on every `/ask` — should be initialized once at startup.
- Retriever opens a new DB client on every query — should reuse the connection from indexing.
- Both factory files silently fall through to ChromaDB for unknown provider names — should raise `ValueError`.
- `_sliding_window` raises `ValueError` on empty files instead of returning `[]`, causing empty `__init__.py` files to log as indexing errors.
- `show_index` in `semantic_chroma.py` fetches all embedding vectors into memory — wasteful for large collections.
- Qdrant indexer batches all docs before upserting — no partial progress on failure.

## Build Order

1. Architecture — done
2. Context layer: indexers + retrievers — **done**
3. Agent reasoning layer — **done (initial)**
4. Memory layer
5. MCP integrations, Skills
6. Safety, Freshness, Observability
7. Eval layer

When adding code, match the layer currently being built in the blog series. Don't implement future layers ahead of the companion post.
