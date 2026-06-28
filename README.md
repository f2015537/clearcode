# ClearCode

![ClearCode — System Architecture](assets/cover.svg)

**Reverse-engineering a production-grade autonomous coding agent — one layer at a time.**

I use Claude Code daily. At some point that stopped being enough — I wanted to understand exactly what happens between a natural-language prompt and a committed code change. ClearCode is my attempt to build that understanding by constructing a full coding agent from scratch, with every architectural decision documented publicly.

This is not a tutorial and not a clone. It is a rigorous, build-in-public engineering project with production-level ambitions: layered architecture, a complete evaluation harness, and honest write-ups on what works and what doesn't.

---

## Why this project

Modern coding agents are surprisingly opaque. The surface area of the problem is wide: context retrieval, tool orchestration, agent reasoning, safety constraints, freshness management, and evaluation — each of which is a non-trivial engineering problem in its own right. Building one end-to-end is the most direct path to genuinely understanding the design space.

The companion blog series at [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode) documents every tradeoff and decision in writing, because building something and being able to explain it clearly are two different skills worth practicing together.

---

## What works today

A working RAG-powered code assistant that runs as a local REPL:

```bash
poetry run clearcode
```

```
> /ask how does the chunking system work?

The chunking system uses tree-sitter for AST-aware parsing across 15 languages.
When a file has no extractable AST blocks, it falls back to a 50-line sliding
window with 10-line overlap. Chunks are stored with stable IDs so re-indexing
is safe and idempotent...
```

On first run it indexes the current working directory. Subsequent runs load the existing index. The agent always searches the codebase before answering, and references specific file names, function names, and line numbers in its responses.

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about the indexed codebase |
| `/show_semantic_index` | Inspect all indexed chunks |
| `/exit` | Quit |

---

## Architecture

The system is decomposed into focused, independently testable layers:

```
clearcode/
│
├── context/              # Context layer — BUILT
│   ├── indexers/         # AST-aware chunking + ChromaDB / Qdrant backends
│   └── retrievers/       # Semantic and hybrid retrieval
│
├── agent/                # Agent reasoning layer — BUILT (initial)
├── llm/                  # LLM + embedder provider abstraction
├── observability/        # Structured logging
│
├── memory/               # Short-term + long-term memory         — planned
├── mcp/                  # MCP server integrations               — planned
├── skills/               # Higher-level composed capabilities     — planned
├── safety/               # Input/output safety guardrails         — planned
├── freshness/            # Staleness detection and re-indexing    — planned
│
└── eval/                 # Evaluation harness                    — planned
    ├── retrieval/        # Recall@k · MRR · NDCG · Hit Rate
    ├── context/          # Context precision and recall
    ├── generation/       # Faithfulness and answer relevancy (RAGAS)
    └── agent/            # Task success rate and step accuracy
```

---

## Context layer

The context layer is the foundation everything else builds on. Getting it right matters more than moving fast.

**Chunking** — `code_parser.py` uses tree-sitter to walk the AST of the source file and extract named blocks (functions, classes, methods) across 15 languages. It stops at the top-level block and doesn't index nested functions separately, keeping chunks semantically coherent. For text and config files with no meaningful AST, it falls back to a sliding window. One subtle correctness fix: tree-sitter returns byte offsets, not character offsets, so all source slicing is done on the encoded bytes before decoding.

**Indexing** — Three backends, all behind a factory interface:

| Backend | Mode | When to use |
|---------|------|-------------|
| ChromaDB | Dense | Local development, no cloud account needed |
| Qdrant (semantic) | Dense | Cloud-hosted, pure embedding similarity |
| Qdrant (hybrid) | Dense + BM25 sparse | Best retrieval quality — active default |

The active backend is a one-line change in `config.yaml`. Switching backend or embedding model requires a re-index.

**Hybrid retrieval** — The Qdrant hybrid backend stores two vector representations per chunk: a dense embedding from `text-embedding-3-small` capturing semantic meaning, and a sparse BM25 vector capturing keyword overlap. At query time, both are scored and fused. This catches cases where pure semantic search misses exact identifiers or rare terms, and where keyword search misses conceptually related code.

---

## Evaluation

The eval layer is first-class, not an afterthought. Retrieval quality, context quality, generation quality, and end-to-end agent performance will each be measured with industry-standard metrics before any layer is considered complete. This makes regressions visible and improvements measurable.

---

## Series

Full series index: [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode)

| Part | Topic | Status |
|------|-------|--------|
| 1 | Architecture and design decisions before writing any code | [Published](https://blog.divyampatro.dev/clearcode-part-1-reverse-engineering-a-coding-agent-before-writing-a-single-line-of-code) |
| 2 | Context layer: AST-aware indexing, vector stores, and hybrid retrieval | In progress |
| 3 | Agent reasoning: tool-calling, orchestration, and the REPL | Upcoming |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Agent orchestration | LangChain |
| LLM | OpenAI GPT-4o (configurable) |
| Embeddings | OpenAI `text-embedding-3-small` (configurable) |
| Vector store | Qdrant (hybrid) · ChromaDB (local) |
| Sparse embeddings | BM25 via fastembed |
| Code parsing | tree-sitter + tree-sitter-languages (15 languages) |
| Tool protocol | MCP (upcoming) |
| Evaluation | RAGAS · custom retrieval metrics (upcoming) |

---

## Running it

```bash
# Clone and install
git clone https://github.com/f2015537/clearcode.git
cd clearcode
poetry install

# Add API keys to .env
echo "OPENAI_API_KEY=sk-..." >> .env
# For Qdrant cloud (optional — defaults to ChromaDB locally):
echo "QDRANT_URL=https://..." >> .env
echo "QDRANT_API_KEY=..." >> .env

# Run from inside any repo you want to query
cd /path/to/your/project
poetry run clearcode
```

To use ChromaDB instead of Qdrant, set `vector_store.provider: chromadb` and `rag.mode: semantic` in `clearcode/config.yaml`.

---

Follow along: [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode)
