# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ClearCode is a build-in-public project to reverse-engineer a production-grade autonomous coding agent from scratch, using Python, LangChain/LangGraph, and MCP. Each layer is built incrementally and documented publicly at [blog.divyampatro.dev](https://blog.divyampatro.dev).

The codebase is **early stage** — the folder structure below is the target architecture; most of it does not exist yet.

## Planned Architecture

```
clearcode/
├── context/          # Context layer
│   ├── indexers/     # Build indexes over the codebase
│   ├── retrievers/   # Query those indexes
│   └── memory/       # Short-term and long-term memory
├── agent/            # Agent reasoning layer (LangGraph)
├── llm/              # LLM provider abstraction
├── tools/            # Individual tool functions
├── mcp/              # MCP server integrations
├── skills/           # Higher-level composed capabilities
├── safety/           # Safety layer
├── freshness/        # Freshness layer
├── observability/    # Observability layer
└── eval/             # Evaluation layer
    ├── datasets/     # Shared golden datasets
    ├── retrieval/    # Recall@k, MRR, NDCG, Hit Rate
    ├── context/      # Context precision and recall
    ├── generation/   # Faithfulness, answer relevancy (RAGAS)
    └── agent/        # Task success rate, step accuracy
```

## Stack

- **Python** — primary language
- **LangChain / LangGraph** — agent orchestration
- **MCP (Model Context Protocol)** — tool/server integrations

Stack evolves as each layer is built; update this file when packages are pinned.

## Development Setup

Commands will be added here as each layer is implemented. Once a `pyproject.toml` or `requirements.txt` exists:

```bash
# Install dependencies (expected)
pip install -e ".[dev]"

# Run tests (expected)
pytest

# Run a single test
pytest path/to/test_file.py::test_name -v

# Lint (expected)
ruff check .
ruff format .
```

Update this section when the actual tooling is wired up.

## Build Order

The project is built layer by layer in series order:
1. Architecture (done — this repo)
2. Context layer: indexers → retrievers → memory
3. Agent reasoning layer
4. LLM abstraction
5. Tools, MCP integrations, Skills
6. Safety, Freshness, Observability
7. Eval layer

When adding code, match the layer currently being built in the blog series. Don't implement future layers ahead of the companion post.
