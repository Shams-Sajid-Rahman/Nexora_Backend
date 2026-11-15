"""Finance routers."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.helpers import get_company_scoped
from app.common.pagination import ok_list
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.db.session import get_db
from . import services
from .models import (Account, BankAccount, Bill, CreditNote, Expense,
                     FiscalYear, Invoice, JournalEntry, JournalLine, Payment)
from .schemas import InvoiceCreate, JournalCreate, PaymentCreate

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


@router.post("/journal-entries", status_code=201, dependencies=[Depends(require_permission("finance.journal.create"))])
def create_journal(payload: JournalCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user), company=Depends(get_current_company),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    entry = services.create_journal(db, company.id, user.id, entry_date=payload.date,
                                    description=payload.description, period_id=payload.period_id,
                                    lines=[l.model_dump() for l in payload.lines],
                                    idempotency_key=idempotency_key or payload.idempotency_key)
    return {"data": serialize(entry), "meta": None}


@router.get("/journal-entries", dependencies=[Depends(require_permission("finance.journal.view"))])
def list_journals(db: Session = Depends(get_db), company=Depends(get_current_company),
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  status: str | None = None):
    q = db.query(JournalEntry).filter(JournalEntry.company_id == company.id).order_by(JournalEntry.date.desc())
    if status:
        q = q.filter(JournalEntry.status == status)
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.get("/journal-entries/{journal_id}", dependencies=[Depends(require_permission("finance.journal.view"))])
def get_journal(journal_id: UUID, db: Session = Depends(get_db), company=Depends(get_current_company)):
    entry = get_company_scoped(db, JournalEntry, journal_id, company.id)
    lines = db.query(JournalLine).filter(JournalLine.journal_id == entry.id).all()
    data = serialize(entry)
    data["lines"] = serialize_list(lines)
    return {"data": data, "meta": None}


@router.post("/journal-entries/{journal_id}/post", dependencies=[Depends(require_permission("finance.journal.post"))])
def post_journal(journal_id: UUID, db: Session = Depends(get_db),
                 user=Depends(get_current_user), company=Depends(get_current_company),
                 idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    entry = services.post_journal(db, company.id, user.id, journal_id)
    return {"data": serialize(entry), "meta": None}


@router.post("/journal-entries/{journal_id}/reverse", dependencies=[Depends(require_permission("finance.journal.post"))])
def reverse_journal(journal_id: UUID, db: Session = Depends(get_db),
                    user=Depends(get_current_user), company=Depends(get_current_company)):
    entry = services.reverse_journal(db, company.id, user.id, journal_id)
    return {"data": serialize(entry), "meta": None}


@router.post("/invoices", status_code=201, dependencies=[Depends(require_permission("finance.invoice.create"))])
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user), company=Depends(get_current_company)):
    inv = services.create_invoice(db, company.id, user.id, customer_id=payload.customer_id,
                                  sales_order_id=payload.sales_order_id, entry_date=payload.date,
                                  due_date=payload.due_date, currency=payload.currency, items=payload.items)
    return {"data": serialize(inv), "meta": None}


@router.post("/invoices/{invoice_id}/post", dependencies=[Depends(require_permission("finance.invoice.create"))])
def post_invoice(invoice_id: UUID, db: Session = Depends(get_db),
                 user=Depends(get_current_user), company=Depends(get_current_company)):
    inv = services.post_invoice(db, company.id, user.id, invoice_id)
    return {"data": serialize(inv), "meta": None}


@router.get("/invoices", dependencies=[Depends(require_permission("finance.invoice.view"))])
def list_invoices(db: Session = Depends(get_db), company=Depends(get_current_company),
                  page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    q = db.query(Invoice).filter(Invoice.company_id == company.id)
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.post("/payments", status_code=201, dependencies=[Depends(require_permission("finance.payment.create"))])
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user), company=Depends(get_current_company),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    data = payload.model_dump()
    if idempotency_key:
        data["idempotency_key"] = idempotency_key
    payment = services.create_payment(db, company.id, user.id, payload=data)
    return {"data": serialize(payment), "meta": None}


@router.get("/profit-and-loss", dependencies=[Depends(require_permission("finance.report.view"))])
def profit_and_loss(db: Session = Depends(get_db), company=Depends(get_current_company),
                    start: date = Query(...), end: date = Query(...)):
    return {"data": services.profit_and_loss(db, company.id, start, end), "meta": None}


@router.get("/trial-balance", dependencies=[Depends(require_permission("finance.report.view"))])
def trial_balance(db: Session = Depends(get_db), company=Depends(get_current_company)):
    return {"data": services.trial_balance(db, company.id), "meta": None}


account_router = make_crud_router(Account, prefix="/api/v1/finance/accounts", permission="finance.account", name="Account")
bank_router = make_crud_router(BankAccount, prefix="/api/v1/finance/bank-accounts", permission="finance.account", name="BankAccount")
bill_router = make_crud_router(Bill, prefix="/api/v1/finance/bills", permission="finance.invoice", name="Bill")
expense_router = make_crud_router(Expense, prefix="/api/v1/finance/expenses", permission="finance.invoice", name="Expense")
fiscal_router = make_crud_router(FiscalYear, prefix="/api/v1/finance/fiscal-years", permission="finance.account", name="FiscalYear")

routers = [router, account_router, bank_router, bill_router, expense_router, fiscal_router]
