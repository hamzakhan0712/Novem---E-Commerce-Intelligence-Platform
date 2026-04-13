from typing import Optional

from pydantic import BaseModel


class SystemInfo(BaseModel):
    engine_version: str
    python_version: str
    duckdb_version: str
    stores_count: int
    memory_usage_mb: float
    uptime_seconds: float


class BackgroundTask(BaseModel):
    id: str
    store_id: str
    task_type: str
    status: str  # "pending" | "running" | "completed" | "failed"
    progress: int  # 0–100
    error: Optional[str] = None
    created_at: str
    updated_at: str
