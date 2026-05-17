from pydantic import BaseModel, Field
from typing import Optional

class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    tool_used: Optional[str] = None
    sources: list[dict] = Field(default_factory=list)
    notices: list[dict] = Field(default_factory=list)
    session_id: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None 