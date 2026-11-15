"""AI routers. AI never posts/approves/modifies salaries — see services."""
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.helpers import get_company_scoped
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import AiConversation, Document, KnowledgeChunk, KnowledgeDocument
from .schemas import ConversationCreate, KnowledgeDocumentCreate, MessageCreate

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


@router.get("/conversations", dependencies=[Depends(require_permission("ai.conversation.view"))])
def list_conversations(db: Session = Depends(get_db), company=Depends(get_current_company)):
    convs = db.query(AiConversation).filter(AiConversation.company_id == company.id).order_by(
        AiConversation.created_at.desc()).all()
    return {"data": serialize_list(convs), "meta": None}


@router.post("/conversations", status_code=201, dependencies=[Depends(require_permission("ai.conversation.create"))])
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db),
                        user=Depends(get_current_user), company=Depends(get_current_company)):
    conv = AiConversation(company_id=company.id, user_id=user.id, title=payload.title)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"data": serialize(conv), "meta": None}


@router.post("/conversations/{conversation_id}/messages", dependencies=[Depends(require_permission("ai.conversation.create"))])
def send_message(conversation_id: UUID, payload: MessageCreate, db: Session = Depends(get_db),
                 user=Depends(get_current_user), company=Depends(get_current_company)):
    conv = get_company_scoped(db, AiConversation, conversation_id, company.id)
    result = services.ask(db, user, company.id, conv.id, payload.content, payload.tool_name)
    return {"data": result, "meta": None}


@router.get("/conversations/{conversation_id}/messages", dependencies=[Depends(require_permission("ai.conversation.view"))])
def list_messages(conversation_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    from .models import AiMessage
    conv = get_company_scoped(db, AiConversation, conversation_id, company.id)
    msgs = db.query(AiMessage).filter(AiMessage.conversation_id == conv.id).order_by(AiMessage.created_at).all()
    return {"data": serialize_list(msgs), "meta": None}


@router.post("/forecast", dependencies=[Depends(require_permission("ai.tool.use"))])
def forecast(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.forecast_sales(db, company.id), "meta": None}


@router.post("/anomalies", dependencies=[Depends(require_permission("ai.tool.use"))])
def anomalies(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.detect_anomalies(db, company.id), "meta": None}


@router.post("/documents", status_code=201, dependencies=[Depends(require_permission("ai.conversation.create"))])
def upload_document(owner_type: str, owner_id: str, file: UploadFile = File(...),
                    db: Session = Depends(get_db), company=Depends(get_current_company)):
    """Stub extraction: metadata is stored; OCR text extraction is a
    Phase 15 worker job (see app/worker.py). No file is served publicly."""
    doc = Document(company_id=company.id, owner_type=owner_type, owner_id=owner_id,
                   file_name=file.filename or "upload",
                   storage_key=f"{company.id}/{owner_type}/{owner_id}/{file.filename or 'upload'}",
                   mime_type=file.content_type, size_bytes=0)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"data": serialize(doc), "meta": None}


@router.post("/knowledge", status_code=201, dependencies=[Depends(require_permission("ai.conversation.create"))])
def add_knowledge(payload: KnowledgeDocumentCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    doc = KnowledgeDocument(company_id=company.id, title=payload.title)
    db.add(doc)
    db.flush()
    # Naive chunking (500 chars); embeddings are a Phase 15 concern.
    for i in range(0, len(payload.text), 500):
        db.add(KnowledgeChunk(knowledge_document_id=doc.id, chunk_text=payload.text[i:i + 500]))
    db.commit()
    db.refresh(doc)
    return {"data": serialize(doc), "meta": None}


conv_router = make_crud_router(AiConversation, prefix="/api/v1/ai/conversations-list", permission="ai.conversation", name="AiConversation")

routers = [router, conv_router]
