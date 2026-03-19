# -*- coding: utf-8 -*-
"""打包为 exe 的构建脚本"""
import PyInstaller.__main__
import os
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
site_packages = os.path.join(base_dir, ".venv", "Lib", "site-packages")

# 需要打包的数据文件/目录
datas = [
    (os.path.join(base_dir, "templates"), "templates"),
    (os.path.join(base_dir, "strategies"), "strategies"),
    (os.path.join(base_dir, "static"), "static"),
    (os.path.join(base_dir, ".env.example"), "."),
    # litellm 整个包（含 JSON 数据文件和子模块）
    (os.path.join(site_packages, "litellm"), "litellm"),
    # tiktoken 编码数据
    (os.path.join(site_packages, "tiktoken_ext"), "tiktoken_ext"),
    # exchange_calendars 交易日历数据
    (os.path.join(site_packages, "exchange_calendars"), "exchange_calendars"),
]

# 需要隐式导入的模块（PyInstaller 自动分析可能遗漏的）
hidden_imports = [
    "src", "src.config", "src.analyzer", "src.stock_analyzer",
    "src.market_analyzer", "src.storage", "src.notification",
    "src.search_service", "src.auth", "src.formatters",
    "src.md2img", "src.feishu_doc", "src.scheduler",
    "src.logging_config", "src.enums", "src.webui_frontend",
    "src.core", "src.core.pipeline", "src.core.market_review",
    "src.core.market_strategy", "src.core.market_profile",
    "src.core.backtest_engine", "src.core.trading_calendar",
    "src.core.config_manager", "src.core.config_registry",
    "src.agent", "src.agent.conversation", "src.agent.memory",
    "src.agent.executor", "src.agent.factory",
    "src.agent.llm_adapter", "src.agent.orchestrator",
    "src.agent.runner",
    "src.agent.agents", "src.agent.agents.base_agent",
    "src.agent.agents.technical_agent", "src.agent.agents.intel_agent",
    "src.agent.agents.risk_agent", "src.agent.agents.decision_agent",
    "src.agent.agents.portfolio_agent",
    "src.agent.strategies", "src.agent.strategies.strategy_agent",
    "src.agent.strategies.aggregator", "src.agent.strategies.router",
    "src.agent.tools", "src.agent.tools.analysis_tools",
    "src.agent.tools.data_tools", "src.agent.tools.market_tools",
    "src.agent.tools.search_tools", "src.agent.tools.registry",
    "src.agent.skills",
    "api", "api.app", "api.deps",
    "api.v1", "api.v1.router",
    "api.v1.endpoints", "api.v1.endpoints.health",
    "api.v1.endpoints.analysis", "api.v1.endpoints.agent",
    "api.v1.endpoints.history", "api.v1.endpoints.stocks",
    "api.v1.endpoints.backtest", "api.v1.endpoints.portfolio",
    "api.v1.endpoints.system_config", "api.v1.endpoints.usage",
    "api.v1.endpoints.auth",
    "api.v1.schemas",
    "api.middlewares", "api.middlewares.auth", "api.middlewares.error_handler",
    "data_provider", "data_provider.base",
    "data_provider.akshare_fetcher", "data_provider.efinance_fetcher",
    "data_provider.tushare_fetcher", "data_provider.pytdx_fetcher",
    "data_provider.baostock_fetcher", "data_provider.yfinance_fetcher",
    "data_provider.fundamental_adapter",
    "bot", "bot.handler", "bot.dispatcher",
    "analyzer_service",
    # 第三方库
    "uvicorn", "uvicorn.logging", "uvicorn.loops",
    "uvicorn.loops.auto", "uvicorn.protocols",
    "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan", "uvicorn.lifespan.on",
    "fastapi", "starlette",
    "litellm", "tiktoken", "tiktoken_ext", "tiktoken_ext.openai_public",
    "sqlalchemy", "sqlalchemy.dialects.sqlite",
    "efinance", "akshare", "baostock", "pytdx", "yfinance",
    "pandas", "numpy", "openpyxl",
    "exchange_calendars",
    "jinja2", "markdown2",
    "newspaper", "nltk",
    "json_repair",
    "schedule",
    "httpx", "httptools", "watchfiles", "websockets",
    "multipart",
]

args = [
    os.path.join(base_dir, "main.py"),
    "--name", "StockAnalysis",
    "--noconfirm",
    "--clean",
    # 用 onedir 模式（比 onefile 启动快很多）
    "--onedir",
    # 控制台模式（需要看日志输出）
    "--console",
    # 输出到 release 目录避免 dist 被占用
    "--distpath", os.path.join(base_dir, "output"),
]

# 添加数据文件
for src, dst in datas:
    if os.path.exists(src):
        args.extend(["--add-data", f"{src}{os.pathsep}{dst}"])

# 添加隐式导入
for mod in hidden_imports:
    args.extend(["--hidden-import", mod])

# 排除不需要的大型库（减小体积）
excludes = ["matplotlib", "scipy", "torch", "tensorflow", "cv2", "PIL.ImageTk"]
for exc in excludes:
    args.extend(["--exclude-module", exc])

print("=" * 60)
print("开始打包 A股智能分析系统...")
print("=" * 60)

PyInstaller.__main__.run(args)

print()
print("=" * 60)
print("打包完成！")
print(f"输出目录: {os.path.join(base_dir, 'dist', 'A股智能分析系统')}")
print("=" * 60)
