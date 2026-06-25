from dotenv import load_dotenv
# Must be called before any clearcode imports — modules may read env vars at import time
load_dotenv()

from rich.console import Console
from rich.prompt import Prompt
from clearcode.observability.logger import get_logger
console = Console()
logger = get_logger(__name__)


def run():
  logger.info("Starting ClearCode ")
  console.print("\n[bold blue]ClearCode[/bold blue] — RAG-powered code assistant")
  console.print("Type [bold]'/exit'[/bold] to quit\n")


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
          # TODO: call retriever + LLM
      else:
          logger.warning(f"Unknown command received: {user_input}")
          console.print("[yellow]Unknown command. Try:[/yellow]")
          console.print("  [bold]index <path>[/bold]  — index a codebase")
          console.print("  [bold]ask <question>[/bold] — ask a question")


if __name__ == "__main__":
  run()
