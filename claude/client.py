"""
Claude CLI 调用模块

安全说明：
- 使用参数列表 + shell=False 调用，邮件正文通过 stdin 传入，
  邮件内容无法注入 shell 命令。
"""
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Claude CLI 客户端"""

    def __init__(self, claude_path: str = "claude", timeout: int = 300):
        self.claude_path = claude_path
        self.timeout = timeout

    def _resolve_executable(self) -> str:
        """解析可执行文件完整路径（兼容 Windows 下 claude.cmd 等 npm shim）"""
        resolved = shutil.which(self.claude_path)
        return resolved or self.claude_path

    def chat(self, prompt: str) -> Optional[str]:
        """发送对话请求到 Claude（print 模式）

        Args:
            prompt: 用户提示词（通过 stdin 传递，避免参数注入）

        Returns:
            Claude 的回复，失败返回 None
        """
        cmd = [self._resolve_executable(), "-p"]
        logger.info("正在调用 Claude...")

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                errors='replace',
                shell=False,
            )
        except subprocess.TimeoutExpired:
            logger.error(f"Claude 执行超时 ({self.timeout}s)")
            return None
        except FileNotFoundError:
            logger.error(f"找不到 Claude CLI: {self.claude_path}，请检查 CLAUDE_PATH 配置")
            return None
        except Exception as e:
            logger.exception(f"Claude 调用异常: {e}")
            return None

        if result.returncode == 0:
            output = (result.stdout or "").strip()
            if not output:
                logger.warning("Claude 返回了空响应")
                return None
            logger.info(f"Claude 响应成功 ({len(output)} 字符)")
            return output

        stderr = (result.stderr or "").strip()
        logger.error(f"Claude 执行失败 (exit={result.returncode}): {stderr[:500]}")
        return None

    def chat_with_system(self, system: str, user: str) -> Optional[str]:
        """带系统提示的对话"""
        prompt = f"{system}\n\n用户: {user}"
        return self.chat(prompt)
