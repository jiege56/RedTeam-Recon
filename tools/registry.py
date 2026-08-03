#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 工具注册表
将所有信息收集工具抽象为统一元数据，便于调度器调用。
"""

TOOLS = {
    # ========== 全自动 CLI 工具 ==========
    "oneforall": {
        "name": "OneForAll 子域名收集",
        "type": "cli",
        "cwd": "oneforall",
        "entry": "python oneforall.py",
        "args_tpl": "--target {target} --fmt csv --path {output}/01_subdomain",
        "timeout": 1800,
        "parser": "parse_oneforall_csv",
        "category": "subdomain",
        "description": "Python 子域名枚举工具，支持多种收集源和字典爆破"
    },
    "goon_webscan": {
        "name": "Goon 综合资产扫描",
        "type": "cli",
        "cwd": "goon",
        "entry": "goon3_win_amd64.exe",
        "args_tpl": "-ip {target} -mode webscan -ofile {output}/02_portscan/goon.txt -thread {threads} -time {timeout}",
        "timeout": 900,
        "parser": "parse_goon_text",
        "category": "portscan",
        "description": "IP探活、端口扫描、Web标题/指纹识别"
    },
    "goon_fofa": {
        "name": "Goon FOFA 网络空间测绘",
        "type": "cli",
        "cwd": "goon",
        "entry": "goon3_win_amd64.exe",
        "args_tpl": "-key 'domain=\"{target}\"' -mode fofa -num {max_results} -ofile {output}/00_cyberspace/goon_fofa.txt",
        "timeout": 300,
        "parser": "parse_goon_fofa",
        "category": "cyberspace",
        "requires_key": "fofa",
        "description": "通过 FOFA 搜索引擎获取目标资产信息"
    },
    "golin_scan": {
        "name": "Golin 资产测绘与漏洞扫描",
        "type": "cli",
        "cwd": "golin",
        "entry": "golin.exe",
        "args_tpl": "scan -i {target} --web --outname {output}/02_portscan/golin_report.html --nocrack",
        "timeout": 1800,
        "parser": "parse_golin_html",
        "category": "portscan",
        "description": "主机存活探测、端口扫描、协议识别、POC扫描、XSS扫描、Web指纹识别"
    },
    "golin_dirsearch": {
        "name": "Golin 目录扫描",
        "type": "cli",
        "cwd": "golin",
        "entry": "golin.exe",
        "args_tpl": "dirsearch -u {url} -f {dict} -c {threads} --code {code} -t {timeout}",
        "timeout": 600,
        "parser": "parse_golin_dirsearch",
        "category": "dirscan",
        "description": "Web目录扫描，支持自定义字典和并发"
    },
    "golin_brute": {
        "name": "Golin 弱口令/未授权爆破",
        "type": "cli",
        "cwd": "golin",
        "entry": "golin.exe",
        "args_tpl": "scan -i {target} --nopoc --outname {output}/05_brute/golin_brute.html",
        "timeout": 1800,
        "parser": "parse_golin_brute",
        "category": "brute",
        "description": "40余种弱口令/未授权访问爆破"
    },
    "builtin_fingerprint": {
        "name": "内置框架指纹识别",
        "type": "builtin",
        "category": "fingerprint",
        "description": "基于HTTP响应特征的框架/CMS/中间件识别，支持100+指纹规则"
    },

    # ========== 仅启动 GUI 工具 ==========
    "fofaviewer": {
        "name": "FOFA Viewer (多瞳孔)",
        "type": "gui",
        "cwd": "fofaviewer",
        "entry": "MultiplePupils.exe",
        "args_tpl": "",
        "category": "cyberspace",
        "description": "FOFA/Hunter/Quake 网络空间测绘查询客户端"
    },
    "fine": {
        "name": "Fine 网络空间测绘",
        "type": "gui",
        "cwd": "fine",
        "entry": "Fine.exe",
        "args_tpl": "",
        "category": "cyberspace",
        "description": "多测绘引擎资产搜索、ICP备案、企业信息、微信小程序"
    },
    "dirscan_3": {
        "name": "Scandir 3.0 目录扫描",
        "type": "gui",
        "cwd": "dirscan_3.0",
        "entry": "scandir-3.0.jar",
        "args_tpl": "",
        "category": "dirscan",
        "description": "JavaFX GUI 目录/后台/备份文件扫描器"
    },
    "yjdirscan": {
        "name": "御剑目录扫描",
        "type": "gui",
        "cwd": "yjdirscanv1.1",
        "entry": "御剑2.exe",
        "args_tpl": "",
        "category": "dirscan",
        "description": "经典 Windows GUI 目录/后台扫描器"
    },
    "leiying": {
        "name": "雪影 SnowShadow",
        "type": "gui",
        "cwd": "leiying/SnowShadow_v1.0",
        "entry": "SnowShadow.exe",
        "args_tpl": "",
        "category": "综合",
        "description": "综合渗透工具箱：IP查询、端口扫描、C段扫描、远程控制"
    },
    "bjx11": {
        "name": "北极熊 Polar bear v4.5",
        "type": "gui",
        "cwd": "bjx11",
        "entry": "bjx.exe",
        "args_tpl": "",
        "category": "综合",
        "description": "综合扫描：域名扫描、端口探测、目录扫描、EXP漏洞扫描、XSS扫描"
    },
    "webfinder": {
        "name": "WebFinder 端口扫描",
        "type": "gui",
        "cwd": ".",
        "entry": "webfinder-next.jar",
        "args_tpl": "",
        "category": "portscan",
        "description": "JavaFX 端口扫描 GUI 工具"
    }
}


# 一键工作流的执行顺序
WORKFLOW_STEPS = [
    {"step": "cyberspace", "tools": ["goon_fofa"], "depends_on": [], "optional": True},
    {"step": "subdomain", "tools": ["oneforall"], "depends_on": [], "optional": False},
    {"step": "portscan", "tools": ["goon_webscan"], "depends_on": [], "optional": False},
    {"step": "fingerprint", "tools": ["golin_scan"], "depends_on": [], "optional": False},
    {"step": "dirscan", "tools": ["golin_dirsearch"], "depends_on": ["subdomain", "portscan"], "optional": False},
    {"step": "brute", "tools": ["golin_brute"], "depends_on": ["portscan"], "optional": True},
]


# GUI 工具列表（仅启动，不捕获结果）
GUI_TOOLS = [
    {"id": "fofaviewer", "icon": "🌐"},
    {"id": "fine", "icon": "🔍"},
    {"id": "dirscan_3", "icon": "📁"},
    {"id": "yjdirscan", "icon": "📂"},
    {"id": "leiying", "icon": "❄️"},
    {"id": "bjx11", "icon": "🐻"},
    {"id": "webfinder", "icon": "🔎"},
]


def get_tool(tool_id: str) -> dict:
    """获取工具元数据。"""
    return TOOLS.get(tool_id, {})


def get_cli_tools_by_category(category: str) -> list:
    """获取指定分类的 CLI 工具。"""
    return [
        (tid, t) for tid, t in TOOLS.items()
        if t["type"] == "cli" and t.get("category") == category
    ]
