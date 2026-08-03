#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam 连通性检测模块
测试目标是否连通，支持 ICMP ping、TCP 端口探测、HTTP 探测
"""

import socket
import subprocess
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    requests = None


class ConnectivityChecker:
    """连通性检测器"""

    def __init__(self, timeout: int = 5, log_callback=None):
        self.timeout = timeout
        self.log = log_callback or (lambda msg: print(msg))

    def check(self, target: str) -> Dict[str, any]:
        """
        全面检测目标连通性

        Returns:
            {
                "target": str,
                "type": str,  # domain/ip/url
                "is_alive": bool,
                "ip": str,
                "ping": {"alive": bool, "time_ms": float},
                "tcp": [{"port": int, "alive": bool}],
                "http": {"alive": bool, "status": int, "title": str},
                "error": str
            }
        """
        result = {
            "target": target,
            "type": "unknown",
            "is_alive": False,
            "ip": "",
            "ping": {"alive": False, "time_ms": -1},
            "tcp": [],
            "http": {"alive": False, "status": 0, "title": ""},
            "error": ""
        }

        # 解析目标
        target_type, host, port = self._parse_target(target)
        result["type"] = target_type

        # 1. DNS 解析（域名类型）
        if target_type == "domain":
            ip = self._dns_resolve(host)
            if not ip:
                result["error"] = f"DNS解析失败: {host}"
                self.log(f"[连通性] {result['error']}")
                return result
            result["ip"] = ip
        elif target_type == "ip":
            result["ip"] = host
            ip = host
        elif target_type == "url":
            parsed = urlparse(target)
            host = parsed.hostname
            ip = self._dns_resolve(host)
            if not ip:
                result["error"] = f"DNS解析失败: {host}"
                self.log(f"[连通性] {result['error']}")
                return result
            result["ip"] = ip
        else:
            result["error"] = f"无法识别的目标类型: {target}"
            return result

        # 2. ICMP Ping
        ping_alive, ping_time = self._ping(ip)
        result["ping"]["alive"] = ping_alive
        result["ping"]["time_ms"] = ping_time

        # 3. TCP 端口探测
        tcp_ports = []
        if port:
            tcp_ports.append(port)
        else:
            # 默认探测常见端口
            tcp_ports = [80, 443, 22, 3389, 8080]

        for tcp_port in tcp_ports:
            tcp_alive = self._tcp_check(ip, tcp_port)
            result["tcp"].append({"port": tcp_port, "alive": tcp_alive})

        # 4. HTTP 探测（如果是Web目标）
        if target_type in ("domain", "url") or any(
            t["port"] in (80, 443, 8080, 8443) and t["alive"]
            for t in result["tcp"]
        ):
            http_result = self._http_check(target if target_type == "url" else f"http://{host}")
            result["http"] = http_result

        # 综合判断
        result["is_alive"] = (
            ping_alive or
            any(t["alive"] for t in result["tcp"]) or
            result["http"]["alive"]
        )

        if not result["is_alive"]:
            result["error"] = f"目标 {target} ({ip}) 无法连通"
            self.log(f"[连通性] {result['error']}")
        else:
            self.log(f"[连通性] {target} ({ip}) 连通正常")

        return result

    def quick_check(self, target: str) -> bool:
        """快速检测目标是否连通"""
        result = self.check(target)
        return result["is_alive"]

    def _parse_target(self, target: str) -> Tuple[str, str, Optional[int]]:
        """解析目标，返回 (类型, 主机, 端口)"""
        target = target.strip()

        # URL
        if target.startswith(("http://", "https://")):
            parsed = urlparse(target)
            port = parsed.port
            if port is None:
                port = 443 if target.startswith("https") else 80
            return "url", parsed.hostname, port

        # IP:port
        if ":" in target and target.count(":") == 1:
            parts = target.split(":")
            try:
                port = int(parts[1])
                return "ip", parts[0], port
            except ValueError:
                pass

        # 纯IP
        if self._is_ip(target):
            return "ip", target, None

        # 域名
        return "domain", target, None

    def _is_ip(self, s: str) -> bool:
        """判断是否为IP地址"""
        parts = s.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False

    def _dns_resolve(self, hostname: str) -> Optional[str]:
        """DNS解析"""
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except socket.gaierror:
            return None

    def _ping(self, ip: str) -> Tuple[bool, float]:
        """ICMP Ping 检测"""
        try:
            start = time.time()
            # Windows ping 命令
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(self.timeout * 1000), ip],
                capture_output=True,
                timeout=self.timeout + 2
            )
            elapsed = (time.time() - start) * 1000

            if result.returncode == 0:
                return True, round(elapsed, 1)
            return False, -1
        except Exception:
            return False, -1

    def _tcp_check(self, ip: str, port: int) -> bool:
        """TCP 端口探测"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _http_check(self, url: str) -> Dict:
        """HTTP 探测"""
        result = {"alive": False, "status": 0, "title": ""}

        if not requests:
            return result

        try:
            resp = requests.get(
                url,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            result["alive"] = True
            result["status"] = resp.status_code

            # 提取标题
            import re
            title_match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
            if title_match:
                result["title"] = title_match.group(1).strip()[:100]

        except requests.exceptions.ConnectionError:
            result["alive"] = False
        except requests.exceptions.Timeout:
            result["alive"] = False
        except Exception:
            result["alive"] = False

        return result


def check_target_alive(target: str, timeout: int = 5, log_callback=None) -> Dict:
    """便捷函数：检测目标连通性"""
    checker = ConnectivityChecker(timeout=timeout, log_callback=log_callback)
    return checker.check(target)
