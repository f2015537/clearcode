# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClearCode is a build-in-public project to reverse-engineering a production-grade autonomous coding agent from scratch, using Python, LangChain, and MCP. Each layer is built incrementally and documented publicly at [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode).

## Current State

The context layer and initial agent layer are implemented and wired together into a working RAG-powered code assistant REPL. Three vector store backends are supported (ChromaDB, Qdrant semantic, Qdrant hybrid), all switchable via config.

```
clearcode/
├── config.py                          # Loads config.yaml via Path(__file__).parent
├── config.yaml                        # LLM, embeddings, RAG mode, vector store config
├── main.py                            # REPL entry point — auto-indexes CWD on first run
├── llm/
│   └── factory.py                     # Provider-dispatched LLM and embedder factories
├── context/
│   ├── indexers/
│   │   ├── factory.py                 # Dispatches to the right indexer by rag.mode + provider
│   │   ├── code_parser.py             # AST chunking (tree-sitter) + sliding window fallback
│   │   ├── semantic_chroma.py         # Dense indexing into ChromaDB
│   │   ├── semantic_qdrant.py         # Dense indexing into Qdrant
│   │   └── hybrid_qdrant.py          # Dense + sparse (BM25) indexing into Qdrant
│   └── retrievers/
│       ├── factory.py                 # Dispatches to the right retriever by rag.mode + provider
│       ├── semantic_chroma.py         # Dense retrieval from ChromaDB
│       ├── semantic_qdrant.py         # Dense retrieval from Qdrant
│       └── hybrid_qdrant.py          # Dense + sparse hybrid retrieval from Qdrant
├── agent/
│   ├── factory.py                     # Builds async tool-calling LangChain agent with MCP + local tools
│   └── orchestrator.py                # handle_query() entry point (async)
├── tools/
│   ├── retrieval_tools.py             # search_codebase LangChain tool
│   ├── filesystem_tools.py            # read/write/append/delete/list/exists tools
│   └── terminal_tools.py             # run_command, run_in_directory tools
├── mcp/
│   ├── clearcode_mcp_client.py        # Connects to MCP servers, returns tools via langchain-mcp-adapters
│   ├── clearcode_mcp_config.py        # Loads clearcode_mcp_servers.json, resolves ${ENV_VAR} placeholders
│   └── clearcode_mcp_servers.json     # MCP server definitions (GitHub configured by default)
├── memory/
│   ├── session.py                     # Session ID management (UUID, persisted to .memory/current_session)
│   └── short_term.py                  # AsyncSqliteSaver path helper + SummarizationMiddleware
└── observability/
    └── logger.py                      # Root logger at WARNING, clearcode loggers at DEBUG
```

Layers not yet built: `skills/`, `safety/`, `freshness/`, `eval/`.

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

`clearcode/config.yaml` controls all active providers and RAG mode:

```yaml
llm:
  provider: openai   # openai | anthropic
  model: gpt-4o

embeddings:
  provider: openai   # openai | huggingface
  model: text-embedding-3-small

rag:
  mode: hybrid       # semantic | hybrid

vector_store:
  provider: qdrant           # chromadb | qdrant
  retrieval_mode: hybrid     # dense | sparse | hybrid (Qdrant only)

chromadb:
  persist_dir: .chromadb/
  collection_name: codebase

qdrant:
  collection_name: codebase
```

API keys go in `.env` at the repo root (gitignored). `load_dotenv()` in `main.py` is called before all `clearcode.*` imports using an explicit path relative to `__file__`. Qdrant requires `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.

**Re-indexing**: switching `rag.mode`, `vector_store.provider`, or `embeddings.model` requires a full re-index:
- ChromaDB: delete `.chromadb/`
- Qdrant: delete the collection via the Qdrant dashboard or client

## REPL Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about the codebase |
| `/show_semantic_index` | Dump all indexed chunks |
| `/exit` | Quit |

## Architecture Notes

- **Chunking**: `code_parser.py` uses tree-sitter for AST-aware chunking across 15 languages. Falls back to a sliding window (50 lines, 10-line overlap) for text/config files and files with no extractable AST blocks. tree-sitter returns byte offsets — all slicing is done on `source_bytes` (not the decoded `str`) to avoid truncation with multi-byte characters.
- **Indexing**: ChromaDB uses stable chunk IDs (`source::name::start_line`) for idempotent upserts. Qdrant backends use `from_documents()` and check `points_count` to skip re-indexing on startup.
- **Hybrid RAG**: `hybrid_qdrant.py` stores both dense (OpenAI `text-embedding-3-small`) and sparse (BM25 via `fastembed`) vectors per chunk. `retrieval_mode` in config controls whether queries use dense, sparse, or hybrid fusion at retrieval time.
- **Factory dispatch**: `indexers/factory.py` and `retrievers/factory.py` select the backend based on `config["rag"]["mode"]` and `config["vector_store"]["provider"]`. Adding a new backend requires a new `*_<backend>.py` pair and a branch in each factory.
- **Agent**: `factory.py` builds a `create_agent` + tool-calling chain with a single `search_codebase` tool. The system prompt instructs the LLM to always search before answering.

## Known Flaws (not yet fixed)

- ~~Agent and LLM client are rebuilt on every `/ask`~~ — fixed, agent is now built once at startup via `AsyncSqliteSaver` context manager.
- Retriever opens a new DB client on every query — should reuse the connection from indexing.
- Both factory files silently fall through to ChromaDB for unknown provider names — should raise `ValueError`.
- ~~`_sliding_window` raises `ValueError` on empty files~~ — fixed, now returns `[]`.
- `show_index` in `semantic_chroma.py` fetches all embedding vectors into memory — wasteful for large collections.
- Qdrant indexers batch all docs before upserting — no partial progress on failure.
- ~~`get_checkpointer()` opens a new SQLite connection on every call~~ — fixed, `AsyncSqliteSaver` is now managed as a context manager in `_run_async` and shared across the session.
- ~~`get_session_history()` in `short_term.py` is defined but never called~~ — removed.
- `memory.db_path` in `config.yaml` is CWD-relative — running `clearcode` from different directories creates separate `.memory/` folders with no session continuity across projects.
- `llm` and `embedder` returned from `initialize()` in `main.py` are never used downstream — the agent constructs its own copies per query.
- `show_index` in Qdrant backends hardcodes `limit=1000` — silently truncates for large collections.
- `switch_session` in `main.py` accepts any arbitrary string with no validation that the thread ID exists in the SQLite DB — passing a non-existent ID silently starts a blank conversation.
- `_build_system_prompt` in `agent/factory.py` formats MCP tool descriptions as `t.description` without guarding against `None` — servers that omit descriptions will render as `tool_name: None` or raise `AttributeError`.
- `rich.Prompt.ask()` is synchronous blocking I/O called inside `async def _run_async` — blocks the event loop while waiting for user input.

## Build Order

1. Architecture — done
2. Context layer: indexers + retrievers — **done**
3. Agent reasoning layer — **done (initial)**
4. Memory layer — **in progress**
5. MCP integrations — **in progress**
6. Skills
7. Safety, Freshness, Observability
8. Eval layer

When adding code, match the layer currently being built in the blog series. Don't implement future layers ahead of the companion post.
