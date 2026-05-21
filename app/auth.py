from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status


@dataclass
class AuthContext:
    raw_authorization: Optional[str]
    token: Optional[str]
    authenticated: bool


def extract_auth_context(request: Request) -> AuthContext:
    raw = request.headers.get("authorization")
    if not raw:
        return AuthContext(raw_authorization=None, token=None, authenticated=False)

    token = None
    parts = raw.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        token = parts[1].strip()

    return AuthContext(
        raw_authorization=raw,
        token=token,
        authenticated=bool(token),
    )


def require_authenticated_user(request: Request) -> AuthContext:
    context = extract_auth_context(request)
    if not context.authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return context

