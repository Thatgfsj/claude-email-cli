#!/usr/bin/env python3
"""
Email AI Assistant - 一键启动脚本 (Web界面版)

- 后台线程运行邮件监控服务
- 主线程运行 Flask Web 管理面板
"""

import os
import sys
import threading
from pathlib import Path

# 确保在项目目录运行
PROJECT_DIR = Path(__file__).parent
os.chdir(PROJECT_DIR)
sys.path.insert(0, str(PROJECT_DIR))

from core.config import load_config, validate_config, ConfigError
from core.constants import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT


def main():
    """主入口"""
    print("""
╔══════════════════════════════════════════════════╗
║     Email AI Assistant - 一键启动                ║
║     邮件AI助手 + Web管理界面                     ║
╚══════════════════════════════════════════════════╝
""")

    # 检查配置
    try:
        config = load_config()
    except ConfigError as e:
        print(f"配置错误: {e}")
        print("运行: python init_setup.py")
        sys.exit(1)

    if not validate_config(config):
        print("\n请先配置邮箱信息！")
        print("运行: python init_setup.py")
        sys.exit(1)

    print(f"邮箱: {config.get('email')}")
    print(f"发件人白名单: {config.get('allowed_senders') or '未配置 (不安全!)'}")
    print()

    # 后台线程运行邮件服务
    from main import EmailAIAssistant

    assistant = EmailAIAssistant(config)
    service_thread = threading.Thread(target=assistant.start, daemon=True, name="email-service")
    service_thread.start()
    print("✓ 邮件监控服务已在后台启动")
    print()

    # 主线程运行 Web 面板
    from web_app import run_app

    port = int(os.getenv("WEB_PORT", str(DEFAULT_WEB_PORT)))
    print("=" * 50)
    print(f"Web 管理面板: http://{DEFAULT_WEB_HOST}:{port}")
    print("按 Ctrl+C 停止所有服务")
    print("=" * 50)
    try:
        run_app(host=DEFAULT_WEB_HOST, port=port)
    finally:
        assistant.stop()
        service_thread.join(timeout=70)


if __name__ == "__main__":
    main()
