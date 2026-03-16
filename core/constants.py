"""
常量定义
"""
import os
from pathlib import Path

# 项目路径
PROJECT_DIR = Path(__file__).parent
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"

# 配置文件
CONFIG_FILE = "config.json"
CONFIG_EXAMPLE = "config.example.json"

# 默认配置
DEFAULT_POLL_INTERVAL = 30
DEFAULT_TIMEOUT = 300
DEFAULT_MAX_RETRIES = 3

# 日志配置
LOG_FILE = LOG_DIR / "email_ai.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# UID 持久化文件
UID_FILE = DATA_DIR / "processed_uids.txt"

# 邮件配置
MAX_EMAIL_BODY_LENGTH = 100000  # 100KB
MAX_REPLY_LENGTH = 50000  # 50KB

# 重试配置
RETRY_DELAYS = [5, 15, 60]  # 指数退避
MAX_RETRY_COUNT = 3

# 网络超时
IMAP_TIMEOUT = 30
SMTP_TIMEOUT = 30
NETWORK_TIMEOUT = 10
