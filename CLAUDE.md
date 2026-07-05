# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClearCode is a build-in-public project to reverse-engineering a production-grade autonomous coding agent from scratch, using Python, LangChain, and MCP. Each layer is built incrementally and documented publicly at [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode).

## Current State

The context, agent, memory, MCP, and skills layers are implemented and wired together into a working RAG-powered code assistant REPL. Three vector store backends are supported (ChromaDB, Qdrant semantic, Qdrant hybrid), all switchable via config. The agent is fully async, connects to MCP servers at startup, and supports a progressive-disclosure skills system.

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
│   └── terminal_tools.py             # run_command, run_in_directory tools
├── mcp/
│   ├── clearcode_mcp_client.py        # Connects to MCP servers, returns tools via langchain-mcp-adapters
│   ├── clearcode_mcp_config.py        # Loads clearcode_mcp_servers.json, resolves ${ENV_VAR} and ${CWD} placeholders
│   └── clearcode_mcp_servers.json     # MCP server definitions (GitHub + filesystem configured by default)
├── memory/
│   ├── session.py                     # Session ID management (UUID, persisted to .memory/current_session)
│   └── short_term.py                  # AsyncSqliteSaver path helper + SummarizationMiddleware
├── skills/
│   ├── registry.py                    # SkillRegistry — scans .clearcode/skills/, parses SKILL.md frontmatter
│   └── skill_tools.py                 # load_skill @tool + singleton get_registry() + build_skills_prompt()
└── observability/
    └── logger.py                      # Root logger at WARNING, clearcode loggers at DEBUG
```

Layers not yet built: `safety/`, `freshness/`, `eval/`.

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
  mode: semantic     # semantic | hybrid

vector_store:
  provider: chromadb         # chromadb | qdrant
  retrieval_mode: hybrid     # dense | sparse | hybrid (Qdrant only)

chromadb:
  persist_dir: .clearcode/chromadb/
  collection_name: codebase

qdrant:
  collection_name: codebase

memory:
  db_path: .clearcode/memory/memory.db
  summarize_at_tokens: 4000
  keep_last_messages: 20

skills:
  skills_dir: .clearcode/skills
```

All runtime state (index, memory DB, skills) is stored under `.clearcode/` in the CWD. API keys go in `.env` at the repo root (gitignored). `load_dotenv()` in `main.py` is called before all `clearcode.*` imports using an explicit path relative to `__file__`. Qdrant requires `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.

**Re-indexing**: switching `rag.mode`, `vector_store.provider`, or `embeddings.model` requires a full re-index:
- ChromaDB: delete `.clearcode/chromadb/`
- Qdrant: delete the collection via the Qdrant dashboard or client

**Skills**: place skill packages under `.clearcode/skills/<skill_name>/SKILL.md` in the project being analysed. Each `SKILL.md` requires YAML frontmatter (`name`, `description`, `when_to_use`) followed by the instruction body. Support files (scripts, templates, resources) can be nested inside the skill folder and are listed to the agent on demand.

## REPL Commands

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about the codebase |
| `/show_index` | Dump all indexed chunks |
| `/new_session` | Start a fresh conversation |
| `/switch <session_id>` | Resume a past session |
| `/session` | Show current session ID |
| `/exit` | Quit |

## Architecture Notes

- **Chunking**: `code_parser.py` uses tree-sitter for AST-aware chunking across 15 languages. Falls back to a sliding window (50 lines, 10-line overlap) for text/config files and files with no extractable AST blocks. tree-sitter returns byte offsets — all slicing is done on `source_bytes` (not the decoded `str`) to avoid truncation with multi-byte characters.
- **Indexing**: ChromaDB uses stable chunk IDs (`source::name::start_line`) for idempotent upserts. Qdrant backends use `from_documents()` and check `points_count` to skip re-indexing on startup.
- **Hybrid RAG**: `hybrid_qdrant.py` stores both dense (OpenAI `text-embedding-3-small`) and sparse (BM25 via `fastembed`) vectors per chunk. `retrieval_mode` in config controls whether queries use dense, sparse, or hybrid fusion at retrieval time.
- **Factory dispatch**: `indexers/factory.py` and `retrievers/factory.py` select the backend based on `config["rag"]["mode"]` and `config["vector_store"]["provider"]`. Adding a new backend requires a new `*_<backend>.py` pair and a branch in each factory.
- **Agent**: `factory.py` builds an async `create_agent` with local tools (search, terminal), MCP tools loaded at startup, and a `load_skill` tool for progressive skill disclosure. The system prompt is built dynamically — it includes MCP tool names/descriptions and a skills index (name + when_to_use) so the LLM knows what's available without paying the token cost of full skill bodies. Filesystem operations are delegated entirely to the filesystem MCP server.
- **Skills**: `SkillRegistry` scans `.clearcode/skills/` at startup. Each skill is a folder with a `SKILL.md` (YAML frontmatter + instruction body). The agent sees a compact metadata summary in the system prompt (Tier 1), loads the full body via `load_skill` on demand (Tier 2), and reads individual support files via `read_file` if needed (Tier 3).
- **MCP**: `clearcode_mcp_servers.json` defines MCP servers. `clearcode_mcp_config.py` resolves `${ENV_VAR}` and `${CWD}` placeholders — `${CWD}` is injected at load time so it always resolves to the directory where clearcode was launched. Two servers are configured by default: GitHub (unauthenticated for public repos; set `GITHUB_TOKEN` in `.env` for private repos and write access) and filesystem (scoped to CWD).

## Known Flaws (not yet fixed)

- Retriever opens a new DB client on every query — should reuse the connection from indexing.
- Both factory files silently fall through to ChromaDB for unknown provider names — should raise `ValueError`.
- `show_index` in `semantic_chroma.py` fetches all embedding vectors into memory — wasteful for large collections.
- Qdrant indexers batch all docs before upserting — no partial progress on failure.
- `memory.db_path` in `config.yaml` is CWD-relative — running `clearcode` from different directories creates separate `.clearcode/memory/` folders with no session continuity across projects.
- `llm` and `embedder` returned from `initialize()` in `main.py` are never used downstream — the agent constructs its own copies per query.
- `show_index` in Qdrant backends hardcodes `limit=1000` — silently truncates for large collections.
- `switch_session` in `main.py` accepts any arbitrary string with no validation that the thread ID exists in the SQLite DB — passing a non-existent ID silently starts a blank conversation.
- `rich.Prompt.ask()` is synchronous blocking I/O called inside `async def _run_async` — blocks the event loop while waiting for user input.
- `MultiServerMCPClient` in `clearcode_mcp_client.py` is not used as an async context manager — the MCP stdio subprocesses (npx) are started but never explicitly terminated, leaking processes for the lifetime of the REPL.
- `get_clearcode_mcp_tools()` has no per-server error isolation — if any one MCP server fails to start (e.g. `npx` not installed, malformed config), the entire call fails and the agent cannot start at all.
- `_BLOCKED_COMMANDS` in `terminal_tools.py` is trivially bypassed — only exact string matches are checked, so `rm -rf /home/` or `sudo rm -rf ~` are not caught. `shell=True` in `subprocess.run` also means shell metacharacters in LLM-generated commands are a latent injection vector.
- `handle_query` in `orchestrator.py` catches all exceptions and returns a generic error string — when a LangGraph checkpoint is corrupted (crash mid-tool-call), the user sees `"Error: ..."` with no hint that deleting `.clearcode/memory/memory.db` would recover the session.
- No `KeyboardInterrupt` handling in `_run_async` — Ctrl+C during an `await handle_query(...)` call propagates up through the `AsyncSqliteSaver` context manager; any in-flight SQLite write may be left inconsistent.
- `SummarizationMiddleware` is imported from `langchain.agents.middleware`, a non-standard module path not present in mainline LangChain — if the `middleware=` parameter to `create_agent()` is also non-standard, summarization may be silently not applied on LangChain version updates.

## Build Order

1. Architecture — done
2. Context layer: indexers + retrievers — **done**
3. Agent reasoning layer — **done (initial)**
4. Memory layer — **done (initial)**
5. MCP integrations — **done (initial)**
6. Skills — **done (initial)**
7. Safety, Freshness, Observability
8. Eval layer

When adding code, match the layer currently being built in the blog series. Don't implement future layers ahead of the companion post.
