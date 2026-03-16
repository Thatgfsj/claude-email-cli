"""
IMAP 邮件接收模块 - 可靠性强化版
"""
import imaplib
import email
from email import policy
from typing import Optional, Tuple, List, Set
import logging
import json
from pathlib import Path

from core.constants import UID_FILE, IMAP_TIMEOUT, RETRY_DELAYS, MAX_RETRY_COUNT

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
    
    def __init__(self, host: str, port: int, email: str, password: str):
        self.host = host
        self.port = port
        self.email = email
        self.password = password
        self.conn: Optional[imaplib.IMAP4_SSL] = None
        self.processed_uids: Set[str] = set()  # 内存缓存
        self._load_uids()  # 持久化加载
    
    def _load_uids(self):
        """从文件加载已处理 UID"""
        if UID_FILE.exists():
            try:
                with open(UID_FILE, 'r', encoding='utf-8') as f:
                    self.processed_uids = set(json.load(f))
                logger.info(f"已加载 {len(self.processed_uids)} 个已处理 UID")
            except Exception as e:
                logger.warning(f"加载 UID 失败: {e}")
                self.processed_uids = set()
    
    def _save_uids(self):
        """持久化保存 UID"""
        UID_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(UID_FILE, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_uids), f)
        except Exception as e:
            logger.error(f"保存 UID 失败: {e}")
    
    def add_processed_uid(self, uid: str):
        """添加已处理 UID"""
        self.processed_uids.add(uid)
        self._save_uids()
    
    def connect(self) -> bool:
        """连接到 IMAP 服务器"""
        try:
            self.conn = imaplib.IMAP4_SSL(
                host=self.host, 
                port=self.port,
                timeout=IMAP_TIMEOUT
            )
            self.conn.login(self.email, self.password)
            logger.info(f"IMAP 连接成功: {self.email}")
            return True
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            if b'AUTHENTICATIONFAILED' in error_msg.encode():
                raise IMAPAuthError(f"IMAP 认证失败: {e}")
            raise IMAPConnectionError(f"IMAP 连接失败: {e}")
    
    def reconnect(self) -> bool:
        """断线重连（指数退避）"""
        for delay in RETRY_DELAYS:
            logger.warning(f"IMAP 断开，{delay}秒后重连...")
            import time
            time.sleep(delay)
            try:
                if self.connect():
                    return True
            except IMAPAuthError:
                logger.error("认证失败，停止重试")
                raise
            except Exception as e:
                logger.error(f"重连失败: {e}")
        return False
    
    def check_new_emails(self, folder: str = "INBOX") -> List[Tuple[str, str, str]]:
        """检查新邮件
        
        Returns:
            List of (uid, from_email, body) tuples
        """
        if not self.conn:
            try:
                self.connect()
            except IMAPError:
                return []
        
        try:
            self.conn.select(folder, readonly=True)  # 只读模式防止误标记
            status, messages = self.conn.search(None, 'UNSEEN')
            if status != 'OK':
                return []
            
            email_ids = messages[0].split()
            if not email_ids:
                return []
            
            new_emails = []
            
            for email_id in email_ids:
                try:
                    # 获取邮件 UID
                    status, uid_data = self.conn.fetch(email_id, 'UID')
                    if status != 'OK':
                        continue
                    
                    uid = uid_data[0].decode().split()[2]
                    
                    # 去重
                    if uid in self.processed_uids:
                        continue
                    
                    # 获取邮件内容
                    status, msg_data = self.conn.fetch(email_id, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    msg = email.message_from_bytes(msg_data[0][1], policy=policy.default)
                    from_addr = email.utils.parseaddr(msg.get('From'))[1]
                    body = self._get_email_body(msg)
                    
                    if body:
                        new_emails.append((uid, from_addr, body))
                        
                except Exception as e:
                    logger.error(f"处理邮件 {email_id} 失败: {e}")
                    continue
            
            # 标记为已读
            if new_emails:
                uids_to_mark = [e[0] for e in new_emails]
                try:
                    self.conn.store(','.join(uids_to_mark), '+FLAGS', '\\Seen')
                except Exception as e:
                    logger.warning(f"标记已读失败: {e}")
            
            return new_emails
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP 错误: {e}")
            try:
                self.reconnect()
            except:
                pass
            return []
        except Exception as e:
            logger.exception(f"检查邮件异常: {e}")
            return []
    
    def _get_email_body(self, msg: email.message.Message) -> str:
        """提取邮件正文（流式读取限制）"""
        from core.constants import MAX_EMAIL_BODY_LENGTH
        
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/plain':
                    try:
                        body = part.get_content()
                        break
                    except:
                        pass
        else:
            if msg.get_content_type() == 'text/plain':
                try:
                    body = msg.get_content()
                except:
                    pass
        
        # 清理 HTML
        import re
        body = re.sub(r'<[^>]+>', '', body)
        body = body.strip()
        
        # 限制长度
        if len(body) > MAX_EMAIL_BODY_LENGTH:
            body = body[:MAX_EMAIL_BODY_LENGTH] + "\n\n[内容已截断...]"
        
        return body
    
    def close(self):
        """关闭连接"""
        if self.conn:
            try:
                self.conn.close()
                self.conn.logout()
            except:
                pass
