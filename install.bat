@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   RedTeam-Recon 安装脚本
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未检测到Python，请先安装Python 3.8+
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 安装Python依赖...
pip install -r requirements.txt -q
echo [OK] 依赖安装完成

echo.
echo [2/3] 下载外部工具...
echo.

:: 创建tools目录
mkdir tools\goon 2>nul
mkdir tools\golin 2>nul
mkdir tools\oneforall 2>nul

:: 下载OneForAll
echo [*] 下载OneForAll...
git clone https://github.com/shmilylty/OneForAll.git tools\oneforall 2>nul
if exist tools\oneforall\oneforall.py (
    echo [OK] OneForAll
) else (
    echo [WARN] OneForAll下载失败，请手动下载
    echo        https://github.com/shmilylty/OneForAll
)

echo.
echo [3/3] 配置说明...
echo.
echo 请手动下载以下工具并放入对应目录:
echo.
echo   Goon: https://github.com/i11us0ry/goon/releases
echo         下载 goon3_win_amd64.exe 放入 tools/goon/
echo.
echo   Golin: https://github.com/selinuxG/Golin/releases
echo          下载 golin.exe 放入 tools/golin/
echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo   运行方式: python ReconHub.pyw
echo   或双击:   启动工具.bat
echo.
pause
