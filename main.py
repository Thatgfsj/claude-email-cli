#!/usr/bin/env python3
"""
Email AI Assistant - 生产级主程序

特性：
- 结构化 JSON 日志
- UID 持久化去重（at-least-once 处理）
- 指数退避重试
- 单任务队列
- 心跳/历史文件（供 Web 面板读取）
"""

import json
import logging
import queue
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

# 添加项目根目录到路径
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from core.config import load_config, validate_config, ConfigError
from core.constants import (
    LOG_FILE, LOG_MAX_BYTES, LOG_BACKUP_COUNT, MAX_RETRY_COUNT,
    MAX_REPLY_LENGTH, HEARTBEAT_FILE, HISTORY_FILE, HISTORY_MAX_ENTRIES,
    DATA_DIR,
)
from mailer.imap import IMAPClient, IMAPAuthError, IMAPConnectionError
from mailer.smtp import SMTPClient
from claude.client import ClaudeClient
from utils.security import SecurityChecker


class JSONFormatter(logging.Formatter):
    """JSON 日志格式化器"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 添加额外字段
        for field in ('uid', 'sender', 'status', 'count'):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        return json.dumps(log_data, ensure_ascii=False)


def setup_logging():
    """配置结构化日志"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())

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
        self.emails_processed = 0
        self.last_poll_time: Optional[float] = None

        # 单任务队列（防止 Claude CLI 并发阻塞）
        self.task_queue: queue.Queue = queue.Queue(maxsize=10)

        self.imap_client = IMAPClient(
            host=config["imap_host"],
            port=int(config.get("imap_port", 993)),
            email_addr=config["email"],
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

        setup_logging()
        self.logger = logging.getLogger(__name__)

        self.worker_thread = threading.Thread(target=self._worker, daemon=True)

    # ---------- 生命周期 ----------

    def start(self):
        """启动助手（阻塞运行，直到收到停止信号）"""
        self.running = True
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # 信号处理只能在主线程注册
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("Email AI Assistant 启动", extra={"status": "startup"})

        try:
            self.imap_client.connect()
        except IMAPAuthError as e:
            self.logger.error(f"认证失败: {e}")
            self.running = False
            return
        except Exception as e:
            self.logger.error(f"IMAP 初始连接失败（将在轮询时重试）: {e}")

        self.worker_thread.start()

        # 主循环
        while self.running:
            self.last_poll_time = time.time()
            self._write_heartbeat()
            try:
                self._check_and_queue_emails()
            except Exception as e:
                self.logger.exception(f"主循环异常: {e}")

            # 用短分片 sleep 替代长 sleep，保证退出响应及时
            self._interruptible_sleep(self.poll_interval)

        self._shutdown()

    def stop(self):
        """请求停止（可从其他线程调用）"""
        self.running = False

    def _shutdown(self):
        """清理资源，尽量处理完队列中的剩余任务"""
        self.logger.info("正在退出，处理剩余任务...", extra={"status": "shutdown"})
        deadline = time.time() + 60
        while not self.task_queue.empty() and time.time() < deadline:
            try:
                uid, from_addr, subject, body = self.task_queue.get(timeout=1)
            except queue.Empty:
                break
            try:
                self._process_email(uid, from_addr, subject, body)
            except Exception:
                self.logger.exception("处理剩余任务失败")

        self.imap_client.close()
        self.smtp_client.close()
        self._write_heartbeat(stopped=True)
        self.logger.info("程序已退出", extra={"status": "shutdown"})

    def _interruptible_sleep(self, seconds: float):
        end = time.time() + seconds
        while self.running and time.time() < end:
            time.sleep(min(1, max(0, end - time.time())))

    def _signal_handler(self, signum, frame):
        """信号处理"""
        self.logger.info(f"收到退出信号 ({signum})")
        self.running = False

    # ---------- 状态文件 ----------

    def _write_heartbeat(self, stopped: bool = False):
        """写心跳文件，供 Web 面板判断服务是否存活"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            HEARTBEAT_FILE.write_text(json.dumps({
                "running": not stopped and self.running,
                "last_poll": self.last_poll_time,
                "emails_processed": self.emails_processed,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            self.logger.warning(f"写心跳失败: {e}")

    def _append_history(self, sender: str, subject: str, status: str):
        """追加处理历史（JSON Lines，供 Web 面板展示）"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            entry = json.dumps({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sender": sender,
                "subject": subject or "(无主题)",
                "status": status,
            }, ensure_ascii=False)
            lines = []
            if HISTORY_FILE.exists():
                lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
            lines.append(entry)
            lines = lines[-HISTORY_MAX_ENTRIES:]
            HISTORY_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as e:
            self.logger.warning(f"写历史记录失败: {e}")

    # ---------- 邮件处理 ----------

    def _check_and_queue_emails(self):
        """检查并加入队列"""
        new_emails = self.imap_client.check_new_emails()

        if not new_emails:
            return

        self.logger.info(f"收到 {len(new_emails)} 封新邮件", extra={"count": len(new_emails)})

        for uid, from_addr, subject, body in new_emails:
            try:
                self.task_queue.put_nowait((uid, from_addr, subject, body))
            except queue.Full:
                self.logger.warning("队列满，跳过新邮件", extra={"uid": uid})

    def _worker(self):
        """任务处理线程"""
        while self.running or not self.task_queue.empty():
            try:
                uid, from_addr, subject, body = self.task_queue.get(timeout=1)
                self._process_email(uid, from_addr, subject, body)
            except queue.Empty:
                continue
            except Exception:
                self.logger.exception("Worker 异常")

    def _process_email(self, uid: str, from_addr: str, subject: str, body: str):
        """处理单封邮件"""
        self.logger.info(
            "开始处理邮件",
            extra={"uid": uid, "sender": from_addr, "status": "processing"}
        )

        # 1. 白名单检查：陌生发件人静默丢弃（不回复，避免被当作垃圾邮件跳板）
        if not self.security.check_sender(from_addr):
            self.logger.warning(
                "发件人不在白名单，已静默丢弃",
                extra={"uid": uid, "sender": from_addr, "status": "rejected"}
            )
            self._finish(uid)
            return

        # 2. 内容安全检查（对白名单发件人给出拒绝回执）
        if not self.security.check_prompt(body):
            self.logger.warning(
                "内容包含破坏性指令",
                extra={"uid": uid, "status": "rejected"}
            )
            self._send_status_email(from_addr, "拒绝", "邮件内容包含不安全的破坏性指令")
            self._append_history(from_addr, subject, "rejected")
            self._finish(uid)
            return

        # 3. 清理 prompt
        clean_prompt = self.security.sanitize_prompt(body)

        # 4. 通知 + 重试机制（指数退避）
        self._send_status_email(from_addr, "处理中", "正在思考，请稍候...")
        response = None
        for attempt in range(self.max_retries):
            try:
                response = self.claude_client.chat(clean_prompt)
                if response:
                    break
            except Exception as e:
                self.logger.warning(f"处理失败 (尝试 {attempt + 1}): {e}")

            if attempt < self.max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避

        # 5. 结果处理
        if response is None:
            self.logger.error("处理失败", extra={"uid": uid, "status": "failed"})
            self._send_status_email(from_addr, "失败", "Claude 处理失败，请稍后重试")
            self._append_history(from_addr, subject, "failed")
        else:
            self.emails_processed += 1
            self.logger.info("处理成功", extra={"uid": uid, "status": "success"})
            self._send_reply_email(from_addr, subject, response)
            self._append_history(from_addr, subject, "success")

        # 6. 标记已处理（持久化 UID + 标记已读）
        self._finish(uid)

    def _finish(self, uid: str):
        """收尾：UID 去重 + 标记已读"""
        self.imap_client.add_processed_uid(uid)
        self.imap_client.mark_seen(uid)

    # ---------- 邮件发送 ----------

    def _send_status_email(self, to_addr: str, status: str, message: str):
        """发送状态邮件"""
        subject = f"[Email AI] {status}"
        body = f"""状态: {status}
详情: {message}

---
由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, subject, body)

    def _send_reply_email(self, to_addr: str, original_subject: str, response: str):
        """发送回复邮件（引用原邮件主题）"""
        if len(response) > MAX_REPLY_LENGTH:
            response = response[:MAX_REPLY_LENGTH] + "\n\n[内容已截断...]"

        reply_subject = f"Re: {original_subject}" if original_subject else "Re: 您的邮件已处理"
        body = f"""您好！

您的邮件已处理完成，以下是 Claude 的回复：

{response}

---
由 Email AI Assistant 自动发送
"""
        self.smtp_client.send(to_addr, reply_subject, body)


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
