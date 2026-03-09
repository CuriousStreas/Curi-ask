@echo off
chcp 65001 >nul
title Curi Ask - 前端 (Vue)
cd /d "%~dp0frontend"

if not exist "node_modules" (
    echo 未检测到 node_modules，请先运行根目录的 init.bat 完成初始化。
    echo.
    pause
    exit /b 1
)

echo 正在启动前端 (Vite 开发模式，修改代码会热更新)...
echo 地址: http://localhost:5173
echo 按 Ctrl+C 停止
echo.

call npm run dev

echo.
echo 开发服务器已退出。
if errorlevel 1 (
    echo 若未安装依赖，请先运行根目录的 init.bat 或在本目录执行: npm install
)
echo.
pause
