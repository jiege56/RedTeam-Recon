@echo off
chcp 65001 >nul
echo ========================================
echo   RedTeam 信息收集工具 - 便携版打包脚本
echo ========================================
echo.

set SOURCE_DIR=%~dp0
set OUTPUT_DIR=%SOURCE_DIR%dist\RedTeam-Recon-Portable
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip

echo [1/6] 创建输出目录...
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%\tools"
mkdir "%OUTPUT_DIR%\ReconHub"
mkdir "%OUTPUT_DIR%\python"

echo [2/6] 复制 ReconHub 主程序...
xcopy "%SOURCE_DIR%core" "%OUTPUT_DIR%\ReconHub\core" /E /I /Y >nul
xcopy "%SOURCE_DIR%tools" "%OUTPUT_DIR%\ReconHub\tools" /E /I /Y >nul
xcopy "%SOURCE_DIR%ui" "%OUTPUT_DIR%\ReconHub\ui" /E /I /Y >nul
mkdir "%OUTPUT_DIR%\ReconHub\data" 2>nul
mkdir "%OUTPUT_DIR%\ReconHub\data\reports" 2>nul
copy "%SOURCE_DIR%ReconHub.pyw" "%OUTPUT_DIR%\ReconHub\" >nul
copy "%SOURCE_DIR%requirements.txt" "%OUTPUT_DIR%\ReconHub\" >nul

echo [3/6] 复制外部工具...
:: 复制 goon
if exist "%SOURCE_DIR%..\goon" (
    xcopy "%SOURCE_DIR%..\goon\goon3_win_amd64.exe" "%OUTPUT_DIR%\tools\goon\" /I /Y >nul
    xcopy "%SOURCE_DIR%..\goon\conf.yml" "%OUTPUT_DIR%\tools\goon\" /I /Y >nul
    echo   - goon: OK
)

:: 复制 golin
if exist "%SOURCE_DIR%..\golin" (
    xcopy "%SOURCE_DIR%..\golin\golin.exe" "%OUTPUT_DIR%\tools\golin\" /I /Y >nul
    xcopy "%SOURCE_DIR%..\golin\cert" "%OUTPUT_DIR%\tools\golin\cert" /E /I /Y >nul
    echo   - golin: OK
)

:: 复制 oneforall（精简版）
if exist "%SOURCE_DIR%..\oneforall" (
    xcopy "%SOURCE_DIR%..\oneforall\*.py" "%OUTPUT_DIR%\tools\oneforall\" /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\config" "%OUTPUT_DIR%\tools\oneforall\config" /E /I /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\common" "%OUTPUT_DIR%\tools\oneforall\common" /E /I /Y >nul
    xcopy "%SOURCE_DIR%..\oneforall\modules" "%OUTPUT_DIR%\tools\oneforall\modules" /E /I /Y >nul
    echo   - oneforall: OK
)

echo [4/6] 下载 Python 嵌入式版本...
:: 使用 PowerShell 下载
powershell -Command "& {Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile '%OUTPUT_DIR%\python\python.zip'}" 2>nul
if exist "%OUTPUT_DIR%\python\python.zip" (
    echo   - 下载完成
    :: 解压
    powershell -Command "& {Expand-Archive -Path '%OUTPUT_DIR%\python\python.zip' -DestinationPath '%OUTPUT_DIR%\python' -Force}" 2>nul
    del "%OUTPUT_DIR%\python\python.zip" 2>nul
    echo   - 解压完成
) else (
    echo   - 下载失败，请手动下载 Python 嵌入式版本
    echo   - URL: %PYTHON_EMBED_URL%
)

echo [5/6] 安装 Python 依赖...
:: 创建 get-pip.py
powershell -Command "& {Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%OUTPUT_DIR%\python\get-pip.py'}" 2>nul
if exist "%OUTPUT_DIR%\python\python.exe" (
    "%OUTPUT_DIR%\python\python.exe" "%OUTPUT_DIR%\python\get-pip.py" --no-warn-script-location 2>nul
    "%OUTPUT_DIR%\python\python.exe" -m pip install openpyxl requests pyyaml --no-warn-script-location 2>nul
    echo   - 依赖安装完成
)

echo [6/6] 创建启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo cd /d "%%~dp0"
echo set PYTHON_PATH=%%~dp0python
echo set PATH=%%PYTHON_PATH%%;%%PATH%%
echo start "" "%%PYTHON_PATH%%\pythonw.exe" "%%~dp0ReconHub\ReconHub.pyw"
) > "%OUTPUT_DIR%\启动RedTeam信息收集.bat"

:: 创建配置文件
(
echo {
echo   "paths": {
echo     "base": ".",
echo     "output": ".\\ReconHub\\data\\reports"
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
) > "%OUTPUT_DIR%\ReconHub\data\config.json"

echo.
echo ========================================
echo   打包完成！
echo ========================================
echo.
echo   输出目录: %OUTPUT_DIR%
echo.
echo   使用方法:
echo   1. 将 %OUTPUT_DIR% 文件夹压缩为 zip
echo   2. 在目标机器解压
echo   3. 双击 "启动RedTeam信息收集.bat"
echo.
echo   注意: 首次运行需要联网下载 Python 依赖
echo ========================================
pause
