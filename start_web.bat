@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 启动 Proxy 配置面板...
echo 浏览器访问: http://localhost:8080
echo.
python web_server.py %*
pause
