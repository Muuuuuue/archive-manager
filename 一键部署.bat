@echo off
chcp 65001 >nul
title 文件编号与归档系统 - 一键部署
color 0A

:: 保存当前目录
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

cls
echo ================================================
echo    文件编号与归档系统 - 一键部署工具
echo ================================================
echo.
echo 当前目录: %CD%
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    echo.
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
echo [✓] Python已安装
echo.

:: 安装依赖
echo [1/5] 正在安装依赖...
pip install flask pandas openpyxl GitPython schedule -i https://pypi.tuna.tsinghua.edu.cn/simple 2>nul
if errorlevel 1 (
    pip install flask pandas openpyxl GitPython schedule
)
echo [✓] 依赖安装完成
echo.

:: 配置环境变量
echo [2/5] 正在配置环境...
if exist "config.env" (
    echo [✓] 配置文件已存在，跳过配置
) else (
    echo.
    echo ================================================
    echo    首次运行，需要配置一些信息
    echo ================================================
    echo.
    
    set /p EMAIL="请输入163邮箱地址: "
    echo.
    set /p AUTH_CODE="请输入163邮箱授权码: "
    echo.
    echo 提示：授权码不是邮箱密码！请去163邮箱设置获取
    echo.
    set /p ADMIN_TOKEN="请设置管理员令牌（建议用简单密码如admin123）: "
    echo.
    
    echo # 邮箱配置> config.env
    echo EMAIL_IMAP_SERVER=imap.163.com>> config.env
    echo EMAIL_SMTP_SERVER=smtp.163.com>> config.env
    echo EMAIL_USERNAME=%EMAIL%>> config.env
    echo EMAIL_PASSWORD=%AUTH_CODE%>> config.env
    echo.>> config.env
    echo # 网页配置>> config.env
    echo WEB_HOST=0.0.0.0>> config.env
    echo WEB_PORT=5000>> config.env
    echo WEB_DEBUG=false>> config.env
    echo.>> config.env
    echo # 管理员配置>> config.env
    echo ADMIN_TOKEN=%ADMIN_TOKEN%>> config.env
    echo.>> config.env
    echo # 周报配置>> config.env
    echo WEEKLY_REPORT_EMAIL=%EMAIL%>> config.env
    echo REMINDER_DAYS=7>> config.env
    echo.>> config.env
    echo # GitHub配置>> config.env
    echo GITHUB_REPO=https://github.com/Muuuuuue/-.git>> config.env
    echo GITHUB_BRANCH=main>> config.env
    echo GITHUB_TOKEN=>> config.env
    echo.>> config.env
    echo # 文件路径配置>> config.env
    echo TEMP_FOLDER=D:\temp\file_archive>> config.env
    echo PENDING_FOLDER=D:\temp\file_archive\pending>> config.env
    
    echo.
    echo [✓] 配置已保存到 config.env
)
echo.

:: 创建必要文件夹
echo [3/5] 正在创建文件夹...
if not exist "web_system\data" mkdir "web_system\data"
if not exist "file_organizer\data" mkdir "file_organizer\data"
mkdir "D:\temp\file_archive" 2>nul
mkdir "D:\temp\file_archive\pending" 2>nul
echo [✓] 文件夹创建完成
echo.

:: 初始化数据库
echo [4/5] 正在初始化数据库...
cd /d "%SCRIPT_DIR%\web_system"
python -c "exec(open('models.py').read()); init_database(); init_default_rules()" 2>nul
cd /d "%SCRIPT_DIR%"
echo [✓] 数据库初始化完成
echo.

:: 获取管理员令牌
echo [5/5] 正在获取访问地址...
set ADMIN_TOKEN=admin
for /f "tokens=2 delims==" %%a in ('findstr "ADMIN_TOKEN=" config.env') do set ADMIN_TOKEN=%%a
echo.

echo ================================================
echo    部署完成！
echo ================================================
echo.
echo 管理员访问地址:
echo   http://localhost:5000/?token=%ADMIN_TOKEN%
echo.
echo 请按任意键启动网页服务...
pause >nul

:: 启动网页服务
cd /d "%SCRIPT_DIR%\web_system"
python app.py

pause
