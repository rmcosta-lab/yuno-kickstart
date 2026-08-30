"""Public, provider-neutral Realtime credential response."""

from typing import Annotated

from pydantic import Field

from app.schemas.common import JS_SAFE_MAX, ResponseModel

RealtimeIdentifier = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$"),
]


class RealtimeClientSecretResponse(ResponseModel):
    client_secret: str = Field(min_length=1, max_length=4096, repr=False)
    expires_at: int = Field(strict=True, gt=0, le=JS_SAFE_MAX)
    session_id: RealtimeIdentifier
    model: RealtimeIdentifier
