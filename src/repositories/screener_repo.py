# -*- coding: utf-8 -*-
"""Screener repository.

Provides database access helpers for screener tables.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, select

from src.storage import DatabaseManager, ScreenerTemplate, ScreenerResult

logger = logging.getLogger(__name__)


class ScreenerRepository:
    """DB access layer for screener feature."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager.get_instance()

    # ── 模板 CRUD ──

    def create_template(
        self,
        name: str,
        rules_json: str,
        description: Optional[str] = None,
        is_builtin: bool = False,
        auto_run: bool = False,
    ) -> ScreenerTemplate:
        with self.db.session_scope() as session:
            template = ScreenerTemplate(
                name=name,
                description=description,
                rules_json=rules_json,
                is_builtin=is_builtin,
                auto_run=auto_run,
            )
            session.add(template)
            session.flush()
            # 读取 id 以便返回
            template_id = template.id
            template_name = template.name

        # 重新查询以获取完整对象
        return self.get_template(template_id)

    def get_template(self, template_id: int) -> Optional[ScreenerTemplate]:
        with self.db.get_session() as session:
            return session.execute(
                select(ScreenerTemplate).where(ScreenerTemplate.id == template_id)
            ).scalar_one_or_none()

    def get_template_by_name(self, name: str) -> Optional[ScreenerTemplate]:
        with self.db.get_session() as session:
            return session.execute(
                select(ScreenerTemplate).where(ScreenerTemplate.name == name)
            ).scalar_one_or_none()

    def list_templates(self) -> List[ScreenerTemplate]:
        with self.db.get_session() as session:
            rows = session.execute(
                select(ScreenerTemplate).order_by(desc(ScreenerTemplate.updated_at))
            ).scalars().all()
            return list(rows)

    def update_template(
        self,
        template_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rules_json: Optional[str] = None,
        auto_run: Optional[bool] = None,
    ) -> Optional[ScreenerTemplate]:
        with self.db.session_scope() as session:
            template = session.execute(
                select(ScreenerTemplate).where(ScreenerTemplate.id == template_id)
            ).scalar_one_or_none()
            if not template:
                return None
            if name is not None:
                template.name = name
            if description is not None:
                template.description = description
            if rules_json is not None:
                template.rules_json = rules_json
            if auto_run is not None:
                template.auto_run = auto_run
            template.updated_at = datetime.now()

        return self.get_template(template_id)

    def delete_template(self, template_id: int) -> bool:
        with self.db.session_scope() as session:
            template = session.execute(
                select(ScreenerTemplate).where(ScreenerTemplate.id == template_id)
            ).scalar_one_or_none()
            if not template:
                return False
            session.delete(template)
            return True

    # ── 结果 CRUD ──

    def save_result(
        self,
        template_id: Optional[int],
        template_name: Optional[str],
        run_date: date,
        total_scanned: int,
        matched_count: int,
        matched_stocks_json: str,
        rules_snapshot_json: str,
        duration_seconds: float,
    ) -> int:
        with self.db.session_scope() as session:
            result = ScreenerResult(
                template_id=template_id,
                template_name=template_name or "临时规则",
                run_date=run_date,
                total_scanned=total_scanned,
                matched_count=matched_count,
                matched_stocks_json=matched_stocks_json,
                rules_snapshot_json=rules_snapshot_json,
                duration_seconds=duration_seconds,
            )
            session.add(result)
            session.flush()
            return result.id

    def get_result(self, result_id: int) -> Optional[ScreenerResult]:
        with self.db.get_session() as session:
            return session.execute(
                select(ScreenerResult).where(ScreenerResult.id == result_id)
            ).scalar_one_or_none()

    def get_results_paginated(
        self,
        *,
        template_id: Optional[int] = None,
        run_date: Optional[date] = None,
        offset: int = 0,
        limit: int = 20,
    ) -> Tuple[List[ScreenerResult], int]:
        with self.db.get_session() as session:
            conditions = []
            if template_id is not None:
                conditions.append(ScreenerResult.template_id == template_id)
            if run_date is not None:
                conditions.append(ScreenerResult.run_date == run_date)

            where_clause = and_(*conditions) if conditions else True

            total = session.execute(
                select(func.count(ScreenerResult.id)).where(where_clause)
            ).scalar() or 0

            rows = session.execute(
                select(ScreenerResult)
                .where(where_clause)
                .order_by(desc(ScreenerResult.created_at))
                .offset(offset)
                .limit(limit)
            ).scalars().all()

            return list(rows), int(total)

    def get_auto_run_templates(self) -> List[ScreenerTemplate]:
        """获取所有标记为自动运行的模板。"""
        with self.db.get_session() as session:
            rows = session.execute(
                select(ScreenerTemplate).where(ScreenerTemplate.auto_run == True)
            ).scalars().all()
            return list(rows)
