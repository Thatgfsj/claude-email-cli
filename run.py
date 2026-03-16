#!/usr/bin/env python3
"""
Email AI Assistant - 一键启动脚本 (CLI版)

功能：
- 启动邮件监控服务
"""

import os
import sys
import signal
from pathlib import Path

# 确保在项目目录运行
PROJECT_DIR = Path(__file__).parent
os.chdir(PROJECT_DIR)

# 添加到路径
sys.path.insert(0, str(PROJECT_DIR))


def main():
    """主入口"""
    print("""
╔══════════════════════════════════════════════════╗
║     Email AI Assistant - 一键启动              ║
║     邮件AI助手 (CLI模式)                      ║
╚══════════════════════════════════════════════════╝
""")
    
    # 检查配置
    from core.config import load_config, validate_config
    config = load_config()
    
    if not validate_config(config):
        print("\n请先配置邮箱信息！")
        print("运行: python init_setup.py")
        sys.exit(1)
    
    print(f"✓ 邮箱: {config.get('email')}")
    print(f"✓ 发件人白名单: {config.get('allowed_senders') or '未配置 (不安全!)'}")
    print(f"✓ 轮询间隔: {config.get('poll_interval', 30)}秒")
    print()
    print("按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 启动服务
    from main import EmailAIAssistant
    
    assistant = EmailAIAssistant(config)
    
    # 信号处理
    def signal_handler(sig, frame):
        print("\n正在退出...")
        assistant.running = False
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    assistant.start()


if __name__ == "__main__":
    main()
