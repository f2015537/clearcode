from clearcode.agent.factory import build_agent
from clearcode.observability.logger import get_logger

logger = get_logger(__name__)


async def handle_query(question: str, thread_id: str) -> str:
    """Entry point for all user queries - builds the agent and runs it."""
    logger.info(f"Handling query for session {thread_id}: {question}")
    agent = await build_agent()
    agent_config = {"configurable": {"thread_id": thread_id}}
    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": question}]}, agent_config
        )
        return response["messages"][-1].content
    except Exception as e:
        logger.error(f"Agent error: {e}")
        return f"Error: {e}"
