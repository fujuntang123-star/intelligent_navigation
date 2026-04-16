@echo off
echo ============================================================
echo                   智职领航 - 启动脚本
echo ============================================================
echo.

REM 检查后端目录
if not exist "backend" (
    echo [错误] 未找到 backend 目录
    pause
    exit /b 1
)

REM 检查前端目录
if not exist "UI\my_self_ui" (
    echo [错误] 未找到 UI\my_self_ui 目录
    pause
    exit /b 1
)

echo [1/3] 启动后端服务...
cd backend
start "Backend Server" cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
cd ..

timeout /t 3 /nobreak > nul

echo [2/3] 启动前端服务...
cd UI\my_self_ui
start "Frontend Dev Server" cmd /k "npm run dev"
cd ..\..

echo [3/3] 等待服务启动...
timeout /t 5 /nobreak > nul

echo.
echo ============================================================
echo                     服务已启动！
echo ============================================================
echo.
echo 后端 API: http://localhost:8000
echo 前端页面：http://localhost:5173
echo API 文档：http://localhost:8000/docs
echo.
echo 按任意键退出此窗口...
echo ============================================================
pause > nul
