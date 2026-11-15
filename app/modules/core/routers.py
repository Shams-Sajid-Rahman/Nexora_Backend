"""Core routers — thin HTTP layer; logic lives in services.py."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.crud import make_crud_router
from app.common.pagination import ok_list
from app.common.serializers import serialize, serialize_list
from app.core.deps import get_current_company, get_current_user, require_permission
from app.core.errors import NotFoundError
from app.db.session import get_db
from . import services
from .models import (AuditLog, Branch, Company, Department, Notification,
                     Role, User)
from .schemas import (AssignRoleRequest, BranchCreate, CompanyCreate,
                      DepartmentCreate, LoginRequest, RefreshRequest,
                      RoleCreate, SwitchCompanyRequest, UserCreate)

router = APIRouter(prefix="/api/v1", tags=["core"])

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.post("/register", status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = services.register_user(db, payload.email, payload.password, payload.full_name)
    return {"data": serialize(user), "meta": None}


@auth_router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return {"data": services.login(db, payload.email, payload.password), "meta": None}


@auth_router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return {"data": services.refresh(db, payload.refresh_token), "meta": None}


@auth_router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    services.logout(db, payload.refresh_token)
    return {"data": {"logged_out": True}, "meta": None}


@auth_router.get("/me")
def me(user=Depends(get_current_user)):
    return {"data": serialize(user), "meta": None}


@auth_router.post("/switch-company")
def switch_company(payload: SwitchCompanyRequest, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    return {"data": services.switch_company(db, user, payload.company_id), "meta": None}


@router.get("/companies", dependencies=[Depends(require_permission("core.company.view"))])
def list_companies(db: Session = Depends(get_db), user=Depends(get_current_user),
                   page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    from .models import UserCompany
    ids = [m.company_id for m in db.query(UserCompany).filter(UserCompany.user_id == user.id).all()]
    q = db.query(Company).filter(Company.id.in_(ids)) if ids else db.query(Company).filter(False)
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.post("/companies", status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db),
                   user=Depends(get_current_user)):
    company = services.create_company(db, user, payload.name, payload.slug,
                                      payload.base_currency, payload.timezone)
    return {"data": serialize(company), "meta": None}


@router.get("/companies/{company_id}", dependencies=[Depends(require_permission("core.company.view"))])
def get_company(company_id: UUID, db: Session = Depends(get_db),
                company=Depends(get_current_company)):
    if company.id != company_id:
        raise NotFoundError("Company not found")
    return {"data": serialize(company), "meta": None}


@router.get("/audit-logs", dependencies=[Depends(require_permission("core.audit.view"))])
def list_audit_logs(db: Session = Depends(get_db), company=Depends(get_current_company),
                    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    q = db.query(AuditLog).filter(AuditLog.company_id == company.id).order_by(AuditLog.created_at.desc())
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.get("/notifications")
def list_notifications(db: Session = Depends(get_db), user=Depends(get_current_user),
                       company=Depends(get_current_company),
                       page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    q = db.query(Notification).filter(Notification.company_id == company.id,
                                      Notification.user_id == user.id).order_by(Notification.created_at.desc())
    total = q.count()
    return ok_list(serialize_list(q.offset((page - 1) * page_size).limit(page_size).all()), total, page, page_size)


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: UUID, db: Session = Depends(get_db),
                           user=Depends(get_current_user), company=Depends(get_current_company)):
    note = db.get(Notification, notification_id)
    if note is None or note.company_id != company.id or note.user_id != user.id:
        raise NotFoundError("Notification not found")
    note.is_read = True
    db.commit()
    return {"data": serialize(note), "meta": None}


@router.post("/roles", status_code=201, dependencies=[Depends(require_permission("core.role.create"))])
def create_role(payload: RoleCreate, db: Session = Depends(get_db), company=Depends(get_current_company)):
    role = Role(company_id=company.id, name=payload.name, description=payload.description)
    db.add(role)
    db.flush()
    perms = services.seed_permissions(db)
    from .models import RolePermission
    for code in payload.permission_codes:
        if code in perms:
            db.add(RolePermission(role_id=role.id, permission_id=perms[code].id))
    db.commit()
    db.refresh(role)
    return {"data": serialize(role), "meta": None}


@router.post("/roles/assign", dependencies=[Depends(require_permission("core.role.create"))])
def assign_role(payload: AssignRoleRequest, db: Session = Depends(get_db), company=Depends(get_current_company)):
    from .models import UserRole
    if db.get(Role, payload.role_id) is None:
        raise NotFoundError("Role not found")
    if db.get(User, payload.user_id) is None:
        raise NotFoundError("User not found")
    existing = db.query(UserRole).filter(UserRole.user_id == payload.user_id,
                                         UserRole.role_id == payload.role_id,
                                         UserRole.company_id == company.id).first()
    if not existing:
        db.add(UserRole(user_id=payload.user_id, role_id=payload.role_id, company_id=company.id))
        db.commit()
    return {"data": {"assigned": True}, "meta": None}


# Generic CRUD for branches / departments (company-scoped, permissioned).
branch_router = make_crud_router(Branch, prefix="/api/v1/branches", permission="core.branch", name="Branch", code_prefix="BR")
department_router = make_crud_router(Department, prefix="/api/v1/departments", permission="core.branch", name="Department", code_prefix="DEPT")
user_router = make_crud_router(User, prefix="/api/v1/users", permission="core.user", name="User")

routers = [auth_router, router, branch_router, department_router, user_router]
