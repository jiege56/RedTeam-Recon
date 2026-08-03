#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam POC 漏洞扫描模块
加载并执行 afrog/xray 格式的 YAML POC 文件
"""

import os
import re
import time
import random
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime

try:
    import yaml
    import requests
except ImportError:
    yaml = None
    requests = None


class PocLoader:
    """POC 文件加载器"""

    def __init__(self, pocs_dir: str = None):
        if pocs_dir is None:
            pocs_dir = Path(__file__).resolve().parent.parent / "pocs"
        self.pocs_dir = Path(pocs_dir)
        self.pocs: List[Dict] = []
        self._load_all()

    def _load_all(self):
        """加载所有 POC 文件"""
        if not self.pocs_dir.exists():
            return

        for yaml_file in self.pocs_dir.rglob("*.yaml"):
            poc = self._load_poc(yaml_file)
            if poc:
                self.pocs.append(poc)

        for yaml_file in self.pocs_dir.rglob("*.yml"):
            poc = self._load_poc(yaml_file)
            if poc:
                self.pocs.append(poc)

    def _load_poc(self, yaml_file: Path) -> Optional[Dict]:
        """加载单个 POC 文件"""
        if not yaml:
            return None

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                poc = yaml.safe_load(f)

            if not poc or "id" not in poc:
                return None

            poc["_file"] = str(yaml_file)
            poc["_source"] = yaml_file.stem
            return poc

        except Exception:
            return None

    def get_pocs(self, tags: List[str] = None, severity: str = None) -> List[Dict]:
        """获取 POC 列表，支持按标签和严重程度过滤"""
        result = self.pocs

        if tags:
            result = [
                p for p in result
                if any(t in p.get("info", {}).get("tags", []) for t in tags)
            ]

        if severity:
            result = [
                p for p in result
                if p.get("info", {}).get("severity", "") == severity
            ]

        return result

    def get_stats(self) -> Dict:
        """获取 POC 统计信息"""
        stats = {
            "total": len(self.pocs),
            "by_severity": {},
            "by_tag": {},
            "by_year": {},
            "by_category": {},
        }

        for poc in self.pocs:
            # 按严重程度统计
            severity = poc.get("info", {}).get("severity", "unknown")
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # 按标签统计
            tags = poc.get("info", {}).get("tags", [])
            for tag in tags:
                stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + 1

            # 按年份统计
            poc_id = poc.get("id", "")
            year_match = re.search(r"(20\d{2})", poc_id)
            if year_match:
                year = year_match.group(1)
                stats["by_year"][year] = stats["by_year"].get(year, 0) + 1

            # 按分类统计（从文件路径提取）
            category = self._get_category(poc)
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

        return stats

    def _get_category(self, poc: Dict) -> str:
        """从POC文件路径提取分类"""
        file_path = poc.get("_file", "")
        # 提取父目录名作为分类
        parts = Path(file_path).parts
        # 查找 pocs/afrog/ 后的第一个目录
        try:
            idx = parts.index("afrog-pocs")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        except ValueError:
            pass
        return "other"

    def get_categories(self) -> List[str]:
        """获取所有可用的POC分类"""
        categories = set()
        for poc in self.pocs:
            categories.add(self._get_category(poc))
        return sorted(list(categories))

    def get_pocs_by_category(self, category: str) -> List[Dict]:
        """按分类获取POC"""
        return [p for p in self.pocs if self._get_category(p) == category]


class PocScanner:
    """POC 漏洞扫描器"""

    def __init__(self, config, pocs_dir: str = None, log_callback: Callable = None):
        self.config = config
        self.log = log_callback or (lambda msg: print(msg))
        self.loader = PocLoader(pocs_dir)
        self.results: List[Dict] = []
        self._cancel = False

    def cancel(self):
        """取消扫描"""
        self._cancel = True

    def scan(self, target: str, poc_filter: Dict = None) -> List[Dict]:
        """
        执行 POC 扫描

        Args:
            target: 目标 URL
            poc_filter: 过滤条件 {"tags": [], "severity": ""}

        Returns:
            漏洞列表
        """
        if not requests:
            self.log("[POC] requests 库未安装")
            return []

        self.results = []
        self._cancel = False

        # 获取要执行的 POC
        if poc_filter:
            pocs = self.loader.get_pocs(
                tags=poc_filter.get("tags"),
                severity=poc_filter.get("severity")
            )
        else:
            pocs = self.loader.get_pocs()

        if not pocs:
            self.log("[POC] 没有匹配的 POC")
            return []

        self.log(f"[POC] 加载 {len(pocs)} 个 POC")
        self.log(f"[POC] 目标: {target}")

        # 确保目标有协议前缀
        if not target.startswith(("http://", "https://")):
            target = "http://" + target

        total = len(pocs)
        for i, poc in enumerate(pocs, 1):
            if self._cancel:
                break

            if i % 100 == 0:
                self.log(f"[POC] 进度: {i}/{total}")

            result = self._execute_poc(target, poc)
            if result:
                self.results.append(result)

        self.log(f"[POC] 扫描完成，发现 {len(self.results)} 个漏洞")
        return self.results

    def _execute_poc(self, target: str, poc: Dict) -> Optional[Dict]:
        """执行单个 POC"""
        try:
            rules = poc.get("rules", {})
            if not rules:
                return None

            # 解析 set 变量
            variables = self._parse_set(poc.get("set", {}))

            # 执行规则
            rule_results = {}
            for rule_name, rule in rules.items():
                if self._cancel:
                    return None

                matched = self._execute_rule(target, rule, variables)
                rule_results[rule_name] = matched

                if not matched:
                    break  # 任一规则不匹配则跳过

            # 检查最终表达式
            expression = poc.get("expression", "")
            if expression and not self._evaluate_expression(expression, rule_results):
                return None

            # 漏洞匹配成功
            info = poc.get("info", {})
            return {
                "id": poc.get("id", "unknown"),
                "name": info.get("name", "Unknown"),
                "severity": info.get("severity", "unknown"),
                "description": info.get("description", ""),
                "target": target,
                "tags": info.get("tags", []),
                "reference": info.get("reference", []),
                "author": info.get("author", ""),
                "file": poc.get("_file", ""),
            }

        except Exception:
            return None

    def _parse_set(self, set_dict: Dict) -> Dict:
        """解析 set 变量"""
        variables = {}
        for key, value in set_dict.items():
            if isinstance(value, str):
                # 处理 randomInt
                if "randomInt" in value:
                    match = re.search(r"randomInt\((\d+),\s*(\d+)\)", value)
                    if match:
                        low, high = int(match.group(1)), int(match.group(2))
                        variables[key] = random.randint(low, high)
                # 处理表达式
                elif "n1" in value and "n2" in value:
                    n1 = variables.get("n1", 0)
                    n2 = variables.get("n2", 0)
                    variables[key] = n1 * n2
                else:
                    variables[key] = value
            else:
                variables[key] = value
        return variables

    def _execute_rule(self, target: str, rule: Dict, variables: Dict) -> bool:
        """执行单个规则"""
        try:
            request = rule.get("request", {})
            method = request.get("method", "GET").upper()
            path = request.get("path", "/")

            # 替换变量
            for key, value in variables.items():
                path = path.replace(f"{{{{{key}}}}}", str(value))

            url = target.rstrip("/") + path

            # 发送请求
            resp = requests.request(
                method,
                url,
                timeout=10,
                verify=False,
                allow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )

            # 检查表达式
            expression = rule.get("expression", "")
            if not expression:
                return True

            return self._evaluate_response(expression, resp, variables)

        except Exception:
            return False

    def _evaluate_response(self, expression: str, resp, variables: Dict) -> bool:
        """评估响应表达式"""
        try:
            # 构建评估上下文
            context = {
                "response": {
                    "status": resp.status_code,
                    "body": resp,
                    "headers": dict(resp.headers),
                    "text": resp.text,
                },
                "string": str,
                "bytes": bytes,
            }
            context.update(variables)

            # 替换表达式中的 response.body.bcontains
            def replace_bcontains(match):
                inner = match.group(1)
                return f"({inner}) in response['text']"

            expression = re.sub(
                r"response\.body\.bcontains\(bytes\(string\((\w+)\)\)\)",
                replace_bcontains,
                expression
            )

            # 替换 response.status
            expression = expression.replace("response.status", "response['status']")

            # 替换 response.body.bcontains (其他格式)
            expression = re.sub(
                r"response\.body\.bcontains\(([^)]+)\)",
                r"(\1) in response['text']",
                expression
            )

            # 安全评估
            allowed_names = {
                "response": context["response"],
                "string": str,
                "bytes": bytes,
                "len": len,
                "str": str,
                "int": int,
            }
            allowed_names.update(variables)

            # 只允许安全的操作
            code = compile(expression, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    return False

            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return bool(result)

        except Exception:
            return False

    def _evaluate_expression(self, expression: str, rule_results: Dict) -> bool:
        """评估最终表达式"""
        try:
            # 替换规则结果
            for rule_name, result in rule_results.items():
                expression = expression.replace(f"{rule_name}()", str(result))

            # 评估布尔表达式
            expression = expression.replace("&&", " and ")
            expression = expression.replace("||", " or ")

            return eval(expression)

        except Exception:
            return False

    def get_stats(self) -> Dict:
        """获取 POC 统计"""
        return self.loader.get_stats()


def scan_with_pocs(target: str, config, log_callback: Callable = None, poc_filter: Dict = None) -> List[Dict]:
    """便捷函数：执行 POC 扫描"""
    scanner = PocScanner(config, log_callback=log_callback)
    return scanner.scan(target, poc_filter)
