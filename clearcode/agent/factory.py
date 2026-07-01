from langchain.agents import create_agent


from clearcode.llm.factory import get_llm
from clearcode.agent.tools import search_codebase
from clearcode.observability.logger import get_logger
from clearcode.memory.short_term import get_checkpointer, get_summarization_middleware


logger = get_logger(__name__)


SYSTEM_PROMPT = """You are a senior software engineer with deep knowledge of the codebase.
Always use the search_codebase tool before answering any question.
Reference specific file names, function names and line numbers in your answers.
If you cannot find the answer in the codebase, say so explicitly."""


def build_agent():
  """Create and return a LangChain agent with persistent memory."""
  llm = get_llm()
  tools = [search_codebase]
  logger.info("Creating agent")
  checkpointer = get_checkpointer()
  middleware = get_summarization_middleware()
  return create_agent(
      llm,
      tools=tools,
      system_prompt=SYSTEM_PROMPT,
      checkpointer=checkpointer,
      middleware=[middleware],
  )
