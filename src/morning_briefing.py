# -*- coding: utf-8 -*-
"""
===================================
早盘情报模块
===================================

职责：
1. 获取隔夜美股数据（三大指数、VIX）
2. 聚合财经新闻（财联社快讯、东方财富新闻）
3. 调用 AI 生成早盘预判报告
4. 推送到飞书等通知渠道

数据源：
- akshare: 美股指数（新浪）、财联社快讯、东方财富新闻
- DeepSeek/其他 LLM: 新闻分析与大盘预判
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def _fetch_us_indices() -> List[Dict[str, Any]]:
    """获取隔夜美股三大指数 + VIX 数据"""
    import akshare as ak

    indices = [
        (".INX", "标普500"),
        (".IXIC", "纳斯达克"),
        (".DJI", "道琼斯"),
    ]

    results = []
    for symbol, name in indices:
        try:
            df = ak.index_us_stock_sina(symbol=symbol)
            if df is None or df.empty:
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else None

            close = float(latest["close"])
            prev_close = float(prev["close"]) if prev is not None else close
            change_pct = (close - prev_close) / prev_close * 100 if prev_close else 0

            results.append({
                "name": name,
                "close": close,
                "prev_close": prev_close,
                "change_pct": round(change_pct, 2),
                "date": str(latest["date"]),
            })
        except Exception as e:
            logger.warning(f"获取美股指数 {name}({symbol}) 失败: {e}")

    return results


def _fetch_cls_news(limit: int = 30) -> List[Dict[str, str]]:
    """获取财联社快讯"""
    import akshare as ak

    news_list = []
    try:
        df = ak.stock_info_global_cls()
        if df is None or df.empty:
            return news_list

        cols = df.columns.tolist()
        # 列名可能是中文编码问题，按位置取
        for _, row in df.head(limit).iterrows():
            values = row.tolist()
            title = str(values[0]) if len(values) > 0 else ""
            content = str(values[1]) if len(values) > 1 else ""
            time_str = str(values[-1]) if len(values) > 1 else ""

            # 优先用标题，标题为空用内容截断
            headline = title.strip() if title.strip() else content[:100].strip()
            if headline:
                news_list.append({
                    "headline": headline,
                    "content": content[:500] if content else "",
                    "time": time_str,
                })
    except Exception as e:
        logger.warning(f"获取财联社快讯失败: {e}")

    return news_list


def _fetch_eastmoney_news(limit: int = 20) -> List[Dict[str, str]]:
    """获取东方财富财经新闻"""
    import akshare as ak

    news_list = []
    try:
        # 搜索大盘相关新闻
        df = ak.stock_news_em(symbol="000001")
        if df is None or df.empty:
            return news_list

        cols = df.columns.tolist()
        for _, row in df.head(limit).iterrows():
            values = row.tolist()
            # 东方财富新闻通常有: 关键词, 新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接
            title = str(values[1]) if len(values) > 1 else str(values[0])
            content = str(values[2]) if len(values) > 2 else ""
            time_str = str(values[3]) if len(values) > 3 else ""

            if title.strip():
                news_list.append({
                    "headline": title.strip(),
                    "content": content[:300] if content else "",
                    "time": time_str,
                })
    except Exception as e:
        logger.warning(f"获取东方财富新闻失败: {e}")

    return news_list


def _build_prompt(
    us_indices: List[Dict[str, Any]],
    cls_news: List[Dict[str, str]],
    em_news: List[Dict[str, str]],
) -> str:
    """构建早盘预判 Prompt"""

    today = datetime.now().strftime("%Y-%m-%d")

    # 美股数据
    us_section = "## 隔夜美股数据\n"
    if us_indices:
        us_section += "| 指数 | 收盘 | 涨跌幅 |\n|------|------|--------|\n"
        for idx in us_indices:
            emoji = "🟢" if idx["change_pct"] >= 0 else "🔴"
            us_section += f"| {idx['name']} | {idx['close']:.2f} | {emoji} {idx['change_pct']:+.2f}% |\n"
        us_section += f"\n数据日期: {us_indices[0]['date']}\n"
    else:
        us_section += "数据获取失败\n"

    # 财联社快讯
    cls_section = "## 财联社快讯（最新）\n"
    for i, news in enumerate(cls_news[:15], 1):
        cls_section += f"{i}. [{news['time']}] {news['headline']}\n"

    # 东方财富新闻
    em_section = "## 东方财富财经新闻\n"
    for i, news in enumerate(em_news[:10], 1):
        em_section += f"{i}. {news['headline']}\n"

    prompt = f"""你是一位资深A股市场分析师，现在是 {today} 早上开盘前。
请根据以下隔夜美股数据和最新财经新闻，生成一份简洁实用的「早盘情报」。

{us_section}

{cls_section}

{em_section}

请严格按以下格式输出：

### 一、隔夜美股复盘
简要分析美股三大指数表现及原因（2-3句），判断对A股开盘的影响。

### 二、重要新闻解读
从上述新闻中筛选出 5-8 条与股市最相关的重要新闻，逐条分析：
- 每条标注【利好·行业】或【利空·行业】或【中性】
- 一句话说明影响

### 三、行业影响与龙头推荐
- 🟢 利好行业：列出受利好影响的行业，每个行业推荐 1-2 只龙头股（附股票代码）
- 🔴 利空行业：列出受利空影响的行业，建议规避的方向

### 四、今日大盘预判
- 综合美股走势、政策面、资金面，预判今日大盘走势（高开/低开/平开，震荡/上攻/回调）
- 预计上证指数运行区间

### 五、操作策略建议
- 若高开：如何操作
- 若低开：如何操作
- 今日重点关注板块/个股

注意：
1. 分析要具体、有数据支撑，不要空洞的废话
2. 龙头股推荐要给出具体股票代码（6位数字）
3. 语言简洁有力，适合早上快速阅读
4. 所有建议仅供参考，需提示投资风险"""

    return prompt


def run_morning_briefing(
    send_notification: bool = True,
    no_notify: bool = False,
) -> Optional[str]:
    """
    执行早盘情报分析

    Args:
        send_notification: 是否发送通知
        no_notify: 是否跳过通知（优先级高于 send_notification）

    Returns:
        生成的早盘报告文本，失败返回 None
    """
    from src.config import get_config
    from src.analyzer import GeminiAnalyzer
    from src.notification import NotificationService

    config = get_config()
    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("=" * 50)
    logger.info(f"早盘情报分析开始 - {today}")
    logger.info("=" * 50)

    # 1. 采集数据
    logger.info("[早盘] 获取隔夜美股数据...")
    us_indices = _fetch_us_indices()
    if us_indices:
        for idx in us_indices:
            logger.info(f"  {idx['name']}: {idx['close']:.2f} ({idx['change_pct']:+.2f}%)")
    else:
        logger.warning("[早盘] 美股数据获取失败")

    logger.info("[早盘] 获取财联社快讯...")
    cls_news = _fetch_cls_news(limit=30)
    logger.info(f"  获取到 {len(cls_news)} 条快讯")

    logger.info("[早盘] 获取东方财富新闻...")
    em_news = _fetch_eastmoney_news(limit=20)
    logger.info(f"  获取到 {len(em_news)} 条新闻")

    if not us_indices and not cls_news and not em_news:
        logger.error("[早盘] 所有数据源均获取失败，跳过分析")
        return None

    # 2. 构建 Prompt 并调用 AI
    prompt = _build_prompt(us_indices, cls_news, em_news)
    logger.info(f"[早盘] Prompt 长度: {len(prompt)} 字符")

    analyzer = GeminiAnalyzer(api_key=config.gemini_api_key)
    if not analyzer.is_available():
        logger.error("[早盘] AI 分析器不可用，请检查 API Key 配置")
        return None

    logger.info("[早盘] 调用 AI 生成早盘情报...")
    report = analyzer.generate_text(prompt, max_tokens=3000, temperature=0.7)

    if not report:
        logger.error("[早盘] AI 返回为空")
        return None

    # 添加标题和时间戳
    header = f"# 📰 早盘情报 | {today}\n\n"
    footer = f"\n\n---\n> ⏰ 生成时间: {datetime.now().strftime('%H:%M:%S')} | 仅供参考，不构成投资建议"
    full_report = header + report + footer

    logger.info(f"[早盘] 报告生成成功，长度: {len(full_report)} 字符")

    # 3. 保存报告
    try:
        from pathlib import Path
        reports_dir = Path(__file__).parent.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / f"morning_briefing_{today.replace('-', '')}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_report)
        logger.info(f"[早盘] 报告已保存: {filepath}")
    except Exception as e:
        logger.warning(f"[早盘] 保存报告失败: {e}")

    # 4. 推送通知
    if send_notification and not no_notify:
        try:
            notifier = NotificationService()
            if notifier.is_available():
                logger.info("[早盘] 推送早盘情报到通知渠道...")
                notifier.send(full_report)
            else:
                logger.warning("[早盘] 通知渠道不可用")
        except Exception as e:
            logger.error(f"[早盘] 推送通知失败: {e}")

    logger.info("[早盘] 早盘情报分析完成")
    return full_report
