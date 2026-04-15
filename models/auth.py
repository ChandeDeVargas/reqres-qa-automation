"""
models/auth.py
──────────────
Pydantic v2 schemas for authentication endpoint responses.
"""

from pydantic import BaseModel

class LoginResponse(BaseModel):
    """Schema for POST /login (200) OK"""

    token: str

class RegisterResponse(BaseModel):
    """Schema for POST /register (200 OK)"""

    id: int
    token: str


class AuthErrorResponse(BaseModel):
    """Schema for 400 error responses on auth endpoints."""

    error: str