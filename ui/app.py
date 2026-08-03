#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam信息收集 GUI 主窗口
支持：域名/IP/CIDR/URL/企业名称 输入，实时统计，一键收集。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


class ReconHubApp:
    """RedTeam信息收集 主应用窗口。"""

    def __init__(self, config, workflow):
        self.config = config
        self.workflow = workflow
        self._is_running = False

        self.root = tk.Tk()
        self.root.title("RedTeam信息收集 - 一体化工具")
        self.root.geometry("1200x850")
        self.root.minsize(1000, 750)

        # 样式
        self.style = ttk.Style()
        self.style.configure("Title.TLabel", font=("微软雅黑", 14, "bold"))
        self.style.configure("Header.TLabel", font=("微软雅黑", 10, "bold"))
        self.style.configure("Status.TLabel", font=("微软雅黑", 9))
        self.style.configure("Start.TButton", font=("微软雅黑", 11, "bold"))
        self.style.configure("Tool.TButton", font=("微软雅黑", 9))
        self.style.configure("Stat.TLabel", font=("Consolas", 10))
        self.style.configure("StatValue.TLabel", font=("Consolas", 10, "bold"))

        # 变量
        self.target_var = tk.StringVar()
        self.company_var = tk.StringVar()  # 企业名称
        self.strategy_var = tk.StringVar(value="全面")
        self.status_var = tk.StringVar(value="就绪")
        self.subdomain_var = tk.BooleanVar(value=True)
        self.cyberspace_var = tk.BooleanVar(value=True)  # 默认开启网络空间测绘
        self.portscan_var = tk.BooleanVar(value=True)
        self.fingerprint_var = tk.BooleanVar(value=True)
        self.dirscan_var = tk.BooleanVar(value=False)
        self.pocscan_var = tk.BooleanVar(value=False)  # POC漏洞扫描
        self.brute_var = tk.BooleanVar(value=False)

        # 速率限制变量
        self.concurrent_var = tk.IntVar(value=config.get("rate_limit.concurrent_tools", 1))
        self.interval_var = tk.DoubleVar(value=config.get("rate_limit.tool_interval_seconds", 3.0))
        self.threads_var = tk.IntVar(value=config.get("rate_limit.tool_threads", 100))

        # 统计数据变量
        self.stat_subdomains = tk.StringVar(value="0")
        self.stat_ips = tk.StringVar(value="0")
        self.stat_assets = tk.StringVar(value="0")
        self.stat_ports = tk.StringVar(value="0")
        self.stat_fingerprints = tk.StringVar(value="0")
        self.stat_frameworks = tk.StringVar(value="")
        self.stat_dirhits = tk.StringVar(value="0")
        self.stat_vulns = tk.StringVar(value="0")

        # 历史记录
        self.target_history = self._load_history("target")
        self.company_history = self._load_history("company")

        self._build_ui()

    def _build_ui(self):
        """构建UI布局。"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶部标题
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(title_frame, text="🔴 RedTeam", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_frame, text="信息收集一体化工具", style="Header.TLabel").pack(side=tk.LEFT, padx=10)

        # 创建Notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 标签页1：信息收集
        scan_frame = ttk.Frame(notebook, padding=10)
        notebook.add(scan_frame, text="📡 信息收集")
        self._build_scan_tab(scan_frame)

        # 标签页2：工具箱
        toolbox_frame = ttk.Frame(notebook, padding=10)
        notebook.add(toolbox_frame, text="🧰 工具箱")
        self._build_toolbox_tab(toolbox_frame)

        # 标签页3：设置
        settings_frame = ttk.Frame(notebook, padding=10)
        notebook.add(settings_frame, text="⚙️ 设置")
        self._build_settings_tab(settings_frame)

        # 底部状态栏
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel").pack(side=tk.LEFT)
        ttk.Button(status_frame, text="📂 打开报告目录", command=self._open_report_dir).pack(side=tk.RIGHT)

    def _build_scan_tab(self, parent):
        """构建信息收集标签页。"""
        # ========== 目标输入区域 ==========
        target_frame = ttk.LabelFrame(parent, text="目标输入", padding=10)
        target_frame.pack(fill=tk.X, pady=(0, 5))

        # 第一行：域名/IP/URL 输入（带历史记录下拉）
        row1 = ttk.Frame(target_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="目标:", width=8).pack(side=tk.LEFT)
        self.target_combo = ttk.Combobox(row1, textvariable=self.target_var, values=self.target_history, width=50)
        self.target_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(row1, text="📁 导入", command=self._import_targets).pack(side=tk.LEFT, padx=2)
        ttk.Button(row1, text="🗑️", width=3, command=self._clear_target_history).pack(side=tk.LEFT)

        # 第二行：企业名称输入（带历史记录下拉）
        row2 = ttk.Frame(target_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="企业:", width=8).pack(side=tk.LEFT)
        self.company_combo = ttk.Combobox(row2, textvariable=self.company_var, values=self.company_history, width=50)
        self.company_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(row2, text="🗑️", width=3, command=self._clear_company_history).pack(side=tk.LEFT)

        # 提示
        ttk.Label(target_frame, text="💡 只输入目标可扫描 | 只输入企业可收集企业信息 | 都输入则先收集企业再扫描目标",
                  foreground="blue").pack(anchor=tk.W, pady=(3, 0))
        ttk.Label(target_frame, text="目标: 域名 / IP / CIDR / URL    企业: 公司名称（FOFA/ICP/Whois/GitHub/邮箱）",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 0))

        # ========== 策略和模块选择 ==========
        config_frame = ttk.Frame(parent)
        config_frame.pack(fill=tk.X, pady=(0, 5))

        # 策略选择
        strategy_frame = ttk.LabelFrame(config_frame, text="扫描策略", padding=10)
        strategy_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        strategies = ["全面", "快速", "仅子域名", "仅端口", "仅目录", "自定义"]
        for s in strategies:
            ttk.Radiobutton(strategy_frame, text=s, variable=self.strategy_var, value=s,
                           command=self._on_strategy_change).pack(anchor=tk.W)

        # 模块勾选
        modules_frame = ttk.LabelFrame(config_frame, text="功能模块", padding=10)
        modules_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ttk.Checkbutton(modules_frame, text="子域名枚举", variable=self.subdomain_var).pack(anchor=tk.W)
        ttk.Checkbutton(modules_frame, text="网络空间测绘 (FOFA)", variable=self.cyberspace_var).pack(anchor=tk.W)
        ttk.Checkbutton(modules_frame, text="端口/资产扫描", variable=self.portscan_var).pack(anchor=tk.W)
        ttk.Checkbutton(modules_frame, text="Web指纹识别", variable=self.fingerprint_var).pack(anchor=tk.W)
        ttk.Checkbutton(modules_frame, text="目录扫描", variable=self.dirscan_var).pack(anchor=tk.W)

        # POC扫描行（带分类选择）
        poc_row = ttk.Frame(modules_frame)
        poc_row.pack(fill=tk.X, anchor=tk.W)
        ttk.Checkbutton(poc_row, text="POC漏洞扫描", variable=self.pocscan_var,
                       command=self._update_poc_categories).pack(side=tk.LEFT)
        ttk.Label(poc_row, text="分类:").pack(side=tk.LEFT, padx=(10, 2))
        self.poc_category_var = tk.StringVar(value="全部")
        self.poc_category_combo = ttk.Combobox(poc_row, textvariable=self.poc_category_var,
                                               values=["全部"], width=18, state="readonly")
        self.poc_category_combo.pack(side=tk.LEFT)
        # 初始化时更新分类
        self._update_poc_categories()

        ttk.Checkbutton(modules_frame, text="弱口令爆破 (默认关闭)", variable=self.brute_var).pack(anchor=tk.W)

        # ========== 按钮区域 ==========
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=(0, 5))
        self.start_btn = ttk.Button(btn_frame, text="▶ 开始收集", style="Start.TButton", command=self._start_scan)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.stop_btn = ttk.Button(btn_frame, text="⏹ 停止", command=self._stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.reset_btn = ttk.Button(btn_frame, text="🔄 重置", command=self._reset_scan, state=tk.NORMAL)
        self.reset_btn.pack(side=tk.LEFT)

        # ========== 实时统计面板 ==========
        stats_frame = ttk.LabelFrame(parent, text="📊 实时收集统计", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 5))

        # 第一行统计
        row1 = ttk.Frame(stats_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="子域名:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_subdomains, style="StatValue.TLabel", foreground="blue").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="IP地址:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_ips, style="StatValue.TLabel", foreground="blue").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="资产数:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_assets, style="StatValue.TLabel", foreground="green").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="开放端口:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_ports, style="StatValue.TLabel", foreground="green").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="指纹:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_fingerprints, style="StatValue.TLabel", foreground="purple").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="目录:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_dirhits, style="StatValue.TLabel", foreground="orange").pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(row1, text="漏洞:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row1, textvariable=self.stat_vulns, style="StatValue.TLabel", foreground="red").pack(side=tk.LEFT)

        # 第二行 - 框架信息
        row2 = ttk.Frame(stats_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="识别框架:", style="Stat.TLabel").pack(side=tk.LEFT)
        ttk.Label(row2, textvariable=self.stat_frameworks, style="StatValue.TLabel", foreground="darkgreen", wraplength=800).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ========== 日志区域 ==========
        log_frame = ttk.LabelFrame(parent, text="执行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _build_toolbox_tab(self, parent):
        """构建工具箱标签页。"""
        ttk.Label(parent, text="以下工具为独立GUI程序，点击启动后需手动操作", foreground="gray").pack(anchor=tk.W, pady=(0, 10))

        tools_grid = ttk.Frame(parent)
        tools_grid.pack(fill=tk.BOTH, expand=True)

        gui_tools = [
            ("🌐 FOFA Viewer", "fofaviewer", "FOFA/Hunter/Quake 网络空间测绘查询"),
            ("🔍 Fine", "fine", "多测绘引擎资产搜索、ICP备案、企业信息"),
            ("📁 Scandir 3.0", "dirscan_3", "JavaFX 目录/后台/备份文件扫描"),
            ("📂 御剑目录扫描", "yjdirscan", "经典 Windows 目录扫描器"),
            ("❄️ 雪影 SnowShadow", "leiying", "综合渗透工具箱"),
            ("🐻 北极熊 Polar bear", "bjx11", "综合扫描：端口、目录、漏洞、XSS"),
            ("🔎 WebFinder", "webfinder", "JavaFX 端口扫描"),
        ]

        for i, (name, tool_id, desc) in enumerate(gui_tools):
            row, col = divmod(i, 2)
            frame = ttk.LabelFrame(tools_grid, text=name, padding=10)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            ttk.Label(frame, text=desc, foreground="gray").pack(anchor=tk.W)
            ttk.Button(frame, text="启动", style="Tool.TButton",
                      command=lambda tid=tool_id: self._launch_gui_tool(tid)).pack(anchor=tk.E, pady=(5, 0))

        tools_grid.columnconfigure(0, weight=1)
        tools_grid.columnconfigure(1, weight=1)

    def _build_settings_tab(self, parent):
        """构建设置标签页。"""
        # 速率限制设置
        rate_frame = ttk.LabelFrame(parent, text="速率限制 (防检测)", padding=10)
        rate_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(rate_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="并发工具数:").pack(side=tk.LEFT)
        ttk.Spinbox(row1, from_=1, to=5, textvariable=self.concurrent_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="(同时运行的外部工具数量)").pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(rate_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="工具间隔(秒):").pack(side=tk.LEFT)
        ttk.Spinbox(row2, from_=1.0, to=30.0, increment=0.5, textvariable=self.interval_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="(每个工具执行后的等待时间)").pack(side=tk.LEFT, padx=5)

        row3 = ttk.Frame(rate_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="工具线程数:").pack(side=tk.LEFT)
        ttk.Spinbox(row3, from_=10, to=1000, increment=50, textvariable=self.threads_var, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Label(row3, text="(传递给工具的并发线程数，越低越隐蔽)").pack(side=tk.LEFT, padx=5)

        # API Key 设置
        api_frame = ttk.LabelFrame(parent, text="API Key 配置", padding=10)
        api_frame.pack(fill=tk.X, pady=(0, 10))

        self.api_entries = {}
        api_keys = [
            ("fofa_email", "FOFA 邮箱", "FOFA账号邮箱"),
            ("fofa_key", "FOFA Key", "已配置: " + self.config.get("apikeys.fofa_key", "")[:8] + "..."),
            ("hunter_key", "Hunter Key", ""),
            ("quake_key", "Quake Key", ""),
            ("shodan_key", "Shodan Key", ""),
            ("zoomeye_key", "ZoomEye Key", ""),
        ]

        for i, (key, label, hint) in enumerate(api_keys):
            row, col = divmod(i, 2)
            frame = ttk.Frame(api_frame)
            frame.grid(row=row, column=col, padx=5, pady=2, sticky="ew")
            ttk.Label(frame, text=f"{label}:").pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=25, show="*" if "key" in key.lower() else "")
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, self.config.get(f"apikeys.{key}", ""))
            self.api_entries[key] = entry
            if hint:
                ttk.Label(frame, text=hint, foreground="gray", font=("微软雅黑", 8)).pack(side=tk.LEFT)

        api_frame.columnconfigure(0, weight=1)
        api_frame.columnconfigure(1, weight=1)

        ttk.Button(parent, text="💾 保存设置", command=self._save_settings).pack(anchor=tk.E, pady=10)

    def _on_strategy_change(self):
        """策略切换时更新模块勾选。"""
        strategy = self.strategy_var.get()
        presets = {
            "全面": {"subdomain": True, "cyberspace": True, "portscan": True, "fingerprint": True, "dirscan": False, "brute": True},
            "快速": {"subdomain": True, "cyberspace": True, "portscan": True, "fingerprint": False, "dirscan": False, "brute": False},
            "仅子域名": {"subdomain": True, "cyberspace": False, "portscan": False, "fingerprint": False, "dirscan": False, "brute": False},
            "仅端口": {"subdomain": False, "cyberspace": False, "portscan": True, "fingerprint": True, "dirscan": False, "brute": False},
            "仅目录": {"subdomain": False, "cyberspace": False, "portscan": False, "fingerprint": False, "dirscan": True, "brute": False},
        }
        if strategy in presets:
            p = presets[strategy]
            self.subdomain_var.set(p["subdomain"])
            self.cyberspace_var.set(p["cyberspace"])
            self.portscan_var.set(p["portscan"])
            self.fingerprint_var.set(p["fingerprint"])
            self.dirscan_var.set(p["dirscan"])
            self.brute_var.set(p["brute"])

    def _update_poc_categories(self):
        """更新POC分类下拉框，显示各分类数量"""
        try:
            from core.pocscanner import PocLoader
            loader = PocLoader()
            stats = loader.get_stats()
            categories = stats.get("by_category", {})

            # 构建带数量的选项列表
            options = ["全部"]
            # 分类名映射（英文->中文）
            name_map = {
                "CNVD": "CNVD",
                "CVE": "CVE",
                "default-pwd": "默认密码",
                "disclosure": "信息泄露",
                "fingerprinting": "指纹识别",
                "unauthorized": "未授权访问",
                "vulnerability": "漏洞",
                "version": "版本",
            }
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                cn_name = name_map.get(cat, cat)
                options.append(f"{cn_name} ({count})")

            self.poc_category_combo["values"] = options
        except Exception:
            # 如果加载失败，使用默认值
            self.poc_category_combo["values"] = ["全部", "CNVD", "CVE", "默认密码",
                                                 "信息泄露", "指纹识别", "未授权访问", "漏洞", "版本"]

    def _start_scan(self):
        """
        开始扫描 - 智能判断输入内容：
        - 只输入目标 → 扫描目标
        - 只输入企业 → 企业信息收集
        - 都输入 → 先企业收集，再扫描目标
        """
        target = self.target_var.get().strip()
        company = self.company_var.get().strip()

        # 至少需要输入一个
        if not target and not company:
            messagebox.showwarning("警告", "请输入目标或企业名称（至少一个）")
            return

        # 保存到历史记录
        if target:
            self._add_to_history("target", target, self.target_history, self.target_combo)
        if company:
            self._add_to_history("company", company, self.company_history, self.company_combo)

        self._save_settings_to_config()

        # 判断扫描模式
        if target and company:
            # 都输入：先企业收集，再扫描目标
            scan_mode = "both"
            self._log(f"[RedTeam] 模式: 企业收集 + 目标扫描")
        elif company:
            # 只输入企业
            scan_mode = "company"
            self._log(f"[RedTeam] 模式: 企业信息收集")
        else:
            # 只输入目标
            scan_mode = "target"
            self._log(f"[RedTeam] 模式: 目标扫描")

        # 构建策略
        strategy = {
            "subdomain": self.subdomain_var.get(),
            "cyberspace": self.cyberspace_var.get(),
            "portscan": self.portscan_var.get(),
            "fingerprint": self.fingerprint_var.get(),
            "dirscan": self.dirscan_var.get(),
            "pocscan": self.pocscan_var.get(),
            # 去掉括号中的数量，如 "CNVD (1523)" -> "CNVD"
            "poc_category": self.poc_category_var.get().split(" (")[0] if " (" in self.poc_category_var.get() else self.poc_category_var.get(),
            "brute": self.brute_var.get(),
        }

        # 如果有企业名称，添加企业模式
        if company:
            strategy["company_mode"] = True
            strategy["company_name"] = company

        # 更新UI状态
        self._is_running = True
        self._update_ui_state(running=True)

        if scan_mode == "company":
            self.status_var.set(f"企业信息收集中: {company}...")
        elif scan_mode == "both":
            self.status_var.set(f"企业收集 + 目标扫描: {company} / {target}")
        else:
            self.status_var.set(f"扫描中: {target}")

        self.log_text.delete(1.0, tk.END)
        self._reset_stats()

        if company:
            self._log(f"[RedTeam] 企业名称: {company}")
        if target:
            self._log(f"[RedTeam] 扫描目标: {target}")

        self.workflow.on_stats_update = self._update_stats

        def run_workflow():
            try:
                if scan_mode == "company":
                    # 只输入企业：企业信息收集
                    self.workflow.run(company, strategy)
                elif scan_mode == "both":
                    # 都输入：先企业收集，再扫描目标
                    self.workflow.run(target, strategy, company_name=company)
                else:
                    # 只输入目标：直接扫描
                    self.workflow.run(target, strategy)
            except Exception as e:
                self._log(f"[错误] {e}")
            finally:
                self._is_running = False
                self.root.after(0, self._on_scan_complete)

        thread = threading.Thread(target=run_workflow, daemon=True)
        thread.start()

    def _start_company_scan(self):
        """开始企业信息收集（保留兼容性）。"""
        company = self.company_var.get().strip()
        if not company:
            messagebox.showwarning("警告", "请输入企业名称")
            return

        # 调用统一的开始扫描方法
        self._start_scan()

    def _on_scan_complete(self):
        """扫描完成回调。"""
        self._update_ui_state(running=False)
        if not self.workflow._cancelled:
            self.status_var.set("完成")
            self._log("[RedTeam] ✅ 信息收集完成")
            messagebox.showinfo("完成", "信息收集已完成，请查看报告")
        else:
            self.status_var.set("已停止")

    def _stop_scan(self):
        """停止扫描。"""
        if self._is_running:
            if messagebox.askyesno("确认", "确定要停止当前扫描吗？"):
                self.workflow.cancel()
                self._is_running = False
                self._update_ui_state(running=False)
                self.status_var.set("已停止")
                self._log("[RedTeam] ⏹ 用户停止了扫描")

    def _reset_scan(self):
        """重置扫描状态。"""
        if self._is_running:
            messagebox.showwarning("警告", "请先停止当前扫描")
            return

        self.workflow._cancelled = False
        self.workflow._running = False
        self.workflow.runner.reset_cancel()

        self.target_var.set("")
        self.company_var.set("")
        self.log_text.delete(1.0, tk.END)
        self._reset_stats()
        self.status_var.set("就绪")
        self._update_ui_state(running=False)
        self.target_combo.focus_set()
        self._log("[RedTeam] 🔄 已重置，可以输入新目标")

    def _reset_stats(self):
        """重置统计数据。"""
        self.stat_subdomains.set("0")
        self.stat_ips.set("0")
        self.stat_assets.set("0")
        self.stat_ports.set("0")
        self.stat_fingerprints.set("0")
        self.stat_frameworks.set("")
        self.stat_dirhits.set("0")
        self.stat_vulns.set("0")

    def _update_stats(self, stats: dict):
        """更新统计数据（从工作流回调）。"""
        def do_update():
            if "subdomains" in stats:
                self.stat_subdomains.set(str(stats["subdomains"]))
            if "ips" in stats:
                self.stat_ips.set(str(stats["ips"]))
            if "assets" in stats:
                self.stat_assets.set(str(stats["assets"]))
            if "ports" in stats:
                self.stat_ports.set(str(stats["ports"]))
            if "fingerprints" in stats:
                self.stat_fingerprints.set(str(stats["fingerprints"]))
            if "frameworks" in stats:
                self.stat_frameworks.set(stats["frameworks"])
            if "dirhits" in stats:
                self.stat_dirhits.set(str(stats["dirhits"]))
            if "vulns" in stats:
                self.stat_vulns.set(str(stats["vulns"]))
        self.root.after(0, do_update)

    def _update_ui_state(self, running: bool):
        """更新UI按钮状态。"""
        if running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.DISABLED)
            self.target_combo.config(state=tk.DISABLED)
            self.company_combo.config(state=tk.DISABLED)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.reset_btn.config(state=tk.NORMAL)
            self.target_combo.config(state=tk.NORMAL)
            self.company_combo.config(state=tk.NORMAL)

    def _log(self, msg: str):
        """向日志区域追加消息。"""
        def append():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_text.see(tk.END)
        self.root.after(0, append)

    def _import_targets(self):
        """从文件导入目标。"""
        filepath = filedialog.askopenfilename(
            title="选择目标文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    targets = [line.strip() for line in f if line.strip()]
                if targets:
                    self.target_var.set(targets[0])
                    messagebox.showinfo("导入成功", f"已导入 {len(targets)} 个目标（当前使用第一个）")
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")

    def _launch_gui_tool(self, tool_id: str):
        """启动GUI工具。"""
        self._log(f"启动工具: {tool_id}")
        result = self.workflow.launch_gui_tool(tool_id)
        if result.get("success"):
            self._log(f"工具 {tool_id} 已启动 (PID={result.get('pid')})")
        else:
            self._log(f"工具 {tool_id} 启动失败: {result.get('error')}")

    def _save_settings(self):
        """保存设置。"""
        self._save_settings_to_config()
        self.config.save()
        messagebox.showinfo("保存成功", "设置已保存")

    def _save_settings_to_config(self):
        """将UI设置保存到配置对象。"""
        self.config.set("rate_limit.concurrent_tools", self.concurrent_var.get())
        self.config.set("rate_limit.tool_interval_seconds", self.interval_var.get())
        self.config.set("rate_limit.tool_threads", self.threads_var.get())
        for key, entry in self.api_entries.items():
            self.config.set(f"apikeys.{key}", entry.get())

    def _open_report_dir(self):
        """打开报告目录。"""
        report_dir = str(self.config.output_dir)
        if os.path.exists(report_dir):
            if sys.platform == "win32":
                os.startfile(report_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", report_dir])
            else:
                subprocess.run(["xdg-open", report_dir])
        else:
            messagebox.showinfo("提示", "报告目录尚不存在，执行扫描后会自动创建")

    # ==================== 历史记录管理 ====================

    def _load_history(self, history_type: str) -> list:
        """加载历史记录。"""
        history_file = self.config.data_dir / f"history_{history_type}.json"
        if history_file.exists():
            try:
                import json
                with open(history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_history(self, history_type: str, history: list):
        """保存历史记录。"""
        history_file = self.config.data_dir / f"history_{history_type}.json"
        try:
            import json
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log(f"[历史记录] 保存失败: {e}")

    def _add_to_history(self, history_type: str, value: str, history_list: list, combo_widget):
        """添加到历史记录。"""
        if not value:
            return

        # 移除已存在的相同记录
        if value in history_list:
            history_list.remove(value)

        # 添加到开头
        history_list.insert(0, value)

        # 限制历史记录数量（最多50条）
        if len(history_list) > 50:
            history_list = history_list[:50]

        # 保存到文件
        self._save_history(history_type, history_list)

        # 更新下拉框
        combo_widget["values"] = history_list

    def _clear_target_history(self):
        """清空目标历史记录。"""
        if messagebox.askyesno("确认", "确定要清空目标历史记录吗？"):
            self.target_history = []
            self._save_history("target", self.target_history)
            self.target_combo["values"] = self.target_history
            self._log("[历史记录] 目标历史记录已清空")

    def _clear_company_history(self):
        """清空企业历史记录。"""
        if messagebox.askyesno("确认", "确定要清空企业历史记录吗？"):
            self.company_history = []
            self._save_history("company", self.company_history)
            self.company_combo["values"] = self.company_history
            self._log("[历史记录] 企业历史记录已清空")

    def run(self):
        """启动GUI主循环。"""
        self.workflow.log = self._log
        self.root.mainloop()
