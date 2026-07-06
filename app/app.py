import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

from app.agent.setup import get_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AskAcademia API",
    version="2.0",
    description="Agentic RAG API for RGUKT Basar students"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    answer: str
    tool_used: str
    sources: List[Dict[str, Any]]
    notices: List[Dict[str, Any]] = []


def extract_notices_from_steps(intermediate_steps):
    """Robust extraction of notices from tool output."""
    for step in intermediate_steps:
        if isinstance(step, tuple) and len(step) == 2:
            action, output = step
            
            # Check if this step used the notice tool
            if hasattr(action, "tool") and action.tool == "fetch_rgukt_notices":
                
                # Case 1: Tool returned dict with 'notices'
                if isinstance(output, dict) and "notices" in output:
                    return output["notices"]
                
                # Case 2: Tool returned list directly
                if isinstance(output, list):
                    return output
                    
    return []


@app.get("/")
async def health_check():
    return {
        "status": "running",
        "service": "AskAcademia Agent API",
        "version": "2.0"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    logger.info(f"Incoming request - Session: {request.session_id}")

    try:
        result = await get_agent().ainvoke({
            "input": request.message,
            "chat_history": []
        })

        answer = result.get("output", "Sorry, I could not process your request.")
        intermediate_steps = result.get("intermediate_steps", [])

        tool_used = "rag_search"
        sources: List[Dict[str, Any]] = []
        notices: List[Dict[str, Any]] = []

        # Detect which tool was used
        for step in intermediate_steps:
            if isinstance(step, tuple) and len(step) >= 2:
                action = step[0]
                if hasattr(action, "tool"):
                    tool_used = action.tool

                    if tool_used == "search_rgukt_documents":
                        observation = step[1]
                        if isinstance(observation, dict) and "sources" in observation:
                            sources = observation["sources"]

                    elif tool_used == "fetch_rgukt_notices":
                        notices = extract_notices_from_steps(intermediate_steps)
                        answer = "Here are the latest RGUKT notices:"

        logger.info(f"Tool used: {tool_used} | Notices returned: {len(notices)}")

        return ChatResponse(
            answer=answer,
            tool_used=tool_used,
            sources=sources,
            notices=notices
        )

    except Exception as e:
        logger.exception(f"FULL ERROR: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request. Please try again."
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
