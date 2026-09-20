# -*- coding: utf-8 -*-
"""core.config 单元测试（离线）"""
import os

import pytest

from core import config as config_mod
from core.config import (
    ConfigError,
    _get_required_env,
    _parse_senders,
    load_config,
    load_dotenv,
    validate_config,
)


def _base_env(monkeypatch):
    monkeypatch.setenv("EMAIL_USER", "tester@qq.com")
    monkeypatch.setenv("EMAIL_PWD", "secret")
    monkeypatch.setenv("IMAP_HOST", "imap.qq.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.qq.com")


class TestParseSenders:
    def test_basic(self):
        assert _parse_senders("a@b.com,c@d.com") == ["a@b.com", "c@d.com"]

    def test_lowercase_and_strip(self):
        assert _parse_senders(" A@B.COM ,  c@d.com ") == ["a@b.com", "c@d.com"]

    def test_empty(self):
        assert _parse_senders(None) is None
        assert _parse_senders("") is None
        assert _parse_senders(" , ") is None


class TestRequiredEnv:
    def test_missing_raises(self, monkeypatch):
        monkeypatch.delenv("SOME_VAR", raising=False)
        with pytest.raises(ConfigError):
            _get_required_env("SOME_VAR", "测试项")

    def test_blank_raises(self, monkeypatch):
        monkeypatch.setenv("SOME_VAR", "  ")
        with pytest.raises(ConfigError):
            _get_required_env("SOME_VAR", "测试项")


class TestLoadDotenv:
    def test_loads_and_keeps_existing(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# comment\nFOO_A=1\nFOO_B=\"quoted\"\nFOO_A=ignored\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("FOO_B", "existing")
        load_dotenv(env_file)
        assert os.environ["FOO_A"] == "1"          # 首个赋值生效
        assert os.environ["FOO_B"] == "existing"   # 已存在的不被覆盖

    def test_missing_file_ok(self, tmp_path):
        load_dotenv(tmp_path / "nope.env")  # 不抛异常


class TestLoadConfig:
    def test_happy_path(self, monkeypatch):
        _base_env(monkeypatch)
        cfg = load_config()
        assert cfg["email"] == "tester@qq.com"
        assert cfg["imap_port"] == 993
        assert cfg["smtp_port"] == 465
        assert cfg["poll_interval"] == 30

    def test_missing_required_raises(self, monkeypatch):
        monkeypatch.delenv("EMAIL_USER", raising=False)
        with pytest.raises(ConfigError):
            load_config()


class TestValidateConfig:
    def _valid_cfg(self):
        return {
            "imap_host": "imap.qq.com",
            "smtp_host": "smtp.qq.com",
            "email": "a@b.com",
            "password": "x",
            "imap_port": 993,
            "smtp_port": 465,
            "poll_interval": 30,
            "timeout": 300,
            "allowed_senders": ["a@b.com"],
        }

    def test_valid(self):
        assert validate_config(self._valid_cfg()) is True

    def test_missing_field(self):
        cfg = self._valid_cfg()
        cfg.pop("password")
        assert validate_config(cfg) is False

    def test_interval_bounds(self):
        cfg = self._valid_cfg()
        cfg["poll_interval"] = 5
        assert validate_config(cfg) is False

    def test_timeout_bounds(self):
        cfg = self._valid_cfg()
        cfg["timeout"] = 5000
        assert validate_config(cfg) is False
