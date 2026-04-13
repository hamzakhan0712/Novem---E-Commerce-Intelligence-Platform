from typing import Optional

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    store_id: str = Field(..., min_length=1)
    data_type: str = Field(..., pattern=r"^(orders|customers|products|ad_spend|reviews)$")
    format: str = Field("csv", pattern=r"^(csv|xlsx)$")
    limit: Optional[int] = Field(None, ge=1, le=1_000_000)


class ExportResponse(BaseModel):
    filename: str
    row_count: int
    file_size: int


class ReportRequest(BaseModel):
    store_id: str = Field(..., min_length=1)
    period: str = Field("30d", pattern=r"^(7d|14d|30d|60d|90d|6m|12m)$")


class NarrativeReportRequest(BaseModel):
    store_id: str = Field(..., min_length=1)
    period: str = Field("30d", pattern=r"^(7d|14d|30d|60d|90d|6m|12m)$")
    mode: str = Field("technical", pattern=r"^(technical|ceo)$")
