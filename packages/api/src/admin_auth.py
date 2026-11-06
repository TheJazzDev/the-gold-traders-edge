"""
Admin key for every API write.

The Controls password only guards the web page, and the API is public, so the
key lives here too. The dashboard's server sends it; browsers never see it.
Fails closed: with no key configured, every write is refused.
"""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

ADMIN_KEY_ENV = "ADMIN_API_KEY"


def require_admin_key(x_admin_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get(ADMIN_KEY_ENV)
    if not expected:
        raise HTTPException(status_code=503, detail="Admin writes are not configured")
    if not x_admin_key or not hmac.compare_digest(x_admin_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid admin key")
