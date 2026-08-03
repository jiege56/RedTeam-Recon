#!/usr/bin/env python3
# coding: utf-8
"""
RedTeam信息收集 - 一体化工具
入口文件 (.pyw 避免 Windows 启动时出现控制台黑窗)

用法: 双击运行或 python ReconHub.pyw
"""

import sys
import os

# 确保当前目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import config
from core.workflow import Workflow
from ui.app import ReconHubApp


def main():
    """主入口。"""
    # 初始化工作流（日志回调在GUI启动后注册）
    workflow = Workflow(config, log_callback=lambda msg: print(msg))

    # 启动GUI
    app = ReconHubApp(config, workflow)
    app.run()


if __name__ == "__main__":
    main()
