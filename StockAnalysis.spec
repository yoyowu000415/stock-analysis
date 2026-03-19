# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\templates', 'templates'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\strategies', 'strategies'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\static', 'static'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\.env.example', '.'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\.venv\\Lib\\site-packages\\litellm', 'litellm'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\.venv\\Lib\\site-packages\\tiktoken_ext', 'tiktoken_ext'), ('D:\\Files\\wuyy\\股票\\daily_stock_analysis-main\\.venv\\Lib\\site-packages\\exchange_calendars', 'exchange_calendars')],
    hiddenimports=['src', 'src.config', 'src.analyzer', 'src.stock_analyzer', 'src.market_analyzer', 'src.storage', 'src.notification', 'src.search_service', 'src.auth', 'src.formatters', 'src.md2img', 'src.feishu_doc', 'src.scheduler', 'src.logging_config', 'src.enums', 'src.webui_frontend', 'src.core', 'src.core.pipeline', 'src.core.market_review', 'src.core.market_strategy', 'src.core.market_profile', 'src.core.backtest_engine', 'src.core.trading_calendar', 'src.core.config_manager', 'src.core.config_registry', 'src.agent', 'src.agent.conversation', 'src.agent.memory', 'src.agent.executor', 'src.agent.factory', 'src.agent.llm_adapter', 'src.agent.orchestrator', 'src.agent.runner', 'src.agent.agents', 'src.agent.agents.base_agent', 'src.agent.agents.technical_agent', 'src.agent.agents.intel_agent', 'src.agent.agents.risk_agent', 'src.agent.agents.decision_agent', 'src.agent.agents.portfolio_agent', 'src.agent.strategies', 'src.agent.strategies.strategy_agent', 'src.agent.strategies.aggregator', 'src.agent.strategies.router', 'src.agent.tools', 'src.agent.tools.analysis_tools', 'src.agent.tools.data_tools', 'src.agent.tools.market_tools', 'src.agent.tools.search_tools', 'src.agent.tools.registry', 'src.agent.skills', 'api', 'api.app', 'api.deps', 'api.v1', 'api.v1.router', 'api.v1.endpoints', 'api.v1.endpoints.health', 'api.v1.endpoints.analysis', 'api.v1.endpoints.agent', 'api.v1.endpoints.history', 'api.v1.endpoints.stocks', 'api.v1.endpoints.backtest', 'api.v1.endpoints.portfolio', 'api.v1.endpoints.system_config', 'api.v1.endpoints.usage', 'api.v1.endpoints.auth', 'api.v1.schemas', 'api.middlewares', 'api.middlewares.auth', 'api.middlewares.error_handler', 'data_provider', 'data_provider.base', 'data_provider.akshare_fetcher', 'data_provider.efinance_fetcher', 'data_provider.tushare_fetcher', 'data_provider.pytdx_fetcher', 'data_provider.baostock_fetcher', 'data_provider.yfinance_fetcher', 'data_provider.fundamental_adapter', 'bot', 'bot.handler', 'bot.dispatcher', 'analyzer_service', 'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi', 'starlette', 'litellm', 'tiktoken', 'tiktoken_ext', 'tiktoken_ext.openai_public', 'sqlalchemy', 'sqlalchemy.dialects.sqlite', 'efinance', 'akshare', 'baostock', 'pytdx', 'yfinance', 'pandas', 'numpy', 'openpyxl', 'exchange_calendars', 'jinja2', 'markdown2', 'newspaper', 'nltk', 'json_repair', 'schedule', 'httpx', 'httptools', 'watchfiles', 'websockets', 'multipart'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'torch', 'tensorflow', 'cv2', 'PIL.ImageTk'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StockAnalysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StockAnalysis',
)
