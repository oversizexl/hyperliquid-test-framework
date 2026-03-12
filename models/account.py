"""Data models for account / clearinghouse state."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MarginSummary(BaseModel):
    account_value: str = Field(alias="accountValue")
    total_ntl_pos: str = Field(alias="totalNtlPos")
    total_raw_usd: str = Field(alias="totalRawUsd")
    total_margin_used: str = Field(alias="totalMarginUsed")


class Leverage(BaseModel):
    type: str
    value: int
    raw_usd: str = Field(alias="rawUsd")


class PositionData(BaseModel):
    coin: str
    entry_px: str | None = Field(None, alias="entryPx")
    leverage: Leverage
    liquidation_px: str | None = Field(None, alias="liquidationPx")
    margin_used: str = Field(alias="marginUsed")
    max_leverage: int = Field(alias="maxLeverage")
    position_value: str = Field(alias="positionValue")
    return_on_equity: str = Field(alias="returnOnEquity")
    szi: str
    unrealized_pnl: str = Field(alias="unrealizedPnl")


class AssetPosition(BaseModel):
    position: PositionData
    type: str


class ClearinghouseState(BaseModel):
    margin_summary: MarginSummary = Field(alias="marginSummary")
    cross_margin_summary: MarginSummary = Field(alias="crossMarginSummary")
    cross_maintenance_margin_used: str = Field(alias="crossMaintenanceMarginUsed")
    withdrawable: str
    asset_positions: list[AssetPosition] = Field(alias="assetPositions")
    time: int
