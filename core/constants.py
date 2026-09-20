"""
常量定义
"""
from pathlib import Path

# 项目路径（constants.py 位于 core/ 下，项目根目录是其上一级）
PROJECT_DIR = Path(__file__).parent.parent
LOG_DIR = PROJECT_DIR / "logs"
DATA_DIR = PROJECT_DIR / "data"

# 默认配置
DEFAULT_POLL_INTERVAL = 30
DEFAULT_TIMEOUT = 300
DEFAULT_MAX_RETRIES = 3

# Web 面板
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 5000

# 日志配置
LOG_FILE = LOG_DIR / "email_ai.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# UID 持久化文件
UID_FILE = DATA_DIR / "processed_uids.txt"
UID_MAX_ENTRIES = 10000  # 防止文件无限增长

# 状态与历史记录（供 Web 面板跨进程读取）
HEARTBEAT_FILE = DATA_DIR / "heartbeat.json"
HISTORY_FILE = DATA_DIR / "history.jsonl"
HISTORY_MAX_ENTRIES = 500

# 邮件配置
MAX_EMAIL_BODY_LENGTH = 100000  # 100KB
MAX_REPLY_LENGTH = 50000  # 50KB

MAX_RETRY_COUNT = 3  # Claude 调用最大重试次数（失败后按 1s/2s/4s 指数退避）

# 网络超时
IMAP_TIMEOUT = 30
SMTP_TIMEOUT = 30
