#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 工作流编排引擎
根据目标类型自动选择并执行信息收集步骤，管理依赖关系，聚合结果。
"""

import os
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, Dict, Any, List

from .config import Config
from .target import Target
from .runner import ToolRunner
from .parsers import parse_tool_output
from .fingerprint import FingerprintEngine
from .portscan import PortScanner, get_common_ports, get_web_ports
from .company import CompanyRecon
from .pocscanner import PocScanner
from .connectivity import ConnectivityChecker
from .report import ReportGenerator
from tools.registry import TOOLS, WORKFLOW_STEPS


class Workflow:
    """一键信息收集工作流。"""

    def __init__(self, config: Config, log_callback: Optional[Callable[[str], None]] = None):
        self.config = config
        self.log = log_callback or (lambda msg: print(msg))
        self.runner = ToolRunner(config)
        self._running = False
        self._cancelled = False
        self.on_stats_update = None  # 统计更新回调

    def cancel(self):
        """取消工作流。"""
        self._cancelled = True
        self.runner.cancel()

    def is_running(self) -> bool:
        return self._running

    def run(self, target_raw: str, strategy: Dict[str, bool] = None, company_name: str = None) -> Dict[str, Any]:
        """
        执行一键信息收集。

        Args:
            target_raw: 目标字符串（域名/IP/CIDR/URL）
            strategy: 策略覆盖，如 {"subdomain": True, "brute": False}
            company_name: 企业名称（可选，如果有则执行企业信息收集）

        Returns:
            统一结果字典
        """
        self._running = True
        self._cancelled = False
        self.runner.reset_cancel()

        # 检查是否为企业模式
        if not company_name:
            company_name = strategy.get("company_name", "") if strategy else ""
        company_mode = strategy.get("company_mode", False) if strategy else False

        company_results = None

        if company_name and target_raw and target_raw != company_name:
            # 同时有目标和企业名称：先企业收集，再扫描目标
            self.log(f"{'='*60}")
            self.log(f"[模式] 企业收集 + 目标扫描")
            self.log(f"[企业] {company_name}")
            self.log(f"[目标] {target_raw}")
            self.log(f"{'='*60}")

            # 先执行企业信息收集
            _, company_results = self._company_recon(company_name, strategy)

            # 使用用户输入的目标
            target = Target(target_raw)

        elif company_name and (not target_raw or target_raw == company_name):
            # 只有企业名称：企业信息收集模式
            self.log(f"{'='*60}")
            self.log(f"[模式] 企业信息收集")
            self.log(f"[企业] {company_name}")
            self.log(f"{'='*60}")

            target, company_results = self._company_recon(company_name, strategy)
            if not target:
                self.log("[企业] 未能发现有效目标，尝试常见域名后缀")
                for suffix in ['.com', '.cn', '.net']:
                    try:
                        test_domain = company_name.replace('有限公司', '').replace('科技', '') + suffix
                        target = Target(test_domain)
                        break
                    except:
                        pass
                if not target:
                    target = Target(company_name + ".com")

        else:
            # 只有目标：普通扫描模式
            self.log(f"{'='*60}")
            self.log(f"[模式] 目标扫描")
            self.log(f"[目标] {target_raw}")
            self.log(f"{'='*60}")
            target = Target(target_raw)

        self.log(f"{'='*60}")
        self.log(f"最终目标: {target}")
        self.log(f"类型: {target.type}")
        self.log(f"{'='*60}")

        # 连通性检测
        if target_raw and target_raw != company_name:
            self.log(f"[连通性] 检测目标连通性...")
            checker = ConnectivityChecker(timeout=5, log_callback=self.log)
            conn_result = checker.check(target.host)

            results_connectivity = conn_result

            if not conn_result["is_alive"]:
                error_msg = f"目标 {target.host} ({conn_result.get('ip', '')}) 无法连通: {conn_result.get('error', '未知错误')}"
                self.log(f"[连通性] {error_msg}")
                self.log(f"[连通性] 扫描终止")

                # 返回结果
                results = {
                    "target": target.raw,
                    "target_type": target.type,
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "output_dir": "",
                    "steps": {},
                    "subdomains": [],
                    "ips": [],
                    "assets": [],
                    "fingerprints": [],
                    "dir_hits": [],
                    "brute_findings": [],
                    "poc_vulns": [],
                    "connectivity": conn_result,
                    "errors": [error_msg],
                    "is_alive": False
                }
                self._running = False
                return results
            else:
                self.log(f"[连通性] 目标连通正常")
                if conn_result.get("ping", {}).get("alive"):
                    self.log(f"[连通性] Ping: {conn_result['ping']['time_ms']}ms")
                if conn_result.get("http", {}).get("alive"):
                    self.log(f"[连通性] HTTP: {conn_result['http']['status']} - {conn_result['http'].get('title', '')}")

        # 创建输出目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = target.host.replace(".", "_").replace("/", "_").replace(":", "_")
        output_dir = self.config.output_dir / f"{timestamp}_{safe_name}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # 结果聚合
        results = {
            "target": target.raw,
            "target_type": target.type,
            "timestamp": timestamp,
            "output_dir": str(output_dir),
            "steps": {},
            "subdomains": [],
            "ips": [],
            "assets": [],
            "fingerprints": [],
            "dir_hits": [],
            "brute_findings": [],
            "errors": [],
            "company_info": None  # 企业信息
        }

        # 如果是企业模式，合并企业收集结果
        if company_mode and company_results:
            results["company_info"] = company_results
            results["subdomains"] = [{"subdomain": d, "ip": "", "status": "", "title": ""} for d in company_results.get("domains", [])]
            results["ips"] = company_results.get("ips", [])
            results["assets"].extend(company_results.get("assets", []))

        try:
            # 执行工作流步骤
            for step_def in WORKFLOW_STEPS:
                if self._cancelled:
                    self.log("[Workflow] 已取消")
                    break

                step_name = step_def["step"]
                step_tools = step_def["tools"]
                optional = step_def.get("optional", False)

                # 检查策略是否启用
                strategy_cfg = self.config.get(f"strategies.{step_name}", {})
                if strategy and step_name in strategy:
                    enabled = strategy[step_name]
                else:
                    enabled = strategy_cfg.get("enable", not optional)

                if not enabled:
                    self.log(f"[Workflow] 跳过: {step_name} (已禁用)")
                    continue

                # 检查目标类型是否适用
                if step_name == "subdomain" and not target.needs_subdomain:
                    self.log(f"[Workflow] 跳过: {step_name} (非域名目标)")
                    continue

                if step_name == "dirscan" and not target.needs_dirscan:
                    self.log(f"[Workflow] 跳过: {step_name} (不支持目录扫描)")
                    continue

                # 执行工具
                for tool_id in step_tools:
                    if self._cancelled:
                        break

                    tool_info = TOOLS.get(tool_id, {})
                    if not tool_info:
                        continue

                    # 检查 API Key 需求
                    if tool_info.get("requires_key"):
                        key_type = tool_info["requires_key"]
                        if key_type == "fofa" and not self.config.fofa_key_ok():
                            self.log(f"[Workflow] 跳过: {tool_id} (FOFA Key 未配置)")
                            continue

                    # 构建命令行并执行
                    step_result = self._execute_tool(
                        tool_id, tool_info, target, output_dir, strategy_cfg
                    )
                    results["steps"][tool_id] = step_result

                    # 聚合数据
                    self._aggregate_results(results, tool_id, step_result, target)

                    # 步骤间隔
                    if not self._cancelled:
                        interval = self.config.get("rate_limit.tool_interval_seconds", 3.0)
                        self.log(f"[Workflow] 等待 {interval}s 后执行下一步...")
                        time.sleep(interval)

            # 内置端口扫描（对发现的IP进行深度端口扫描）
            if not self._cancelled and strategy.get("portscan", True):
                self._run_builtin_portscan(target, results, output_dir, strategy)

            # 内置指纹识别（对发现的资产进行深度指纹识别）
            if not self._cancelled and self.config.get("strategies.fingerprint.enable", True):
                self._run_builtin_fingerprint(target, results, output_dir)

            # POC漏洞扫描（对发现的Web资产进行漏洞检测）
            if not self._cancelled and strategy.get("pocscan", False):
                self._run_poc_scan(target, results, output_dir)

        except Exception as e:
            self.log(f"[Workflow] 异常: {e}")
            results["errors"].append(str(e))
        finally:
            self._running = False

        # 生成报告
        self.log(f"{'='*60}")
        self.log(f"[Workflow] 工作流完成，生成报告...")

        report_gen = ReportGenerator(self.config)
        report_path = report_gen.generate(results, output_dir)
        results["report_path"] = str(report_path)

        self.log(f"[Workflow] 报告已生成: {report_path}")
        self.log(f"[Workflow] 输出目录: {output_dir}")
        self.log(f"{'='*60}")

        return results

    def _company_recon(self, company_name: str, strategy: dict) -> tuple:
        """
        企业信息收集：通过FOFA搜索企业相关资产，提取域名和IP。
        增强版：包含ICP备案、Whois、GitHub、邮箱收集。

        Returns:
            (Target, dict) - 主目标和企业收集结果
        """
        self.log(f"[企业信息收集] 开始全面收集: {company_name}")

        # 1. FOFA资产搜索
        fofa_results = self._fofa_search(company_name)

        # 2. 使用CompanyRecon模块进行完整收集
        recon = CompanyRecon(self.config, self.log)
        company_results = recon.collect_all(company_name, fofa_results)

        # 3. 选择主目标（优先使用域名）
        target = None
        domains = company_results.get("domains", [])
        ips = company_results.get("ips", [])

        if domains:
            main_domain = domains[0]
            self.log(f"[企业信息收集] 主目标域名: {main_domain}")
            target = Target(main_domain)
        elif ips:
            main_ip = ips[0]
            self.log(f"[企业信息收集] 主目标IP: {main_ip}")
            target = Target(main_ip)
        else:
            self.log(f"[企业信息收集] 未发现有效资产，尝试使用企业名称作为域名")
            # 尝试常见域名后缀
            for suffix in ['.com', '.cn', '.net', '.org']:
                test_domain = company_name.replace('有限公司', '').replace('科技', '') + suffix
                try:
                    socket.gethostbyname(test_domain)
                    target = Target(test_domain)
                    company_results["domains"].append(test_domain)
                    self.log(f"[企业信息收集] 发现域名: {test_domain}")
                    break
                except:
                    pass

        # 保存结果
        if target:
            self._company_results = company_results

        return target, company_results

    def _fofa_search(self, company_name: str) -> dict:
        """FOFA资产搜索。"""
        self.log(f"[FOFA] 搜索企业资产: {company_name}")

        fofa_queries = [
            f'org="{company_name}"',
            f'cert="{company_name}"',
            f'title="{company_name}"',
            f'icp="{company_name}"',
        ]

        all_domains = set()
        all_ips = set()
        all_assets = []

        goon_path = self.config.tool_path("goon/goon3_win_amd64.exe")
        if not goon_path.exists():
            self.log(f"[FOFA] goon工具不存在: {goon_path}")
            return {"domains": [], "ips": [], "assets": [], "fofa_queries": fofa_queries}

        for query in fofa_queries:
            if self._cancelled:
                break

            self.log(f"[FOFA] 查询: {query}")

            output_file = self.config.output_dir / f"company_{company_name}" / "fofa_results.txt"
            output_file.parent.mkdir(parents=True, exist_ok=True)

            cmd = f'goon3_win_amd64.exe -key \'{query}\' -mode fofa -num 100 -ofile "{output_file}"'
            cwd = str(self.config.tool_path("goon"))

            result = self.runner.run(
                tool_id="company_fofa",
                cmd=cmd,
                cwd=cwd,
                timeout=120,
                log_callback=self.log
            )

            if result.get("success") and output_file.exists():
                try:
                    with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith("#"):
                                continue

                            import re
                            domain_match = re.search(r'([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}', line)
                            if domain_match:
                                domain = domain_match.group(0)
                                if not any(x in domain for x in ['fofa.info', 'qianxin.com', 'example.com']):
                                    all_domains.add(domain)
                                    all_assets.append({"type": "domain", "source": "fofa", "value": domain, "query": query})

                            ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
                            if ip_match:
                                ip = ip_match.group(1)
                                if not ip.startswith(('0.', '127.', '255.')):
                                    all_ips.add(ip)
                                    all_assets.append({"type": "ip", "source": "fofa", "value": ip, "query": query})
                except Exception as e:
                    self.log(f"[FOFA] 解析结果失败: {e}")

            time.sleep(2)

        return {
            "domains": list(all_domains),
            "ips": list(all_ips),
            "assets": all_assets,
            "fofa_queries": fofa_queries
        }

    def _execute_tool(
        self,
        tool_id: str,
        tool_info: dict,
        target: Target,
        output_dir: Path,
        strategy_cfg: dict
    ) -> Dict[str, Any]:
        """执行单个工具并返回结果。"""
        step_output_dir = output_dir / tool_id
        step_output_dir.mkdir(parents=True, exist_ok=True)

        # 构建命令参数
        args_map = {
            "target": target.portscan_target if tool_id in ("goon_webscan", "golin_scan") else target.host,
            "host": target.host,
            "ip": target.ip or target.host,
            "url": target.dirscan_url,
            "cidr": target.cidr or target.host,
            "output": str(output_dir),
            "threads": str(strategy_cfg.get("threads", self.config.get("rate_limit.tool_threads", 100))),
            "timeout": str(strategy_cfg.get("timeout", self.config.get("rate_limit.timeout", 300))),
            "code": strategy_cfg.get("code", self.config.get("strategies.dirscan.code", "200,302,403")),
            "max_results": str(strategy_cfg.get("max_results", self.config.get("strategies.cyberspace.max_results", 100))),
            "dict": str(self.config.tool_path(strategy_cfg.get("dict", self.config.get("strategies.dirscan.dict", "dirscan_3.0/dict/全部.txt")))),
        }

        # 构建完整命令
        args = tool_info["args_tpl"]
        for key, value in args_map.items():
            args = args.replace(f"{{{key}}}", str(value))

        cmd = f"{tool_info['entry']} {args}"
        cwd = str(self.config.tool_path(tool_info["cwd"]))

        # 执行
        timeout = int(tool_info.get("timeout", 300))
        result = self.runner.run(
            tool_id=tool_id,
            cmd=cmd,
            cwd=cwd,
            timeout=timeout,
            log_callback=self.log
        )

        # 解析输出
        parsed = parse_tool_output(tool_id, str(step_output_dir), target.host)
        result["parsed"] = parsed

        return result

    def _aggregate_results(self, results: dict, tool_id: str, step_result: dict, target: Target):
        """聚合工具结果到统一结果中。"""
        parsed = step_result.get("parsed", {})

        if tool_id == "oneforall":
            results["subdomains"] = parsed.get("subdomains", [])
            results["ips"] = list(set(results["ips"] + parsed.get("ips", [])))

        elif tool_id in ("goon_webscan", "golin_scan"):
            results["assets"].extend(parsed.get("assets", []))

        elif tool_id == "goon_fofa":
            results["assets"].extend(parsed.get("assets", []))

        elif tool_id == "golin_dirsearch":
            results["dir_hits"].extend(parsed.get("hits", []))

        elif tool_id == "golin_brute":
            results["brute_findings"].extend(parsed.get("findings", []))

        # 更新统计
        self._emit_stats(results)

    def _run_builtin_portscan(self, target: Target, results: dict, output_dir: Path, strategy: dict):
        """运行内置端口扫描模块。"""
        self.log(f"[PortScan] 启动内置端口扫描...")

        # 收集需要扫描的IP
        ips_to_scan = []

        # 目标IP
        if target.ip:
            ips_to_scan.append(target.ip)
        elif target.type == "domain":
            ips_to_scan.append(target.host)

        # 从结果中收集IP（最多10个）
        for ip in results.get("ips", [])[:10]:
            if ip not in ips_to_scan:
                ips_to_scan.append(ip)

        if not ips_to_scan:
            self.log(f"[PortScan] 没有需要扫描的IP")
            return

        self.log(f"[PortScan] 待扫描目标: {len(ips_to_scan)} 个")

        # 执行端口扫描
        try:
            timeout = self.config.get("rate_limit.timeout", 2)
            threads = strategy.get("threads", self.config.get("rate_limit.tool_threads", 100))

            scanner = PortScanner(timeout=timeout, max_threads=threads)

            for i, ip in enumerate(ips_to_scan, 1):
                if self._cancelled:
                    break

                self.log(f"[PortScan] ({i}/{len(ips_to_scan)}) 扫描: {ip}")

                # 使用常见端口列表
                ports = get_common_ports()
                scan_result = scanner.scan(ip, ports, log_callback=self.log)

                # 将端口扫描结果添加到资产列表
                for port_info in scan_result.get("open_ports", []):
                    asset = {
                        "type": "port",
                        "ip": ip,
                        "port": port_info["port"],
                        "state": port_info["state"],
                        "service": port_info["service"],
                        "banner": port_info.get("banner", ""),
                        "source": "builtin_portscan"
                    }
                    results["assets"].append(asset)

                # 保存原始结果
                results.setdefault("portscan_results", []).append(scan_result)

                # 间隔
                if i < len(ips_to_scan):
                    time.sleep(1)

        except Exception as e:
            self.log(f"[PortScan] 端口扫描异常: {e}")
            results["errors"].append(f"端口扫描: {e}")

        self.log(f"[PortScan] 端口扫描完成")
        self._emit_stats(results)

    def _run_builtin_fingerprint(self, target: Target, results: dict, output_dir: Path):
        """运行内置指纹识别模块。"""
        self.log(f"[Fingerprint] 启动内置框架指纹识别...")

        # 收集需要识别的URL
        urls_to_scan = []

        # 目标URL
        if target.type == "url":
            urls_to_scan.append(target.url)
        elif target.type in ("domain", "ip"):
            urls_to_scan.append(f"http://{target.host}")
            urls_to_scan.append(f"https://{target.host}")

        # 从子域名中收集URL（最多20个）
        for sub in results.get("subdomains", [])[:20]:
            subdomain = sub.get("subdomain", "")
            if subdomain:
                urls_to_scan.append(f"http://{subdomain}")

        # 从资产中收集Web URL
        for asset in results.get("assets", []):
            if asset.get("type") == "web" and asset.get("url"):
                urls_to_scan.append(asset["url"])

        # 去重
        urls_to_scan = list(set(urls_to_scan))[:30]  # 最多30个

        if not urls_to_scan:
            self.log(f"[Fingerprint] 没有需要识别的目标URL")
            return

        self.log(f"[Fingerprint] 待识别目标: {len(urls_to_scan)} 个")

        # 执行指纹识别
        try:
            timeout = self.config.get("rate_limit.timeout", 10)
            engine = FingerprintEngine(timeout=timeout)

            for i, url in enumerate(urls_to_scan, 1):
                if self._cancelled:
                    break

                self.log(f"[Fingerprint] ({i}/{len(urls_to_scan)}) 识别: {url}")
                fp_result = engine.scan(url)

                if fp_result.get("error"):
                    self.log(f"[Fingerprint]   错误: {fp_result['error']}")
                else:
                    fps = fp_result.get("fingerprints", [])
                    if fps:
                        self.log(f"[Fingerprint]   发现 {len(fps)} 个指纹:")
                        for fp in fps:
                            self.log(f"[Fingerprint]     - {fp['name']} ({fp['category']})")
                    else:
                        self.log(f"[Fingerprint]   未识别到框架指纹")

                    results["fingerprints"].append(fp_result)

                # 间隔
                if i < len(urls_to_scan):
                    time.sleep(0.5)

        except Exception as e:
            self.log(f"[Fingerprint] 指纹识别异常: {e}")
            results["errors"].append(f"指纹识别: {e}")

        self.log(f"[Fingerprint] 指纹识别完成，共识别 {len(results['fingerprints'])} 个目标")
        self._emit_stats(results)

    def _emit_stats(self, results: dict):
        """发送统计数据到UI回调。"""
        if not self.on_stats_update:
            return

        # 提取框架名称
        frameworks = []
        for fp_data in results.get("fingerprints", []):
            for fp in fp_data.get("fingerprints", []):
                name = fp.get("name", "")
                if name and name not in frameworks:
                    frameworks.append(name)

        # 统计资产中的端口数
        ports = set()
        for asset in results.get("assets", []):
            port = asset.get("port", "")
            if port:
                ports.add(port)

        stats = {
            "subdomains": len(results.get("subdomains", [])),
            "ips": len(results.get("ips", [])),
            "assets": len(results.get("assets", [])),
            "ports": len(ports),
            "fingerprints": sum(len(fp.get("fingerprints", [])) for fp in results.get("fingerprints", [])),
            "frameworks": ", ".join(frameworks[:10]) if frameworks else "无",
            "dirhits": len(results.get("dir_hits", [])),
            "vulns": len(results.get("brute_findings", [])),
        }

        try:
            self.on_stats_update(stats)
        except Exception:
            pass

    def launch_gui_tool(self, tool_id: str) -> dict:
        """启动 GUI 工具。"""
        tool_info = TOOLS.get(tool_id, {})
        if not tool_info or tool_info.get("type") != "gui":
            return {"success": False, "error": f"未知 GUI 工具: {tool_id}"}

        entry = tool_info["entry"]
        cwd = str(self.config.tool_path(tool_info["cwd"]))

        return self.runner.run_gui_tool(tool_id, entry, cwd, log_callback=self.log)

    def _run_poc_scan(self, target: Target, results: dict, output_dir: Path):
        """运行 POC 漏洞扫描。"""
        self.log(f"[POC] 启动 POC 漏洞扫描...")

        # 获取 POC 扫描器统计
        scanner = PocScanner(self.config, log_callback=self.log)
        poc_stats = scanner.get_stats()
        self.log(f"[POC] 加载 {poc_stats.get('total', 0)} 个 POC")

        if poc_stats.get("total", 0) == 0:
            self.log(f"[POC] 没有可用的 POC 文件")
            return

        # 收集需要扫描的 URL
        urls_to_scan = []

        # 目标URL
        if target.type == "url":
            urls_to_scan.append(target.url)
        elif target.type in ("domain", "ip"):
            urls_to_scan.append(f"http://{target.host}")
            urls_to_scan.append(f"https://{target.host}")

        # 从资产中收集Web URL
        for asset in results.get("assets", []):
            if asset.get("type") == "web" and asset.get("url"):
                url = asset["url"]
                if url not in urls_to_scan:
                    urls_to_scan.append(url)

        # 限制扫描URL数量（避免时间过长）
        urls_to_scan = urls_to_scan[:5]

        if not urls_to_scan:
            self.log(f"[POC] 没有需要扫描的 Web 目标")
            return

        self.log(f"[POC] 待扫描目标: {len(urls_to_scan)} 个")
        for url in urls_to_scan:
            self.log(f"[POC]   - {url}")

        # 执行 POC 扫描
        all_vulns = []
        try:
            for i, url in enumerate(urls_to_scan, 1):
                if self._cancelled:
                    break

                self.log(f"[POC] ({i}/{len(urls_to_scan)}) 扫描: {url}")

                # 扫描（限制POC数量以加快速度）
                vulns = scanner.scan(url, poc_filter={"severity": "high"})
                all_vulns.extend(vulns)

                for vuln in vulns:
                    self.log(f"[POC]   [!] 发现漏洞: {vuln.get('name', 'Unknown')} [{vuln.get('severity', 'unknown')}]")

        except Exception as e:
            self.log(f"[POC] POC扫描异常: {e}")
            results["errors"].append(f"POC扫描: {e}")

        results["poc_vulns"] = all_vulns
        self.log(f"[POC] POC扫描完成，发现 {len(all_vulns)} 个漏洞")
        self._emit_stats(results)
