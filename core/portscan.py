#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam 内置端口扫描模块
使用 socket 进行快速端口扫描，支持多线程。
"""

import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Callable, Optional
import time


# 常见端口及服务映射
COMMON_PORTS = {
    # 基础服务
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    111: "RPC",
    135: "SMB",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    513: "Rlogin",
    554: "RTSP",
    587: "SMTP",
    631: "CUPS",
    636: "LDAPS",
    993: "IMAPS",
    995: "POP3S",
    1080: "SOCKS",

    # 数据库
    1433: "MSSQL",
    1521: "Oracle",
    3306: "MySQL",
    5432: "PostgreSQL",
    5984: "CouchDB",
    6379: "Redis",
    9200: "Elasticsearch",
    9300: "Elasticsearch",
    11211: "Memcached",
    27017: "MongoDB",
    27018: "MongoDB",

    # 中间件/应用服务器
    2375: "Docker",
    2376: "Docker",
    3389: "RDP",
    4443: "HTTPS",
    5000: "Flask/Docker",
    5001: "Flask/HTTPS",
    5003: "Custom/WebSphere",
    5060: "SIP",
    5061: "SIPS",
    5443: "HTTPS",
    5555: "ADB/Debug",
    5900: "VNC",
    5901: "VNC",
    5985: "WinRM",
    5986: "WinRM-HTTPS",
    6379: "Redis",
    6443: "Kubernetes",
    7001: "WebLogic",
    7002: "WebLogic",
    7443: "HTTPS",
    8000: "HTTP",
    8001: "HTTP",
    8002: "HTTP",
    8008: "HTTP",
    8009: "AJP",
    8010: "HTTP",
    8060: "HTTP",
    8080: "HTTP",
    8081: "HTTP",
    8082: "HTTP",
    8083: "HTTP",
    8084: "HTTP",
    8085: "HTTP",
    8086: "HTTP",
    8087: "HTTP",
    8088: "HTTP",
    8089: "HTTP",
    8090: "HTTP",
    8091: "HTTP",
    8161: "ActiveMQ",
    8443: "HTTPS",
    8444: "HTTPS",
    8834: "Nessus",
    8848: "Nacos",
    8880: "HTTP",
    8888: "HTTP",
    8983: "Solr",
    9000: "HTTP",
    9001: "HTTP",
    9002: "HTTP",
    9043: "WebSphere",
    9060: "WebSphere",
    9080: "HTTP",
    9090: "HTTP",
    9091: "HTTP",
    9418: "Git",
    9443: "HTTPS",
    9999: "HTTP",
    10000: "Webmin",
    10443: "HTTPS",

    # 大数据/消息队列
    2181: "Zookeeper",
    50070: "Hadoop",
    61616: "ActiveMQ",
    9092: "Kafka",

    # 特定应用
    80: "HTTP",
    443: "HTTPS",
    8080: "HTTP-Proxy",
    8443: "HTTPS-Alt",
    9200: "ES-HTTP",
    9300: "ES-Transport",
    15672: "RabbitMQ",
    5672: "RabbitMQ-AMQP",
}


class PortScanner:
    """内置端口扫描器。"""

    def __init__(self, timeout: float = 2.0, max_threads: int = 100):
        self.timeout = timeout
        self.max_threads = max_threads
        self._cancel = False

    def cancel(self):
        """取消扫描。"""
        self._cancel = True

    def scan(self, target: str, ports: List[int] = None, log_callback: Callable = None) -> Dict[str, Any]:
        """
        扫描目标端口。

        Args:
            target: 目标IP或域名
            ports: 要扫描的端口列表，默认为常见端口
            log_callback: 日志回调

        Returns:
            扫描结果字典
        """
        self._cancel = False

        if ports is None:
            ports = list(COMMON_PORTS.keys())

        result = {
            "target": target,
            "open_ports": [],
            "closed_ports": [],
            "filtered_ports": [],
            "total_scanned": len(ports),
            "start_time": time.time(),
            "end_time": None
        }

        # 解析目标IP
        try:
            ip = socket.gethostbyname(target)
            result["ip"] = ip
            if log_callback:
                log_callback(f"[PortScan] 目标: {target} -> {ip}")
        except socket.gaierror:
            result["ip"] = target
            if log_callback:
                log_callback(f"[PortScan] 目标: {target}")

        if log_callback:
            log_callback(f"[PortScan] 开始扫描 {len(ports)} 个端口...")

        # 多线程扫描
        open_ports = []
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_port = {
                executor.submit(self._check_port, ip, port): port
                for port in ports
            }

            completed = 0
            for future in as_completed(future_to_port):
                if self._cancel:
                    break

                port = future_to_port[future]
                completed += 1

                try:
                    is_open, service, banner = future.result()
                    if is_open:
                        port_info = {
                            "port": port,
                            "state": "open",
                            "service": service,
                            "banner": banner
                        }
                        open_ports.append(port_info)
                        result["open_ports"].append(port_info)

                        if log_callback:
                            log_callback(f"[PortScan]   {port}/tcp  OPEN  {service}  {banner[:50] if banner else ''}")
                except Exception:
                    pass

                # 进度日志
                if completed % 50 == 0 and log_callback:
                    log_callback(f"[PortScan] 进度: {completed}/{len(ports)}")

        result["end_time"] = time.time()
        result["duration"] = result["end_time"] - result["start_time"]

        if log_callback:
            log_callback(f"[PortScan] 扫描完成，耗时 {result['duration']:.1f}s")
            log_callback(f"[PortScan] 发现 {len(result['open_ports'])} 个开放端口")

        return result

    def _check_port(self, ip: str, port: int) -> tuple:
        """检查单个端口是否开放。"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))

            if result == 0:
                # 端口开放，尝试获取banner
                service = COMMON_PORTS.get(port, "unknown")
                banner = self._grab_banner(sock, port)
                sock.close()
                return True, service, banner
            else:
                sock.close()
                return False, "", ""
        except Exception:
            return False, "", ""

    def _grab_banner(self, sock: socket.socket, port: int) -> str:
        """获取服务banner。"""
        try:
            sock.settimeout(1.0)

            # 对于某些服务，发送探测请求
            if port in (80, 443, 8080, 8443, 8000, 8001, 8888):
                sock.send(b"HEAD / HTTP/1.1\r\nHost: test\r\n\r\n")
            elif port == 22:
                pass  # SSH会主动发送banner
            elif port == 21:
                pass  # FTP会主动发送banner
            elif port == 25:
                pass  # SMTP会主动发送banner

            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            return banner[:200]  # 限制长度
        except:
            return ""


def quick_port_scan(target: str, ports: List[int] = None, timeout: float = 2.0, threads: int = 100, log_callback: Callable = None) -> Dict[str, Any]:
    """便捷函数：快速端口扫描。"""
    scanner = PortScanner(timeout=timeout, max_threads=threads)
    return scanner.scan(target, ports, log_callback)


def get_common_ports() -> List[int]:
    """获取常见端口列表。"""
    return list(COMMON_PORTS.keys())


def get_web_ports() -> List[int]:
    """获取Web端口列表。"""
    return [80, 443, 8000, 8001, 8008, 8009, 8080, 8081, 8082, 8083, 8088, 8090, 8443, 8888, 9000, 9001, 9090]


def get_service_name(port: int) -> str:
    """获取端口对应的服务名称。"""
    return COMMON_PORTS.get(port, "unknown")
