@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title A股智能分析系统
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     A股自选股智能分析系统                 ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: 检查 .env 是否存在
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
    ) else (
        echo DEEPSEEK_API_KEY=> ".env"
        echo STOCK_LIST=600519,300750,002594>> ".env"
        echo DATABASE_PATH=./data/stock_analysis.db>> ".env"
        echo RUN_IMMEDIATELY=true>> ".env"
        echo MARKET_REVIEW_ENABLED=true>> ".env"
        echo LOG_DIR=./logs>> ".env"
        echo LOG_LEVEL=INFO>> ".env"
        echo MAX_WORKERS=3>> ".env"
    )
)

:: 检查 API Key
findstr /r "DEEPSEEK_API_KEY=sk-" ".env" >nul 2>&1
if %errorlevel% neq 0 (
    echo  ┌─────────────────────────────────────────┐
    echo  │  首次运行需要配置 DeepSeek API Key        │
    echo  │  获取地址: https://platform.deepseek.com  │
    echo  └─────────────────────────────────────────┘
    echo.
    set /p "API_KEY=  请输入你的 DeepSeek API Key: "
    if "!API_KEY!"=="" (
        echo  [错误] API Key 不能为空
        pause
        exit /b 1
    )
    powershell -Command "(Get-Content '.env') -replace 'DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=!API_KEY!' | Set-Content '.env' -Encoding UTF8"
    echo  [完成] API Key 已保存
    echo.
)

echo  正在启动，请稍候...
echo  启动后请在浏览器打开: http://127.0.0.1:8000
echo  按 Ctrl+C 可停止服务
echo.

"StockAnalysis.exe" --webui-only

pause
