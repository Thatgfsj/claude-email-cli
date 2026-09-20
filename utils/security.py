"""
安全检查模块
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class SecurityChecker:
    """安全检查器"""

    # 破坏性操作关键词（尽力而为的启发式过滤）
    # 注意：这不能替代 Claude Code 自身的权限控制，仅作为第一道防线。
    DANGEROUS_KEYWORDS = [
        "rm -rf", "rm -fr", "del /f /s /q", "rd /s /q",
        "format ", "mkfs", "diskpart", "reg delete",
        "shutdown ", "cipher /w", "dd if=",
        ":(){:|:&};:",  # fork bomb
    ]

    def __init__(self, allowed_senders: Optional[List[str]] = None):
        self.allowed_senders = {s.strip().lower() for s in (allowed_senders or [])}

    def check_sender(self, from_email: str) -> bool:
        """检查发件人是否在白名单中（大小写不敏感的精确匹配）

        注意：绝不使用子串匹配，防止 user@qq.com@evil.com 之类的伪造绕过。
        """
        if not self.allowed_senders:
            logger.warning("未配置发件人白名单，放行所有邮件（不安全）")
            return True

        normalized = (from_email or "").strip().lower()
        # 容错：解析 "Name <a@b.com>" 形式
        parsed = re.findall(r'<([^>]+)>', normalized)
        if parsed:
            normalized = parsed[0].strip()

        if normalized in self.allowed_senders:
            return True

        logger.warning(f"发件人不在白名单中: {from_email}")
        return False

    def check_prompt(self, prompt: str) -> bool:
        """检查 prompt 是否包含破坏性指令

        Returns:
            True=安全, False=包含危险内容
        """
        prompt_lower = prompt.lower()

        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in prompt_lower:
                logger.warning(f"检测到危险关键词: {keyword.strip()}")
                return False

        return True

    def sanitize_prompt(self, prompt: str) -> str:
        """清理 prompt，移除敏感信息（路径、API 密钥）"""
        # 移除可能的路径信息
        prompt = re.sub(r'[A-Za-z]:\\[^ \n]+', '[路径]', prompt)
        prompt = re.sub(r'/home/[^ \n]+', '[路径]', prompt)

        # 移除可能的 API 密钥
        prompt = re.sub(r'api[_-]?key["\s:=]+[a-zA-Z0-9_-]+', '[API_KEY]', prompt, flags=re.IGNORECASE)
        prompt = re.sub(r'sk-[a-zA-Z0-9_-]+', '[API_KEY]', prompt)

        return prompt
