#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 目标解析模块
识别输入类型（域名/IP/CIDR/URL）并标准化为后续工具可用格式。
"""

import re
from urllib.parse import urlparse


class Target:
    """目标信息载体。"""

    def __init__(self, raw: str):
        self.raw = raw.strip()
        self.type = self._detect_type()
        self.domain = None
        self.ip = None
        self.cidr = None
        self.url = None
        self.host = None  # 域名或IP，用于日志显示
        self._parse()

    def _detect_type(self) -> str:
        s = self.raw.lower()

        # URL
        if s.startswith("http://") or s.startswith("https://"):
            return "url"

        # CIDR
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$", s):
            return "cidr"

        # IP
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", s):
            return "ip"

        # 域名（基本判断：包含.且不含空格）
        if "." in s and " " not in s:
            return "domain"

        return "unknown"

    def _parse(self):
        if self.type == "url":
            parsed = urlparse(self.raw)
            self.url = self.raw
            self.host = parsed.hostname
            # 判断 host 是 IP 还是域名
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", self.host):
                self.ip = self.host
            else:
                self.domain = self.host
        elif self.type == "cidr":
            self.cidr = self.raw
            self.host = self.raw
            self.ip = self.raw.split("/")[0]
        elif self.type == "ip":
            self.ip = self.raw
            self.host = self.raw
        elif self.type == "domain":
            self.domain = self.raw
            self.host = self.raw

    @property
    def needs_subdomain(self) -> bool:
        """是否需要子域名枚举步骤。"""
        return self.type == "domain"

    @property
    def needs_portscan(self) -> bool:
        """是否需要端口扫描步骤。"""
        return self.type in ("domain", "ip", "cidr")

    @property
    def needs_dirscan(self) -> bool:
        """是否需要目录扫描步骤。"""
        return self.type in ("domain", "url", "ip")

    @property
    def portscan_target(self) -> str:
        """用于端口扫描的目标字符串（IP或CIDR）。"""
        if self.type == "cidr":
            return self.cidr
        if self.ip:
            return self.ip
        return self.host

    @property
    def dirscan_url(self) -> str:
        """用于目录扫描的URL。"""
        if self.type == "url":
            return self.url
        return f"http://{self.host}"

    def __str__(self):
        return f"Target({self.raw}, type={self.type}, host={self.host})"
