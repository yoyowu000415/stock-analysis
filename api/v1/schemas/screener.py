# -*- coding: utf-8 -*-
"""Screener API schemas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ScreenerCondition(BaseModel):
    """单个筛选条件或条件组。"""

    # 条件组字段（AND/OR 组）
    logic: Optional[str] = Field(None, description="逻辑运算: AND / OR", pattern="^(AND|OR)$")
    conditions: Optional[List["ScreenerCondition"]] = Field(None, description="子条件列表")

    # 叶节点条件字段
    type: Optional[str] = Field(None, description="条件类型: fundamental / technical / market")
    indicator: Optional[str] = Field(None, description="指标名称，如 pe_ratio, ma_cross, rsi")
    params: Optional[Dict[str, Any]] = Field(None, description="指标参数，如 {fast: 5, slow: 20}")
    operator: Optional[str] = Field(
        None,
        description="比较运算符: gt, gte, lt, lte, eq, between, cross_above, cross_below, in_list",
    )
    value: Optional[Any] = Field(None, description="阈值，between 时为 [min, max] 数组")


# 解决递归引用
ScreenerCondition.model_rebuild()


class ScreenerTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    rules: ScreenerCondition = Field(..., description="筛选规则")
    auto_run: bool = Field(False, description="是否每日自动运行")


class ScreenerTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    rules: Optional[ScreenerCondition] = None
    auto_run: Optional[bool] = None


class ScreenerTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rules: Dict[str, Any] = Field(default_factory=dict)
    is_builtin: bool = False
    auto_run: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ScreenerRunRequest(BaseModel):
    template_id: Optional[int] = Field(None, description="使用已保存的模板ID")
    rules: Optional[ScreenerCondition] = Field(None, description="内联规则（与template_id二选一）")
    stock_pool: Optional[List[str]] = Field(None, description="自定义股票池，为空则扫描全市场")
    notify: bool = Field(False, description="筛选完成后是否推送通知")


class MatchedStock(BaseModel):
    code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    price: Optional[float] = None
    change_pct: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    total_mv: Optional[float] = None
    volume_ratio: Optional[float] = None
    turnover_rate: Optional[float] = None
    matched_indicators: Dict[str, Any] = Field(default_factory=dict, description="命中的指标值")


class ScreenerRunResponse(BaseModel):
    run_id: int = Field(..., description="本次运行记录ID")
    template_name: Optional[str] = None
    total_scanned: int = 0
    matched_count: int = 0
    matched_stocks: List[MatchedStock] = Field(default_factory=list)
    duration_seconds: float = 0.0


class ScreenerResultResponse(BaseModel):
    id: int
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    run_date: str
    total_scanned: int = 0
    matched_count: int = 0
    matched_stocks: List[MatchedStock] = Field(default_factory=list)
    duration_seconds: float = 0.0
    created_at: Optional[str] = None


class ScreenerResultsListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: List[ScreenerResultResponse] = Field(default_factory=list)


class IndicatorMeta(BaseModel):
    name: str
    label: str
    type: str  # fundamental / technical / market
    operators: List[str]
    default_params: Optional[Dict[str, Any]] = None
    description: str = ""


class IndicatorsResponse(BaseModel):
    indicators: List[IndicatorMeta] = Field(default_factory=list)
