import os
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_tool_calling_agent, AgentExecutor

from app.tools.rag_tool import search_rgukt_documents
from app.tools.notice_tool import fetch_rgukt_notices
from app.agent.prompts import get_agent_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


def create_askacademia_agent():
    """Create and return the AskAcademia tool-calling agent."""
    groq_api_key = os.getenv("GROQ_API_KEY")

    if not groq_api_key:
        logger.error("GROQ_API_KEY not found in environment variables")
        raise ValueError("GROQ_API_KEY is required")

    tools = [search_rgukt_documents, fetch_rgukt_notices]
    logger.info(f"Registered {len(tools)} tools: {[t.name for t in tools]}")

    llm = ChatGroq(
        model_name="llama-3.1-8b-instant",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        request_timeout=120,
        max_retries=5,
    )
    logger.info("Initialized Groq LLM (mixtral-8x7b-32768)")

    prompt = get_agent_prompt()

    agent = create_tool_calling_agent(llm, tools, prompt)
    logger.info("Created tool-calling agent")

    askacademia_agent = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True
    )
    logger.info("AskAcademia agent setup complete")

    return askacademia_agent


_agent_instance = None

def get_agent():
    global _agent_instance
    if _agent_instance is None:
        logger.info("Initializing AskAcademia agent (first request)...")
        _agent_instance = create_askacademia_agent()
    return _agent_instance


if __name__ == "__main__":
    print("AskAcademia agent initialized successfully.")
    print(f"Available tools: {[t.name for t in get_agent().tools]}")
