"""Core schemas (Pydantic v2)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: UUID
    company_id: UUID | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    is_active: bool
    model_config = {"from_attributes": True}


class CompanyCreate(BaseModel):
    name: str
    slug: str | None = None
    base_currency: str = "BDT"
    timezone: str = "Asia/Dhaka"


class CompanyOut(BaseModel):
    id: UUID
    name: str
    slug: str
    base_currency: str
    timezone: str
    model_config = {"from_attributes": True}


class BranchCreate(BaseModel):
    name: str
    code: str
    address: str | None = None
    is_head_office: bool = False


class DepartmentCreate(BaseModel):
    name: str
    code: str
    branch_id: UUID | None = None
    parent_department_id: UUID | None = None


class RoleCreate(BaseModel):
    name: str
    description: str | None = None
    permission_codes: list[str] = []


class AssignRoleRequest(BaseModel):
    user_id: UUID
    role_id: UUID


class SwitchCompanyRequest(BaseModel):
    company_id: UUID
