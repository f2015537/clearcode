from langchain.agents.middleware import SummarizationMiddleware
from pathlib import Path


from clearcode.config import config
from clearcode.llm.factory import get_llm
from clearcode.observability.logger import get_logger

logger = get_logger(__name__)


def get_checkpointer_db_path() -> str:
  db_path = config["memory"]["db_path"]
  # Resolve to absolute so Path.mkdir(parents=True) works reliably on macOS
  # when none of the ancestor directories exist yet.
  abs_path = (Path.cwd() / db_path).resolve()
  abs_path.parent.mkdir(parents=True, exist_ok=True)
  logger.info(f"Using SQLite checkpointer at {abs_path}")
  return str(abs_path)
  

def get_summarization_middleware(llm=None) -> SummarizationMiddleware:
    return SummarizationMiddleware(
        model=llm or get_llm(),
        trigger=("tokens", config["memory"]["summarize_at_tokens"]),
        keep=("messages", config["memory"]["keep_last_messages"]),
    )
