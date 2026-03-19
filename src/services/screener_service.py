# -*- coding: utf-8 -*-
"""Screener orchestration service."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config import get_config
from src.core.screener_engine import ScreenerEngine
from src.repositories.screener_repo import ScreenerRepository
from src.storage import DatabaseManager

logger = logging.getLogger(__name__)

# 内置模板定义
BUILTIN_TEMPLATES = [
    {
        "name": "低估值蓝筹",
        "description": "PE < 15, PB < 2, 总市值 > 1000亿, 量比 > 0.8",
        "rules": {
            "logic": "AND",
            "conditions": [
                {"type": "fundamental", "indicator": "pe_ratio", "operator": "between", "value": [0, 15]},
                {"type": "fundamental", "indicator": "pb_ratio", "operator": "lt", "value": 2},
                {"type": "fundamental", "indicator": "total_mv", "operator": "gt", "value": 100_000_000_000},
                {"type": "market", "indicator": "volume_ratio", "operator": "gt", "value": 0.8},
            ],
        },
    },
    {
        "name": "均线多头放量",
        "description": "趋势为多头排列或强势多头, 5日量比 > 1.5",
        "rules": {
            "logic": "AND",
            "conditions": [
                {"type": "technical", "indicator": "trend_status", "operator": "in_list",
                 "value": ["强势多头", "多头排列"]},
                {"type": "technical", "indicator": "volume_ratio_5d", "operator": "gt", "value": 1.5},
            ],
        },
    },
    {
        "name": "超卖反弹",
        "description": "RSI(6) < 30, MACD 金叉或即将金叉",
        "rules": {
            "logic": "AND",
            "conditions": [
                {"type": "technical", "indicator": "rsi_6", "operator": "lt", "value": 30},
                {"type": "technical", "indicator": "macd_status", "operator": "in_list",
                 "value": ["金叉", "零轴上金叉"]},
            ],
        },
    },
    {
        "name": "高成长小盘",
        "description": "营收同比 > 30%, 总市值 < 200亿, PE < 50",
        "rules": {
            "logic": "AND",
            "conditions": [
                {"type": "fundamental", "indicator": "revenue_yoy", "operator": "gt", "value": 30},
                {"type": "fundamental", "indicator": "total_mv", "operator": "lt", "value": 20_000_000_000},
                {"type": "fundamental", "indicator": "pe_ratio", "operator": "between", "value": [0, 50]},
            ],
        },
    },
]


class ScreenerService:
    """Service layer for stock screening."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()
        self.repo = ScreenerRepository(self.db)

    def ensure_builtin_templates(self) -> int:
        """确保内置模板存在，返回新创建的数量。"""
        created = 0
        for tmpl in BUILTIN_TEMPLATES:
            existing = self.repo.get_template_by_name(tmpl["name"])
            if not existing:
                self.repo.create_template(
                    name=tmpl["name"],
                    description=tmpl.get("description"),
                    rules_json=json.dumps(tmpl["rules"], ensure_ascii=False),
                    is_builtin=True,
                    auto_run=False,
                )
                created += 1
                logger.info(f"[选股服务] 创建内置模板: {tmpl['name']}")
        return created

    def run_screen(
        self,
        *,
        rules_dict: Optional[Dict[str, Any]] = None,
        template_id: Optional[int] = None,
        stock_pool: Optional[List[str]] = None,
        notify: bool = False,
    ) -> Dict[str, Any]:
        """
        执行选股扫描。

        Args:
            rules_dict: 内联规则
            template_id: 模板 ID（与 rules_dict 二选一）
            stock_pool: 自定义股票池
            notify: 是否推送通知

        Returns:
            包含 run_id, matched_stocks, total_scanned, duration_seconds 的 dict
        """
        template_name = None

        if template_id:
            template = self.repo.get_template(template_id)
            if not template:
                raise ValueError(f"模板不存在: {template_id}")
            rules_dict = json.loads(template.rules_json)
            template_name = template.name
        elif rules_dict is None:
            raise ValueError("必须提供 rules_dict 或 template_id")

        # 执行引擎
        engine = ScreenerEngine()
        scan_result = engine.scan(rules=rules_dict, stock_pool=stock_pool)

        matched_stocks = scan_result.get("matched_stocks", [])
        total_scanned = scan_result.get("total_scanned", 0)
        duration = scan_result.get("duration_seconds", 0)

        # 保存结果
        run_id = self.repo.save_result(
            template_id=template_id,
            template_name=template_name,
            run_date=date.today(),
            total_scanned=total_scanned,
            matched_count=len(matched_stocks),
            matched_stocks_json=json.dumps(matched_stocks, ensure_ascii=False, default=str),
            rules_snapshot_json=json.dumps(rules_dict, ensure_ascii=False),
            duration_seconds=duration,
        )

        # 推送通知
        if notify and matched_stocks:
            self._send_notification(template_name, matched_stocks)

        return {
            "run_id": run_id,
            "template_name": template_name,
            "total_scanned": total_scanned,
            "matched_count": len(matched_stocks),
            "matched_stocks": matched_stocks,
            "duration_seconds": duration,
        }

    # ── 模板管理 ──

    def create_template(
        self,
        name: str,
        rules: Dict[str, Any],
        description: Optional[str] = None,
        auto_run: bool = False,
    ) -> Dict[str, Any]:
        template = self.repo.create_template(
            name=name,
            description=description,
            rules_json=json.dumps(rules, ensure_ascii=False),
            auto_run=auto_run,
        )
        return self._template_to_dict(template)

    def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
        auto_run: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        template = self.repo.update_template(
            template_id=template_id,
            name=name,
            description=description,
            rules_json=json.dumps(rules, ensure_ascii=False) if rules else None,
            auto_run=auto_run,
        )
        if template is None:
            return None
        return self._template_to_dict(template)

    def delete_template(self, template_id: int) -> bool:
        return self.repo.delete_template(template_id)

    def list_templates(self) -> List[Dict[str, Any]]:
        templates = self.repo.list_templates()
        return [self._template_to_dict(t) for t in templates]

    def get_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        template = self.repo.get_template(template_id)
        if not template:
            return None
        return self._template_to_dict(template)

    # ── 结果查询 ──

    def get_results(
        self,
        *,
        template_id: Optional[int] = None,
        run_date: Optional[date] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        offset = max(page - 1, 0) * limit
        rows, total = self.repo.get_results_paginated(
            template_id=template_id,
            run_date=run_date,
            offset=offset,
            limit=limit,
        )
        items = [self._result_to_dict(r) for r in rows]
        return {"total": total, "page": page, "limit": limit, "items": items}

    def get_result_detail(self, result_id: int) -> Optional[Dict[str, Any]]:
        result = self.repo.get_result(result_id)
        if not result:
            return None
        return self._result_to_dict(result)

    # ── 通知 ──

    def _send_notification(self, template_name: Optional[str], matched_stocks: List[Dict[str, Any]]) -> None:
        try:
            from src.notification import NotificationService

            title = f"📊 选股结果: {template_name or '自定义规则'}"
            lines = [f"**{title}**", f"共命中 {len(matched_stocks)} 只股票", ""]
            lines.append("| 代码 | 名称 | 最新价 | 涨跌幅 | PE | PB |")
            lines.append("|------|------|--------|--------|-----|-----|")

            for stock in matched_stocks[:30]:  # 最多展示 30 只
                code = stock.get("code", "")
                name = stock.get("name", "")
                price = stock.get("price", "-")
                change = stock.get("change_pct", "-")
                pe = stock.get("pe_ratio", "-")
                pb = stock.get("pb_ratio", "-")

                if isinstance(change, (int, float)):
                    change = f"{change:+.2f}%"
                if isinstance(pe, (int, float)):
                    pe = f"{pe:.1f}"
                if isinstance(pb, (int, float)):
                    pb = f"{pb:.2f}"

                lines.append(f"| {code} | {name} | {price} | {change} | {pe} | {pb} |")

            if len(matched_stocks) > 30:
                lines.append(f"\n... 还有 {len(matched_stocks) - 30} 只未显示")

            content = "\n".join(lines)
            notifier = NotificationService()
            notifier.send(content)
            logger.info(f"[选股服务] 通知已发送: {len(matched_stocks)} 只股票")
        except Exception as e:
            logger.error(f"[选股服务] 发送通知失败: {e}")

    # ── 转换 ──

    @staticmethod
    def _template_to_dict(template) -> Dict[str, Any]:
        rules = {}
        try:
            rules = json.loads(template.rules_json) if template.rules_json else {}
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "rules": rules,
            "is_builtin": template.is_builtin,
            "auto_run": template.auto_run,
            "created_at": template.created_at.isoformat() if template.created_at else None,
            "updated_at": template.updated_at.isoformat() if template.updated_at else None,
        }

    @staticmethod
    def _result_to_dict(result) -> Dict[str, Any]:
        matched_stocks = []
        try:
            matched_stocks = json.loads(result.matched_stocks_json) if result.matched_stocks_json else []
        except (json.JSONDecodeError, TypeError):
            pass

        return {
            "id": result.id,
            "template_id": result.template_id,
            "template_name": result.template_name,
            "run_date": result.run_date.isoformat() if result.run_date else None,
            "total_scanned": result.total_scanned,
            "matched_count": result.matched_count,
            "matched_stocks": matched_stocks,
            "duration_seconds": result.duration_seconds,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }
