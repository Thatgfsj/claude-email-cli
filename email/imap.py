"""
IMAP 邮件接收模块
"""
import imaplib
import email
from email import policy
from typing import Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)


class IMAPClient:
    """IMAP 邮件客户端"""
    
    def __init__(self, host: str, port: int, email: str, password: str):
        self.host = host
        self.port = port
        self.email = email
        self.password = password
        self.conn: Optional[imaplib.IMAP4_SSL] = None
        self.processed_uids: set = set()  # 已处理邮件 UID 去重
    
    def connect(self) -> bool:
        """连接到 IMAP 服务器"""
        try:
            self.conn = imaplib.IMAP4_SSL(host=self.host, port=self.port)
            self.conn.login(self.email, self.password)
            logger.info(f"IMAP 连接成功: {self.email}")
            return True
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP 连接失败: {e}")
            return False
    
    def reconnect(self) -> bool:
        """断线重连"""
        logger.warning("IMAP 断开，尝试重连...")
        try:
            if self.conn:
                try:
                    self.conn.close()
                except:
                    pass
            return self.connect()
        except Exception as e:
            logger.error(f"IMAP 重连失败: {e}")
            return False
    
    def check_new_emails(self, folder: str = "INBOX") -> List[Tuple[str, str, str]]:
        """检查新邮件
        
        Returns:
            List of (uid, from_email, body) tuples
        """
        if not self.conn:
            if not self.connect():
                return []
        
        try:
            self.conn.select(folder)
            # 搜索未读邮件
            status, messages = self.conn.search(None, 'UNSEEN')
            if status != 'OK':
                logger.warning(f"搜索邮件失败: {status}")
                return []
            
            email_ids = messages[0].split()
            new_emails = []
            
            for email_id in email_ids:
                # 获取邮件 UID
                status, uid_data = self.conn.fetch(email_id, 'UID')
                if status != 'OK':
                    continue
                
                uid = uid_data[0].decode().split()[2]
                
                # 去重：跳过已处理的 UID
                if uid in self.processed_uids:
                    continue
                
                # 获取邮件内容
                status, msg_data = self.conn.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                msg = email.message_from_bytes(msg_data[0][1], policy=policy.default)
                
                # 提取发件人
                from_addr = email.utils.parseaddr(msg.get('From'))[1]
                
                # 提取邮件正文
                body = self._get_email_body(msg)
                
                if body:
                    new_emails.append((uid, from_addr, body))
                    self.processed_uids.add(uid)  # 标记为已处理
            
            return new_emails
            
        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP 错误: {e}")
            self.reconnect()
            return []
        except Exception as e:
            logger.exception(f"检查邮件异常: {e}")
            return []
    
    def _get_email_body(self, msg: email.message.Message) -> str:
        """提取邮件正文"""
        body = ""
        
        if msg.is_multipart():
            # 多部分邮件
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body = part.get_content()
                        break
                    except:
                        pass
        else:
            # 单部分邮件
            if msg.get_content_type() == 'text/plain':
                try:
                    body = msg.get_content()
                except:
                    pass
        
        # 清理 HTML 标签
        import re
        body = re.sub(r'<[^>]+>', '', body)
        return body.strip()
    
    def close(self):
        """关闭连接"""
        if self.conn:
            try:
                self.conn.close()
                self.conn.logout()
            except:
                pass
