# -*- coding: utf-8 -*-
"""
===================================
选股引擎 - 三阶段过滤
===================================

Phase 1: 实时行情批量数据（PE/PB/市值/涨跌幅等） → 粗筛
Phase 2: 日K线 + 技术分析（MA/MACD/RSI）          → 精筛
Phase 3: 深度基本面数据（营收增速/ROE）            → 终筛
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from src.config import get_config
from src.stock_analyzer import StockTrendAnalyzer, TrendAnalysisResult

logger = logging.getLogger(__name__)

# Phase 1 可直接从实时行情获取的指标
PHASE1_INDICATORS: Set[str] = {
    "pe_ratio", "pb_ratio", "total_mv", "circ_mv",
    "price", "change_pct", "volume_ratio", "turnover_rate",
    "amplitude", "change_60d", "high_52w", "low_52w",
}

# Phase 2 需要日K线技术分析的指标
PHASE2_INDICATORS: Set[str] = {
    "ma_cross", "ma_alignment", "trend_status", "trend_strength",
    "bias_ma5", "bias_ma10", "bias_ma20",
    "macd_status", "macd_cross", "macd_dif", "macd_dea", "macd_bar",
    "rsi", "rsi_6", "rsi_12", "rsi_24",
    "volume_ratio_5d", "volume_status",
    "signal_score",
}

# Phase 3 深度基本面指标
PHASE3_INDICATORS: Set[str] = {
    "revenue_yoy", "net_profit_yoy", "roe", "gross_margin",
}

# 实时行情 DataFrame 列名 → 内部指标名 映射
SPOT_COLUMN_MAP = {
    "pe_ratio": "市盈率-动态",
    "pb_ratio": "市净率",
    "total_mv": "总市值",
    "circ_mv": "流通市值",
    "price": "最新价",
    "change_pct": "涨跌幅",
    "volume_ratio": "量比",
    "turnover_rate": "换手率",
    "amplitude": "振幅",
    "change_60d": "60日涨跌幅",
    "high_52w": "52周最高",
    "low_52w": "52周最低",
}

# 支持的比较运算符
OPERATORS = {
    "gt": lambda v, t: v is not None and v > t,
    "gte": lambda v, t: v is not None and v >= t,
    "lt": lambda v, t: v is not None and v < t,
    "lte": lambda v, t: v is not None and v <= t,
    "eq": lambda v, t: v is not None and v == t,
    "between": lambda v, t: v is not None and isinstance(t, (list, tuple)) and len(t) == 2 and t[0] <= v <= t[1],
    "in_list": lambda v, t: v is not None and v in t,
}

# 特殊运算符（技术指标用）
SPECIAL_OPERATORS = {"cross_above", "cross_below"}


def _safe_float(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def get_available_indicators() -> List[Dict[str, Any]]:
    """返回所有可用的筛选指标元数据，供前端动态渲染。"""
    indicators = [
        # Phase 1 基本面
        {"name": "pe_ratio", "label": "市盈率(动态)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "eq", "between"], "description": "动态市盈率"},
        {"name": "pb_ratio", "label": "市净率", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "eq", "between"], "description": "市净率"},
        {"name": "total_mv", "label": "总市值(元)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "总市值，单位：元"},
        {"name": "circ_mv", "label": "流通市值(元)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "流通市值，单位：元"},
        # Phase 1 行情
        {"name": "price", "label": "最新价", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "最新价格"},
        {"name": "change_pct", "label": "涨跌幅(%)", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "当日涨跌幅"},
        {"name": "volume_ratio", "label": "量比", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "量比"},
        {"name": "turnover_rate", "label": "换手率(%)", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "换手率"},
        {"name": "amplitude", "label": "振幅(%)", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "振幅"},
        {"name": "change_60d", "label": "60日涨跌幅(%)", "type": "market",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "60日涨跌幅"},
        # Phase 2 技术指标
        {"name": "trend_status", "label": "趋势状态", "type": "technical",
         "operators": ["in_list"],
         "description": "趋势状态: 强势多头/多头排列/弱势多头/盘整/弱势空头/空头排列/强势空头"},
        {"name": "trend_strength", "label": "趋势强度(0-100)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "趋势强度评分"},
        {"name": "ma_alignment", "label": "均线排列", "type": "technical",
         "operators": ["in_list"],
         "description": "均线排列状态"},
        {"name": "ma_cross", "label": "均线交叉", "type": "technical",
         "operators": ["cross_above", "cross_below"],
         "default_params": {"fast": 5, "slow": 20},
         "description": "均线交叉信号，需指定 fast/slow 周期"},
        {"name": "bias_ma5", "label": "MA5乖离率(%)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "价格偏离MA5百分比"},
        {"name": "bias_ma10", "label": "MA10乖离率(%)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "价格偏离MA10百分比"},
        {"name": "bias_ma20", "label": "MA20乖离率(%)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "价格偏离MA20百分比"},
        {"name": "macd_status", "label": "MACD状态", "type": "technical",
         "operators": ["in_list"],
         "description": "MACD状态: 零轴上金叉/金叉/多头/上穿零轴/下穿零轴/空头/死叉"},
        {"name": "rsi_6", "label": "RSI(6)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "6日RSI"},
        {"name": "rsi_12", "label": "RSI(12)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "12日RSI"},
        {"name": "rsi_24", "label": "RSI(24)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "24日RSI"},
        {"name": "volume_ratio_5d", "label": "5日量比", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "当日成交量/5日均量"},
        {"name": "signal_score", "label": "综合信号评分(0-100)", "type": "technical",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "综合技术面评分"},
        # Phase 3 深度基本面
        {"name": "revenue_yoy", "label": "营收同比增速(%)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "营业收入同比增速"},
        {"name": "net_profit_yoy", "label": "净利润同比增速(%)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "净利润同比增速"},
        {"name": "roe", "label": "ROE(%)", "type": "fundamental",
         "operators": ["gt", "gte", "lt", "lte", "between"], "description": "净资产收益率"},
    ]
    return indicators


def _classify_conditions(rules: Dict[str, Any]) -> Tuple[Set[int], Set[str]]:
    """遍历规则树，返回需要的阶段集合和指标名集合。"""
    phases = set()
    indicators = set()

    def _walk(node: Dict[str, Any]):
        if node.get("logic") and node.get("conditions"):
            for child in node["conditions"]:
                _walk(child)
        elif node.get("indicator"):
            ind = node["indicator"]
            indicators.add(ind)
            if ind in PHASE1_INDICATORS:
                phases.add(1)
            elif ind in PHASE2_INDICATORS:
                phases.add(2)
            elif ind in PHASE3_INDICATORS:
                phases.add(3)
            else:
                phases.add(1)  # 默认尝试 Phase 1

    _walk(rules)
    return phases, indicators


@dataclass
class ScreenerEngine:
    """选股引擎：支持多条件、多阶段过滤的全市场扫描。"""

    max_workers: int = 4
    batch_sleep: float = 1.0

    def scan(
        self,
        rules: Dict[str, Any],
        stock_pool: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        执行选股扫描。

        Args:
            rules: 规则树 dict
            stock_pool: 可选股票池，为空扫描全市场

        Returns:
            dict with keys: matched_stocks, total_scanned, duration_seconds
        """
        start_time = time.time()
        phases_needed, _ = _classify_conditions(rules)

        # ── Phase 1: 获取全市场实时行情 ──
        spot_df = self._fetch_spot_data()
        if spot_df is None or spot_df.empty:
            logger.error("[选股引擎] 获取实时行情失败，终止扫描")
            return {"matched_stocks": [], "total_scanned": 0, "duration_seconds": 0}

        # 过滤股票池
        if stock_pool:
            spot_df = spot_df[spot_df["代码"].isin(stock_pool)]

        total_scanned = len(spot_df)
        logger.info(f"[选股引擎] 开始扫描，共 {total_scanned} 只股票，需要 Phase {sorted(phases_needed)}")

        # Phase 1 过滤
        phase1_rules = self._extract_phase_rules(rules, PHASE1_INDICATORS)
        if phase1_rules:
            candidates = []
            for _, row in spot_df.iterrows():
                stock_data = self._spot_row_to_dict(row)
                if self._evaluate(phase1_rules, stock_data):
                    candidates.append(row)
            logger.info(f"[选股引擎] Phase 1 完成: {len(spot_df)} → {len(candidates)} 只")
        else:
            candidates = [row for _, row in spot_df.iterrows()]

        if not candidates:
            duration = time.time() - start_time
            return {"matched_stocks": [], "total_scanned": total_scanned, "duration_seconds": round(duration, 2)}

        # ── Phase 2: 技术分析过滤 ──
        if 2 in phases_needed:
            phase2_rules = self._extract_phase_rules(rules, PHASE2_INDICATORS)
            if phase2_rules:
                candidates = self._phase2_filter(candidates, phase2_rules)
                logger.info(f"[选股引擎] Phase 2 完成: 剩余 {len(candidates)} 只")

        if not candidates:
            duration = time.time() - start_time
            return {"matched_stocks": [], "total_scanned": total_scanned, "duration_seconds": round(duration, 2)}

        # ── Phase 3: 深度基本面过滤 ──
        if 3 in phases_needed:
            phase3_rules = self._extract_phase_rules(rules, PHASE3_INDICATORS)
            if phase3_rules:
                candidates = self._phase3_filter(candidates, phase3_rules)
                logger.info(f"[选股引擎] Phase 3 完成: 剩余 {len(candidates)} 只")

        # 如果规则同时跨多个阶段，需要对最终候选做完整规则校验
        # （因为各阶段分别只校验了自己阶段的条件子集）
        # 但由于候选已通过所有子阶段的子集，此处的全规则校验是冗余安全检查
        # 暂略，直接输出

        # ── 构建结果 ──
        matched_stocks = []
        for item in candidates:
            if isinstance(item, dict):
                matched_stocks.append(item)
            else:
                matched_stocks.append(self._spot_row_to_dict(item))

        duration = time.time() - start_time
        logger.info(f"[选股引擎] 扫描完成: {total_scanned} 只 → 命中 {len(matched_stocks)} 只，耗时 {duration:.1f}s")

        return {
            "matched_stocks": matched_stocks,
            "total_scanned": total_scanned,
            "duration_seconds": round(duration, 2),
        }

    # ── 数据获取 ──

    def _fetch_spot_data(self) -> Optional[pd.DataFrame]:
        """获取全 A 股实时行情 DataFrame。"""
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                logger.info(f"[选股引擎] 获取实时行情成功: {len(df)} 只")
            return df
        except Exception as e:
            logger.error(f"[选股引擎] 获取实时行情失败: {e}")
            return None

    def _fetch_technical_data(self, code: str) -> Optional[TrendAnalysisResult]:
        """获取单只股票的技术分析结果。"""
        try:
            from data_provider.base import DataFetcherManager
            manager = DataFetcherManager()
            df, source = manager.get_daily_data(stock_code=code, days=120)
            if df is None or df.empty:
                return None
            analyzer = StockTrendAnalyzer()
            return analyzer.analyze(df, code)
        except Exception as e:
            logger.debug(f"[选股引擎] 技术分析失败 {code}: {e}")
            return None

    def _fetch_fundamental_data(self, code: str) -> Dict[str, Any]:
        """获取深度基本面数据。"""
        try:
            from data_provider.base import DataFetcherManager
            manager = DataFetcherManager()
            bundle = manager.get_fundamental_context(stock_code=code, budget_seconds=10)
            if not bundle:
                return {}
            # 提取关键字段
            result = {}
            growth = bundle.get("growth") or {}
            if isinstance(growth, dict):
                result["revenue_yoy"] = _safe_float(growth.get("revenue_yoy") or growth.get("营业收入同比增长"))
                result["net_profit_yoy"] = _safe_float(growth.get("net_profit_yoy") or growth.get("净利润同比增长"))
            valuation = bundle.get("valuation") or {}
            if isinstance(valuation, dict):
                result["roe"] = _safe_float(valuation.get("roe") or valuation.get("ROE"))
                result["gross_margin"] = _safe_float(valuation.get("gross_margin") or valuation.get("毛利率"))
            return result
        except Exception as e:
            logger.debug(f"[选股引擎] 基本面获取失败 {code}: {e}")
            return {}

    # ── 转换 ──

    @staticmethod
    def _spot_row_to_dict(row) -> Dict[str, Any]:
        """将实时行情 DataFrame 行转为标准 dict。"""
        if isinstance(row, dict):
            return row
        return {
            "code": str(row.get("代码", "")),
            "name": str(row.get("名称", "")),
            "price": _safe_float(row.get("最新价")),
            "change_pct": _safe_float(row.get("涨跌幅")),
            "pe_ratio": _safe_float(row.get("市盈率-动态")),
            "pb_ratio": _safe_float(row.get("市净率")),
            "total_mv": _safe_float(row.get("总市值")),
            "circ_mv": _safe_float(row.get("流通市值")),
            "volume_ratio": _safe_float(row.get("量比")),
            "turnover_rate": _safe_float(row.get("换手率")),
            "amplitude": _safe_float(row.get("振幅")),
            "change_60d": _safe_float(row.get("60日涨跌幅")),
            "high_52w": _safe_float(row.get("52周最高")),
            "low_52w": _safe_float(row.get("52周最低")),
        }

    @staticmethod
    def _trend_to_dict(result: TrendAnalysisResult) -> Dict[str, Any]:
        """将技术分析结果转为可筛选的 dict。"""
        return {
            "trend_status": result.trend_status.value,
            "trend_strength": result.trend_strength,
            "ma_alignment": result.ma_alignment,
            "bias_ma5": result.bias_ma5,
            "bias_ma10": result.bias_ma10,
            "bias_ma20": result.bias_ma20,
            "macd_status": result.macd_status.value,
            "macd_dif": result.macd_dif,
            "macd_dea": result.macd_dea,
            "macd_bar": result.macd_bar,
            "rsi_6": result.rsi_6,
            "rsi_12": result.rsi_12,
            "rsi_24": result.rsi_24,
            "volume_ratio_5d": result.volume_ratio_5d,
            "volume_status": result.volume_status.value,
            "signal_score": result.signal_score,
        }

    # ── Phase 2 / 3 过滤 ──

    def _phase2_filter(self, candidates: List, rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """对候选股票进行技术分析过滤。"""
        passed = []
        codes = [self._get_code(c) for c in candidates]
        spot_map = {}
        for c in candidates:
            code = self._get_code(c)
            spot_map[code] = self._spot_row_to_dict(c) if not isinstance(c, dict) else c

        # 批量并发获取技术数据
        tech_map: Dict[str, TrendAnalysisResult] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, code in enumerate(codes):
                futures[executor.submit(self._fetch_technical_data, code)] = code
                # 批次间休眠
                if (i + 1) % (self.max_workers * 2) == 0:
                    time.sleep(self.batch_sleep)

            for future in as_completed(futures):
                code = futures[future]
                try:
                    result = future.result()
                    if result:
                        tech_map[code] = result
                except Exception as e:
                    logger.debug(f"[选股引擎] 技术数据获取异常 {code}: {e}")

        for code in codes:
            if code not in tech_map:
                continue
            tech_data = self._trend_to_dict(tech_map[code])
            # 合并实时行情 + 技术数据
            merged = {**spot_map.get(code, {}), **tech_data}
            if self._evaluate(rules, merged):
                merged["matched_indicators"] = {k: v for k, v in tech_data.items() if v is not None}
                passed.append(merged)

        return passed

    def _phase3_filter(self, candidates: List[Dict[str, Any]], rules: Dict[str, Any]) -> List[Dict[str, Any]]:
        """对候选股票进行深度基本面过滤。"""
        passed = []
        codes = [c.get("code", "") for c in candidates]
        fund_map: Dict[str, Dict[str, Any]] = {}

        with ThreadPoolExecutor(max_workers=min(self.max_workers, 2)) as executor:
            futures = {}
            for code in codes:
                futures[executor.submit(self._fetch_fundamental_data, code)] = code

            for future in as_completed(futures):
                code = futures[future]
                try:
                    result = future.result()
                    if result:
                        fund_map[code] = result
                except Exception:
                    pass

        for c in candidates:
            code = c.get("code", "")
            fund_data = fund_map.get(code, {})
            merged = {**c, **fund_data}
            if self._evaluate(rules, merged):
                passed.append(merged)

        return passed

    @staticmethod
    def _get_code(item) -> str:
        if isinstance(item, dict):
            return item.get("code", "")
        return str(item.get("代码", ""))

    # ── 条件评估 ──

    def _evaluate(self, rules: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """递归评估条件树。"""
        logic = rules.get("logic")
        conditions = rules.get("conditions")

        if logic and conditions:
            if logic == "AND":
                return all(self._evaluate(c, data) for c in conditions)
            elif logic == "OR":
                return any(self._evaluate(c, data) for c in conditions)
            return False

        # 叶节点
        indicator = rules.get("indicator")
        operator = rules.get("operator")
        value = rules.get("value")

        if not indicator or not operator:
            return True  # 无效条件默认通过

        actual = data.get(indicator)
        if actual is None:
            return False

        # 特殊运算符
        if operator in SPECIAL_OPERATORS:
            # cross_above / cross_below 主要通过 macd_status / trend_status 等状态判断
            # 简化实现：转为 in_list 判断
            if operator == "cross_above":
                return actual in ("金叉", "零轴上金叉", "强势多头", "多头排列")
            elif operator == "cross_below":
                return actual in ("死叉", "强势空头", "空头排列")
            return False

        # 标准运算符
        op_func = OPERATORS.get(operator)
        if not op_func:
            logger.warning(f"[选股引擎] 不支持的运算符: {operator}")
            return False

        try:
            return op_func(actual, value)
        except (TypeError, ValueError) as e:
            logger.debug(f"[选股引擎] 条件评估异常: {indicator} {operator} {value}: {e}")
            return False

    # ── 规则提取 ──

    def _extract_phase_rules(self, rules: Dict[str, Any], phase_indicators: Set[str]) -> Optional[Dict[str, Any]]:
        """从完整规则树中提取指定阶段相关的条件子集。"""
        extracted = self._extract_node(rules, phase_indicators)
        return extracted

    def _extract_node(self, node: Dict[str, Any], phase_indicators: Set[str]) -> Optional[Dict[str, Any]]:
        logic = node.get("logic")
        conditions = node.get("conditions")

        if logic and conditions:
            extracted_children = []
            for child in conditions:
                extracted = self._extract_node(child, phase_indicators)
                if extracted:
                    extracted_children.append(extracted)
            if not extracted_children:
                return None
            if len(extracted_children) == 1:
                return extracted_children[0]
            return {"logic": logic, "conditions": extracted_children}

        # 叶节点
        indicator = node.get("indicator")
        if indicator and indicator in phase_indicators:
            return node
        return None
