"""Data models for orders."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OpenOrder(BaseModel):
    coin: str
    limit_px: str = Field(alias="limitPx")
    oid: int
    side: str
    sz: str
    timestamp: int


class FrontendOpenOrder(BaseModel):
    coin: str
    is_position_tpsl: bool = Field(alias="isPositionTpsl")
    is_trigger: bool = Field(alias="isTrigger")
    limit_px: str = Field(alias="limitPx")
    oid: int
    order_type: str = Field(alias="orderType")
    orig_sz: str = Field(alias="origSz")
    reduce_only: bool = Field(alias="reduceOnly")
    side: str
    sz: str
    timestamp: int
    trigger_condition: str = Field(alias="triggerCondition")
    trigger_px: str = Field(alias="triggerPx")
    cloid: str | None = None


class OrderStatusInfo(BaseModel):
    coin: str
    side: str
    limit_px: str = Field(alias="limitPx")
    sz: str
    oid: int
    timestamp: int
    order_type: str = Field(alias="orderType")
    orig_sz: str = Field(alias="origSz")
    tif: str | None = None
    cloid: str | None = None


class OrderStatusResponse(BaseModel):
    """Wrapper for the orderStatus info endpoint response."""
    status: str
    order: dict | None = None
