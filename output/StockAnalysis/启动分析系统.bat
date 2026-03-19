@echo off
setlocal EnableDelayedExpansion
title Stock Analysis System
color 0A

echo.
echo  ========================================
echo     Stock Analysis System - Launcher
echo  ========================================
echo.

cd /d "%~dp0"

if not exist ".env" (
    echo  [INIT] Creating config file...
    (
        echo STOCK_LIST=600519,300750,002594
        echo DEEPSEEK_API_KEY=
        echo DATABASE_PATH=./data/stock_analysis.db
        echo RUN_IMMEDIATELY=true
        echo MARKET_REVIEW_ENABLED=true
        echo LOG_DIR=./logs
        echo LOG_LEVEL=INFO
        echo MAX_WORKERS=3
        echo BACKTEST_ENABLED=true
        echo SCHEDULE_ENABLED=false
        echo WEBUI_HOST=127.0.0.1
        echo WEBUI_PORT=8000
    ) > ".env"
    echo  [OK] Config file created
    echo.
)

set "HAS_KEY=0"
for /f "tokens=1,* delims==" %%a in ('findstr /B "DEEPSEEK_API_KEY=" ".env" 2^>nul') do (
    if not "%%b"=="" set "HAS_KEY=1"
)

if "!HAS_KEY!"=="0" (
    echo  ----------------------------------------
    echo   DeepSeek API Key required!
    echo   Get yours at: https://platform.deepseek.com
    echo   Register and create an API Key
    echo  ----------------------------------------
    echo.
    set /p "API_KEY=  Enter your DeepSeek API Key: "
    if "!API_KEY!"=="" (
        echo.
        echo  [ERROR] API Key cannot be empty!
        echo.
        pause
        exit /b 1
    )
    powershell -Command "$c = Get-Content '.env' -Encoding UTF8; $c = $c -replace '^DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=!API_KEY!'; $c | Set-Content '.env' -Encoding UTF8"
    echo.
    echo  [OK] API Key saved
    echo.
)

echo  Default stocks: 600519, 300750, 002594
set /p "CHG=  Change stocks? Press Enter to skip, or type codes (comma separated): "
if not "!CHG!"=="" (
    powershell -Command "$c = Get-Content '.env' -Encoding UTF8; $c = $c -replace '^STOCK_LIST=.*', 'STOCK_LIST=!CHG!'; $c | Set-Content '.env' -Encoding UTF8"
    echo  [OK] Stocks updated
)

echo.
echo  ========================================
echo   Starting web server...
echo   Open in browser: http://127.0.0.1:8000
echo   Press Ctrl+C to stop
echo  ========================================
echo.

StockAnalysis.exe --webui-only

echo.
echo  Server stopped.
pause
