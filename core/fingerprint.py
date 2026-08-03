#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 框架指纹识别模块
基于 HTTP 响应头、HTML 特征、特定路径识别 Web 框架/CMS/中间件。
"""

import re
import hashlib
from typing import Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


# ==================== 指纹规则库 ====================

# 响应头指纹规则
HEADER_RULES = [
    # Web服务器
    {"name": "Nginx", "header": "Server", "pattern": r"nginx", "category": "WebServer"},
    {"name": "Apache", "header": "Server", "pattern": r"Apache", "category": "WebServer"},
    {"name": "IIS", "header": "Server", "pattern": r"Microsoft-IIS", "category": "WebServer"},
    {"name": "Tomcat", "header": "Server", "pattern": r"Apache-Coyote", "category": "WebServer"},
    {"name": "Jetty", "header": "Server", "pattern": r"Jetty", "category": "WebServer"},
    {"name": "Lighttpd", "header": "Server", "pattern": r"lighttpd", "category": "WebServer"},
    {"name": "Caddy", "header": "Server", "pattern": r"Caddy", "category": "WebServer"},

    # 编程语言
    {"name": "PHP", "header": "X-Powered-By", "pattern": r"PHP", "category": "Language"},
    {"name": "ASP.NET", "header": "X-Powered-By", "pattern": r"ASP\.NET", "category": "Language"},
    {"name": "Express", "header": "X-Powered-By", "pattern": r"Express", "category": "Language"},
    {"name": "Django", "header": "X-Frame-Options", "pattern": r"DENY", "category": "Framework"},

    # 安全头部（辅助判断）
    {"name": "HSTS", "header": "Strict-Transport-Security", "pattern": r".+", "category": "Security"},
]

# HTML Body 指纹规则
BODY_RULES = [
    # CMS 识别
    {"name": "WordPress", "pattern": r"wp-content|wp-includes|wordpress", "category": "CMS"},
    {"name": "Drupal", "pattern": r"Drupal\.settings|drupal\.js|sites/default/files", "category": "CMS"},
    {"name": "Joomla", "pattern": r"/media/jui/|Joomla!", "category": "CMS"},
    {"name": "DedeCMS", "pattern": r"dedecms|织梦", "category": "CMS"},
    {"name": "Discuz", "pattern": r"Discuz!|discuz_uid", "category": "CMS"},
    {"name": "phpMyAdmin", "pattern": r"phpMyAdmin|pma_", "category": "CMS"},
    {"name": "phpcms", "pattern": r"phpcms|phpsso", "category": "CMS"},
    {"name": "帝国CMS", "pattern": r"ecms|帝国", "category": "CMS"},
    {"name": "PHPCMS", "pattern": r"phpcms", "category": "CMS"},

    # 前端框架
    {"name": "Vue.js", "pattern": r"vue\.js|vue\.min\.js|v-cloak|data-v-", "category": "Frontend"},
    {"name": "React", "pattern": r"react\.js|react\.min\.js|react-dom|data-reactroot", "category": "Frontend"},
    {"name": "Angular", "pattern": r"angular\.js|angular\.min\.js|ng-app|ng-controller", "category": "Frontend"},
    {"name": "jQuery", "pattern": r"jquery[\.\-]?\d|jquery\.min\.js", "category": "Frontend"},
    {"name": "Bootstrap", "pattern": r"bootstrap\.css|bootstrap\.min\.css|bootstrap\.js", "category": "Frontend"},
    {"name": "Layui", "pattern": r"layui\.css|layui\.js|layui\.all", "category": "Frontend"},
    {"name": "Element UI", "pattern": r"element-ui|element\.min\.css", "category": "Frontend"},
    {"name": "Ant Design", "pattern": r"antd\.css|antd\.min\.css|ant-design", "category": "Frontend"},

    # 后端框架
    {"name": "Spring Boot", "pattern": r"Whitelabel Error Page|spring-boot", "category": "Backend"},
    {"name": "Laravel", "pattern": r"laravel_session|csrf-token|laravel", "category": "Backend"},
    {"name": "ThinkPHP", "pattern": r"thinkphp|ThinkPHP|think\\\\", "category": "Backend"},
    {"name": "Django", "pattern": r"csrfmiddlewaretoken|django", "category": "Backend"},
    {"name": "Flask", "pattern": r"flask|werkzeug", "category": "Backend"},
    {"name": "Express", "pattern": r"express|X-Powered-By: Express", "category": "Backend"},
    {"name": "Struts2", "pattern": r"\.action|\.do|struts|s:form", "category": "Backend"},
    {"name": "Shiro", "pattern": r"rememberMe|shiro|deleteMe", "category": "Backend"},

    # 中间件/组件
    {"name": "Swagger", "pattern": r"swagger-ui|api-docs|swagger\.json", "category": "Component"},
    {"name": "Actuator", "pattern": r"actuator|health|env|metrics", "category": "Component"},
    {"name": "Druid", "pattern": r"druid|DruidStatView", "category": "Component"},
    {"name": "Nacos", "pattern": r"nacos|Nacos", "category": "Component"},
    {"name": "WebLogic", "pattern": r"WebLogic|wls", "category": "Component"},
    {"name": "Jenkins", "pattern": r"Jenkins|jenkins", "category": "Component"},
    {"name": "GitLab", "pattern": r"GitLab|gitlab", "category": "Component"},
    {"name": "Harbor", "pattern": r"Harbor|harbor", "category": "Component"},
    {"name": "Kibana", "pattern": r"Kibana|kibana", "category": "Component"},
    {"name": "Grafana", "pattern": r"Grafana|grafana", "category": "Component"},
    {"name": "Prometheus", "pattern": r"Prometheus|prometheus", "category": "Component"},
    {"name": "RabbitMQ", "pattern": r"RabbitMQ|rabbitmq", "category": "Component"},
    {"name": "Kafka", "pattern": r"Kafka|kafka", "category": "Component"},
    {"name": "Elasticsearch", "pattern": r"elasticsearch|elastic", "category": "Component"},
]

# 特定路径检测规则
PATH_RULES = [
    {"name": "Spring Boot Actuator", "path": "/actuator", "status": [200], "category": "Component"},
    {"name": "Swagger UI", "path": "/swagger-ui.html", "status": [200, 301, 302], "category": "Component"},
    {"name": "Druid Monitor", "path": "/druid/index.html", "status": [200], "category": "Component"},
    {"name": "Nacos", "path": "/nacos/", "status": [200, 302], "category": "Component"},
    {"name": "phpMyAdmin", "path": "/phpmyadmin/", "status": [200, 302], "category": "Component"},
    {"name": "Adminer", "path": "/adminer.php", "status": [200], "category": "Component"},
    {"name": "WordPress Login", "path": "/wp-login.php", "status": [200], "category": "CMS"},
    {"name": "WordPress Admin", "path": "/wp-admin/", "status": [200, 302], "category": "CMS"},
    {"name": "Joomla Admin", "path": "/administrator/", "status": [200, 302], "category": "CMS"},
    {"name": "Drupal Login", "path": "/user/login", "status": [200], "category": "CMS"},
    {"name": "Jenkins", "path": "/login", "status": [200], "category": "Component"},
    {"name": "GitLab", "path": "/users/sign_in", "status": [200], "category": "Component"},
    {"name": "Harbor", "path": "/harbor/sign-in", "status": [200], "category": "Component"},
    {"name": "Kibana", "path": "/app/kibana", "status": [200], "category": "Component"},
    {"name": "Grafana", "path": "/login", "status": [200], "category": "Component"},
    {"name": "RabbitMQ Management", "path": "/#/queues", "status": [200], "category": "Component"},
    {"name": "Elasticsearch", "path": "/_cat/health", "status": [200], "category": "Component"},
    {"name": "Solr Admin", "path": "/solr/admin/", "status": [200], "category": "Component"},
    {"name": "WebLogic Console", "path": "/console/login/LoginForm.jsp", "status": [200], "category": "Component"},
    {"name": "Tomcat Manager", "path": "/manager/html", "status": [200, 401], "category": "Component"},
]


# ==================== 指纹识别引擎 ====================

class FingerprintEngine:
    """Web 框架指纹识别引擎。"""

    def __init__(self, timeout: int = 10, verify_ssl: bool = False):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.session = None
        if requests:
            self.session = requests.Session()
            self.session.verify = verify_ssl
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

    def scan(self, url: str) -> Dict[str, any]:
        """
        对目标URL进行指纹识别。

        Args:
            url: 目标URL

        Returns:
            {
                "url": str,
                "fingerprints": [{"name": str, "category": str, "evidence": str}],
                "headers": dict,
                "status_code": int,
                "title": str
            }
        """
        result = {
            "url": url,
            "fingerprints": [],
            "headers": {},
            "status_code": 0,
            "title": "",
            "server": "",
            "powered_by": "",
            "error": None
        }

        if not requests:
            result["error"] = "requests 库未安装，请执行: pip install requests"
            return result

        try:
            # 发送请求
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            result["status_code"] = resp.status_code
            result["headers"] = dict(resp.headers)
            result["server"] = resp.headers.get("Server", "")
            result["powered_by"] = resp.headers.get("X-Powered-By", "")

            # 提取标题
            title_match = re.search(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
            if title_match:
                result["title"] = title_match.group(1).strip()[:100]

            # 响应头指纹识别
            self._match_headers(resp.headers, result["fingerprints"])

            # HTML Body 指纹识别
            self._match_body(resp.text, result["fingerprints"])

            # 主动探测 Shiro（发送 rememberMe cookie 触发 deleteMe 响应）
            self._detect_shiro(url, result["fingerprints"])

            # 特定路径检测
            self._check_paths(url, result["fingerprints"])

        except requests.exceptions.Timeout:
            result["error"] = "请求超时"
        except requests.exceptions.ConnectionError:
            result["error"] = "连接失败"
        except Exception as e:
            result["error"] = str(e)

        # 去重
        seen = set()
        unique_fps = []
        for fp in result["fingerprints"]:
            key = fp["name"]
            if key not in seen:
                seen.add(key)
                unique_fps.append(fp)
        result["fingerprints"] = unique_fps

        return result

    def _match_headers(self, headers: dict, fingerprints: list):
        """匹配响应头指纹。"""
        for rule in HEADER_RULES:
            header_value = headers.get(rule["header"], "")
            if header_value and re.search(rule["pattern"], header_value, re.IGNORECASE):
                fingerprints.append({
                    "name": rule["name"],
                    "category": rule["category"],
                    "evidence": f"{rule['header']}: {header_value}"
                })

        # 特殊处理 Set-Cookie（检查 Shiro 等框架特征）
        set_cookie = headers.get("Set-Cookie", "")
        if set_cookie:
            # Shiro 特征：rememberMe=deleteMe
            if "rememberMe" in set_cookie or "deleteMe" in set_cookie:
                fingerprints.append({
                    "name": "Shiro",
                    "category": "Backend",
                    "evidence": f"Set-Cookie: {set_cookie}"
                })

            # Laravel 特征
            if "laravel_session" in set_cookie:
                fingerprints.append({
                    "name": "Laravel",
                    "category": "Backend",
                    "evidence": f"Set-Cookie: {set_cookie}"
                })

            # PHPSESSION 特征
            if "PHPSESSID" in set_cookie:
                fingerprints.append({
                    "name": "PHP",
                    "category": "Language",
                    "evidence": f"Set-Cookie: {set_cookie}"
                })

            # JSESSIONID 特征（Java应用）
            if "JSESSIONID" in set_cookie:
                fingerprints.append({
                    "name": "Java",
                    "category": "Language",
                    "evidence": f"Set-Cookie: {set_cookie}"
                })

            # ASP.NET 特征
            if "ASP.NET_SessionId" in set_cookie:
                fingerprints.append({
                    "name": "ASP.NET",
                    "category": "Language",
                    "evidence": f"Set-Cookie: {set_cookie}"
                })

    def _match_body(self, body: str, fingerprints: list):
        """匹配 HTML Body 指纹。"""
        for rule in BODY_RULES:
            if re.search(rule["pattern"], body, re.IGNORECASE):
                fingerprints.append({
                    "name": rule["name"],
                    "category": rule["category"],
                    "evidence": f"Pattern: {rule['pattern']}"
                })

    def _check_paths(self, base_url: str, fingerprints: list):
        """检测特定路径。"""
        base = base_url.rstrip("/")
        for rule in PATH_RULES:
            try:
                url = base + rule["path"]
                resp = self.session.get(url, timeout=self.timeout, allow_redirects=False)
                if resp.status_code in rule["status"]:
                    fingerprints.append({
                        "name": rule["name"],
                        "category": rule["category"],
                        "evidence": f"{url} [{resp.status_code}]"
                    })
            except:
                pass

    def _detect_shiro(self, url: str, fingerprints: list):
        """
        主动探测 Apache Shiro。
        发送带有 rememberMe cookie 的请求，如果返回 rememberMe=deleteMe 则说明存在 Shiro。
        """
        # 检查是否已经识别到 Shiro
        for fp in fingerprints:
            if fp["name"] == "Shiro":
                return

        try:
            # 发送带有 rememberMe cookie 的请求
            headers = {"Cookie": "rememberMe=1"}
            resp = self.session.get(url, timeout=self.timeout, allow_redirects=False, headers=headers)

            # 检查响应头中是否有 rememberMe=deleteMe
            set_cookie = resp.headers.get("Set-Cookie", "")
            if "rememberMe=deleteMe" in set_cookie:
                fingerprints.append({
                    "name": "Shiro",
                    "category": "Backend",
                    "evidence": "rememberMe=deleteMe detected (active probe)"
                })
                return

            # 再次检查所有 Set-Cookie（可能有多个）
            for header_value in resp.headers.get("Set-Cookie", "").split(","):
                if "rememberMe=deleteMe" in header_value:
                    fingerprints.append({
                        "name": "Shiro",
                        "category": "Backend",
                        "evidence": "rememberMe=deleteMe detected (active probe)"
                    })
                    return

        except Exception:
            pass

    def scan_batch(self, urls: List[str]) -> List[Dict]:
        """批量扫描多个URL。"""
        results = []
        for url in urls:
            results.append(self.scan(url))
        return results


def fingerprint_scan(url: str, timeout: int = 10) -> Dict:
    """便捷函数：单URL指纹识别。"""
    engine = FingerprintEngine(timeout=timeout)
    return engine.scan(url)


def fingerprint_scan_batch(urls: List[str], timeout: int = 10) -> List[Dict]:
    """便捷函数：批量指纹识别。"""
    engine = FingerprintEngine(timeout=timeout)
    return engine.scan_batch(urls)
