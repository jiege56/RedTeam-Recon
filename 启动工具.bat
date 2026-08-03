@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   RedTeam 信息收集工具 - 便携版
echo ========================================
echo.

:: 检测 Python 版本
set PYTHON_CMD=
set PYTHON_VER=
set PYTHON_MAJOR=
set PYTHON_MINOR=

:: 尝试 python 命令
for /f "tokens=2 delims= " %%i in ('python --version 2^>nul') do (
    set PYTHON_VER=%%i
    set PYTHON_CMD=python
)
if defined PYTHON_CMD goto :check_version

:: 尝试 python3 命令
for /f "tokens=2 delims= " %%i in ('python3 --version 2^>nul') do (
    set PYTHON_VER=%%i
    set PYTHON_CMD=python3
)
if defined PYTHON_CMD goto :check_version

:: 尝试 py 命令
for /f "tokens=2 delims= " %%i in ('py -3 --version 2^>nul') do (
    set PYTHON_VER=%%i
    set PYTHON_CMD=py -3
)
if defined PYTHON_CMD goto :check_version

:: 未找到 Python
goto :no_python

:check_version
echo [OK] 检测到 Python %PYTHON_VER%

:: 解析版本号
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VER%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

:: 检查版本是否 >= 3.8
if %PYTHON_MAJOR% LSS 3 goto :old_version
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 8 goto :old_version

echo [OK] Python 版本符合要求 (>= 3.8)
echo.

:: 检查并安装依赖
echo [*] 检查依赖...
%PYTHON_CMD% -m pip show openpyxl >nul 2>&1 || (
    echo [*] 安装 openpyxl...
    %PYTHON_CMD% -m pip install openpyxl -q
)
%PYTHON_CMD% -m pip show requests >nul 2>&1 || (
    echo [*] 安装 requests...
    %PYTHON_CMD% -m pip install requests -q
)
%PYTHON_CMD% -m pip show pyyaml >nul 2>&1 || (
    echo [*] 安装 pyyaml...
    %PYTHON_CMD% -m pip install pyyaml -q
)
echo [OK] 依赖检查完成
echo.

:: 启动程序
echo [*] 启动 RedTeam 信息收集工具...
echo.
start "" %PYTHON_CMD%w "%~dp0ReconHub\ReconHub.pyw"
exit /b 0

:no_python
echo [!] 未检测到 Python 3.8+
echo.
echo ========================================
echo   请选择安装方式:
echo ========================================
echo.
echo   [1] 下载 Python 3.11 (推荐，稳定)
echo   [2] 下载 Python 3.12 (最新)
echo   [3] 下载 Python 3.13 (最新)
echo   [4] 使用嵌入式 Python (无需安装)
echo   [5] 退出
echo.
set /p choice=请输入选项 (1-5):

if "%choice%"=="1" goto :download_311
if "%choice%"=="2" goto :download_312
if "%choice%"=="3" goto :download_313
if "%choice%"=="4" goto :use_embedded
exit /b 0

:download_311
echo.
echo [*] 正在下载 Python 3.11.9...
echo     URL: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
echo.
echo 请手动下载并安装，安装时勾选 "Add Python to PATH"
start https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
pause
exit /b 0

:download_312
echo.
echo [*] 正在下载 Python 3.12.4...
echo     URL: https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
echo.
echo 请手动下载并安装，安装时勾选 "Add Python to PATH"
start https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
pause
exit /b 0

:download_313
echo.
echo [*] 正在下载 Python 3.13.0...
echo     URL: https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
echo.
echo 请手动下载并安装，安装时勾选 "Add Python to PATH"
start https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe
pause
exit /b 0

:use_embedded
echo.
echo [*] 正在下载嵌入式 Python 3.11...
set EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip
set EMBED_DIR=%~dp0python\embed

if not exist "%EMBED_DIR%" mkdir "%EMBED_DIR%"

echo [*] 下载中...
powershell -Command "& {Invoke-WebRequest -Uri '%EMBED_URL%' -OutFile '%EMBED_DIR%\python.zip'}"

if not exist "%EMBED_DIR%\python.zip" (
    echo [!] 下载失败，请检查网络
    pause
    exit /b 1
)

echo [*] 解压中...
powershell -Command "& {Expand-Archive -Path '%EMBED_DIR%\python.zip' -DestinationPath '%EMBED_DIR%' -Force}"
del "%EMBED_DIR%\python.zip" 2>nul

:: 配置嵌入式 Python
echo [*] 配置嵌入式 Python...
(
echo import sys
echo import os
echo sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
) > "%EMBED_DIR%\sitecustomize.py"

:: 下载 get-pip
echo [*] 下载 pip...
powershell -Command "& {Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%EMBED_DIR%\get-pip.py'}"

:: 安装 pip 和依赖
echo [*] 安装依赖...
"%EMBED_DIR%\python.exe" "%EMBED_DIR%\get-pip.py" --no-warn-script-location
"%EMBED_DIR%\python.exe" -m pip install openpyxl requests pyyaml --no-warn-script-location

echo [OK] 嵌入式 Python 安装完成
echo.

:: 启动程序
echo [*] 启动 RedTeam 信息收集工具...
echo.
start "" "%EMBED_DIR%\pythonw.exe" "%~dp0ReconHub\ReconHub.pyw"
exit /b 0

:old_version
echo [!] Python 版本过低: %PYTHON_VER%
echo     需要 Python 3.8 或更高版本
echo.
echo 请升级 Python:
echo   https://www.python.org/downloads/
echo.
pause
exit /b 1
