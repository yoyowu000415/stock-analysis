@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title A股智能分析系统 - 一键启动
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     A股自选股智能分析系统 - 一键启动     ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ========== 1. 检查 Python ==========
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [错误] 未检测到 Python，请先安装 Python 3.11 或以上版本
    echo  下载地址: https://www.python.org/downloads/
    echo  安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

:: ========== 2. 检查 uv ==========
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo  [提示] 未检测到 uv，正在自动安装...
    pip install uv
    if %errorlevel% neq 0 (
        echo  [错误] uv 安装失败，请手动运行: pip install uv
        pause
        exit /b 1
    )
)

:: ========== 3. 检查 Node.js ==========
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo  [警告] 未检测到 Node.js，Web 前端可能无法构建
    echo  下载地址: https://nodejs.org/
    echo.
)

:: ========== 4. 创建虚拟环境 ==========
if not exist ".venv" (
    echo  [1/4] 正在创建 Python 虚拟环境...
    uv venv .venv --python 3.13 2>nul || uv venv .venv --python 3.12 2>nul || uv venv .venv --python 3.11 2>nul || uv venv .venv
    if %errorlevel% neq 0 (
        echo  [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo  [完成] 虚拟环境已创建
) else (
    echo  [1/4] 虚拟环境已存在，跳过
)

:: ========== 5. 安装依赖 ==========
echo  [2/4] 正在检查并安装依赖（首次较慢，请耐心等待）...
uv pip install -r requirements.txt -q 2>nul
if %errorlevel% neq 0 (
    echo  [提示] 静默安装失败，正在重试...
    uv pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo  [错误] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
)
echo  [完成] 依赖安装成功

:: ========== 6. 配置 API Key ==========
echo  [3/4] 检查配置...

:: 如果 .env 不存在，从模板复制
if not exist ".env" (
    copy ".env.example" ".env" >nul 2>&1
)

:: 检查是否已配置 API Key
findstr /r "DEEPSEEK_API_KEY=sk-" ".env" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ┌────────────────────────────────────────┐
    echo  │  首次运行需要配置 DeepSeek API Key      │
    echo  │  获取地址: https://platform.deepseek.com │
    echo  │  注册后在"API Keys"页面创建即可          │
    echo  └────────────────────────────────────────┘
    echo.
    set /p "API_KEY=  请输入你的 DeepSeek API Key: "

    if "!API_KEY!"=="" (
        echo  [错误] API Key 不能为空
        pause
        exit /b 1
    )

    :: 用 PowerShell 替换 .env 中的 DEEPSEEK_API_KEY
    powershell -Command "(Get-Content '.env') -replace 'DEEPSEEK_API_KEY=.*', 'DEEPSEEK_API_KEY=%API_KEY%' | Set-Content '.env' -Encoding UTF8"

    echo  [完成] API Key 已保存
) else (
    echo  [完成] API Key 已配置
)

:: ========== 7. 配置股票（可选） ==========
echo.
set /p "CHANGE_STOCKS=  是否修改自选股？当前默认: 600519,300750,002594 (y/N): "
if /i "%CHANGE_STOCKS%"=="y" (
    echo.
    echo  请输入股票代码，逗号分隔
    echo  示例: 600519,000001,300750,AAPL,00700
    set /p "STOCKS=  股票代码: "
    if not "!STOCKS!"=="" (
        powershell -Command "(Get-Content '.env') -replace 'STOCK_LIST=.*', 'STOCK_LIST=!STOCKS!' | Set-Content '.env' -Encoding UTF8"
        echo  [完成] 自选股已更新
    )
)

:: ========== 8. 启动服务 ==========
echo.
echo  [4/4] 正在启动 Web 分析界面...
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║  启动成功后请在浏览器打开:               ║
echo  ║  http://127.0.0.1:8000                   ║
echo  ║                                          ║
echo  ║  按 Ctrl+C 可停止服务                    ║
echo  ╚══════════════════════════════════════════╝
echo.

uv run python main.py --webui-only

pause
