from langchain.agents import create_agent


from clearcode.llm.factory import get_llm
from clearcode.tools.retrieval_tools import search_codebase
from clearcode.observability.logger import get_logger

from clearcode.memory.short_term import get_summarization_middleware
from clearcode.tools.terminal_tools import run_command, run_in_directory
from clearcode.mcp.clearcode_mcp_client import get_clearcode_mcp_tools
from clearcode.skills.skill_tools import load_skill, build_skills_prompt

logger = get_logger(__name__)


_BASE_SYSTEM_PROMPT = """You are a senior software engineer assistant with access to the user's codebase and local environment.

You have the following tools available:

Local tools:
- search_codebase: Semantic search over indexed source files. Always use this first when answering questions about the code.
- run_command: Run a shell command. Use for tasks like running tests, checking git status, or inspecting build output.
- run_in_directory: Run a shell command in a specific directory.

Filesystem tools are available via MCP — use them to read, write, and navigate files when needed.
GitHub tools are available via MCP — use them to interact with GitHub repositories: list issues, create PRs, read file contents, search code, and more.

Guidelines:
- Always search_codebase before answering questions about the code.
- Reference specific file names, function names, and line numbers in your answers.
- Prefer reading over writing — only modify files when the user explicitly asks.
- If you cannot find the answer, say so explicitly rather than guessing."""


def _build_system_prompt(mcp_tools: list) -> str:
    prompt = _BASE_SYSTEM_PROMPT

    if mcp_tools:
        tool_lines = "\n".join(
            f"- {t.name}: {t.description or 'No description'}" for t in mcp_tools
        )
        prompt += f"\n\nMCP tools:\n{tool_lines}"

    skills_prompt = build_skills_prompt()
    if skills_prompt:
        prompt += f"\n\nSkills:\n{skills_prompt}"

    return prompt


async def build_agent(checkpointer):
   """Create and return a LangChain agent with persistent memory."""
   llm = get_llm()
   mcp_tools = await get_clearcode_mcp_tools()
   tools = [
       search_codebase,
       load_skill,
       run_command,
       run_in_directory,
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

