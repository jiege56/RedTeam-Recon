# RedTeam-Recon 🔴

> 基于天狐渗透工具箱二次开发的一体化信息收集工具

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 项目简介

RedTeam-Recon 是一款集成多种信息收集工具的一体化渗透测试辅助工具。本项目基于**天狐渗透工具箱社区版V3.0**进行二次开发，将多个独立工具整合为统一的 GUI 界面，实现一键化信息收集。

### ⚠️ 免责声明

**本项目仅供合法授权的安全测试和学习研究使用。使用者应遵守当地法律法规，未经授权对他人系统进行测试属于违法行为，后果由使用者自行承担。**

---

## ✨ 功能特性

### 核心功能

| 功能模块 | 工具来源 | 说明 |
|----------|----------|------|
| 🌐 子域名枚举 | OneForAll | 多源子域名收集，支持字典爆破 |
| 📡 网络空间测绘 | Goon/FOFA | FOFA/Hunter/Quake 资产搜索 |
| 🔌 端口扫描 | 内置模块 | 98个常见端口，服务识别 |
| 🔍 框架指纹识别 | 内置模块 | 71条规则，识别62+框架/组件 |
| 📁 目录扫描 | Golin | Web目录/后台/备份文件扫描 |
| 🔓 弱口令/POC | Golin | 40+协议弱口令，65+ POC |
| 🏢 企业信息收集 | 内置模块 | FOFA/ICP/Whois/GitHub/邮箱 |
| 📊 Excel报告 | 内置模块 | 一键生成详细报告 |

### 自动化工具链

```
输入目标 → 子域名枚举 → 网络空间测绘 → 端口扫描 → 框架识别 → 目录扫描 → 生成报告
```

### 框架识别能力

| 类别 | 可识别框架 |
|------|------------|
| 后端框架 | Shiro, Spring Boot, Laravel, ThinkPHP, Django, Flask, Struts2 |
| CMS系统 | WordPress, Drupal, Joomla, DedeCMS, Discuz, phpMyAdmin |
| 前端框架 | Vue.js, React, Angular, jQuery, Bootstrap, Layui, Element UI |
| 中间件 | Nacos, Jenkins, GitLab, Harbor, Kibana, Grafana, Druid |
| Web服务器 | Nginx, Apache, IIS, Tomcat, Jetty |

---

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.8 - 3.14（任意版本）
- **磁盘空间**: 50 MB

### 安装步骤

#### 方式一：下载便携版（推荐）

1. 下载 [最新发布版本](https://github.com/jiege56/RedTeam-Recon/releases)
2. 解压到任意目录
3. 双击 `启动工具.bat`

#### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/jiege56/RedTeam-Recon.git
cd RedTeam-Recon

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行程序
python ReconHub.pyw
```

### 配置 API Key

启动工具后，在「设置」页面配置：

| API | 获取地址 | 用途 |
|-----|----------|------|
| FOFA | https://fofa.info | 网络空间测绘 |
| Hunter | https://hunter.qianxin.com | 奇安信威胁情报 |
| Quake | https://quake.360.cn | 360网络空间测绘 |

---

## 📖 使用说明

### 基本使用

```
┌─────────────────────────────────────────────────────────────────┐
│  目标输入                                                        │
│  目标: [example.com                    ▼] [📁 导入] [🗑️]       │
│  企业: [某某科技有限公司                 ▼]               [🗑️]   │
│                                                                 │
│  💡 只输入目标可扫描 | 只输入企业可收集企业信息 | 都输入则先收集再扫描│
├─────────────────────────────────────────────────────────────────┤
│  [▶ 开始收集]  [⏹ 停止]  [🔄 重置]                             │
└─────────────────────────────────────────────────────────────────┘
```

### 三种使用模式

| 输入情况 | 执行流程 |
|----------|----------|
| 只输入目标 | 扫描目标（子域名→端口→指纹→报告） |
| 只输入企业 | 企业信息收集（FOFA/ICP/Whois/GitHub/邮箱） |
| 都输入 | 先企业收集，再扫描目标 |

### 扫描策略

| 策略 | 包含模块 |
|------|----------|
| 全面 | 子域名 + 测绘 + 端口 + 指纹 + 爆破 |
| 快速 | 子域名 + 测绘 + 端口 |
| 仅子域名 | 子域名枚举 |
| 仅端口 | 端口扫描 + 指纹识别 |
| 仅目录 | 目录扫描 |

### 报告输出

扫描完成后自动生成 Excel 报告，包含：

- 总览（统计+详细信息）
- 子域名列表
- 端口扫描结果
- 资产清单
- 框架指纹
- 目录扫描结果
- 漏洞/弱口令发现

---

## 📁 项目结构

```
RedTeam-Recon/
│
├── ReconHub/                    # 主程序
│   ├── ReconHub.pyw            # 入口文件
│   ├── core/                   # 核心模块
│   │   ├── config.py          # 配置管理
│   │   ├── workflow.py        # 工作流引擎
│   │   ├── target.py          # 目标解析
│   │   ├── runner.py          # 进程调度
│   │   ├── portscan.py        # 端口扫描
│   │   ├── fingerprint.py     # 指纹识别
│   │   ├── company.py         # 企业信息收集
│   │   ├── parsers.py         # 结果解析
│   │   └── report.py          # 报告生成
│   ├── tools/                  # 工具注册表
│   │   └── registry.py
│   ├── ui/                     # GUI界面
│   │   └── app.py
│   └── data/                   # 数据目录
│       └── config.json        # 配置文件
│
├── tools/                       # 外部工具（需自行下载）
│   ├── goon/                   # Goon 扫描器
│   ├── golin/                  # Golin 资产测绘
│   └── oneforall/              # OneForAll 子域名
│
├── 启动工具.bat                 # 便携版启动脚本
├── requirements.txt            # Python依赖
├── build.py                    # 打包脚本
└── README.md                   # 本文件
```

---

## 🔧 依赖工具

本项目集成以下开源工具（需自行下载放入 `tools` 目录）：

| 工具 | 作者 | 用途 | 下载地址 |
|------|------|------|----------|
| [OneForAll](https://github.com/shmilylty/OneForAll) | shmilylty | 子域名枚举 | GitHub |
| [Goon](https://github.com/i11us0ry/goon) | i11us0ry | 综合扫描 | GitHub |
| [Golin](https://github.com/selinuxG/Golin) | selinuxG | 资产测绘 | GitHub |

### 下载命令

```bash
# OneForAll
git clone https://github.com/shmilylty/OneForAll.git tools/oneforall

# Goon（从Releases下载对应版本）
# 下载 goon3_win_amd64.exe 放入 tools/goon/

# Golin（从Releases下载对应版本）
# 下载 golin.exe 放入 tools/golin/
```

---

## 📊 端口扫描范围

默认扫描 98 个常见端口：

```
基础服务: 21(FTP) 22(SSH) 23(Telnet) 25(SMTP) 53(DNS) 80(HTTP) 443(HTTPS)
数据库:   1433(MSSQL) 1521(Oracle) 3306(MySQL) 5432(PostgreSQL) 6379(Redis) 27017(MongoDB)
中间件:   2375(Docker) 7001(WebLogic) 8080(HTTP) 8443(HTTPS) 8848(Nacos) 9200(ES)
Web服务:  8000-9091系列 (30个端口)
消息队列: 2181(Zookeeper) 5672(RabbitMQ) 61616(ActiveMQ) 9092(Kafka)
```

---

## ❓ 常见问题

### Q: 启动报错 "No module named xxx"

```bash
pip install -r requirements.txt
```

### Q: JavaFX 工具无法启动

Scandir 3.0 和 WebFinder 需要 JavaFX，可安装 [Azul Zulu JDK](https://www.azul.com/downloads/)（含JavaFX版本）

### Q: FOFA 查询无结果

请在「设置」页面配置正确的 FOFA Email 和 API Key

### Q: 如何添加自定义端口？

编辑 `ReconHub/core/portscan.py` 中的 `COMMON_PORTS` 字典

---

## 🙏 致谢

本项目基于以下开源项目二次开发：

- [天狐渗透工具箱](https://github.com/AttackTeamFamily/ToolSet) - 原始工具箱
- [OneForAll](https://github.com/shmilylty/OneForAll) - 子域名枚举工具
- [Golin](https://github.com/selinuxG/Golin) - 资产测绘工具
- [Goon](https://github.com/i11us0ry/goon) - 综合扫描工具

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 📧 联系方式

- GitHub: [jiege56](https://github.com/jiege56/)

---

## ⭐ Star History

如果本项目对您有帮助，请给个 Star 支持一下！

[![Star History Chart](https://api.star-history.com/svg?repos=jiege56/RedTeam-Recon&type=Date)](https://star-history.com/#jiege56/RedTeam-Recon&Date)
