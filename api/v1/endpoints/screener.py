# -*- coding: utf-8 -*-
"""Screener endpoints."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.screener import (
    IndicatorsResponse,
    IndicatorMeta,
    MatchedStock,
    ScreenerResultResponse,
    ScreenerResultsListResponse,
    ScreenerRunRequest,
    ScreenerRunResponse,
    ScreenerTemplateCreate,
    ScreenerTemplateResponse,
    ScreenerTemplateUpdate,
)
from api.v1.schemas.common import ErrorResponse
from src.services.screener_service import ScreenerService
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ── 执行选股 ──

@router.post(
    "/run",
    response_model=ScreenerRunResponse,
    responses={
        200: {"description": "选股执行完成"},
        400: {"description": "参数错误", "model": ErrorResponse},
        500: {"description": "服务器错误", "model": ErrorResponse},
    },
    summary="执行选股扫描",
    description="使用模板或内联规则执行全市场选股扫描",
)
def run_screener(
    request: ScreenerRunRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerRunResponse:
    if not request.template_id and not request.rules:
        raise HTTPException(
            status_code=400,
            detail={"error": "bad_request", "message": "必须提供 template_id 或 rules"},
        )

    try:
        service = ScreenerService(db_manager)
        rules_dict = request.rules.model_dump(exclude_none=True) if request.rules else None
        result = service.run_screen(
            rules_dict=rules_dict,
            template_id=request.template_id,
            stock_pool=request.stock_pool,
            notify=request.notify,
        )
        matched = [MatchedStock(**s) for s in result.get("matched_stocks", [])]
        return ScreenerRunResponse(
            run_id=result["run_id"],
            template_name=result.get("template_name"),
            total_scanned=result.get("total_scanned", 0),
            matched_count=result.get("matched_count", 0),
            matched_stocks=matched,
            duration_seconds=result.get("duration_seconds", 0),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "bad_request", "message": str(e)})
    except Exception as exc:
        logger.error(f"选股执行失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"选股执行失败: {str(exc)}"},
        )


# ── 结果查询 ──

@router.get(
    "/results",
    response_model=ScreenerResultsListResponse,
    summary="获取选股结果列表",
)
def get_screener_results(
    template_id: Optional[int] = Query(None, description="按模板ID筛选"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerResultsListResponse:
    try:
        service = ScreenerService(db_manager)
        data = service.get_results(template_id=template_id, page=page, limit=limit)
        items = []
        for item in data.get("items", []):
            matched = [MatchedStock(**s) for s in item.get("matched_stocks", [])]
            items.append(ScreenerResultResponse(
                id=item["id"],
                template_id=item.get("template_id"),
                template_name=item.get("template_name"),
                run_date=item.get("run_date", ""),
                total_scanned=item.get("total_scanned", 0),
                matched_count=item.get("matched_count", 0),
                matched_stocks=matched,
                duration_seconds=item.get("duration_seconds", 0),
                created_at=item.get("created_at"),
            ))
        return ScreenerResultsListResponse(
            total=data.get("total", 0),
            page=page,
            limit=limit,
            items=items,
        )
    except Exception as exc:
        logger.error(f"查询选股结果失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(exc)},
        )


@router.get(
    "/results/{result_id}",
    response_model=ScreenerResultResponse,
    summary="获取选股结果详情",
)
def get_screener_result_detail(
    result_id: int,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerResultResponse:
    service = ScreenerService(db_manager)
    detail = service.get_result_detail(result_id)
    if not detail:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "结果不存在"})
    matched = [MatchedStock(**s) for s in detail.get("matched_stocks", [])]
    return ScreenerResultResponse(
        id=detail["id"],
        template_id=detail.get("template_id"),
        template_name=detail.get("template_name"),
        run_date=detail.get("run_date", ""),
        total_scanned=detail.get("total_scanned", 0),
        matched_count=detail.get("matched_count", 0),
        matched_stocks=matched,
        duration_seconds=detail.get("duration_seconds", 0),
        created_at=detail.get("created_at"),
    )


# ── 模板管理 ──

@router.post(
    "/templates",
    response_model=ScreenerTemplateResponse,
    summary="创建选股模板",
)
def create_template(
    request: ScreenerTemplateCreate,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerTemplateResponse:
    try:
        service = ScreenerService(db_manager)
        result = service.create_template(
            name=request.name,
            description=request.description,
            rules=request.rules.model_dump(exclude_none=True),
            auto_run=request.auto_run,
        )
        return ScreenerTemplateResponse(**result)
    except Exception as exc:
        logger.error(f"创建模板失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(exc)},
        )


@router.get(
    "/templates",
    response_model=list[ScreenerTemplateResponse],
    summary="获取所有选股模板",
)
def list_templates(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> list[ScreenerTemplateResponse]:
    service = ScreenerService(db_manager)
    templates = service.list_templates()
    return [ScreenerTemplateResponse(**t) for t in templates]


@router.get(
    "/templates/{template_id}",
    response_model=ScreenerTemplateResponse,
    summary="获取选股模板详情",
)
def get_template(
    template_id: int,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerTemplateResponse:
    service = ScreenerService(db_manager)
    result = service.get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "模板不存在"})
    return ScreenerTemplateResponse(**result)


@router.put(
    "/templates/{template_id}",
    response_model=ScreenerTemplateResponse,
    summary="更新选股模板",
)
def update_template(
    template_id: int,
    request: ScreenerTemplateUpdate,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> ScreenerTemplateResponse:
    service = ScreenerService(db_manager)
    rules = request.rules.model_dump(exclude_none=True) if request.rules else None
    result = service.update_template(
        template_id=template_id,
        name=request.name,
        description=request.description,
        rules=rules,
        auto_run=request.auto_run,
    )
    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "模板不存在"})
    return ScreenerTemplateResponse(**result)


@router.delete(
    "/templates/{template_id}",
    summary="删除选股模板",
)
def delete_template(
    template_id: int,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> dict:
    service = ScreenerService(db_manager)
    if not service.delete_template(template_id):
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "模板不存在"})
    return {"success": True, "message": "模板已删除"}


# ── 指标元数据 ──

@router.get(
    "/indicators",
    response_model=IndicatorsResponse,
    summary="获取可用筛选指标列表",
    description="返回所有可用的选股指标及其支持的运算符，供前端动态渲染",
)
def get_indicators() -> IndicatorsResponse:
    from src.core.screener_engine import get_available_indicators
    raw = get_available_indicators()
    indicators = [IndicatorMeta(**ind) for ind in raw]
    return IndicatorsResponse(indicators=indicators)
