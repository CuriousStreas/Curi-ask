@echo off
chcp 65001 >nul
title Curi Ask - 一键初始化
cd /d "%~dp0"

echo ========================================
echo   Curi Ask 一键初始化
echo ========================================
echo.

:: 后端：复制 .env 模板（若不存在）
if not exist "backend\.env" (
    copy "backend\.env.example" "backend\.env"
    echo [后端] 已从 .env.example 生成 backend\.env，请稍后编辑填入 API 地址和密钥。
) else (
    echo [后端] backend\.env 已存在，跳过复制。
)
echo.

:: 后端：安装 Python 依赖
echo [后端] 正在安装 Python 依赖 (pip install -r requirements.txt)...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [后端] 安装失败，请检查是否已安装 Python 和 pip。
    cd ..
    pause
    exit /b 1
)
cd ..
echo [后端] 依赖安装完成.
echo.

:: 前端：安装 npm 依赖
echo [前端] 正在安装 npm 依赖 (npm install)...
cd frontend
call npm install
if errorlevel 1 (
    echo [前端] 安装失败，请检查是否已安装 Node.js 和 npm。
    cd ..
    pause
    exit /b 1
)
cd ..
echo [前端] 依赖安装完成.
echo.

echo ========================================
echo   初始化完成
echo ========================================
echo.
echo 下一步：
echo   1. 编辑 backend\.env，填入 AI_API_BASE_URL 和 AI_API_KEY
echo   2. 双击 start-backend.bat 启动后端
echo   3. 双击 start-frontend.bat 启动前端
echo   4. 浏览器打开 http://localhost:5173
echo.
pause
