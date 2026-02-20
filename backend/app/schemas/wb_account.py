"""WB Account schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class WBAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["Основной кабинет"])
    api_key: str = Field(..., min_length=10, examples=["eyJhbGciOi..."])


class WBAccountUpdate(BaseModel):
    tax_rate: float | None = None
    tariff_rate: float | None = None


class WBAccountResponse(BaseModel):
    id: int
    name: str
    api_key_masked: str  # Only last 8 chars visible
    user_id: int
    is_active: bool
    permissions: list[str] | None = None
    tax_rate: float | None = None
    tariff_rate: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WBAccountList(BaseModel):
    items: list[WBAccountResponse]
    total: int


class WBKeyValidationResult(BaseModel):
    valid: bool
    permissions: list[str]
    error: str | None = None
