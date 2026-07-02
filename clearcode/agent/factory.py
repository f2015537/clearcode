from langchain.agents import create_agent


from clearcode.llm.factory import get_llm
from clearcode.tools.retrieval_tools import search_codebase
from clearcode.observability.logger import get_logger

from clearcode.memory.short_term import get_summarization_middleware
from clearcode.tools.terminal_tools import run_command, run_in_directory
from clearcode.tools.filesystem_tools import (
    read_file,
    write_file,
    append_file,
    delete_file,
    list_directory,
    file_exists,
)
from clearcode.mcp.clearcode_mcp_client import get_clearcode_mcp_tools

logger = get_logger(__name__)


_BASE_SYSTEM_PROMPT = """You are a senior software engineer assistant with access to the user's codebase and local environment.

You have the following tools available:

Local tools:
- search_codebase: Semantic search over indexed source files. Always use this first when answering questions about the code.
- read_file: Read any file by absolute path. Use when search results reference a file you need to inspect in full.
- write_file / append_file: Write or append to files. Only use when explicitly asked to make changes.
- delete_file: Delete a file. Only use when explicitly asked.
- list_directory: List directory contents. Use to explore project structure.
- run_command: Run a shell command. Use for tasks like running tests, checking git status, or inspecting build output.
- run_in_directory: Run a shell command in a specific directory.

Guidelines:
- Always search_codebase before answering questions about the code.
- Reference specific file names, function names, and line numbers in your answers.
- Prefer reading over writing — only modify files when the user explicitly asks.
- If you cannot find the answer, say so explicitly rather than guessing."""


def _build_system_prompt(mcp_tools: list) -> str:
    if not mcp_tools:
        return _BASE_SYSTEM_PROMPT
    tool_lines = "\n".join(f"- {t.name}: {t.description}" for t in mcp_tools)
    return f"{_BASE_SYSTEM_PROMPT}\n\nMCP tools:\n{tool_lines}"


async def build_agent(checkpointer):
   """Create and return a LangChain agent with persistent memory."""
   llm = get_llm()
   mcp_tools = await get_clearcode_mcp_tools()
   tools = [
       search_codebase,
       run_command,
       run_in_directory,
       read_file,
       write_file,
       append_file,
       delete_file,
       list_directory,
       file_exists,
       *mcp_tools,
   ]
   middleware = get_summarization_middleware(llm)
   system_prompt = _build_system_prompt(mcp_tools)

   return create_agent(
       llm,
       tools=tools,
       system_prompt=system_prompt,
       checkpointer=checkpointer,
       middleware=[middleware],
   )

