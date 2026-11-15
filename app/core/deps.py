"""Auth dependencies (docs/05 §5.3).

- get_current_user: Bearer JWT access token, user must exist and be active.
- get_current_company: active company from the X-Company-Id header, or
  the user's default membership. Validated against user_companies on
  every request; never trusted from a request body alone.
- require_permission(code): 403 when the user lacks the permission in
  the active company.
"""
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(db: Session = Depends(get_db),
                     token: str = Depends(oauth2_scheme)):
    from app.modules.core.models import User
    payload = decode_access_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    try:
        user_id = UUID(payload["sub"])
    except Exception as exc:
        raise UnauthorizedError("Invalid token subject") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive")
    return user


def get_current_company(db: Session = Depends(get_db),
                        user=Depends(get_current_user),
                        x_company_id: str | None = Header(default=None, alias="X-Company-Id")):
    from app.modules.core.models import Company, UserCompany
    memberships = db.query(UserCompany).filter(UserCompany.user_id == user.id).all()
    if not memberships:
        raise ForbiddenError("User belongs to no company")
    if x_company_id:
        try:
            wanted = UUID(x_company_id)
        except Exception as exc:
            raise NotFoundError("Company not found") from exc
        if not any(m.company_id == wanted for m in memberships):
            # 404, not 403, so another company's existence is not leaked.
            raise NotFoundError("Company not found")
        company_id = wanted
    else:
        default = next((m for m in memberships if m.is_default), memberships[0])
        company_id = default.company_id
    company = db.get(Company, company_id)
    if company is None:
        raise NotFoundError("Company not found")
    return company


def _user_has_permission(db: Session, user, company_id: UUID, code: str) -> bool:
    from app.modules.core.models import Permission, RolePermission, UserRole
    q = (db.query(Permission)
         .join(RolePermission, RolePermission.permission_id == Permission.id)
         .join(UserRole, UserRole.role_id == RolePermission.role_id)
         .filter(UserRole.user_id == user.id,
                 UserRole.company_id == company_id,
                 Permission.code == code))
    return db.query(q.exists()).scalar()


def require_permission(code: str):
    def _checker(db: Session = Depends(get_db),
                 user=Depends(get_current_user),
                 company=Depends(get_current_company)):
        if not _user_has_permission(db, user, company.id, code):
            raise ForbiddenError(f"Missing permission: {code}")
        return True
    return _checker


def company_context(db: Session = Depends(get_db),
                    user=Depends(get_current_user),
                    company=Depends(get_current_company)):
    """Convenience dependency returning (db, user, company)."""
    return db, user, company
