#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 输出解析器
解析各工具的输出文件，提取结构化数据。
"""

import csv
import re
import os
from pathlib import Path
from typing import List, Dict, Any


def parse_oneforall_csv(output_dir: str, target: str) -> Dict[str, Any]:
    """解析 OneForAll CSV 输出。"""
    result = {
        "tool": "oneforall",
        "subdomains": [],
        "ips": [],
        "total": 0
    }

    # 查找CSV文件
    csv_files = list(Path(output_dir).rglob("*.csv"))
    if not csv_files:
        return result

    for csv_file in csv_files:
        try:
            with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    subdomain = row.get("subdomain", "")
                    ip = row.get("ip", "")
                    status = row.get("status", "")
                    title = row.get("title", "")

                    if subdomain:
                        result["subdomains"].append({
                            "subdomain": subdomain,
                            "ip": ip,
                            "status": status,
                            "title": title
                        })
                        if ip and ip not in result["ips"]:
                            result["ips"].append(ip)
        except Exception as e:
            print(f"[Parser] 解析 OneForAll CSV 失败: {e}")

    result["total"] = len(result["subdomains"])
    return result


def parse_goon_text(output_file: str) -> Dict[str, Any]:
    """解析 Goon webscan 文本输出。"""
    result = {
        "tool": "goon",
        "assets": [],
        "total": 0
    }

    if not os.path.exists(output_file):
        return result

    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # Goon 输出格式示例：
                # [+] http://example.com:80 [200] [Example Site] [nginx]
                # [+] 192.168.1.1:22 [ssh] [OpenSSH 7.4]
                asset = _parse_goon_line(line)
                if asset:
                    result["assets"].append(asset)
    except Exception as e:
        print(f"[Parser] 解析 Goon 输出失败: {e}")

    result["total"] = len(result["assets"])
    return result


def _parse_goon_line(line: str) -> Dict[str, str]:
    """解析单行 Goon 输出。"""
    asset = {}

    # 尝试匹配 Web 格式：[+] URL [status] [title] [server]
    web_match = re.match(
        r"\[?\+?\]?\s*(https?://[\w\.\-]+(?::\d+)?)\s*\[(\d+)\]\s*\[([^\]]*)\]\s*\[([^\]]*)\]",
        line
    )
    if web_match:
        return {
            "url": web_match.group(1),
            "status": web_match.group(2),
            "title": web_match.group(3),
            "server": web_match.group(4),
            "type": "web"
        }

    # 尝试匹配服务格式：[+] IP:port [service] [banner]
    svc_match = re.match(
        r"\[?\+?\]?\s*([\d\.]+):(\d+)\s*\[(\w+)\]\s*(.*)",
        line
    )
    if svc_match:
        return {
            "ip": svc_match.group(1),
            "port": svc_match.group(2),
            "service": svc_match.group(3),
            "banner": svc_match.group(4).strip(),
            "type": "service"
        }

    return None


def parse_goon_fofa(output_file: str) -> Dict[str, Any]:
    """解析 Goon FOFA 输出。"""
    result = {
        "tool": "goon_fofa",
        "assets": [],
        "total": 0
    }

    if not os.path.exists(output_file):
        return result

    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    result["assets"].append({"raw": line})
    except Exception as e:
        print(f"[Parser] 解析 Goon FOFA 输出失败: {e}")

    result["total"] = len(result["assets"])
    return result


def parse_golin_html(output_file: str) -> Dict[str, Any]:
    """解析 Golin HTML 报告（提取关键信息）。"""
    result = {
        "tool": "golin",
        "assets": [],
        "ports": [],
        "fingerprints": [],
        "total": 0
    }

    if not os.path.exists(output_file):
        return result

    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 从HTML中提取表格数据（简单正则）
        # 匹配 IP、端口、服务、标题等
        ip_pattern = r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        port_pattern = r"(\d{1,5})/(?:tcp|udp)"
        title_pattern = r"<title>([^<]+)</title>"

        ips = re.findall(ip_pattern, content)
        ports = re.findall(port_pattern, content)

        result["total"] = len(set(ips))
    except Exception as e:
        print(f"[Parser] 解析 Golin HTML 失败: {e}")

    return result


def parse_golin_dirsearch(output_dir: str) -> Dict[str, Any]:
    """解析 Golin 目录扫描输出。"""
    result = {
        "tool": "golin_dirsearch",
        "hits": [],
        "total": 0
    }

    # Golin dirsearch 输出到 stdout，需要从日志中提取
    # 或从输出文件中读取
    if os.path.isdir(output_dir):
        for f in Path(output_dir).rglob("*"):
            if f.is_file():
                try:
                    with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                        for line in fh:
                            line = line.strip()
                            hit = _parse_dirsearch_line(line)
                            if hit:
                                result["hits"].append(hit)
                except Exception:
                    pass

    result["total"] = len(result["hits"])
    return result


def _parse_dirsearch_line(line: str) -> Dict[str, str]:
    """解析目录扫描单行输出。"""
    # 格式示例：[200] /admin [Size: 1234]
    match = re.match(r"\[(\d+)\]\s+(/[^\s]+)(?:\s+\[Size:\s*(\d+)\])?", line)
    if match:
        return {
            "status": match.group(1),
            "path": match.group(2),
            "size": match.group(3) or ""
        }
    return None


def parse_golin_brute(output_file: str) -> Dict[str, Any]:
    """解析 Golin 弱口令爆破输出。"""
    result = {
        "tool": "golin_brute",
        "findings": [],
        "total": 0
    }

    if not os.path.exists(output_file):
        return result

    try:
        with open(output_file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # 从HTML中提取弱口令发现
        pattern = r"(?:弱口令|未授权|默认密码).*?(\w+):(\w+)"
        matches = re.findall(pattern, content)
        for user, pwd in matches:
            result["findings"].append({
                "type": "weak_password",
                "user": user,
                "password": pwd
            })
    except Exception as e:
        print(f"[Parser] 解析 Golin 爆破结果失败: {e}")

    result["total"] = len(result["findings"])
    return result


def parse_tool_output(tool_id: str, output_path: str, target: str) -> Dict[str, Any]:
    """统一解析入口。"""
    parsers = {
        "oneforall": lambda: parse_oneforall_csv(output_path, target),
        "goon_webscan": lambda: parse_goon_text(output_path),
        "goon_fofa": lambda: parse_goon_fofa(output_path),
        "golin_scan": lambda: parse_golin_html(output_path),
        "golin_dirsearch": lambda: parse_golin_dirsearch(output_path),
        "golin_brute": lambda: parse_golin_brute(output_path),
    }

    parser = parsers.get(tool_id)
    if parser:
        return parser()
    return {"tool": tool_id, "data": [], "total": 0}
