#!/usr/bin/env python3
"""
Email AI Assistant - 邮件AI助手主程序

功能：
- 监控邮箱新邮件
- 将邮件内容发送给 Claude CLI 处理
- 将结果通过邮件发回给发件人

安全特性：
- 发件人白名单校验
- 危险命令过滤
- 邮件 UID 去重
- 异常自动重连
"""

import os
import sys
import time
import logging
import signal
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.config import load_config, validate_config
from email.imap import IMAPClient
from email.smtp import SMTPClient
from claude.client import ClaudeClient
from utils.security import SecurityChecker


class EmailAIAssistant:
    """邮件AI助手主类"""
    
    def __init__(self, config: dict):
        self.config = config
        self.running = False
        
        # 初始化各模块
        self.imap_client = IMAPClient(
            host=config["imap_host"],
            port=int(config.get("imap_port", 993)),
            email=config["email"],
            password=config["password"]
        )
        
        self.smtp_client = SMTPClient(
            host=config["smtp_host"],
            port=int(config.get("smtp_port", 465)),
            email=config["email"],
            password=config["password"]
        )
        
        self.claude_client = ClaudeClient(
            claude_path=config.get("claude_path", "claude"),
            timeout=int(config.get("timeout", 300))
        )
        
        self.security = SecurityChecker(
            allowed_senders=config.get("allowed_senders")
        )
        
        # 轮询间隔
        self.poll_interval = int(config.get("poll_interval", 30))
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """配置日志"""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'email_ai.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def start(self):
        """启动助手"""
        self.running = True
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logging.info("=" * 50)
        logging.info("Email AI Assistant 启动")
        logging.info(f"轮询间隔: {self.poll_interval}秒")
        logging.info("=" * 50)
        
        # 初始化连接
        if not self.imap_client.connect():
            logging.error("IMAP 连接失败，程序退出")
            return
        
        if not self.smtp_client.connect():
            logging.error("SMTP 连接失败，程序退出")
            return
        
        # 主循环
        while self.running:
            try:
                self._check_and_process_emails()
            except Exception as e:
                logging.exception(f"主循环异常: {e}")
            
            # 休眠
            time.sleep(self.poll_interval)
        
        # 清理
        self.imap_client.close()
        self.smtp_client.close()
        logging.info("程序已退出")
    
    def _check_and_process_emails(self):
        """检查并处理新邮件"""
        new_emails = self.imap_client.check_new_emails()
        
        if not new_emails:
            return
        
        logging.info(f"收到 {len(new_emails)} 封新邮件")
        
        for uid, from_addr, body in new_emails:
            self._process_email(uid, from_addr, body)
    
    def _process_email(self, uid: str, from_addr: str, body: str):
        """处理单封邮件"""
        logging.info(f"处理邮件 from: {from_addr}")
        
        # 1. 安全检查：发件人白名单
        if not self.security.check_sender(from_addr):
            logging.warning(f"发件人不在白名单，跳过: {from_addr}")
            self._send_status_email(from_addr, "拒绝", "发件人不在白名单中")
            return
        
        # 2. 安全检查：内容过滤
        if not self.security.check_prompt(body):
            logging.warning(f"内容包含危险信息，跳过")
            self._send_status_email(from_addr, "拒绝", "邮件内容包含不安全指令")
            return
        
        # 3. 清理 prompt
        clean_prompt = self.security.sanitize_prompt(body)
        
        # 4. 发送处理中状态
        self._send_status_email(from_addr, "处理中", "正在思考...")
        
        # 5. 调用 Claude
        response = self.claude_client.chat(clean_prompt)
        
        if response is None:
            self._send_status_email(from_addr, "失败", "Claude 处理失败")
            return
        
        # 6. 发送回复
        self._send_reply_email(from_addr, body, response)
        
        # 7. 标记为已读
        logging.info(f"邮件处理完成: {uid}")
    
    def _send_status_email(self, to_addr: str, status: str, message: str):
        """发送状态邮件"""
        subject = f"[Email AI] {status}"
        body = f"""
状态: {status}
详情: {message}

---
由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, subject, body)
    
    def _send_reply_email(self, to_addr: str, original: str, response: str):
        """发送回复邮件"""
        subject = "Re: 您的邮件已处理"
        body = f"""
您好！

您的邮件已处理完成，以下是 Claude 的回复：

{response}

---
原始邮件:
{original[:200]}...

由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, subject, body)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logging.info("收到退出信号，正在关闭...")
        self.running = False


def main():
    """主入口"""
    # 加载配置
    config = load_config()
    
    # 验证配置
    if not validate_config(config):
        sys.exit(1)
    
    # 启动助手
    assistant = EmailAIAssistant(config)
    assistant.start()


if __name__ == "__main__":
    main()
