# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClearCode is a build-in-public project to reverse-engineering a production-grade autonomous coding agent from scratch, using Python, LangChain, and MCP. Each layer is built incrementally and documented publicly at [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode).

## Current State

The context, agent, memory, MCP, skills, and tasks layers are implemented and wired together. Three vector store backends are supported (ChromaDB, Qdrant semantic, Qdrant hybrid), all switchable via config. The agent is fully async, connects to MCP servers at startup, and supports a progressive-disclosure skills system. The tasks layer adds autonomous multi-step plan execution: the LLM produces a structured `ExecutionPlan`, the user approves it, and an orchestrator executes tasks serially with dependency resolution, retry logic, and an LLM-as-judge per task.

```
clearcode/
├── config.py                          # Loads config.yaml via Path(__file__).parent
├── config.yaml                        # LLM, embeddings, RAG mode, vector store config
├── main.py                            # REPL entry point — auto-indexes CWD on first run
├── llm/
│   └── factory.py                     # Provider-dispatched LLM and embedder factories
├── context/
│   ├── indexers/
│   │   ├── factory.py                 # Dispatches to the right indexer/watcher handler by rag.mode + provider
│   │   ├── code_parser.py             # AST chunking (tree-sitter) + sliding window fallback
│   │   ├── semantic_chroma.py         # Incremental (mtime-based) dense indexing into ChromaDB
│   │   ├── semantic_qdrant.py         # Dense indexing into Qdrant
│   │   ├── hybrid_qdrant.py          # Dense + sparse (BM25) indexing into Qdrant
│   │   └── watcher.py                 # Watchdog observer — real-time per-file re-indexing on save
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
├── tasks/
│   ├── planner.py                     # create_plan() — LLM → structured ExecutionPlan (Pydantic)
│   ├── approval.py                    # present_plan_for_approval() — Rich table + A/M/R loop
│   ├── task_store.py                  # SQLiteTaskStore — WAL mode, atomic state transitions, retry logic
│   ├── executor.py                    # run_subtask_agent() — per-task agent + LLM-as-judge
│   ├── orchestrator.py                # TaskOrchestrator + handle_plan_command() — dependency loop, recovery
│   └── recovery.py                    # RecoveryManager — resets IN_PROGRESS → PENDING on restart
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
| `/plan <goal>` | Generate, approve, and execute an autonomous multi-step plan |
| `/task_status` | Show progress table for the active project |
| `/show_index` | Dump all indexed chunks |
| `/reindex` | Force a full incremental re-index of the current directory |
| `/new_session` | Start a fresh conversation |
| `/switch <session_id>` | Resume a past session |
| `/session` | Show current session ID |
| `/exit` | Quit |

## Architecture Notes

- **Chunking**: `code_parser.py` uses tree-sitter for AST-aware chunking across 15 languages. Falls back to a sliding window (50 lines, 10-line overlap) for text/config files and files with no extractable AST blocks. tree-sitter returns byte offsets — all slicing is done on `source_bytes` (not the decoded `str`) to avoid truncation with multi-byte characters.
- **Indexing**: ChromaDB uses stable chunk IDs (`source::name::start_line`) for idempotent upserts and mtime-based incremental indexing — unchanged files are skipped entirely, changed files have old chunks deleted before re-embedding, deleted files are pruned. Qdrant backends use `from_documents()` and check `points_count` to skip re-indexing on startup.
- **Watcher**: `watcher.py` starts a `watchdog` FSEvents/inotify observer in a background daemon thread. File create/modify/delete/rename events are debounced per-file (1.5 s) then dispatched to `index_single_file()` or `remove_file_from_index()` via `factory.get_single_file_indexer()` / `get_file_remover()` — so the right backend is used regardless of which provider is configured. This keeps the index current in real time without a full re-scan.
- **Hybrid RAG**: `hybrid_qdrant.py` stores both dense (OpenAI `text-embedding-3-small`) and sparse (BM25 via `fastembed`) vectors per chunk. `retrieval_mode` in config controls whether queries use dense, sparse, or hybrid fusion at retrieval time.
- **Factory dispatch**: `indexers/factory.py` and `retrievers/factory.py` select the backend based on `config["rag"]["mode"]` and `config["vector_store"]["provider"]`. Four dispatcher functions: `get_indexer()`, `get_index_inspector()`, `get_single_file_indexer()`, `get_file_remover()`. Adding a new backend requires a new `*_<backend>.py` pair and a branch in each dispatcher.
- **Agent**: `factory.py` builds an async `create_agent` with local tools (search, terminal), MCP tools loaded at startup, and a `load_skill` tool for progressive skill disclosure. The system prompt is built dynamically — it includes MCP tool names/descriptions and a skills index (name + when_to_use) so the LLM knows what's available without paying the token cost of full skill bodies. Filesystem operations are delegated entirely to the filesystem MCP server.
- **Skills**: `SkillRegistry` scans `.clearcode/skills/` at startup. Each skill is a folder with a `SKILL.md` (YAML frontmatter + instruction body). The agent sees a compact metadata summary in the system prompt (Tier 1), loads the full body via `load_skill` on demand (Tier 2), and reads individual support files via `read_file` if needed (Tier 3).
- **MCP**: `clearcode_mcp_servers.json` defines MCP servers. `clearcode_mcp_config.py` resolves `${ENV_VAR}` and `${CWD}` placeholders — `${CWD}` is injected at load time so it always resolves to the directory where clearcode was launched. Two servers are configured by default: GitHub (unauthenticated for public repos; set `GITHUB_TOKEN` in `.env` for private repos and write access) and filesystem (scoped to CWD).
- **Tasks layer**: `planner.py` calls the LLM with `response_format=ExecutionPlan` (structured output) to produce a typed DAG of `PlannedTask` objects. `approval.py` renders the plan as a Rich table and loops until the user approves (A), modifies (M), or rejects (R). `task_store.py` persists the approved plan to SQLite (WAL mode) and manages all state transitions atomically. `executor.py` builds a fresh agent per task with a least-privilege tool set keyed on `task_type`, then runs an LLM-as-judge to verify the output against `acceptance_criteria` before marking the task complete. `orchestrator.py` loops over ready tasks (all deps completed/skipped), dispatches them serially, and handles retries via `fail_task`'s SQL CASE logic. `recovery.py` resets any `IN_PROGRESS` tasks to `PENDING` on restart so crashed runs can resume cleanly.

## Tasks Layer Config

```yaml
tasks:
  db_path: .clearcode/tasks/tasks.db   # CWD-relative — separate DB per project directory
```

Add this block to `config.yaml` to control where the task store lives. `db_path` is resolved relative to CWD at startup.

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
- LLM planner occasionally generates duplicate task `id` values (e.g. two tasks both named `task_005`). `create_project` does a direct INSERT with no deduplication guard, so SQLite raises `UNIQUE constraint failed: tasks.id` after the user has already approved — the entire run is lost.
- `fail_task` increments `retry_count` unconditionally before checking `max_retries`, so a task that exhausts all retries ends up with `retry_count = max_retries + 1` in the DB.
- `get_dep_results` only returns `id`, `title`, and `result` — it omits `output_files`. Downstream agents therefore cannot read the actual files written by dependency tasks; they only see the text summary stored in `result`.

## Build Order

1. Architecture — done
2. Context layer: indexers + retrievers — **done**
3. Agent reasoning layer — **done (initial)**
4. Memory layer — **done (initial)**
5. MCP integrations — **done (initial)**
6. Skills — **done (initial)**
7. Tasks layer — **done (initial)**
8. Safety, Freshness, Observability
9. Eval layer

When adding code, match the layer currently being built in the blog series. Don't implement future layers ahead of the companion post.
