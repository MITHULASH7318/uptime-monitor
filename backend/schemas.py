from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator


class URLCreate(BaseModel):
    name: str
    url: str

    @field_validator("url")
    @classmethod
    def must_have_scheme(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class LatestCheck(BaseModel):
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    is_up: bool
    error_message: Optional[str] = None
    checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class URLOut(BaseModel):
    id: int
    name: str
    url: str
    created_at: datetime
    latest_check: Optional[LatestCheck] = None

    class Config:
        from_attributes = True


class CheckOut(BaseModel):
    status_code: Optional[int]
    response_time_ms: Optional[float]
    is_up: bool
    error_message: Optional[str]
    checked_at: datetime

    class Config:
        from_attributes = True
