"""
SMTP 邮件发送模块

端口与加密方式自动匹配：
- 465: 隐式 TLS (SMTP_SSL)
- 其他端口（如 587）: 明文连接 + STARTTLS
"""
import smtplib
import logging
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional

from core.constants import SMTP_TIMEOUT

logger = logging.getLogger(__name__)

IMPLICIT_TLS_PORT = 465


class SMTPClient:
    """SMTP 邮件客户端"""

    def __init__(self, host: str, port: int, email: str, password: str):
        self.host = host
        self.port = port
        self.email = email
        self.password = password
        self.conn: Optional[smtplib.SMTP] = None

    def connect(self) -> bool:
        """连接到 SMTP 服务器"""
        try:
            if self.port == IMPLICIT_TLS_PORT:
                self.conn = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=SMTP_TIMEOUT
                )
            else:
                self.conn = smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT)
                self.conn.starttls()
            self.conn.login(self.email, self.password)
            logger.info(f"SMTP 连接成功: {self.email}")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"SMTP 连接失败: {e}")
            self.conn = None
            return False
        except OSError as e:
            logger.error(f"SMTP 网络错误: {e}")
            self.conn = None
            return False

    def send(self, to_addr: str, subject: str, body: str, is_html: bool = False) -> bool:
        """发送邮件

        Args:
            to_addr: 收件人
            subject: 主题
            body: 正文
            is_html: 是否为 HTML

        Returns:
            是否发送成功
        """
        if not self.conn and not self.connect():
            return False

        try:
            return self._send_message(to_addr, subject, body, is_html)
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPSenderRefused, OSError) as e:
            # 连接可能被服务器断开，重连一次后重试
            logger.warning(f"发送失败 ({e})，尝试重连...")
            self.close()
            if not self.connect():
                return False
            try:
                return self._send_message(to_addr, subject, body, is_html)
            except smtplib.SMTPException as e2:
                logger.error(f"重试发送失败: {e2}")
                return False
        except smtplib.SMTPException as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def _send_message(self, to_addr: str, subject: str, body: str, is_html: bool) -> bool:
        """构造并发送单封邮件"""
        if not is_html:
            body = self._markdown_to_text(body)

        msg = MIMEMultipart('alternative')
        msg['From'] = self.email
        msg['To'] = to_addr
        msg['Subject'] = Header(subject, 'utf-8')

        text_part = MIMEText(body, 'plain', 'utf-8')
        msg.attach(text_part)

        if is_html:
            html_part = MIMEText(body, 'html', 'utf-8')
            msg.attach(html_part)

        self.conn.sendmail(self.email, [to_addr], msg.as_string())
        logger.info(f"邮件发送成功: {to_addr}")
        return True

    @staticmethod
    def _markdown_to_text(markdown: str) -> str:
        """将 Markdown 转换为纯文本，保留内容可读性"""
        # 移除代码块围栏和行内代码标记（保留代码内容本身）
        text = re.sub(r'```[\w-]*\n?', '', markdown)
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 移除图片
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)

        # 移除链接，保留文字
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)

        # 移除标题标记
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # 移除加粗斜体标记
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'__([^_]+)__', r'\1', text)
        text = re.sub(r'_([^_]+)_', r'\1', text)

        # 移除列表标记
        text = re.sub(r'^[\s]*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[\s]*\d+\.\s+', '', text, flags=re.MULTILINE)

        # 移除水平线
        text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)

        return text.strip()

    def close(self):
        """关闭连接"""
        if self.conn:
            try:
                self.conn.quit()
            except Exception:
                pass
            self.conn = None
