# -*- coding: utf-8 -*-
"""web_app 单元测试（离线，Flask test client）"""
import json
import time

import pytest

import core.config as config_mod
import web_app


@pytest.fixture()
def client():
    web_app.app.config["TESTING"] = True
    with web_app.app.test_client() as c:
        yield c


@pytest.fixture()
def isolated_paths(tmp_path, monkeypatch):
    """把面板读取的心跳/历史/日志文件指向临时目录"""
    monkeypatch.setattr(web_app, "HEARTBEAT_FILE", tmp_path / "heartbeat.json")
    monkeypatch.setattr(web_app, "HISTORY_FILE", tmp_path / "history.jsonl")
    monkeypatch.setattr(web_app, "LOG_FILE", tmp_path / "email_ai.log")
    return tmp_path


@pytest.fixture()
def fake_env(monkeypatch):
    env = {
        "EMAIL_USER": "tester@qq.com",
        "EMAIL_PWD": "secret",
        "IMAP_HOST": "imap.qq.com",
        "SMTP_HOST": "smtp.qq.com",
        "ALLOWED_SENDERS": "tester@qq.com",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)


class TestIndex:
    def test_without_config(self, client, monkeypatch):
        for var in ("EMAIL_USER", "EMAIL_PWD", "IMAP_HOST", "SMTP_HOST"):
            monkeypatch.delenv(var, raising=False)
        page = client.get("/").get_data(as_text=True)
        assert "未配置" in page

    def test_with_config_and_heartbeat(self, client, fake_env, isolated_paths):
        web_app.HEARTBEAT_FILE.write_text(json.dumps({
            "running": True,
            "last_poll": time.time(),
            "emails_processed": 5,
        }), encoding="utf-8")
        page = client.get("/").get_data(as_text=True)
        assert "运行中" in page
        assert "tester@qq.com" in page

    def test_stale_heartbeat_shows_offline(self, client, fake_env, isolated_paths):
        web_app.HEARTBEAT_FILE.write_text(json.dumps({
            "running": True,
            "last_poll": time.time() - web_app.HEARTBEAT_STALE_SECONDS - 10,
        }), encoding="utf-8")
        page = client.get("/").get_data(as_text=True)
        assert "未运行" in page


class TestTasksApi:
    def test_empty(self, client, isolated_paths):
        assert client.get("/api/tasks").get_json() == {"tasks": []}

    def test_history_order(self, client, isolated_paths):
        web_app.HISTORY_FILE.write_text("\n".join([
            json.dumps({"time": "t1", "sender": "a@b.com", "subject": "旧", "status": "success"}),
            json.dumps({"time": "t2", "sender": "a@b.com", "subject": "新", "status": "failed"}),
        ]), encoding="utf-8")
        tasks = client.get("/api/tasks").get_json()["tasks"]
        assert tasks[0]["subject"] == "新"
        assert tasks[1]["subject"] == "旧"

    def test_skips_corrupt_lines(self, client, isolated_paths):
        web_app.HISTORY_FILE.write_text(
            "{broken json\n" + json.dumps(
                {"time": "t", "sender": "a@b.com", "subject": "好", "status": "success"}),
            encoding="utf-8",
        )
        tasks = client.get("/api/tasks").get_json()["tasks"]
        assert len(tasks) == 1


class TestLogs:
    def test_missing_log(self, client, isolated_paths):
        assert "暂无日志" in client.get("/").get_data(as_text=True)

    def test_json_log_rendered_readable(self, client, fake_env, isolated_paths):
        web_app.LOG_FILE.write_text(json.dumps({
            "timestamp": "2026-09-20T00:00:00+00:00",
            "level": "INFO",
            "message": "服务启动",
        }), encoding="utf-8")
        page = client.get("/").get_data(as_text=True)
        assert "INFO 服务启动" in page
        assert '"timestamp"' not in page  # 不再原样展示 JSON


class TestSendApi:
    def test_rejects_empty_content(self, client, fake_env, isolated_paths):
        resp = client.post("/api/send", json={"content": "  "})
        assert resp.get_json()["success"] is False

    def test_unreachable_smtp_fails_gracefully(self, client, fake_env, isolated_paths, monkeypatch):
        # 指向不可能连接的地址，验证不崩溃
        monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("SMTP_PORT", "1")
        resp = client.post("/api/send", json={"content": "任务内容"})
        body = resp.get_json()
        assert body["success"] is False
        assert "error" in body

    def test_requires_config(self, client, monkeypatch, isolated_paths):
        for var in ("EMAIL_USER", "EMAIL_PWD", "IMAP_HOST", "SMTP_HOST"):
            monkeypatch.delenv(var, raising=False)
        resp = client.post("/api/send", json={"content": "任务内容"})
        assert resp.get_json()["success"] is False


class TestClearApi:
    def test_clear_removes_history(self, client, isolated_paths):
        web_app.HISTORY_FILE.write_text("x", encoding="utf-8")
        assert client.post("/api/clear").get_json()["success"] is True
        assert not web_app.HISTORY_FILE.exists()
