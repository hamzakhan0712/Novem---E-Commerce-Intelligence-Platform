from typing import Optional

from pydantic import BaseModel, Field


class AlertOut(BaseModel):
    id: str
    store_id: Optional[str] = None
    module: str
    severity: str
    title: str
    message: str
    is_read: bool = False
    created_at: str


class CreateAlertRequest(BaseModel):
    store_id: Optional[str] = None
    module: str = Field(..., min_length=1)
    severity: str = Field(..., pattern=r"^(info|warning|error|critical)$")
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1)


class MarkReadRequest(BaseModel):
    alert_ids: list[str]
