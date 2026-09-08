@echo off
chcp 65001 >nul
echo 正在设置 subconverter...

if not exist "subconverter" (
    echo 下载 subconverter...
    curl -L -o subconverter.zip https://github.com/tindy2013/subconverter/releases/latest/download/subconverter_win64.zip

    echo 解压文件...
    tar -xf subconverter.zip -C .
    del subconverter.zip

    echo subconverter 安装完成！
) else (
    echo subconverter 已存在
)

echo.
echo 配置 subconverter...
copy /Y pref.ini subconverter\pref.ini

echo.
echo 启动 subconverter 服务...
cd subconverter
start "Subconverter" subconverter.exe

echo.
echo subconverter 已在后台启动，监听端口 25500
echo 按任意键退出...
pause >nul
