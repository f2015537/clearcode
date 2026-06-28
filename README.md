# ClearCode

![ClearCode — System Architecture](assets/cover.svg)

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/LangChain-powered-green" alt="LangChain" />
  <img src="https://img.shields.io/badge/vector%20store-Qdrant%20%7C%20ChromaDB-purple" alt="Vector Store" />
  <img src="https://img.shields.io/badge/build-in%20public-orange" alt="Build in Public" />
</p>

> Reverse-engineering a production-grade autonomous coding agent — one layer at a time.

I use Claude Code daily. At some point that stopped being enough — I wanted to understand exactly what happens between a natural-language prompt and a committed code change. ClearCode is my attempt to build that understanding by constructing a full coding agent from scratch, with every architectural decision documented publicly.

This is not a tutorial and not a clone. It is a rigorous, build-in-public engineering project with production-level ambitions: layered architecture, a complete evaluation harness, and honest write-ups on what works and what doesn't.

Companion series: [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode)

---

## What works today

A working RAG-powered code assistant that runs as a local REPL. Point it at any codebase and ask questions — it indexes the source files, embeds them into a vector store, and answers using retrieved context.

```bash
cd /path/to/your/project
poetry run clearcode
```

```
ClearCode — RAG-powered code assistant

> /ask how does the chunking system work?

The chunking system in code_parser.py (lines 71–87) uses tree-sitter to walk
the AST and extract named blocks — functions, classes, and methods — across 15
languages. It stops at the top-level block and does not index nested functions
separately, keeping chunks semantically coherent.

For files with no meaningful AST (config, markdown, text), it falls back to a
sliding window of 50 lines with 10-line overlap (lines 146–170).
```

| Command | Description |
|---------|-------------|
| `/ask <question>` | Ask a question about the indexed codebase |
| `/show_semantic_index` | Inspect all indexed chunks |
| `/exit` | Quit |

---

## Architecture

The system is decomposed into focused, independently testable layers. Each layer has a clearly defined interface so it can be built, evaluated, and improved without breaking adjacent layers.

```
clearcode/
│
├── context/              # Context layer — built
│   ├── indexers/         # AST-aware chunking + ChromaDB / Qdrant backends
│   └── retrievers/       # Semantic and hybrid retrieval
│
├── agent/                # Agent reasoning layer — built (initial)
├── llm/                  # LLM + embedder provider abstraction
├── observability/        # Structured logging
│
├── memory/               # Short-term + long-term memory        — planned
├── mcp/                  # MCP server integrations              — planned
├── skills/               # Higher-level composed capabilities    — planned
├── safety/               # Input/output safety guardrails        — planned
├── freshness/            # Staleness detection and re-indexing   — planned
│
└── eval/                 # Evaluation harness                   — planned
    ├── retrieval/        # Recall@k · MRR · NDCG · Hit Rate
    ├── context/          # Context precision and recall
    ├── generation/       # Faithfulness and answer relevancy (RAGAS)
    └── agent/            # Task success rate and step accuracy
```

---

## Context layer

The context layer is the foundation everything else builds on. Getting it right matters more than moving fast.

**Chunking** — `code_parser.py` uses tree-sitter to walk the AST and extract named blocks (functions, classes, methods) across 15 languages. It stops at the top-level block and does not index nested functions separately, keeping chunks semantically coherent. For text and config files with no meaningful AST, it falls back to a sliding window. One correctness detail: tree-sitter returns byte offsets, not character offsets, so all source slicing is done on the encoded bytes before decoding — otherwise multi-byte characters silently truncate chunk names.

**Indexing** — Three backends, all behind a factory interface. Switching is a one-line change in `config.yaml`:

| Backend | Mode | Notes |
|---------|------|-------|
| ChromaDB | Dense | Local, no cloud account needed |
| Qdrant (semantic) | Dense | Cloud-hosted, pure embedding similarity |
| Qdrant (hybrid) | Dense + BM25 sparse | Best retrieval quality — active default |

**Hybrid retrieval** — The Qdrant hybrid backend stores two vector representations per chunk: a dense embedding from `text-embedding-3-small` capturing semantic meaning, and a sparse BM25 vector capturing exact keyword overlap. At query time, both are scored and fused. This catches cases where pure semantic search misses exact identifiers or rare terms, and where keyword search misses conceptually related code.

---

## Evaluation

The eval layer is first-class, not an afterthought. Retrieval quality, context quality, generation quality, and end-to-end agent performance will each be measured with industry-standard metrics before any layer is considered complete. This makes regressions visible and improvements measurable.

---

## Series

Full series index: [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode)

| Part | Topic | Status |
|------|-------|--------|
| 1 | [Architecture and design decisions before writing any code](https://blog.divyampatro.dev/clearcode-part-1-reverse-engineering-a-coding-agent-before-writing-a-single-line-of-code) | Published |
| 2 | Context layer: AST-aware indexing, vector stores, and hybrid retrieval | Coming soon |
| 3 | Agent reasoning: tool-calling, orchestration, and the REPL | Upcoming |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| Agent orchestration | LangChain |
| LLM | OpenAI GPT-4o · Anthropic Claude (configurable) |
| Embeddings | OpenAI `text-embedding-3-small` · HuggingFace (configurable) |
| Vector store | Qdrant (hybrid) · ChromaDB (local) |
| Sparse embeddings | BM25 via fastembed |
| Code parsing | tree-sitter · tree-sitter-languages (15 languages) |
| Tool protocol | MCP (upcoming) |
| Evaluation | RAGAS · custom retrieval metrics (upcoming) |

---

## Getting started

**Prerequisites:** Python 3.12, [Poetry](https://python-poetry.org)

```bash
# 1. Clone and install
git clone https://github.com/f2015537/clearcode.git
cd clearcode
poetry install

# 2. Configure credentials
cp .env.example .env
# Edit .env and add your API keys

# 3. Run from inside any repo you want to query
cd /path/to/your/project
poetry run clearcode
```

To use ChromaDB locally instead of Qdrant (no cloud account needed), set the following in `clearcode/config.yaml`:

```yaml
rag:
  mode: semantic

vector_store:
  provider: chromadb
```

---

Follow along: [blog.divyampatro.dev/series/clearcode](https://blog.divyampatro.dev/series/clearcode)
