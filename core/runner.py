#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 子进程调度器
负责异步执行外部工具，支持并发控制、速率限制、超时、日志回调。
"""

import subprocess
import threading
import time
import shlex
from pathlib import Path
from typing import Callable, Optional


class ToolRunner:
    """子进程调度器，支持并发控制和速率限制。"""

    def __init__(self, config):
        self.config = config
        self._semaphore = threading.Semaphore(
            config.get("rate_limit.concurrent_tools", 1)
        )
        self._tool_interval = config.get("rate_limit.tool_interval_seconds", 3.0)
        self._last_run_time = 0
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()

    def cancel(self):
        """取消当前运行的任务。"""
        self._cancel_event.set()

    def reset_cancel(self):
        self._cancel_event.clear()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(
        self,
        tool_id: str,
        cmd: str,
        cwd: str,
        timeout: int = 300,
        log_callback: Optional[Callable[[str], None]] = None,
        on_finish: Optional[Callable[[int, str], None]] = None,
    ) -> dict:
        """
        执行外部工具命令。

        Args:
            tool_id: 工具ID（用于日志）
            cmd: 完整命令行
            cwd: 工作目录
            timeout: 超时秒数
            log_callback: 日志输出回调，接收 str
            on_finish: 完成回调，接收 (returncode, output_path)

        Returns:
            {"success": bool, "returncode": int, "output": str, "error": str}
        """
        result = {"success": False, "returncode": -1, "output": "", "error": ""}

        # 速率限制：等待足够间隔
        with self._lock:
            elapsed = time.time() - self._last_run_time
            if elapsed < self._tool_interval:
                wait = self._tool_interval - elapsed
                if log_callback:
                    log_callback(f"[{tool_id}] 速率限制等待 {wait:.1f}s...")
                time.sleep(wait)
            self._last_run_time = time.time()

        # 并发控制
        acquired = self._semaphore.acquire(timeout=timeout)
        if not acquired:
            result["error"] = f"[{tool_id}] 获取并发锁超时"
            if log_callback:
                log_callback(result["error"])
            return result

        try:
            if self.is_cancelled():
                result["error"] = f"[{tool_id}] 已取消"
                if log_callback:
                    log_callback(result["error"])
                return result

            if log_callback:
                log_callback(f"[{tool_id}] 启动: {cmd}")
                log_callback(f"[{tool_id}] 工作目录: {cwd}")

            # 执行子进程
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            output_lines = []

            def read_output():
                try:
                    for line in iter(proc.stdout.readline, ""):
                        if self.is_cancelled():
                            break
                        line = line.rstrip("\n\r")
                        if line:
                            output_lines.append(line)
                            if log_callback:
                                log_callback(f"  {line}")
                except Exception as e:
                    if log_callback:
                        log_callback(f"[{tool_id}] 读取输出异常: {e}")

            # 启动读取线程
            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()

            # 等待进程结束或超时
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                result["error"] = f"[{tool_id}] 超时 ({timeout}s)"
                if log_callback:
                    log_callback(result["error"])

            reader.join(timeout=5)

            result["returncode"] = proc.returncode
            result["output"] = "\n".join(output_lines)
            result["success"] = proc.returncode == 0 and not self.is_cancelled()

            if log_callback:
                status = "成功" if result["success"] else f"失败 (code={proc.returncode})"
                log_callback(f"[{tool_id}] 完成: {status}")

        except Exception as e:
            result["error"] = f"[{tool_id}] 执行异常: {e}"
            if log_callback:
                log_callback(result["error"])
        finally:
            self._semaphore.release()

        return result

    def run_gui_tool(self, tool_id: str, entry: str, cwd: str, log_callback=None):
        """启动 GUI 工具（不捕获输出，仅启动进程）。"""
        with self._lock:
            elapsed = time.time() - self._last_run_time
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
            self._last_run_time = time.time()

        try:
            if log_callback:
                log_callback(f"[{tool_id}] 启动 GUI 工具: {entry}")

            # 根据文件扩展名决定启动方式
            ext = Path(entry).suffix.lower()
            if ext == ".jar":
                # 检查是否需要 JavaFX（webfinder 和 dirscan_3.0 需要）
                if tool_id in ("webfinder", "dirscan_3"):
                    # 使用 leiying 目录自带的 Java 17（包含 JavaFX）
                    java_path = str(self.config.tool_path("leiying/SnowShadow_v1.0/env/bin/java.exe"))
                    if Path(java_path).exists():
                        cmd = f'"{java_path}" -jar "{entry}"'
                        if log_callback:
                            log_callback(f"[{tool_id}] 使用自带 JavaFX 的 Java 17")
                    else:
                        cmd = f'java -jar "{entry}"'
                        if log_callback:
                            log_callback(f"[{tool_id}] 警告: 未找到自带Java，可能需要JavaFX")
                else:
                    cmd = f'java -jar "{entry}"'
            elif ext == ".exe":
                cmd = f'"{entry}"'
            else:
                cmd = f'"{entry}"'

            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                shell=True,
                creationflags=subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NEW_PROCESS_GROUP
                if hasattr(subprocess, "DETACHED_PROCESS")
                else 0,
            )

            if log_callback:
                log_callback(f"[{tool_id}] GUI 工具已启动 (PID={proc.pid})")

            return {"success": True, "pid": proc.pid}
        except FileNotFoundError as e:
            error_msg = f"找不到程序: {e}"
            if "java" in str(e).lower():
                error_msg = "未安装 Java 运行环境，请安装 JDK 或 JRE"
            if log_callback:
                log_callback(f"[{tool_id}] 启动失败: {error_msg}")
            return {"success": False, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            if "javafx" in error_msg.lower() or "NoClassDefFoundError" in error_msg:
                error_msg = "缺少 JavaFX 运行环境。解决方案：\n1. 安装 Azul Zulu JDK (含JavaFX): https://www.azul.com/downloads/\n2. 或安装 OpenJFX SDK: https://openjfx.io/"
            if log_callback:
                log_callback(f"[{tool_id}] 启动失败: {error_msg}")
            return {"success": False, "error": error_msg}
