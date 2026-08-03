#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam 信息收集工具 - 打包脚本
生成便携版，解压即用。
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           RedTeam 信息收集工具 - 便携版打包程序              ║
╚══════════════════════════════════════════════════════════════╝
    """)


def check_pyinstaller():
    """检查并安装 PyInstaller。"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("[*] 安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                      capture_output=True)
        return True


def build_exe():
    """使用 PyInstaller 打包 exe。"""
    print("[1/4] 打包 ReconHub.exe...")

    # PyInstaller 参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                    # 单文件
        "--windowed",                   # 无控制台
        "--name=RedTeam-Recon",         # 输出文件名
        "--icon=NONE",                  # 无图标
        "--add-data=core;core",         # 添加 core 目录
        "--add-data=tools;tools",       # 添加 tools 目录
        "--add-data=ui;ui",             # 添加 ui 目录
        "--hidden-import=openpyxl",     # 隐藏导入
        "--hidden-import=requests",
        "--hidden-import=yaml",
        "ReconHub.pyw"
    ]

    subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    exe_path = Path("dist/RedTeam-Recon.exe")
    if exe_path.exists():
        print(f"    [OK] 打包成功: {exe_path}")
        return exe_path
    else:
        print("    [FAIL] 打包失败")
        return None


def create_portable_package():
    """创建便携版压缩包。"""
    print("[2/4] 创建便携版目录...")

    # 便携版目录
    portable_dir = Path("dist/RedTeam-Recon-Portable")
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    portable_dir.mkdir(parents=True)

    # 创建目录结构
    (portable_dir / "tools").mkdir()
    (portable_dir / "tools" / "goon").mkdir()
    (portable_dir / "tools" / "golin").mkdir()
    (portable_dir / "tools" / "oneforall").mkdir()
    (portable_dir / "data").mkdir()
    (portable_dir / "data" / "reports").mkdir()
    (portable_dir / "python").mkdir()

    print("[3/4] 复制文件...")

    # 复制 ReconHub
    shutil.copytree("core", portable_dir / "ReconHub" / "core", dirs_exist_ok=True)
    shutil.copytree("tools", portable_dir / "ReconHub" / "tools", dirs_exist_ok=True)
    shutil.copytree("ui", portable_dir / "ReconHub" / "ui", dirs_exist_ok=True)
    shutil.copy("ReconHub.pyw", portable_dir / "ReconHub")
    shutil.copy("requirements.txt", portable_dir / "ReconHub")

    # 复制外部工具
    base_dir = Path("..")

    # Goon
    goon_src = base_dir / "goon"
    if goon_src.exists():
        shutil.copy(goon_src / "goon3_win_amd64.exe", portable_dir / "tools" / "goon")
        shutil.copy(goon_src / "conf.yml", portable_dir / "tools" / "goon")
        print("    [OK] goon")

    # Golin
    golin_src = base_dir / "golin"
    if golin_src.exists():
        shutil.copy(golin_src / "golin.exe", portable_dir / "tools" / "golin")
        if (golin_src / "cert").exists():
            shutil.copytree(golin_src / "cert", portable_dir / "tools" / "golin" / "cert", dirs_exist_ok=True)
        print("    [OK] golin")

    # OneForAll（精简）
    ofa_src = base_dir / "oneforall"
    if ofa_src.exists():
        for item in ["*.py", "config", "common", "modules"]:
            if "*" in item:
                for f in ofa_src.glob(item):
                    shutil.copy(f, portable_dir / "tools" / "oneforall")
            elif (ofa_src / item).exists():
                shutil.copytree(ofa_src / item, portable_dir / "tools" / "oneforall" / item, dirs_exist_ok=True)
        print("    [OK] oneforall")

    # 创建配置文件
    config = {
        "paths": {
            "base": "..\\tools",
            "output": "..\\data\\reports"
        },
        "apikeys": {
            "fofa_email": "",
            "fofa_key": "",
            "hunter_key": "",
            "quake_key": "",
            "shodan_key": "",
            "zoomeye_key": ""
        },
        "rate_limit": {
            "concurrent_tools": 1,
            "tool_threads": 100,
            "tool_interval_seconds": 3.0,
            "timeout": 300
        }
    }

    import json
    with open(portable_dir / "data" / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    return portable_dir


def create_launcher(portable_dir):
    """创建启动脚本。"""
    print("[4/4] 创建启动脚本...")

    # Windows 批处理启动脚本
    bat_content = '''@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   RedTeam 信息收集工具 - 便携版
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] 未检测到 Python，请先安装 Python 3.8+
    echo     下载: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 安装依赖
echo [*] 检查依赖...
pip show openpyxl >nul 2>&1 || pip install openpyxl -q
pip show requests >nul 2>&1 || pip install requests -q
pip show pyyaml >nul 2>&1 || pip install pyyaml -q

:: 启动程序
echo [*] 启动 RedTeam 信息收集工具...
echo.
start "" pythonw.exe "%~dp0ReconHub\\ReconHub.pyw"
'''

    with open(portable_dir / "启动工具.bat", "w", encoding="utf-8") as f:
        f.write(bat_content)

    # 无 Python 环境的安装脚本
    install_content = '''@echo off
chcp 65001 >nul
echo ========================================
echo   安装 Python 环境
echo ========================================
echo.
echo 请按以下步骤操作:
echo.
echo 1. 访问 https://www.python.org/downloads/
echo 2. 下载 Python 3.11 或更高版本
echo 3. 安装时勾选 "Add Python to PATH"
echo 4. 安装完成后运行 "启动工具.bat"
echo.
pause
'''

    with open(portable_dir / "安装Python.bat", "w", encoding="utf-8") as f:
        f.write(install_content)

    # README
    readme_content = '''# RedTeam 信息收集工具 - 便携版

## 使用方法

### 方法一：已有 Python 环境
1. 双击 `启动工具.bat`

### 方法二：没有 Python 环境
1. 双击 `安装Python.bat` 查看安装说明
2. 安装 Python 3.8+
3. 双击 `启动工具.bat`

## 目录结构

```
RedTeam-Recon-Portable/
├── 启动工具.bat          # 启动脚本
├── 安装Python.bat       # Python 安装说明
├── ReconHub/            # 主程序
│   ├── ReconHub.pyw    # 入口文件
│   ├── core/           # 核心模块
│   ├── tools/          # 工具注册
│   └── ui/             # 界面
├── tools/               # 外部工具
│   ├── goon/           # Goon 扫描器
│   ├── golin/          # Golin 资产测绘
│   └── oneforall/      # 子域名收集
└── data/                # 数据目录
    ├── config.json     # 配置文件
    └── reports/        # 报告输出
```

## 功能

- [OK] 子域名枚举
- [OK] 网络空间测绘 (FOFA)
- [OK] 端口扫描
- [OK] 框架指纹识别
- [OK] 目录扫描
- [OK] 弱口令爆破
- [OK] 企业信息收集
- [OK] Excel 报告生成

## 配置 API Key

启动工具后，在「设置」页面配置:
- FOFA Email + Key
- 其他 API Key (可选)

## 注意事项

- 仅支持 Windows 系统
- 需要 Python 3.8+ 环境
- 首次运行会自动安装依赖
'''

    with open(portable_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("    [OK] 启动脚本")
    print("    [OK] 安装说明")
    print("    [OK] README")


def create_zip(portable_dir):
    """创建压缩包。"""
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_name = f"RedTeam-Recon-Portable-{timestamp}.zip"
    zip_path = Path("dist") / zip_name

    print(f"\n[*] 创建压缩包: {zip_name}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in portable_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(portable_dir.parent)
                zf.write(file, arcname)

    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"    [OK] 压缩包大小: {size_mb:.1f} MB")
    print(f"    [OK] 保存位置: {zip_path.absolute()}")

    return zip_path


def main():
    print_banner()

    # 切换到脚本目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # 检查 PyInstaller
    check_pyinstaller()

    # 创建便携版
    portable_dir = create_portable_package()

    # 创建启动脚本
    create_launcher(portable_dir)

    # 创建压缩包
    zip_path = create_zip(portable_dir)

    print("\n" + "=" * 60)
    print("  [OK] 打包完成！")
    print("=" * 60)
    print(f"""
  输出文件: {zip_path.absolute()}

  使用方法:
  1. 将压缩包复制到目标机器
  2. 解压
  3. 双击 "启动工具.bat"

  注意: 目标机器需要安装 Python 3.8+
        如果没有 Python，双击 "安装Python.bat" 查看说明
    """)


if __name__ == "__main__":
    main()
