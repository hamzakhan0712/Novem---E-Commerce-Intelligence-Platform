from typing import Optional

from pydantic import BaseModel, Field


class ShopifyCredentials(BaseModel):
    shop_domain: str = Field(..., description="e.g. my-store.myshopify.com")
    api_key: str
    api_secret: str


class GoogleSheetsApiCredentials(BaseModel):
    api_key: str
    spreadsheet_id: str
    sheet_name: Optional[str] = None


class PostgresCredentials(BaseModel):
    host: str
    port: int = 5432
    database: str
    user: str
    password: str
    table: Optional[str] = None
    query: Optional[str] = None


class SaveCredentialRequest(BaseModel):
    store_id: str
    credential_type: str = Field(
        ...,
        description="One of: shopify_api, google_sheets_api, postgresql",
    )
    credentials: dict


class CredentialOut(BaseModel):
    id: str
    store_id: str
    credential_type: str
    created_at: str
    updated_at: Optional[str] = None


class TestCredentialResponse(BaseModel):
    success: bool
    message: str
