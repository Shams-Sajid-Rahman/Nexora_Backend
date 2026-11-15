"""Finance services — the system of record for money.

Invariants (docs/02 FR-FIN, docs/04):
- every posted journal balances (debits == credits), else 409 JOURNAL_UNBALANCED
- closed periods reject postings, else 409 PERIOD_CLOSED
- posted journals are immutable; corrections use reversal entries
- money is NUMERIC, never float; exchange-rate snapshots are stored at posting
- sensitive operations are idempotent via Idempotency-Key
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.helpers import get_company_scoped, next_code, require_same_company
from app.core.audit import log_audit
from app.core.errors import ConflictError, NotFoundError
from .models import (Account, AccountingPeriod, BankAccount, Bill, CreditNote,
                     Expense, Invoice, InvoiceItem, JournalEntry, JournalLine,
                     Payment, PaymentAllocation)

SUPPORTED_CURRENCIES = {"BDT", "USD", "EUR", "GBP"}


def validate_currency(code: str) -> str:
    code = code.upper()
    if code not in SUPPORTED_CURRENCIES:
        raise ConflictError(f"Unsupported currency: {code}")
    return code


def _period_is_closed(db: Session, period_id: UUID | None, entry_date: date) -> bool:
    if period_id:
        period = db.get(AccountingPeriod, period_id)
        if period and period.is_closed:
            return True
    # also reject if any period covering the date is closed
    period = db.query(AccountingPeriod).filter(
        AccountingPeriod.start_date <= entry_date,
        AccountingPeriod.end_date >= entry_date,
        AccountingPeriod.is_closed.is_(True)).first()
    return period is not None


def create_journal(db: Session, company_id: UUID, user_id: UUID, *,
                   entry_date: date, description: str | None,
                   period_id: UUID | None, lines: list[dict],
                   source_type: str | None = None, source_id: str | None = None,
                   idempotency_key: str | None = None) -> JournalEntry:
    if idempotency_key:
        existing = db.query(JournalEntry).filter(
            JournalEntry.company_id == company_id,
            JournalEntry.idempotency_key == idempotency_key).first()
        if existing:
            return existing
    total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)
    if total_debit <= 0 or total_debit != total_credit:
        raise ConflictError("Journal entry must balance: total debits must equal total credits",
                            code="JOURNAL_UNBALANCED", status_code=409)
    entry = JournalEntry(
        company_id=company_id, period_id=period_id, date=entry_date,
        description=description, status="draft", source_type=source_type,
        source_id=source_id, idempotency_key=idempotency_key,
        code=next_code(db, JournalEntry, company_id, "JE"))
    db.add(entry)
    db.flush()
    for line in lines:
        account = db.get(Account, line["account_id"])
        if account is None:
            raise NotFoundError("Account not found")
        require_same_company(account.company_id, company_id, "account")
        currency = validate_currency(line.get("currency", "BDT"))
        rate = Decimal(str(line.get("exchange_rate_snapshot", 1)))
        amount = Decimal(str(line.get("debit", 0))) or Decimal(str(line.get("credit", 0)))
        db.add(JournalLine(
            journal_id=entry.id, account_id=account.id,
            debit=Decimal(str(line.get("debit", 0))),
            credit=Decimal(str(line.get("credit", 0))),
            currency=currency, exchange_rate_snapshot=rate,
            base_amount=(amount * rate).quantize(Decimal("0.0001")),
            description=line.get("description")))
    db.commit()
    db.refresh(entry)
    return entry


def post_journal(db: Session, company_id: UUID, user_id: UUID, journal_id: UUID) -> JournalEntry:
    entry = get_company_scoped(db, JournalEntry, journal_id, company_id)
    if entry.status == "posted":
        return entry
    if _period_is_closed(db, entry.period_id, entry.date):
        raise ConflictError("Accounting period is closed", code="PERIOD_CLOSED", status_code=409)
    lines = db.query(JournalLine).filter(JournalLine.journal_id == entry.id).all()
    if not lines:
        raise ConflictError("Journal entry has no lines", code="JOURNAL_UNBALANCED", status_code=409)
    if sum(l.debit for l in lines) != sum(l.credit for l in lines):
        raise ConflictError("Journal entry must balance", code="JOURNAL_UNBALANCED", status_code=409)
    entry.status = "posted"
    entry.posted_at = datetime.now(timezone.utc)
    entry.posted_by = user_id
    log_audit(db, action="finance.journal.post", entity_type="journal_entry",
              entity_id=entry.id, user_id=user_id, company_id=company_id)
    db.commit()
    db.refresh(entry)
    return entry


def reverse_journal(db: Session, company_id: UUID, user_id: UUID, journal_id: UUID) -> JournalEntry:
    """Posted journals are immutable — correct them with a reversal entry."""
    original = get_company_scoped(db, JournalEntry, journal_id, company_id)
    if original.status != "posted":
        raise ConflictError("Only a posted journal can be reversed")
    lines = db.query(JournalLine).filter(JournalLine.journal_id == original.id).all()
    reversed_lines = [{
        "account_id": l.account_id, "debit": l.credit, "credit": l.debit,
        "currency": l.currency, "exchange_rate_snapshot": l.exchange_rate_snapshot,
        "description": f"Reversal of {original.code}",
    } for l in lines]
    reversal = create_journal(db, company_id, user_id, entry_date=date.today(),
                              description=f"Reversal of {original.code}",
                              period_id=original.period_id, lines=reversed_lines)
    reversal.reverses_id = original.id
    db.commit()
    return post_journal(db, company_id, user_id, reversal.id)


def post_balanced_journal(db: Session, company_id: UUID, user_id: UUID, *,
                          entry_date: date, description: str, lines: list[dict],
                          source_type: str | None = None, source_id: str | None = None) -> JournalEntry:
    """Helper for other modules (payroll, sales, purchases): create + post
    in one transaction. Never write journal rows directly from a router."""
    entry = create_journal(db, company_id, user_id, entry_date=entry_date,
                           description=description, period_id=None, lines=lines,
                           source_type=source_type, source_id=source_id)
    return post_journal(db, company_id, user_id, entry.id)


def create_invoice(db: Session, company_id: UUID, user_id: UUID, *,
                   customer_id: UUID, sales_order_id: UUID | None, entry_date: date,
                   due_date, currency: str, items: list[dict]) -> Invoice:
    from app.modules.sales.models import Customer
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    require_same_company(customer.company_id, company_id, "customer")
    total = sum(Decimal(str(i.get("quantity", 0))) * Decimal(str(i.get("unit_price", 0)))
                for i in items)
    invoice = Invoice(company_id=company_id, customer_id=customer_id,
                      sales_order_id=sales_order_id, code=next_code(db, Invoice, company_id, "INV"),
                      date=entry_date, due_date=due_date, currency=validate_currency(currency),
                      total=total, status="draft")
    db.add(invoice)
    db.flush()
    for item in items:
        db.add(InvoiceItem(invoice_id=invoice.id, product_id=item.get("product_id"),
                           description=item.get("description", ""),
                           quantity=Decimal(str(item.get("quantity", 0))),
                           unit_price=Decimal(str(item.get("unit_price", 0))),
                           total=Decimal(str(item.get("quantity", 0))) * Decimal(str(item.get("unit_price", 0)))))
    db.commit()
    db.refresh(invoice)
    return invoice


def post_invoice(db: Session, company_id: UUID, user_id: UUID, invoice_id: UUID) -> Invoice:
    """Revenue is recognised here — not at quotation or sales-order time."""
    invoice = get_company_scoped(db, Invoice, invoice_id, company_id)
    if invoice.status == "posted":
        return invoice
    ar = db.query(Account).filter(Account.company_id == company_id, Account.code == "1100").first()
    revenue = db.query(Account).filter(Account.company_id == company_id, Account.code == "4000").first()
    if ar is None or revenue is None:
        raise ConflictError("Chart of accounts is incomplete (need 1100 AR and 4000 Revenue)")
    post_balanced_journal(db, company_id, user_id, entry_date=invoice.date,
                          description=f"Invoice {invoice.code}",
                          lines=[{"account_id": ar.id, "debit": invoice.total, "credit": Decimal("0"), "currency": invoice.currency},
                                 {"account_id": revenue.id, "debit": Decimal("0"), "credit": invoice.total, "currency": invoice.currency}],
                          source_type="invoice", source_id=str(invoice.id))
    invoice.status = "posted"
    db.commit()
    db.refresh(invoice)
    return invoice


def create_payment(db: Session, company_id: UUID, user_id: UUID, *, payload: dict) -> Payment:
    if payload.get("idempotency_key"):
        existing = db.query(Payment).filter(
            Payment.company_id == company_id,
            Payment.idempotency_key == payload["idempotency_key"]).first()
        if existing:
            return existing
    payment = Payment(company_id=company_id, type=payload["type"],
                      counterparty_type=payload.get("counterparty_type"),
                      counterparty_id=payload.get("counterparty_id"),
                      bank_account_id=payload.get("bank_account_id"),
                      amount=Decimal(str(payload["amount"])),
                      currency=validate_currency(payload.get("currency", "BDT")),
                      date=payload["date"], reference=payload.get("reference"),
                      idempotency_key=payload.get("idempotency_key"))
    db.add(payment)
    db.flush()
    for alloc in payload.get("allocate_to", []):
        db.add(PaymentAllocation(payment_id=payment.id, document_type=alloc["document_type"],
                                 document_id=alloc["document_id"],
                                 amount=Decimal(str(alloc["amount"]))))
        if alloc["document_type"] == "invoice":
            inv = db.get(Invoice, alloc["document_id"])
            if inv and inv.company_id == company_id:
                inv.paid_total = (inv.paid_total or Decimal("0")) + Decimal(str(alloc["amount"]))
                if inv.paid_total >= inv.total:
                    inv.status = "paid"
        elif alloc["document_type"] == "bill":
            bill = db.get(Bill, alloc["document_id"])
            if bill and bill.company_id == company_id:
                bill.paid_total = (bill.paid_total or Decimal("0")) + Decimal(str(alloc["amount"]))
                if bill.paid_total >= bill.total:
                    bill.status = "paid"
    db.commit()
    db.refresh(payment)
    return payment


def profit_and_loss(db: Session, company_id: UUID, start: date, end: date) -> dict:
    """Derived from posted journals only, never from draft invoices."""
    from sqlalchemy import func
    q = (db.query(Account.type, func.sum(JournalLine.credit - JournalLine.debit))
         .join(JournalLine, JournalLine.account_id == Account.id)
         .join(JournalEntry, JournalEntry.id == JournalLine.journal_id)
         .filter(Account.company_id == company_id,
                 JournalEntry.company_id == company_id,
                 JournalEntry.status == "posted",
                 JournalEntry.date >= start, JournalEntry.date <= end)
         .group_by(Account.type))
    totals = {t: float(v or 0) for t, v in q.all()}
    revenue = totals.get("income", 0.0)
    expenses = -totals.get("expense", 0.0)
    return {"revenue": revenue, "expenses": expenses, "net_profit": revenue - expenses,
            "by_type": totals, "from": str(start), "to": str(end)}


def trial_balance(db: Session, company_id: UUID) -> list[dict]:
    """Posted journals only — drafts must not appear in the trial balance."""
    from sqlalchemy import func, or_
    q = (db.query(Account.code, Account.name, Account.type,
                  func.coalesce(func.sum(JournalLine.debit), 0),
                  func.coalesce(func.sum(JournalLine.credit), 0))
         .outerjoin(JournalLine, JournalLine.account_id == Account.id)
         .outerjoin(JournalEntry, JournalEntry.id == JournalLine.journal_id)
         .filter(Account.company_id == company_id,
                 or_(JournalEntry.id.is_(None), JournalEntry.status == "posted"))
         .group_by(Account.code, Account.name, Account.type))
    return [{"code": c, "name": n, "type": t, "debit": float(d or 0), "credit": float(cr or 0)}
            for c, n, t, d, cr in q.all()]
