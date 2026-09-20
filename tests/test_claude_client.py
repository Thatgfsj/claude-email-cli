# -*- coding: utf-8 -*-
"""claude.client 单元测试（离线，mock subprocess）"""
import subprocess

import pytest

from claude.client import ClaudeClient


@pytest.fixture()
def mock_run(monkeypatch):
    calls = {}

    def _run(cmd, **kwargs):
        calls["cmd"] = cmd
        calls["kwargs"] = kwargs
        return subprocess.CompletedProcess(cmd, 0, stdout="claude says hi", stderr="")

    monkeypatch.setattr(subprocess, "run", _run)
    return calls


class TestChat:
    def test_uses_arg_list_and_stdin(self, mock_run):
        client = ClaudeClient(claude_path="claude", timeout=60)
        result = client.chat('来自邮件的提示 " with quotes && rm -rf /')

        assert result == "claude says hi"
        cmd = mock_run["cmd"]
        assert isinstance(cmd, list)
        assert cmd[1:] == ["-p"]                 # 正确的 CLI 语法
        assert mock_run["kwargs"]["shell"] is False
        # 正文通过 stdin 传递，不进入命令行
        assert mock_run["kwargs"]["input"].startswith("来自邮件的提示")
        assert not any("rm -rf" in str(a) for a in cmd)

    def test_empty_response_is_none(self, monkeypatch, mock_run):
        def _run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="   ", stderr="")

        monkeypatch.setattr(subprocess, "run", _run)
        assert ClaudeClient().chat("hi") is None

    def test_failure_returns_none(self, monkeypatch, mock_run):
        def _run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

        monkeypatch.setattr(subprocess, "run", _run)
        assert ClaudeClient().chat("hi") is None

    def test_timeout_returns_none(self, monkeypatch, mock_run):
        def _run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, 999)

        monkeypatch.setattr(subprocess, "run", _run)
        assert ClaudeClient().chat("hi") is None

    def test_missing_binary_returns_none(self, monkeypatch, mock_run):
        def _run(cmd, **kwargs):
            raise FileNotFoundError("claude not found")

        monkeypatch.setattr(subprocess, "run", _run)
        assert ClaudeClient().chat("hi") is None
