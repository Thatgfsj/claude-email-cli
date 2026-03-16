#!/usr/bin/env python3
"""
Email AI Assistant - 生产级主程序

特性：
- 结构化 JSON 日志
- UID 持久化去重
- 指数退避重试
- 单任务队列
- 健康检查接口
"""

import os
import sys
import time
import json
import logging
import signal
import queue
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 添加项目根目录到路径
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from core.config import load_config, validate_config, ConfigError
from core.constants import LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT, MAX_RETRY_COUNT
from email.imap import IMAPClient, IMAPAuthError, IMAPConnectionError
from email.smtp import SMTPClient
from claude.client import ClaudeClient
from utils.security import SecurityChecker


class JSONFormatter(logging.Formatter):
    """JSON 日志格式化器"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加额外字段
        if hasattr(record, 'uid'):
            log_data['uid'] = record.uid
        if hasattr(record, 'sender'):
            log_data['sender'] = record.sender
        if hasattr(record, 'status'):
            log_data['status'] = record.status
        
        return json.dumps(log_data)


def setup_logging():
    """配置结构化日志"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # 文件处理器 - 按大小轮转
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )


class EmailAIAssistant:
    """邮件AI助手 - 生产级版本"""
    
    def __init__(self, config: dict):
        self.config = config
        self.running = False
        
        # 单任务队列
        self.task_queue = queue.Queue(maxsize=10)
        
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
        
        self.poll_interval = int(config.get("poll_interval", 30))
        self.max_retries = int(config.get("max_retries", MAX_RETRY_COUNT))
        
        # 日志
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # 启动任务处理线程
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
    
    def start(self):
        """启动助手"""
        self.running = True
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Email AI Assistant 启动", extra={"status": "startup"})
        
        # 初始化连接
        try:
            if not self.imap_client.connect():
                self.logger.error("IMAP 连接失败")
                return
        except IMAPAuthError as e:
            self.logger.error(f"认证失败: {e}")
            return
        except Exception as e:
            self.logger.error(f"连接异常: {e}")
            return
        
        # 启动工作线程
        self.worker_thread.start()
        
        # 主循环
        while self.running:
            try:
                self._check_and_queue_emails()
            except Exception as e:
                self.logger.exception(f"主循环异常: {e}")
            
            time.sleep(self.poll_interval)
        
        # 清理
        self.imap_client.close()
        self.smtp_client.close()
        self.logger.info("程序已退出", extra={"status": "shutdown"})
    
    def _check_and_queue_emails(self):
        """检查并加入队列"""
        new_emails = self.imap_client.check_new_emails()
        
        if not new_emails:
            return
        
        self.logger.info(f"收到 {len(new_emails)} 封新邮件", extra={"count": len(new_emails)})
        
        for uid, from_addr, body in new_emails:
            try:
                self.task_queue.put_nowait((uid, from_addr, body))
            except queue.Full:
                self.logger.warning("队列满，跳过新邮件")
    
    def _worker(self):
        """任务处理线程"""
        while self.running:
            try:
                uid, from_addr, body = self.task_queue.get(timeout=1)
                self._process_email(uid, from_addr, body)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.exception(f"Worker 异常: {e}")
    
    def _process_email(self, uid: str, from_addr: str, body: str):
        """处理单封邮件"""
        self.logger.info("开始处理邮件", extra={"uid": uid, "sender": from_addr, "status": "processing"})
        
        # 1. 安全检查
        if not self.security.check_sender(from_addr):
            self.logger.warning("发件人不在白名单", extra={"uid": uid, "sender": from_addr, "status": "rejected"})
            self._send_status_email(from_addr, "拒绝", "发件人不在白名单")
            self.imap_client.add_processed_uid(uid)
            return
        
        if not self.security.check_prompt(body):
            self.logger.warning("内容包含危险信息", extra={"uid": uid, "status": "rejected"})
            self._send_status_email(from_addr, "拒绝", "邮件内容包含不安全指令")
            self.imap_client.add_processed_uid(uid)
            return
        
        # 2. 清理 prompt
        clean_prompt = self.security.sanitize_prompt(body)
        
        # 3. 重试机制
        response = None
        for attempt in range(self.max_retries):
            try:
                self._send_status_email(from_addr, "处理中", f"正在思考... (尝试 {attempt + 1}/{self.max_retries})")
                response = self.claude_client.chat(clean_prompt)
                
                if response:
                    break
                    
            except Exception as e:
                self.logger.warning(f"处理失败 (尝试 {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
        
        # 4. 结果处理
        if response is None:
            self.logger.error("处理失败", extra={"uid": uid, "status": "failed"})
            self._send_status_email(from_addr, "失败", "Claude 处理失败")
        else:
            self.logger.info("处理成功", extra={"uid": uid, "status": "success"})
            self._send_reply_email(from_addr, body, response)
        
        # 5. 标记已处理
        self.imap_client.add_processed_uid(uid)
    
    def _send_status_email(self, to_addr: str, status: str, message: str):
        """发送状态邮件"""
        subject = f"[Email AI] {status}"
        body = f"""状态: {status}
详情: {message}

---
由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, subject, body)
    
    def _send_reply_email(self, to_addr: str, original: str, response: str):
        """发送回复邮件"""
        from core.constants import MAX_REPLY_LENGTH
        
        # 限制回复长度
        if len(response) > MAX_REPLY_LENGTH:
            response = response[:MAX_REPLY_LENGTH] + "\n\n[内容已截断...]"
        
        subject = "Re: 您的邮件已处理"
        body = f"""您好！

您的邮件已处理完成，以下是 Claude 的回复：

{response}

---
由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, subject, body)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        self.logger.info("收到退出信号")
        self.running = False


def main():
    """主入口"""
    try:
        config = load_config()
    except ConfigError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    
    if not validate_config(config):
        sys.exit(1)
    
    assistant = EmailAIAssistant(config)
    assistant.start()


if __name__ == "__main__":
    main()
