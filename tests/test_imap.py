# -*- coding: utf-8 -*-
"""mailer.imap 单元测试（离线，不连接服务器）"""
import base64
import email
import json
from email import policy
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mailer.imap import IMAPClient


def make_client(tmp_path, monkeypatch=None) -> IMAPClient:
    """构造不连接网络的客户端实例（UID 文件指向临时目录）"""
    import mailer.imap as imap_mod

    if monkeypatch is not None:
        monkeypatch.setattr(imap_mod, "UID_FILE", tmp_path / "processed_uids.txt")
        return IMAPClient("imap.qq.com", 993, "a@b.com", "pwd")

    # 无 monkeypatch 时手动切换（调用方负责恢复）
    original = imap_mod.UID_FILE
    imap_mod.UID_FILE = tmp_path / "processed_uids.txt"
    try:
        return IMAPClient("imap.qq.com", 993, "a@b.com", "pwd")
    finally:
        imap_mod.UID_FILE = original


def _parse(raw_msg) -> email.message.Message:
    return email.message_from_bytes(raw_msg.as_bytes(), policy=policy.default)


class TestBodyExtraction:
    def test_plain_preferred_over_html(self, tmp_path):
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("<b>HTML 版本</b>", "html", "utf-8"))
        msg.attach(MIMEText("纯文本版本", "plain", "utf-8"))
        client = make_client(tmp_path)
        assert client._get_email_body(_parse(msg)) == "纯文本版本"

    def test_html_fallback(self, tmp_path):
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("<p>只有 <i>HTML</i></p>", "html", "utf-8"))
        client = make_client(tmp_path)
        body = client._get_email_body(_parse(msg))
        assert "只有" in body and "HTML" in body
        assert "<p>" not in body

    def test_truncation(self, tmp_path, monkeypatch):
        import mailer.imap as imap_mod
        monkeypatch.setattr(imap_mod, "MAX_EMAIL_BODY_LENGTH", 10)
        msg = MIMEText("x" * 100, "plain", "utf-8")
        client = make_client(tmp_path)
        body = client._get_email_body(_parse(msg))
        assert body.startswith("x" * 10)
        assert "内容已截断" in body

    def test_subject_decode(self, tmp_path):
        msg = MIMEText("正文", "plain", "utf-8")
        msg["Subject"] = "=?utf-8?b?" + base64.b64encode("中文主题".encode()).decode() + "?="
        client = make_client(tmp_path)
        assert client._decode_subject(_parse(msg)) == "中文主题"


class TestUidPersistence:
    def test_add_and_reload(self, tmp_path, monkeypatch):
        client = make_client(tmp_path, monkeypatch)
        client.add_processed_uid("101")
        assert "101" in client.processed_uids

        # 新实例应从文件恢复
        client2 = make_client(tmp_path, monkeypatch)
        assert "101" in client2.processed_uids

    def test_corrupt_file_recovered(self, tmp_path):
        import mailer.imap as imap_mod
        uid_file = tmp_path / "processed_uids.txt"
        uid_file.write_text("{not json", encoding="utf-8")
        original = imap_mod.UID_FILE
        imap_mod.UID_FILE = uid_file
        try:
            client = IMAPClient("imap.qq.com", 993, "a@b.com", "pwd")
        finally:
            imap_mod.UID_FILE = original
        assert client.processed_uids == set()

    def test_file_content_is_json_list(self, tmp_path, monkeypatch):
        client = make_client(tmp_path, monkeypatch)
        client.add_processed_uid("7")
        content = (tmp_path / "processed_uids.txt").read_text(encoding="utf-8")
        assert json.loads(content) == ["7"]
