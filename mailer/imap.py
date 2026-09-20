"""
IMAP 邮件接收模块 - 可靠性强化版

统一使用 imaplib 的 UID API：
- UID 在会话之间稳定，配合本地持久化去重
- 搜索/抓取/标记已读全部基于 UID，避免序号漂移
"""
import email
import email.utils
import imaplib
import json
import logging
import re
from email import policy
from typing import List, Optional, Set, Tuple

from core.constants import (
    UID_FILE,
    UID_MAX_ENTRIES,
    IMAP_TIMEOUT,
    MAX_EMAIL_BODY_LENGTH,
)

logger = logging.getLogger(__name__)


class IMAPError(Exception):
    """IMAP 错误基类"""
    pass


class IMAPAuthError(IMAPError):
    """认证失败"""
    pass


class IMAPConnectionError(IMAPError):
    """连接失败"""
    pass


class IMAPClient:
    """IMAP 邮件客户端 - 可靠性强化"""

    def __init__(self, host: str, port: int, email_addr: str, password: str):
        self.host = host
        self.port = port
        self.email = email_addr
        self.password = password
        self.conn: Optional[imaplib.IMAP4_SSL] = None
        self.processed_uids: Set[str] = set()  # 内存缓存
        self._load_uids()  # 持久化加载

    # ---------- UID 持久化 ----------

    def _load_uids(self):
        """从文件加载已处理 UID"""
        if UID_FILE.exists():
            try:
                data = json.loads(UID_FILE.read_text(encoding='utf-8'))
                self.processed_uids = set(data)
                logger.info(f"已加载 {len(self.processed_uids)} 个已处理 UID")
            except (OSError, ValueError) as e:
                logger.warning(f"加载 UID 失败: {e}")
                self.processed_uids = set()

    def _save_uids(self):
        """持久化保存 UID（限制条目数，防止文件无限增长）"""
        UID_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            uids = list(self.processed_uids)
            if len(uids) > UID_MAX_ENTRIES:
                uids = uids[-UID_MAX_ENTRIES:]
                self.processed_uids = set(uids)
            UID_FILE.write_text(json.dumps(uids), encoding='utf-8')
        except OSError as e:
            logger.error(f"保存 UID 失败: {e}")

    def add_processed_uid(self, uid: str):
        """添加已处理 UID 并持久化"""
        self.processed_uids.add(uid)
        self._save_uids()

    # ---------- 连接管理 ----------

    def connect(self) -> bool:
        """连接到 IMAP 服务器"""
        try:
            self.conn = imaplib.IMAP4_SSL(
                host=self.host,
                port=self.port,
                timeout=IMAP_TIMEOUT,
            )
            self.conn.login(self.email, self.password)
            logger.info(f"IMAP 连接成功: {self.email}")
            return True
        except imaplib.IMAP4.error as e:
            self.conn = None
            error_msg = str(e)
            if 'AUTHENTICATIONFAILED' in error_msg:
                raise IMAPAuthError(f"IMAP 认证失败: {e}")
            raise IMAPConnectionError(f"IMAP 连接失败: {e}")
        except OSError as e:
            self.conn = None
            raise IMAPConnectionError(f"IMAP 网络错误: {e}")

    def _ensure_connection(self):
        """确保连接可用，必要时重连（失败抛 IMAPError，由调用方决定重试时机）"""
        if self.conn is None:
            self.connect()

    # ---------- 邮件获取 ----------

    def check_new_emails(self, folder: str = "INBOX") -> List[Tuple[str, str, str, str]]:
        """检查新邮件（UNSEEN 且未被本地去重记录的邮件）

        Returns:
            List of (uid, from_email, subject, body) tuples
        """
        try:
            self._ensure_connection()
            # 非只读模式：处理完的邮件需要标记已读，避免依赖服务器 UNSEEN 状态
            status, _ = self.conn.select(folder)
            if status != 'OK':
                logger.error(f"选择邮箱文件夹失败: {folder}")
                return []

            status, data = self.conn.uid('search', None, 'UNSEEN')
            if status != 'OK':
                return []

            unread_uids = data[0].split()
            if not unread_uids:
                return []

            new_emails = []
            for uid_bytes in unread_uids:
                uid = uid_bytes.decode('ascii', errors='replace')
                if uid in self.processed_uids:
                    continue
                try:
                    entry = self._fetch_email(uid)
                    if entry:
                        new_emails.append(entry)
                except Exception as e:
                    logger.error(f"处理邮件 UID={uid} 失败: {e}")
                    continue

            return new_emails

        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.error(f"IMAP 错误: {e}")
            self.close()
            return []
        except IMAPError as e:
            logger.error(f"IMAP 连接问题: {e}")
            return []
        except Exception as e:
            logger.exception(f"检查邮件异常: {e}")
            self.close()
            return []

    def _fetch_email(self, uid: str) -> Optional[Tuple[str, str, str, str]]:
        """抓取单封邮件，返回 (uid, from, subject, body)"""
        status, msg_data = self.conn.uid('fetch', uid, '(RFC822)')
        if status != 'OK' or not msg_data or msg_data[0] is None:
            return None

        raw_bytes = msg_data[0][1]
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)

        from_addr = email.utils.parseaddr(str(msg.get('From', '')))[1]
        subject = self._decode_subject(msg)
        body = self._get_email_body(msg)

        if not body:
            return None
        return (uid, from_addr, subject, body)

    @staticmethod
    def _decode_subject(msg: email.message.Message) -> str:
        """解码邮件主题"""
        try:
            return str(msg.get('Subject', '') or '').strip()
        except Exception:
            return ''

    def mark_seen(self, uid: str):
        """将邮件标记为已读（处理完成后调用）"""
        if not self.conn:
            return
        try:
            self.conn.uid('store', uid, '+FLAGS', '(\\Seen)')
        except (imaplib.IMAP4.abort, imaplib.IMAP4.error) as e:
            logger.warning(f"标记已读失败 UID={uid}: {e}")

    # ---------- 正文提取 ----------

    def _get_email_body(self, msg: email.message.Message) -> str:
        """提取邮件正文（优先 text/plain，限制长度）"""
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        body = part.get_content()
                        break
                    except Exception:
                        continue
            # 纯文本缺失时回退到 HTML 部分
            if not body:
                for part in msg.walk():
                    if part.get_content_type() == 'text/html':
                        try:
                            body = part.get_content()
                            break
                        except Exception:
                            continue
        elif msg.get_content_type() == 'text/plain':
            try:
                body = msg.get_content()
            except Exception:
                body = ""

        body = self._strip_html(body).strip()

        if len(body) > MAX_EMAIL_BODY_LENGTH:
            body = body[:MAX_EMAIL_BODY_LENGTH] + "\n\n[内容已截断...]"

        return body

    @staticmethod
    def _strip_html(text: str) -> str:
        """粗略清理 HTML 标签，保留可见文本"""
        if not text:
            return ""
        text = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', '', text)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '', text)
        return text

    def close(self):
        """关闭连接"""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            try:
                self.conn.logout()
            except Exception:
                pass
            self.conn = None
