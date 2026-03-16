"""
Claude CLI 调用模块
"""
import subprocess
import logging
import shlex
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude CLI 客户端"""
    
    def __init__(self, claude_path: str = "claude", timeout: int = 300):
        self.claude_path = claude_path
        self.timeout = timeout
    
    def chat(self, prompt: str) -> Optional[str]:
        """发送对话请求到 Claude
        
        Args:
            prompt: 用户提示词
        
        Returns:
            Claude 的回复，失败返回 None
        """
        try:
            # 构建命令
            # 使用 --print 选项直接输出结果
            cmd = f'{self.claude_path} chat "{prompt}" --print'
            
            logger.info(f"正在调用 Claude...")
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                logger.info(f"Claude 响应成功 ({len(output)} 字符)")
                return output
            else:
                logger.error(f"Claude 执行失败: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Claude 执行超时 ({self.timeout}s)")
            return None
        except Exception as e:
            logger.exception(f"Claude 调用异常: {e}")
            return None
    
    def chat_with_system(self, system: str, user: str) -> Optional[str]:
        """带系统提示的对话
        
        Args:
            system: 系统提示
            user: 用户输入
        
        Returns:
            Claude 的回复
        """
        prompt = f"{system}\n\n用户: {user}"
        return self.chat(prompt)
