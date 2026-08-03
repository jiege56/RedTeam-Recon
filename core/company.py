#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam 企业信息收集模块
支持：FOFA资产搜索、ICP备案查询、Whois查询、GitHub代码搜索、邮箱收集
"""

import re
import time
import socket
from typing import Dict, List, Any, Callable, Optional

try:
    import requests
except ImportError:
    requests = None


class CompanyRecon:
    """企业信息收集引擎。"""

    def __init__(self, config, log_callback: Callable = None):
        self.config = config
        self.log = log_callback or (lambda msg: print(msg))
        self.session = None
        if requests:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

    def collect_all(self, company_name: str, fofa_results: dict = None) -> Dict[str, Any]:
        """
        执行全面的企业信息收集。

        Args:
            company_name: 企业名称
            fofa_results: FOFA查询结果（可选，避免重复查询）

        Returns:
            企业信息汇总字典
        """
        self.log(f"[企业信息收集] 开始全面收集: {company_name}")

        results = {
            "company_name": company_name,
            "domains": [],
            "ips": [],
            "icp_info": [],
            "whois_info": [],
            "emails": [],
            "github_leaks": [],
            "employees": [],
            "assets": []
        }

        # 1. FOFA资产搜索（如果已有结果则直接使用）
        if fofa_results:
            results["domains"] = fofa_results.get("domains", [])
            results["ips"] = fofa_results.get("ips", [])
            results["assets"] = fofa_results.get("assets", [])
            self.log(f"[企业信息收集] 使用已有FOFA结果: {len(results['domains'])} 域名, {len(results['ips'])} IP")

        # 2. ICP备案查询
        self.log(f"[企业信息收集] 查询ICP备案...")
        icp_info = self.query_icp(company_name)
        results["icp_info"] = icp_info
        # 从ICP结果中提取域名
        for icp in icp_info:
            domain = icp.get("domain", "")
            if domain and domain not in results["domains"]:
                results["domains"].append(domain)

        # 3. Whois信息查询（对发现的域名）
        self.log(f"[企业信息收集] 查询Whois信息...")
        domains_to_query = results["domains"][:5]  # 最多查询5个域名
        for domain in domains_to_query:
            if self._is_cancelled():
                break
            whois_info = self.query_whois(domain)
            if whois_info:
                results["whois_info"].append(whois_info)
            time.sleep(1)

        # 4. GitHub代码搜索
        self.log(f"[企业信息收集] 搜索GitHub代码...")
        github_results = self.search_github(company_name, results["domains"])
        results["github_leaks"] = github_results

        # 5. 邮箱收集
        self.log(f"[企业信息收集] 收集邮箱地址...")
        emails = self.collect_emails(company_name, results["domains"])
        results["emails"] = emails

        # 统计
        self.log(f"[企业信息收集] 收集完成:")
        self.log(f"  域名: {len(results['domains'])} 个")
        self.log(f"  IP: {len(results['ips'])} 个")
        self.log(f"  ICP备案: {len(results['icp_info'])} 条")
        self.log(f"  Whois: {len(results['whois_info'])} 条")
        self.log(f"  邮箱: {len(results['emails'])} 个")
        self.log(f"  GitHub泄露: {len(results['github_leaks'])} 条")

        return results

    def _is_cancelled(self) -> bool:
        """检查是否取消（由workflow设置）"""
        return False

    # ==================== ICP备案查询 ====================

    def query_icp(self, company_name: str) -> List[Dict]:
        """
        查询ICP备案信息。
        使用在线API或网页解析。
        """
        icp_results = []

        if not requests:
            self.log("[ICP] requests库未安装")
            return icp_results

        try:
            # 使用ICP备案查询API（示例使用在线接口）
            # 注意：实际使用时可能需要替换为可用的API
            url = f"https://apidatav2.chinaz.com/ICP?key={company_name}"

            # 备用：使用搜索引擎缓存
            search_url = f"https://www.google.com/search?q=site:beian.miit.gov.cn+{company_name}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            # 尝试从已有数据中提取ICP信息
            self.log(f"[ICP] 搜索ICP备案信息: {company_name}")

            # 常见ICP备案格式匹配
            icp_patterns = [
                r'京ICP备\d+号',
                r'沪ICP备\d+号',
                r'粤ICP备\d+号',
                r'苏ICP备\d+号',
                r'浙ICP备\d+号',
                r'ICP备\d+号',
            ]

            # 搜索引擎查询
            try:
                resp = self.session.get(
                    f"https://www.baidu.com/s?wd={company_name}+ICP备案",
                    headers=headers,
                    timeout=10
                )
                if resp.status_code == 200:
                    # 提取ICP号
                    for pattern in icp_patterns:
                        matches = re.findall(pattern, resp.text)
                        for match in matches:
                            icp_results.append({
                                "icp_number": match,
                                "company": company_name,
                                "source": "search_engine"
                            })

                    # 提取域名
                    domain_pattern = r'([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}'
                    domains = re.findall(domain_pattern, resp.text)
                    for domain in set(domains):
                        if not any(x in domain for x in ['baidu.com', 'google.com', 'bing.com']):
                            icp_results.append({
                                "domain": domain,
                                "company": company_name,
                                "source": "search_engine"
                            })
            except Exception as e:
                self.log(f"[ICP] 搜索引擎查询失败: {e}")

        except Exception as e:
            self.log(f"[ICP] 查询异常: {e}")

        return icp_results

    # ==================== Whois查询 ====================

    def query_whois(self, domain: str) -> Dict[str, Any]:
        """
        查询域名Whois信息。
        """
        whois_info = {
            "domain": domain,
            "registrar": "",
            "registrant": "",
            "email": "",
            "creation_date": "",
            "expiration_date": "",
            "name_servers": []
        }

        if not requests:
            return whois_info

        try:
            # 使用Whois API
            url = f"https://whois.arin.net/rest/domain/{domain}.json"
            resp = self.session.get(url, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                whois_info["registrar"] = data.get("registrar", {}).get("name", "")
                whois_info["registrant"] = data.get("registrant", {}).get("name", "")
                whois_info["email"] = data.get("registrant", {}).get("email", "")
        except Exception as e:
            self.log(f"[Whois] 查询 {domain} 失败: {e}")

        # 备用：使用socket直接查询
        try:
            whois_server = "whois.verisign-grs.com"
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((whois_server, 43))
            sock.send(f"{domain}\r\n".encode())

            response = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
            sock.close()

            response_text = response.decode("utf-8", errors="ignore")

            # 解析Whois响应
            for line in response_text.split("\n"):
                line = line.strip()
                if line.startswith("Registrar:"):
                    whois_info["registrar"] = line.split(":", 1)[1].strip()
                elif line.startswith("Registrant Organization:"):
                    whois_info["registrant"] = line.split(":", 1)[1].strip()
                elif line.startswith("Registrant Email:"):
                    whois_info["email"] = line.split(":", 1)[1].strip()
                elif line.startswith("Creation Date:"):
                    whois_info["creation_date"] = line.split(":", 1)[1].strip()
                elif line.startswith("Registry Expiry Date:"):
                    whois_info["expiration_date"] = line.split(":", 1)[1].strip()
                elif line.startswith("Name Server:"):
                    ns = line.split(":", 1)[1].strip().lower()
                    if ns not in whois_info["name_servers"]:
                        whois_info["name_servers"].append(ns)

        except Exception as e:
            self.log(f"[Whois] Socket查询 {domain} 失败: {e}")

        return whois_info

    # ==================== GitHub代码搜索 ====================

    def search_github(self, company_name: str, domains: List[str] = None) -> List[Dict]:
        """
        搜索GitHub上的代码泄露。
        """
        github_results = []

        if not requests:
            self.log("[GitHub] requests库未安装")
            return github_results

        # 构建搜索关键词
        search_terms = [company_name]
        if domains:
            search_terms.extend(domains[:3])

        github_token = self.config.get("apikeys.github_token", "")

        for term in search_terms:
            if not term:
                continue

            try:
                self.log(f"[GitHub] 搜索: {term}")

                # GitHub代码搜索API
                url = "https://api.github.com/search/code"
                params = {
                    "q": f'"{term}" password OR secret OR api_key OR token',
                    "per_page": 10,
                    "sort": "indexed",
                    "order": "desc"
                }
                headers = {
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "ReconHub"
                }
                if github_token:
                    headers["Authorization"] = f"token {github_token}"

                resp = self.session.get(url, params=params, headers=headers, timeout=15)

                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        github_results.append({
                            "file": item.get("name", ""),
                            "path": item.get("path", ""),
                            "repo": item.get("repository", {}).get("full_name", ""),
                            "url": item.get("html_url", ""),
                            "search_term": term
                        })
                elif resp.status_code == 403:
                    self.log("[GitHub] API速率限制，跳过")
                    break
                else:
                    self.log(f"[GitHub] API返回 {resp.status_code}")

                time.sleep(2)  # 避免速率限制

            except Exception as e:
                self.log(f"[GitHub] 搜索失败: {e}")

        return github_results

    # ==================== 邮箱收集 ====================

    def collect_emails(self, company_name: str, domains: List[str] = None) -> List[Dict]:
        """
        收集企业邮箱地址。
        """
        emails = []
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

        if not requests:
            return emails

        # 搜索引擎查询
        search_queries = [
            f'"{company_name}" email OR 邮箱',
            f'@{company_name}.com',
        ]

        if domains:
            for domain in domains[:3]:
                search_queries.append(f'@{domain}')

        for query in search_queries:
            try:
                self.log(f"[邮箱] 搜索: {query}")

                resp = self.session.get(
                    f"https://www.bing.com/search?q={query}",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=10
                )

                if resp.status_code == 200:
                    found_emails = re.findall(email_pattern, resp.text)
                    for email in set(found_emails):
                        # 过滤掉常见的非企业邮箱
                        if not any(x in email for x in ['example.com', 'test.com', 'gmail.com', 'yahoo.com', 'hotmail.com']):
                            emails.append({
                                "email": email,
                                "source": "search_engine",
                                "query": query
                            })

                time.sleep(1)

            except Exception as e:
                self.log(f"[邮箱] 搜索失败: {e}")

        # 从Whois结果中提取邮箱
        # （需要外部传入whois结果）

        return emails

    # ==================== 子域名枚举 ====================

    def enumerate_subdomains(self, domain: str) -> List[str]:
        """
        枚举子域名（使用字典爆破）。
        """
        subdomains = []
        common_prefixes = [
            'www', 'mail', 'ftp', 'smtp', 'pop', 'ns1', 'ns2', 'ns3',
            'dns', 'dns1', 'dns2', 'mx', 'mx1', 'mx2', 'relay',
            'webmail', 'email', 'admin', 'manage', 'manager',
            'portal', 'login', 'sso', 'auth', 'api', 'dev',
            'test', 'staging', 'demo', 'beta', 'alpha',
            'app', 'apps', 'mobile', 'm', 'wap',
            'cdn', 'static', 'img', 'images', 'media',
            'assets', 'js', 'css', 'files', 'download',
            'docs', 'wiki', 'help', 'support', 'kb',
            'blog', 'news', 'forum', 'bbs', 'community',
            'shop', 'store', 'pay', 'payment', 'order',
            'crm', 'erp', 'oa', 'hr', 'finance',
            'vpn', 'remote', 'rdp', 'ssh', 'gateway',
            'proxy', 'lb', 'load', 'cluster', 'node',
            'db', 'database', 'mysql', 'postgres', 'redis',
            'mongo', 'elastic', 'search', 'mq', 'rabbit',
            'jenkins', 'git', 'gitlab', 'svn', 'ci',
            'monitor', 'zabbix', 'nagios', 'grafana',
            'log', 'logs', 'kibana', 'graylog',
            'backup', 'bak', 'old', 'archive',
            'internal', 'intranet', 'private', 'local',
        ]

        for prefix in common_prefixes:
            subdomain = f"{prefix}.{domain}"
            try:
                socket.gethostbyname(subdomain)
                subdomains.append(subdomain)
            except:
                pass

        return subdomains


def collect_company_info(company_name: str, config, fofa_results: dict = None, log_callback: Callable = None) -> Dict[str, Any]:
    """便捷函数：执行企业信息收集。"""
    recon = CompanyRecon(config, log_callback)
    return recon.collect_all(company_name, fofa_results)
