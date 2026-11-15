"""Core services: auth (rotation + reuse detection), companies, RBAC.

Business logic lives here, not in routers (docs/01 §1.5).
"""
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.common.helpers import to_aware
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (create_access_token, get_password_hash,
                               hash_refresh_token, new_refresh_token,
                               verify_password)
from app.core.config import settings
from .models import (Company, Permission, RefreshToken, Role, RolePermission,
                     User, UserCompany, UserRole)

# Permission catalogue — seeded by db/seed.py and kept in sync here.
PERMISSIONS = [
    ("core", "core.company.view"), ("core", "core.company.create"),
    ("core", "core.company.update"), ("core", "core.branch.view"),
    ("core", "core.branch.create"), ("core", "core.user.view"),
    ("core", "core.user.create"), ("core", "core.role.view"),
    ("core", "core.role.create"), ("core", "core.audit.view"),
    ("hr", "hr.employee.view"), ("hr", "hr.employee.create"),
    ("hr", "hr.employee.update"), ("hr", "hr.employee.delete"),
    ("hr", "hr.leave.view"), ("hr", "hr.leave.approve"),
    ("payroll", "payroll.structure.view"), ("payroll", "payroll.structure.create"),
    ("payroll", "payroll.run.view"), ("payroll", "payroll.run.create"),
    ("payroll", "payroll.run.approve"), ("payroll", "payroll.run.post"),
    ("inventory", "inventory.product.view"), ("inventory", "inventory.product.create"),
    ("inventory", "inventory.product.update"), ("inventory", "inventory.product.delete"),
    ("inventory", "inventory.stock.view"), ("inventory", "inventory.stock.adjust"),
    ("purchase", "purchase.supplier.view"), ("purchase", "purchase.supplier.create"),
    ("purchase", "purchase.order.view"), ("purchase", "purchase.order.create"),
    ("purchase", "purchase.order.approve"), ("purchase", "purchase.receipt.create"),
    ("sales", "sales.customer.view"), ("sales", "sales.customer.create"),
    ("sales", "sales.quotation.view"), ("sales", "sales.quotation.create"),
    ("sales", "sales.quotation.approve"), ("sales", "sales.order.view"),
    ("sales", "sales.order.create"), ("sales", "sales.order.fulfil"),
    ("finance", "finance.account.view"), ("finance", "finance.account.create"),
    ("finance", "finance.journal.view"), ("finance", "finance.journal.create"),
    ("finance", "finance.journal.post"), ("finance", "finance.invoice.view"),
    ("finance", "finance.invoice.create"), ("finance", "finance.payment.create"),
    ("finance", "finance.report.view"),
    ("projects", "projects.project.view"), ("projects", "projects.project.create"),
    ("projects", "projects.task.view"), ("projects", "projects.task.create"),
    ("support", "support.ticket.view"), ("support", "support.ticket.create"),
    ("support", "support.ticket.update"),
    ("reports", "reports.view"), ("reports", "reports.export"),
    ("workflow", "workflow.view"), ("workflow", "workflow.create"),
    ("workflow", "workflow.approve"),
    ("ai", "ai.conversation.view"), ("ai", "ai.conversation.create"),
    ("ai", "ai.tool.use"),
]


def seed_permissions(db: Session) -> dict[str, Permission]:
    out = {}
    for module, code in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, module=module, description=code)
            db.add(perm)
        out[code] = perm
    db.flush()
    return out


def create_admin_role(db: Session, company_id: UUID) -> Role:
    perms = seed_permissions(db)
    role = db.query(Role).filter(Role.company_id == company_id, Role.name == "Admin").first()
    if not role:
        role = Role(company_id=company_id, name="Admin",
                    description="Full access to this company", is_system=True)
        db.add(role)
        db.flush()
    for perm in perms.values():
        if not db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id).first():
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.flush()
    return role


def register_user(db: Session, email: str, password: str, full_name: str) -> User:
    if db.query(User).filter(User.email == email).first():
        raise ConflictError("A user with this email already exists")
    user = User(email=email, password_hash=get_password_hash(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _issue_tokens(db: Session, user: User, company_id: UUID | None) -> tuple[str, str]:
    access = create_access_token(user.id, company_id)
    raw = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)))
    db.flush()
    return access, raw


def login(db: Session, email: str, password: str):
    """Generic error — never reveal whether the email exists (docs/05)."""
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    if not user.is_active:
        raise UnauthorizedError("Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    membership = db.query(UserCompany).filter(UserCompany.user_id == user.id).first()
    company_id = membership.company_id if membership else None
    access, raw = _issue_tokens(db, user, company_id)
    log_audit(db, action="auth.login", entity_type="user", entity_id=user.id, user_id=user.id, company_id=company_id)
    db.commit()
    return {"access_token": access, "refresh_token": raw, "token_type": "bearer",
            "user_id": user.id, "company_id": company_id}


def refresh(db: Session, raw_token: str):
    token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_refresh_token(raw_token)).first()
    if token is None:
        raise UnauthorizedError("Invalid refresh token")
    now = datetime.now(timezone.utc)
    if token.revoked_at is not None:
        # Reuse of a revoked token: revoke the whole family (docs/05 §5.2).
        db.query(RefreshToken).filter(
            RefreshToken.user_id == token.user_id,
            RefreshToken.revoked_at.is_(None)).update({"revoked_at": now})
        db.commit()
        raise UnauthorizedError("Refresh token has been revoked")
    if to_aware(token.expires_at) < now:
        raise UnauthorizedError("Refresh token expired")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    # Rotate: revoke old, link to replacement.
    new_raw = new_refresh_token()
    replacement = RefreshToken(
        user_id=user.id, token_hash=hash_refresh_token(new_raw),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days))
    db.add(replacement)
    db.flush()
    token.revoked_at = now
    token.replaced_by_id = replacement.id
    membership = db.query(UserCompany).filter(UserCompany.user_id == user.id).first()
    company_id = membership.company_id if membership else None
    access = create_access_token(user.id, company_id)
    db.commit()
    return {"access_token": access, "refresh_token": new_raw, "token_type": "bearer",
            "user_id": user.id, "company_id": company_id}


def logout(db: Session, raw_token: str) -> None:
    token = db.query(RefreshToken).filter(
        RefreshToken.token_hash == hash_refresh_token(raw_token)).first()
    if token and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all_sessions(db: Session, user_id: UUID) -> None:
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": datetime.now(timezone.utc)})
    db.commit()


def create_company(db: Session, user: User, name: str, slug: str | None,
                   base_currency: str, timezone: str) -> Company:
    slug = slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if db.query(Company).filter(Company.slug == slug).first():
        raise ConflictError(f"Company slug '{slug}' already exists")
    company = Company(name=name, slug=slug, base_currency=base_currency.upper(), timezone=timezone)
    db.add(company)
    db.flush()
    db.add(UserCompany(user_id=user.id, company_id=company.id, is_default=True))
    role = create_admin_role(db, company.id)
    db.add(UserRole(user_id=user.id, role_id=role.id, company_id=company.id))
    log_audit(db, action="company.create", entity_type="company", entity_id=company.id,
              user_id=user.id, company_id=company.id)
    db.commit()
    db.refresh(company)
    return company


def switch_company(db: Session, user: User, company_id: UUID):
    membership = db.query(UserCompany).filter(
        UserCompany.user_id == user.id, UserCompany.company_id == company_id).first()
    if membership is None:
        raise NotFoundError("Company not found")
    return {"access_token": create_access_token(user.id, company_id),
            "refresh_token": "", "token_type": "bearer",
            "user_id": user.id, "company_id": company_id}
