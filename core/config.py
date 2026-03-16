"""
配置加载模块
"""
import os
import json
import sys
from pathlib import Path
from typing import Optional

CONFIG_FILE = "config.json"


def load_config() -> dict:
    """Load configuration from JSON file or environment variables."""
    # 优先从环境变量加载
    config = {
        "imap_host": os.getenv("IMAP_HOST"),
        "imap_port": os.getenv("IMAP_PORT", "993"),
        "smtp_host": os.getenv("SMTP_HOST"),
        "smtp_port": os.getenv("SMTP_PORT", "465"),
        "email": os.getenv("EMAIL_USER"),
        "password": os.getenv("EMAIL_PWD"),
        "allowed_senders": _parse_env_list("ALLOWED_SENDERS"),
        "claude_path": os.getenv("CLAUDE_PATH", "claude"),
        "poll_interval": int(os.getenv("POLL_INTERVAL", "30")),
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "timeout": int(os.getenv("CLAUDE_TIMEOUT", "300")),
    }
    
    # 如果环境变量存在，直接返回
    if config["email"] and config["password"]:
        return config
    
    # 否则从配置文件加载（兼容旧版本）
    script_dir = Path(__file__).parent
    config_path = script_dir / CONFIG_FILE
    example_path = script_dir / "config.example.json"
    
    if not config_path.exists():
        if example_path.exists():
            print(f"配置文件 '{config_path}' 不存在!")
            print("请运行 'python init_setup.py' 创建配置文件")
            print("或复制 config.example.json 为 config.json 并编辑")
            sys.exit(1)
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _parse_env_list(env_var: str) -> Optional[list]:
    """Parse comma-separated environment variable into list."""
    value = os.getenv(env_var)
    if value:
        return [s.strip() for s in value.split(',') if s.strip()]
    return None


def validate_config(config: dict) -> bool:
    """Validate required configuration fields."""
    required = ["imap_host", "smtp_host", "email", "password"]
    for field in required:
        if not config.get(field):
            print(f"错误: 缺少必需配置项: {field}")
            return False
    
    # 检查白名单配置
    if not config.get("allowed_senders"):
        print("警告: 未配置发件人白名单，建议配置以增强安全性!")
    
    return True
