# ClearCode

![ClearCode — System Architecture](assets/cover.svg)

**Reverse-engineering a production-grade autonomous coding agent — one layer at a time.**

I use Claude Code daily. At some point that stopped being enough — I wanted to understand exactly what happens between a natural-language prompt and a committed code change. ClearCode is my attempt to build that understanding by constructing a full coding agent from scratch, with every architectural decision documented publicly.

This is not a tutorial and not a clone. It is a rigorous, build-in-public engineering project with production-level ambitions: layered architecture, a complete evaluation harness, and honest write-ups on what works and what doesn't.

---

## Why this project

Modern coding agents are surprisingly opaque. The surface area of the problem is wide: context retrieval, tool orchestration, agent reasoning, safety constraints, freshness management, and evaluation — each of which is a non-trivial engineering problem in its own right. Building one end-to-end is the most direct path to genuinely understanding the design space.

The companion blog series at [blog.divyampatro.dev](https://blog.divyampatro.dev) documents every tradeoff and decision in writing, because building something and being able to explain it clearly are two different skills worth practicing together.

---

## Architecture

The system is decomposed into focused, independently testable layers:

```
clearcode/
│
├── context/              # Context layer
│   ├── indexers/         # AST-aware and embedding-based codebase indexing
│   ├── retrievers/       # Hybrid retrieval over code indexes
│   └── memory/           # Short-term working memory + long-term storage
│
├── agent/                # Agent reasoning and planning (LangGraph)
├── llm/                  # Provider abstraction layer
├── tools/                # Discrete, composable tool functions
├── mcp/                  # MCP server integrations
├── skills/               # Higher-level composed capabilities
├── safety/               # Input/output safety guardrails
├── freshness/            # Index staleness detection and re-indexing
├── observability/        # Tracing, logging, and metrics
│
└── eval/                 # Evaluation harness
    ├── datasets/         # Shared golden datasets
    ├── retrieval/        # Recall@k · MRR · NDCG · Hit Rate
    ├── context/          # Context precision and context recall
    ├── generation/       # Faithfulness and answer relevancy (RAGAS)
    └── agent/            # Task success rate and step accuracy
```

Each layer has a clearly defined interface so it can be built, evaluated, and improved without breaking adjacent layers.

---

## Evaluation

The eval layer is first-class, not an afterthought. Retrieval quality, context quality, generation quality, and end-to-end agent performance are each measured with industry-standard metrics before any layer is considered complete. This makes regressions visible and improvements measurable.

---

## Series

| Part | Topic | Status |
|------|-------|--------|
| 1 | Architecture and design decisions before writing any code | [Published](https://blog.divyampatro.dev/clearcode-part-1-reverse-engineering-a-coding-agent-before-writing-a-single-line-of-code) |
| 2 | Context layer: indexing a codebase | In progress |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Language | Python |
| Agent orchestration | LangChain / LangGraph |
| Tool protocol | MCP (Model Context Protocol) |
| Evaluation | RAGAS, custom retrieval metrics |

The stack is intentionally minimal at the start and grows only when a new layer genuinely requires it.

---

## Status

Active development. The architecture is defined; implementation begins at the context layer and proceeds upward. Each part of the series ships with working code and a companion post.

Follow along: [blog.divyampatro.dev](https://blog.divyampatro.dev)
