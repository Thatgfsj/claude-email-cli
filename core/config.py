"""
配置加载模块 - 安全强化版

强制使用环境变量，支持项目根目录下的 .env 文件（不覆盖已存在的环境变量）
"""
import os
from typing import List, Optional

from core.constants import (
    DEFAULT_POLL_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    PROJECT_DIR,
)

ENV_FILE = PROJECT_DIR / ".env"


class ConfigError(Exception):
    """配置错误异常"""
    pass


def load_dotenv(env_file=ENV_FILE) -> None:
    """加载 .env 文件中的环境变量（已存在的环境变量优先，不被覆盖）"""
    if not env_file.exists():
        return
    try:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError as e:
        print(f"警告: 读取 .env 文件失败: {e}")


def load_config() -> dict:
    """加载配置 - 强制环境变量（自动加载 .env）"""
    load_dotenv()

    return {
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


def _get_required_env(name: str, desc: str) -> str:
    """获取必需的环境变量，不存在或为空白则报错"""
    value = (os.getenv(name) or "").strip()
    if not value:
        raise ConfigError(
            f"缺少必需配置: {name} ({desc})\n"
            f"请设置环境变量: set {name}=your_value\n"
            f"或复制 .env.example 为 .env 并填写（也可运行 python init_setup.py）"
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
    if config.get("imap_port", 0) <= 0:
        errors.append("IMAP端口必须为正整数")

    if config.get("smtp_port", 0) <= 0:
        errors.append("SMTP端口必须为正整数")

    # 检查轮询间隔
    interval = config.get("poll_interval", 0)
    if interval < 10 or interval > 3600:
        errors.append("轮询间隔应在 10-3600 秒之间")

    # 检查超时
    timeout = config.get("timeout", 0)
    if timeout < 30 or timeout > 3600:
        errors.append("超时时间应在 30-3600 秒之间")

    # 白名单缺失时给出强警告（不阻止启动，但必须让用户看到风险）
    if not config.get("allowed_senders"):
        print("⚠️  警告: 未设置 ALLOWED_SENDERS 白名单，任何发件人的邮件都会被处理！")
        print("    强烈建议在 .env 中设置 ALLOWED_SENDERS=你的邮箱")

    if errors:
        print("配置验证失败:")
        for e in errors:
            print(f"  - {e}")
        return False

    return True


def check_config() -> bool:
    """检查配置是否正确 - 用于 --check-config"""
    print("检查配置...")

    try:
        config = load_config()
        if validate_config(config):
            print("✓ 配置检查通过")
            print(f"  邮箱: {config['email']}")
            print(f"  IMAP: {config['imap_host']}:{config['imap_port']}")
            print(f"  SMTP: {config['smtp_host']}:{config['smtp_port']}")
            print(f"  白名单: {config.get('allowed_senders') or '未设置（不安全）'}")
            return True
        return False
    except ConfigError as e:
        print(f"✗ 配置错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False
