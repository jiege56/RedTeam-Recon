@echo off
chcp 65001 >nul
echo ========================================
echo   RedTeam 信息收集工具 - 多版本Python便携版打包
echo ========================================
echo.

set SOURCE_DIR=%~dp0
set OUTPUT_DIR=%SOURCE_DIR%dist\RedTeam-Recon-Portable

echo [1/5] 创建目录结构...
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\ReconHub"
mkdir "%OUTPUT_DIR%\tools"
mkdir "%OUTPUT_DIR%\tools\goon"
mkdir "%OUTPUT_DIR%\tools\golin"
mkdir "%OUTPUT_DIR%\tools\oneforall"
mkdir "%OUTPUT_DIR%\data"
mkdir "%OUTPUT_DIR%\data\reports"
mkdir "%OUTPUT_DIR%\python"

echo [2/5] 复制 ReconHub 主程序...
xcopy "%SOURCE_DIR%core" "%OUTPUT_DIR%\ReconHub\core" /E /I /Y >nul
xcopy "%SOURCE_DIR%tools" "%OUTPUT_DIR%\ReconHub\tools" /E /I /Y >nul
xcopy "%SOURCE_DIR%ui" "%OUTPUT_DIR%\ReconHub\ui" /E /I /Y >nul
copy "%SOURCE_DIR%ReconHub.pyw" "%OUTPUT_DIR%\ReconHub\" >nul
copy "%SOURCE_DIR%requirements.txt" "%OUTPUT_DIR%\ReconHub\" >nul
echo   [OK] ReconHub

echo [3/5] 复制外部工具...
if exist "%SOURCE_DIR%..\goon" (
    copy "%SOURCE_DIR%..\goon\goon3_win_amd64.exe" "%OUTPUT_DIR%\tools\goon\" >nul
    copy "%SOURCE_DIR%..\goon\conf.yml" "%OUTPUT_DIR%\tools\goon\" >nul
    echo   [OK] goon
)
if exist "%SOURCE_DIR%..\golin" (
    copy "%SOURCE_DIR%..\golin\golin.exe" "%OUTPUT_DIR%\tools\golin\" >nul
    if exist "%SOURCE_DIR%..\golin\cert" xcopy "%SOURCE_DIR%..\golin\cert" "%OUTPUT_DIR%\tools\golin\cert" /E /I /Y >nul
    echo   [OK] golin
)
if exist "%SOURCE_DIR%..\oneforall" (
    xcopy "%SOURCE_DIR%..\oneforall\*.py" "%OUTPUT_DIR%\tools\oneforall\" /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\config" "%OUTPUT_DIR%\tools\oneforall\config" /E /I /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\common" "%OUTPUT_DIR%\tools\oneforall\common" /E /I /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\modules" "%OUTPUT_DIR%\tools\oneforall\modules" /E /I /Y >nul
    echo   [OK] oneforall
)

echo [4/5] 创建配置文件...
(
echo {
echo   "paths": {
echo     "base": "..\\tools",
echo     "output": "..\\data\\reports"
echo   },
echo   "apikeys": {
echo     "fofa_email": "",
echo     "fofa_key": "",
echo     "hunter_key": "",
echo     "quake_key": "",
echo     "shodan_key": "",
echo     "zoomeye_key": ""
echo   },
echo   "rate_limit": {
echo     "concurrent_tools": 1,
echo     "tool_threads": 100,
echo     "tool_interval_seconds": 3.0,
echo     "timeout": 300
echo   }
echo }
) > "%OUTPUT_DIR%\data\config.json"
echo   [OK] config.json

echo [5/5] 创建启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo.
echo echo ========================================
echo echo   RedTeam 信息收集工具 - 便携版
echo echo ========================================
echo echo.
echo.
echo :: 检测 Python 版本
echo set PYTHON_CMD=
echo set PYTHON_VER=
echo.
echo :: 尝试 python 命令
echo python --version 2^>nul ^| findstr /C:"Python 3." ^>nul
echo if not errorlevel 1 ^(
echo     set PYTHON_CMD=python
echo     for /f "tokens=2" %%%%i in ^('python --version 2^^^>nul'^) do set PYTHON_VER=%%%%i
echo     goto :found
echo ^)
echo.
echo :: 尝试 python3 命令
echo python3 --version 2^>nul ^| findstr /C:"Python 3." ^>nul
echo if not errorlevel 1 ^(
echo     set PYTHON_CMD=python3
echo     for /f "tokens=2" %%%%i in ^('python3 --version 2^^^>nul'^) do set PYTHON_VER=%%%%i
echo     goto :found
echo ^)
echo.
echo :: 尝试 py 命令
echo py -3 --version 2^>nul ^| findstr /C:"Python 3." ^>nul
echo if not errorlevel 1 ^(
echo     set PYTHON_CMD=py -3
echo     for /f "tokens=2" %%%%i in ^('py -3 --version 2^^^>nul'^) do set PYTHON_VER=%%%%i
echo     goto :found
echo ^)
echo.
echo :: 未找到 Python
echo echo [!] 未检测到 Python 3.8+
echo echo.
echo echo 请安装以下任一版本:
echo echo   - Python 3.8:  https://www.python.org/downloads/release/python-3810/
echo echo   - Python 3.9:  https://www.python.org/downloads/release/python-3913/
echo echo   - Python 3.10: https://www.python.org/downloads/release/python-31011/
echo echo   - Python 3.11: https://www.python.org/downloads/release/python-3119/
echo echo   - Python 3.12: https://www.python.org/downloads/release/python-3124/
echo echo   - Python 3.13: https://www.python.org/downloads/release/python-3130/
echo echo   - Python 3.14: https://www.python.org/downloads/release/python-3140/
echo echo.
echo echo 安装时请勾选 "Add Python to PATH"
echo echo.
echo pause
echo exit /b 1
echo.
echo :found
echo echo [OK] 检测到 Python %PYTHON_VER%
echo echo.
echo.
echo :: 检查并安装依赖
echo echo [*] 检查依赖...
echo %PYTHON_CMD% -m pip show openpyxl 2^>nul ^|^| %PYTHON_CMD% -m pip install openpyxl -q
echo %PYTHON_CMD% -m pip show requests 2^>nul ^|^| %PYTHON_CMD% -m pip install requests -q
echo %PYTHON_CMD% -m pip show pyyaml 2^>nul ^|^| %PYTHON_CMD% -m pip install pyyaml -q
echo echo [OK] 依赖检查完成
echo echo.
echo.
echo :: 启动程序
echo echo [*] 启动 RedTeam 信息收集工具...
echo start "" %PYTHON_CMD%w "%%~dp0ReconHub\\ReconHub.pyw"
) > "%OUTPUT_DIR%\启动工具.bat"

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo   输出目录: %OUTPUT_DIR%
echo   支持Python: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
echo.
echo   使用方法:
echo   1. 将 %OUTPUT_DIR% 压缩为 zip
echo   2. 在目标机器解压
echo   3. 双击 "启动工具.bat"
echo.
echo   如果没有Python，脚本会提示下载链接
echo ========================================
pause
