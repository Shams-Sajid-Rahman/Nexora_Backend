"""AI schemas."""
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str = "New conversation"


class MessageCreate(BaseModel):
    content: str
    tool_name: str | None = None  # explicit read-only tool to run, if any


class KnowledgeDocumentCreate(BaseModel):
    title: str
    text: str
