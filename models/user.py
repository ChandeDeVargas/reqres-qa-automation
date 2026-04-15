"""
models/user.py
──────────────
Pydantic v2 schemas that mirror the ReqRes API response contracts.

These models serve as living documentation: if the API changes its
response shape, schema validation in the tests will fail immediately,
pointing to the exact field that broke.
"""

from pydantic import BaseModel, HttpUrl, field_validator

class UserData(BaseModel):
    """Single user object as returned inside response bodies"""

    id: int
    email: str
    first_name: str
    last_name: str
    avatar: str # URL- kept as str for simplicity (HttpUrl adds trailing slash)

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("email must contain @")
        return v

class SupportInfo(BaseModel):
    """Support block present in most ReqRes list/single responses"""

    url: str
    text: str

class SingleUserResponse(BaseModel):
    """Schema for GET /users/{id}"""

    data: UserData
    support: SupportInfo

class UserListResponse(BaseModel):
    """Schema for GET /users?page={n}"""

    page: int
    per_page: int
    total: int
    total_pages: int
    data: list[UserData]
    support: SupportInfo

class CreateUserResponse(BaseModel):
    """Schema for POST /users (201 Created)"""

    name: str
    job: str
    id: str # ReqRes returns id as string on creation
    createdAt: str

class UpdateUserResponse(BaseModel):
    """Schema for PUT /users{id} and PATCH /users/{id} (200 OK)"""
    name: str
    job: str
    updatedAt: str