#!/usr/bin/env python3
# coding: utf-8
"""
ReconHub 配置管理模块
"""

import json
import os
from pathlib import Path


class Config:
    """统一配置读写，包含路径、API Key、速率限制、策略模板。"""

    def __init__(self):
        # 确定 ReconHub 根目录
        self._reconhub_dir = Path(__file__).resolve().parent.parent
        self._data_dir = self._reconhub_dir / "data"
        self._config_file = self._data_dir / "config.json"
        self._profiles_dir = self._data_dir / "profiles"
        self._reports_dir = self._data_dir / "reports"
        self._tools_base = self._reconhub_dir.parent

        self._ensure_dirs()
        self._config = self._load()

    def _ensure_dirs(self):
        for d in (self._data_dir, self._profiles_dir, self._reports_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _default_config(self) -> dict:
        return {
            "paths": {
                "base": str(self._tools_base),
                "output": str(self._reports_dir)
            },
            "apikeys": {
                "fofa_email": "",
                "fofa_key": "",
                "hunter_key": "",
                "quake_key": "",
                "shodan_key": "",
                "zoomeye_key": ""
            },
            "proxy": {
                "enable": False,
                "http": "http://127.0.0.1:8080",
                "https": "http://127.0.0.1:8080"
            },
            "rate_limit": {
                "enabled": True,
                "concurrent_tools": 1,
                "tool_threads": 100,
                "requests_per_second": 50,
                "tool_interval_seconds": 3.0,
                "timeout": 300
            },
            "strategies": {
                "subdomain": {"enable": True, "brute": True, "alive": True},
                "cyberspace": {"enable": False, "engine": "fofa", "max_results": 100},
                "portscan": {"enable": True, "mode": "goon_webscan", "threads": 100, "timeout": 5},
                "fingerprint": {"enable": True},
                "dirscan": {"enable": False, "dict": "dirscan_3.0/dict/全部.txt", "code": "200,302,403"},
                "brute": {"enable": False, "thread": 50, "timeout": 10}
            }
        }

    def _load(self) -> dict:
        if self._config_file.exists():
            try:
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                default = self._default_config()
                return self._merge(default, loaded)
            except Exception as e:
                print(f"[Config] 读取配置失败: {e}，使用默认配置")
        return self._default_config()

    def _merge(self, default: dict, override: dict) -> dict:
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def save(self):
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Config] 保存配置失败: {e}")

    def get(self, key_path: str, default=None):
        """通过点号路径获取配置，如 'apikeys.fofa_key'。"""
        keys = key_path.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key_path: str, value):
        keys = key_path.split(".")
        cfg = self._config
        for k in keys[:-1]:
            if k not in cfg or not isinstance(cfg[k], dict):
                cfg[k] = {}
            cfg = cfg[k]
        cfg[keys[-1]] = value

    @property
    def raw(self) -> dict:
        return self._config

    @property
    def reconhub_dir(self) -> Path:
        return self._reconhub_dir

    @property
    def data_dir(self) -> Path:
        return self._data_dir

    @property
    def output_dir(self) -> Path:
        return Path(self.get("paths.output", str(self._reports_dir)))

    @property
    def tools_base(self) -> Path:
        return Path(self.get("paths.base", str(self._tools_base)))

    @property
    def config_file(self) -> Path:
        return self._config_file

    def tool_path(self, rel_path: str) -> Path:
        return self.tools_base / rel_path

    def fofa_key_ok(self) -> bool:
        return bool(self.get("apikeys.fofa_email") and self.get("apikeys.fofa_key"))


# 全局单例
config = Config()
