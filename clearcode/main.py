import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Must run before any clearcode.* import — those modules call get_llm/get_embedder
# lazily, but any future refactor moving those calls to module level would silently
# break credential loading if .env isn't loaded first.
load_dotenv(Path(__file__).parent.parent / ".env")

from rich.console import Console
from rich.prompt import Prompt

from clearcode.config import config
from clearcode.context.indexers.factory import get_indexer, get_index_inspector
from clearcode.llm.factory import get_llm, get_embedder
from clearcode.agent.orchestrator import handle_query
from clearcode.memory.session import get_current_session, new_session, switch_session
from clearcode.observability.logger import get_logger
from clearcode.agent.factory import build_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from clearcode.memory.short_term import get_checkpointer_db_path
from clearcode.tasks.orchestrator import handle_plan_command
from clearcode.tasks.status import show_task_status
from clearcode.context.indexers.watcher import start_watcher, stop_watcher
from clearcode.cache.semantic_cache import build_semantic_cache, get_repo_domain

console = Console()
logger = get_logger(__name__)


def get_or_create_index():
    repo_path = str(Path.cwd())
    logger.info(f"Checking index for: {repo_path}")
    console.print(f"[dim]Checking index for {repo_path}...[/dim]")
    return get_indexer()(repo_path)


async def initialize(checkpointer):
    """Bootstrap LLM, embedder, index, watcher, MCP tools, and session before the REPL starts."""
    llm = get_llm()
    embedder = get_embedder()
    console.print(
        f"[dim]LLM: {config['llm']['provider']} / {config['llm']['model']}[/dim]"
    )
    console.print(
        f"[dim]Embedder: {config['embeddings']['provider']} / {config['embeddings']['model']}[/dim]"
    )

    repo_path = str(Path.cwd())
    index = get_or_create_index()

    semantic_cache = await build_semantic_cache()
    cache_domain = get_repo_domain(repo_path) if semantic_cache else None

    if semantic_cache is not None:
        console.print(f"[dim]Semantic cache: enabled (threshold={semantic_cache.threshold})[/dim]")
    else:
        console.print(f"[dim]Semantic cache: disabled[/dim]")

    loop = asyncio.get_running_loop()

    def invalidate_cache_on_change():
        if semantic_cache is not None:
            asyncio.run_coroutine_threadsafe(semantic_cache.invalidate_domain(cache_domain), loop)


    observer = start_watcher(repo_path, invalidate_cache_on_change)
    agent = await build_agent(checkpointer)
    session_id = get_current_session()
    console.print(f"[dim]Session: {session_id}[/dim]")
    console.print(f"[green]✓ Ready[/green]\n")
    return llm, embedder, index, observer, agent, session_id, semantic_cache, cache_domain


async def _run_async():
    logger.info("Starting ClearCode")
    console.print("\n[bold blue]ClearCode[/bold blue] — RAG-powered code assistant")

    async with AsyncSqliteSaver.from_conn_string(
        get_checkpointer_db_path()
    ) as checkpointer:
        llm, embedder, index, observer, agent, session_id, semantic_cache, cache_domain = await initialize(checkpointer)
        console.print("Type [bold]'/exit'[/bold] to quit\n")
        try:
            while True:
                user_input = Prompt.ask("[bold green]>[/bold green]")

                if not user_input.strip():
                    continue
                if user_input.lower() in ("/exit", "/quit"):
                    logger.info("Shutting down")
                    console.print("[dim]Goodbye![/dim]")
                    break
                elif user_input.startswith("/ask "):
                    question = user_input.removeprefix("/ask ").strip()
                    logger.info(f"Ask command received: {question}")
                    console.print(f"[dim]Searching for: {question}...[/dim]")
                    response, from_cache = await handle_query(agent, question, session_id, semantic_cache, cache_domain)
                    if from_cache:
                        console.print("[dim]⚡ cache hit[/dim]")
                    console.print(response)
                elif user_input == "/reindex":
                    console.print("[dim]Re-indexing current directory...[/dim]")
                    index = get_or_create_index()
                    if semantic_cache is not None:
                        await semantic_cache.invalidate_domain(cache_domain)
                        console.print("[dim]Semantic cache invalidated for this repo.[/dim]")
                    console.print("[green]✓ Re-index complete.[/green]")
                elif user_input == "/new_session":
                    session_id = new_session()
                    console.print(f"[green]New session started: {session_id}[/green]")
                elif user_input.startswith("/switch "):
                    target = user_input.removeprefix("/switch ").strip()
                    session_id = switch_session(target)
                    console.print(f"[green]Switched to session: {session_id}[/green]")
                elif user_input == "/session":
                    console.print(f"[dim]Current session: {session_id}[/dim]")
                elif user_input == "/show_index":
                    logger.info("Showing index")
                    get_index_inspector()(index)
                elif user_input.startswith("/plan "):
                    goal = user_input.removeprefix("/plan ").strip()
                    logger.info(f"Plan command received: {goal}")
                    await handle_plan_command(goal)
                elif user_input == "/task_status":
                    show_task_status()
                else:
                    logger.warning(f"Unknown command received: {user_input}")
                    console.print("[yellow]Unknown command. Try:[/yellow]")
                    console.print(
                        "  [bold]/ask <question>[/bold]          — ask a question about the codebase"
                    )
                    console.print(
                        "  [bold]/show_index[/bold]              — show all chunks in the index"
                    )
                    console.print(
                        "  [bold]/reindex[/bold]                  — manually re-index the current directory"
                    )
                    console.print(
                        "  [bold]/new_session[/bold]             — start a fresh conversation"
                    )
                    console.print(
                        "  [bold]/switch <session_id>[/bold]     — resume a past session"
                    )
                    console.print(
                        "  [bold]/session[/bold]                 — show current session id"
                    )
                    console.print(  
                        "  [bold]/plan <goal>[/bold]             — generate and execute a plan"
                    )
                    console.print(
                        "  [bold]/task_status[/bold]             — show task progress for active project"
                    )
        finally:
            stop_watcher(observer)


def run():
    asyncio.run(_run_async())


if __name__ == "__main__":
    run()
