# -*- coding: utf-8 -*-
"""utils.security 单元测试（离线）"""
from utils.security import SecurityChecker


class TestCheckSender:
    def test_exact_match_case_insensitive(self):
        sec = SecurityChecker(["User@QQ.com"])
        assert sec.check_sender("USER@qq.com") is True
        assert sec.check_sender("user@qq.com ") is True

    def test_display_name_parsed(self):
        sec = SecurityChecker(["user@qq.com"])
        assert sec.check_sender("Someone <user@qq.com>") is True

    def test_substring_spoof_rejected(self):
        sec = SecurityChecker(["user@qq.com"])
        # 旧的子串匹配会让这种伪造地址通过
        assert sec.check_sender("user@qq.com@evil.com") is False
        assert sec.check_sender("xuser@qq.com.evil.com") is False

    def test_unknown_rejected(self):
        sec = SecurityChecker(["user@qq.com"])
        assert sec.check_sender("stranger@qq.com") is False

    def test_no_whitelist_allows(self):
        sec = SecurityChecker(None)
        assert sec.check_sender("anyone@any.com") is True


class TestCheckPrompt:
    def test_dangerous_detected(self):
        sec = SecurityChecker(["a@b.com"])
        assert sec.check_prompt("请帮我 rm -rf /") is False
        assert sec.check_prompt("format c:") is False

    def test_normal_allowed(self):
        sec = SecurityChecker(["a@b.com"])
        assert sec.check_prompt("帮我写一封请假条") is True
        # 普通文本中的竖线（如表格）不应误杀
        assert sec.check_prompt("对比 A | B 的区别") is True


class TestSanitizePrompt:
    def test_masks_api_key(self):
        sec = SecurityChecker([])
        out = sec.sanitize_prompt("my key is sk-abc123DEF-456 keep secret")
        assert "sk-abc123DEF-456" not in out
        assert "[API_KEY]" in out

    def test_masks_windows_path(self):
        sec = SecurityChecker([])
        out = sec.sanitize_prompt("open C:\\Users\\me\\secret.txt please")
        assert "C:\\Users\\me\\secret.txt" not in out
        assert "[路径]" in out
