"""
配置加载模块 - 安全强化版

强制使用环境变量，拒绝明文配置
"""
import os
import json
import sys
from pathlib import Path
from typing import Optional, List
from core.constants import (
    CONFIG_FILE, CONFIG_EXAMPLE, DEFAULT_POLL_INTERVAL, 
    DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES
)


class ConfigError(Exception):
    """配置错误异常"""
    pass


def load_config() -> dict:
    """加载配置 - 优先环境变量，兼容配置文件"""
    
    # 强制从环境变量加载
    config = {
        # 邮件服务
        "imap_host": _get_required_env("IMAP_HOST", "IMAP服务器地址"),
        "imap_port": int(os.getenv("IMAP_PORT", "993")),
        "smtp_host": _get_required_env("SMTP_HOST", "SMTP服务器地址"),
        "smtp_port": int(os.getenv("SMTP_PORT", "465")),
        "email": _get_required_env("EMAIL_USER", "邮箱地址"),
        "password": _get_required_env("EMAIL_PWD", "邮箱密码/授权码"),
        
        # 安全配置
        "allowed_senders": _parse_senders(os.getenv("ALLOWED_SENDERS")),
        
        # Claude 配置
        "claude_path": os.getenv("CLAUDE_PATH", "claude"),
        "timeout": int(os.getenv("CLAUDE_TIMEOUT", str(DEFAULT_TIMEOUT))),
        
        # 行为配置
        "poll_interval": int(os.getenv("POLL_INTERVAL", str(DEFAULT_POLL_INTERVAL))),
        "max_retries": int(os.getenv("MAX_RETRIES", str(DEFAULT_MAX_RETRIES))),
    }
    
    return config


def _get_required_env(name: str, desc: str) -> str:
    """获取必需的环境变量，不存在则报错"""
    value = os.getenv(name)
    if not value:
        raise ConfigError(
            f"缺少必需配置: {name} ({desc})\n"
            f"请设置环境变量: set {name}=your_value\n"
            f"或使用 .env 文件"
        )
    return value


def _parse_senders(value: Optional[str]) -> Optional[List[str]]:
    """解析发件人列表"""
    if not value:
        return None
    senders = []
    for s in value.split(','):
        s = s.strip()
        if s:
            senders.append(s.lower())  # 统一小写
    return senders if senders else None


def validate_config(config: dict) -> bool:
    """验证配置完整性"""
    errors = []
    
    # 检查必填字段
    required = ["imap_host", "smtp_host", "email", "password"]
    for field in required:
        if not config.get(field):
            errors.append(f"缺少必需配置: {field}")
    
    # 检查端口
    if config.get("imap_port") and config["imap_port"] <= 0:
        errors.append("IMAP端口必须为正整数")
    
    if config.get("smtp_port") and config["smtp_port"] <= 0:
        errors.append("SMTP端口必须为正整数")
    
    # 检查轮询间隔
    interval = config.get("poll_interval", 0)
    if interval < 10 or interval > 3600:
        errors.append("轮询间隔应在 10-3600 秒之间")
    
    # 检查超时
    timeout = config.get("timeout", 0)
    if timeout < 30 or timeout > 3600:
        errors.append("超时时间应在 30-3600 秒之间")
    
    if errors:
        print("配置验证失败:")
        for e in errors:
            print(f"  - {e}")
        return False
    
    return True


def check_config() -> bool:
    """检查配置是否正确 - 用于 --check-config"""
    print("检查配置文件...")
    
    try:
        config = load_config()
        if validate_config(config):
            print("✓ 配置检查通过")
            print(f"  邮箱: {config['email']}")
            print(f"  IMAP: {config['imap_host']}:{config['imap_port']}")
            print(f"  SMTP: {config['smtp_host']}:{config['smtp_port']}")
            print(f"  白名单: {config.get('allowed_senders') or '未设置'}")
            return True
        return False
    except ConfigError as e:
        print(f"✗ 配置错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False


# 兼容旧版本配置文件（警告但不强制）
def load_config_compat() -> dict:
    """兼容旧版配置文件加载"""
    script_dir = Path(__file__).parent
    config_path = script_dir / CONFIG_FILE
    
    if config_path.exists():
        print(f"警告: 检测到配置文件 {CONFIG_FILE}")
        print("建议迁移到环境变量以提高安全性")
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 尝试环境变量
    return load_config()
