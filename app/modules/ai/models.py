"""AI models — docs/04 AI.

knowledge_chunks.embedding is stored as JSON here so the schema runs
without pgvector. On PostgreSQL with pgvector, replace the column with
``Vector(1536)`` (dimension is set in Phase 15 when the embedding model
is chosen — see docs/04). The migration keeps the JSON column and notes
the optional pgvector upgrade.
"""
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, new_uuid


class AiConversation(Base, TimestampMixin):
    __tablename__ = "ai_conversations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="New conversation")


class AiMessage(Base, TimestampMixin):
    __tablename__ = "ai_messages"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("ai_conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)


class AiToolCall(Base):
    __tablename__ = "ai_tool_calls"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai_conversations.id"))
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    arguments: Mapped[dict | None] = mapped_column(JSON)
    result_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AiActionLog(Base):
    __tablename__ = "ai_action_logs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(128))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    was_executed: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(default=0)


class DocumentExtraction(Base, TimestampMixin):
    __tablename__ = "document_extractions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id"), nullable=False, index=True)
    extracted: Mapped[dict | None] = mapped_column(JSON)
    confidence: Mapped[float | None] = mapped_column(Float)


class KnowledgeDocument(Base, TimestampMixin):
    __tablename__ = "knowledge_documents"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    company_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("companies.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documents.id"))


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    knowledge_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional pgvector: replace with Vector(1536) on PostgreSQL in Phase 15.
    embedding: Mapped[dict | None] = mapped_column(JSON)
