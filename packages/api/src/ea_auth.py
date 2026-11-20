"""
Key for the MT5 Expert Advisor.

Separate from the admin key: this one sits in the EA's settings on the
trading terminal, and it should not be able to change the bot's settings.
Fails closed: with no key configured the EA endpoints refuse everything.
"""
import hmac
import os
from typing import Optional

from fastapi import Header, HTTPException

EA_KEY_ENV = "EA_API_KEY"


def require_ea_key(x_ea_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get(EA_KEY_ENV)
    if not expected:
        raise HTTPException(status_code=503, detail="EA access is not configured")
    if not x_ea_key or not hmac.compare_digest(x_ea_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid EA key")
