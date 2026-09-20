# -*- coding: utf-8 -*-
"""mailer.smtp 单元测试（离线，mock smtplib）"""
import smtplib

from mailer.smtp import IMPLICIT_TLS_PORT, SMTPClient


class TestMarkdownToText:
    def test_headers_and_bold(self):
        text = SMTPClient._markdown_to_text("## 标题\n**加粗** 和 *斜体*")
        assert "##" not in text and "**" not in text and "*" not in text
        assert "标题" in text and "加粗" in text and "斜体" in text

    def test_code_fence_keeps_content(self):
        text = SMTPClient._markdown_to_text("```python\nprint('hi')\n```")
        assert "```" not in text
        assert "print('hi')" in text

    def test_link_keeps_label(self):
        text = SMTPClient._markdown_to_text("[点击这里](https://example.com)")
        assert "点击这里" in text
        assert "https://example.com" not in text

    def test_image_removed(self):
        text = SMTPClient._markdown_to_text("前文 ![图片](x.png) 后文")
        assert "![" not in text and "x.png" not in text
        assert "前文" in text and "后文" in text


class _FakeConn:
    def __init__(self):
        self.started_tls = False
        self.logged_in = False
        self.sent = []

    def starttls(self):
        self.started_tls = True

    def login(self, user, pwd):
        self.logged_in = True

    def sendmail(self, frm, to, msg):
        self.sent.append((frm, to, msg))

    def quit(self):
        pass


class TestConnectTLS:
    def test_port_465_uses_implicit_tls(self, monkeypatch):
        created = {}

        def fake_ssl(host, port, timeout=None):
            created["cls"] = "ssl"
            return _FakeConn()

        monkeypatch.setattr(smtplib, "SMTP_SSL", fake_ssl)
        client = SMTPClient("smtp.qq.com", 465, "a@b.com", "pwd")
        assert client.connect() is True
        assert created["cls"] == "ssl"

    def test_port_587_uses_starttls(self, monkeypatch):
        conn = _FakeConn()

        def fake_smtp(host, port, timeout=None):
            return conn

        monkeypatch.setattr(smtplib, "SMTP", fake_smtp)
        client = SMTPClient("smtp.qq.com", 587, "a@b.com", "pwd")
        assert client.connect() is True
        assert conn.started_tls is True
        assert conn.logged_in is True


class TestSend:
    def test_send_success(self, monkeypatch):
        conn = _FakeConn()
        monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: conn)
        client = SMTPClient("smtp.qq.com", IMPLICIT_TLS_PORT, "a@b.com", "pwd")
        assert client.send("to@b.com", "标题", "正文") is True
        assert len(conn.sent) == 1
        frm, to, msg = conn.sent[0]
        assert to == ["to@b.com"]
        assert "From: a@b.com" in msg
        assert "To: to@b.com" in msg
        assert "Subject: =?utf-8?" in msg  # 中文主题按 RFC2047 编码
        assert "5q2j5paH" in msg           # "正文" 的 base64

    def test_send_reconnects_after_disconnect(self, monkeypatch):
        broken, healthy = _FakeConn(), _FakeConn()
        broken.sendmail = lambda *a, **k: (_ for _ in ()).throw(
            smtplib.SMTPServerDisconnected("dropped")
        )
        conns = [broken, healthy]
        monkeypatch.setattr(smtplib, "SMTP_SSL", lambda *a, **k: conns.pop(0))
        client = SMTPClient("smtp.qq.com", IMPLICIT_TLS_PORT, "a@b.com", "pwd")
        assert client.send("to@b.com", "标题", "正文") is True
        assert len(healthy.sent) == 1

    def test_send_connect_failure(self, monkeypatch):
        def fake_ssl(host, port, timeout=None):
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

        monkeypatch.setattr(smtplib, "SMTP_SSL", fake_ssl)
        client = SMTPClient("smtp.qq.com", IMPLICIT_TLS_PORT, "a@b.com", "pwd")
        assert client.send("to@b.com", "标题", "正文") is False
