"""
安全检查模块
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SecurityChecker:
    """安全检查器"""
    
    # 危险命令关键词
    DANGEROUS_KEYWORDS = [
        "rm -rf", "del /f /s /q", "format", "mkfs",
        "powershell -", "cmd /c", "bash -c",
        "wget", "curl | sh", "eval ", "exec ",
        "import os", "import sys", "subprocess",
        ">; ", ">> ", "| ", "&& ", "|| ",
    ]
    
    # 允许的命令类型
    ALLOWED_COMMANDS = [
        "问", "查询", "请", "帮我", "告诉",
        "解释", "说明", "什么是", "如何",
        "写", "创建", "生成", "翻译",
    ]
    
    def __init__(self, allowed_senders: Optional[List[str]] = None):
        self.allowed_senders = set(allowed_senders or [])
    
    def check_sender(self, from_email: str) -> bool:
        """检查发件人是否在白名单中"""
        if not self.allowed_senders:
            logger.warning("未配置发件人白名单，放行所有邮件")
            return True
        
        # 简单匹配：检查域名和用户名
        for allowed in self.allowed_senders:
            if allowed in from_email or from_email.endswith(allowed):
                return True
        
        logger.warning(f"发件人不在白名单中: {from_email}")
        return False
    
    def check_prompt(self, prompt: str) -> bool:
        """检查 prompt 是否包含危险内容
        
        Returns:
            True=安全, False=包含危险内容
        """
        prompt_lower = prompt.lower()
        
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword.lower() in prompt_lower:
                logger.warning(f"检测到危险关键词: {keyword}")
                return False
        
        return True
    
    def sanitize_prompt(self, prompt: str) -> str:
        """清理 prompt，移除敏感信息"""
        import re
        
        # 移除可能的路径信息
        prompt = re.sub(r'[A-Za-z]:\\[^ \n]+', '[路径]', prompt)
        prompt = re.sub(r'/home/[^ \n]+', '[路径]', prompt)
        
        # 移除可能的 API 密钥
        prompt = re.sub(r'api[_-]?key["\s:=]+[a-zA-Z0-9_-]+', '[API_KEY]', prompt, flags=re.IGNORECASE)
        prompt = re.sub(r'sk-[a-zA-Z0-9_-]+', '[API_KEY]', prompt)
        
        return prompt
