@echo off
chcp 65001 >nul
title Curi Ask - 后端 (Flask)
cd /d "%~dp0backend"

echo 正在启动后端 (Flask 调试模式，修改代码会自动重载)...
echo 地址: http://localhost:3001
echo 按 Ctrl+C 停止
echo.

python app.py
if errorlevel 1 (
    echo.
    echo 若未安装依赖，请先运行: pip install -r requirements.txt
    pause
)
