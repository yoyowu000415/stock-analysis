@echo off
chcp 65001 >nul 2>&1
title 打包分享

echo.
echo  正在打包项目（排除敏感文件和缓存）...
echo.

cd /d "%~dp0\.."

powershell -Command "Compress-Archive -Path 'daily_stock_analysis-main\*' -DestinationPath 'A股智能分析系统.zip' -Force -CompressionLevel Optimal" 2>nul

if %errorlevel% neq 0 (
    echo  使用 PowerShell 精确打包...
    powershell -Command ^
        "$src = 'daily_stock_analysis-main'; " ^
        "$exclude = @('.venv', 'node_modules', 'data', 'logs', '__pycache__', '.env'); " ^
        "$files = Get-ChildItem -Path $src -Recurse -Force | Where-Object { " ^
        "  $rel = $_.FullName.Substring((Resolve-Path $src).Path.Length+1); " ^
        "  $skip = $false; " ^
        "  foreach ($e in $exclude) { if ($rel -like \"$e*\" -or $rel -like \"*\$e*\") { $skip = $true; break } }; " ^
        "  -not $skip " ^
        "}; " ^
        "Compress-Archive -Path $files.FullName -DestinationPath 'A股智能分析系统.zip' -Force"
)

echo.
echo  [完成] 已生成: ..\A股智能分析系统.zip
echo  可以直接发送给朋友，双击「一键启动.bat」即可使用
echo.
pause
