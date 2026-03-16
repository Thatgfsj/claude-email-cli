#!/usr/bin/env python3
"""
Email AI Assistant - 一键启动脚本 (Web界面版)

功能：
- 启动 Flask Web 管理界面
- 后台运行邮件监控服务
"""

import os
import sys
import subprocess
import threading
import time
from pathlib import Path

# 确保在项目目录运行
PROJECT_DIR = Path(__file__).parent
os.chdir(PROJECT_DIR)

# 添加到路径
sys.path.insert(0, str(PROJECT_DIR))


def start_web_server():
    """启动 Flask Web 服务器"""
    print("=" * 50)
    print("启动 Web 管理界面...")
    print("=" * 50)
    print("访问 http://localhost:5000")
    print("=" * 50)
    
    from web_app import app
    app.run(host='127.0.0.1', port=5000, debug=False)


def main():
    """主入口"""
    print("""
╔══════════════════════════════════════════════════╗
║     Email AI Assistant - 一键启动                ║
║     邮件AI助手 + Web管理界面                     ║
╚══════════════════════════════════════════════════╝
""")
    
    # 检查配置
    from core.config import load_config
    config = load_config()
    
    if not config.get("email") or not config.get("password"):
        print("错误: 请先配置邮箱信息！")
        print("运行: python init_setup.py")
        sys.exit(1)
    
    print(f"邮箱: {config.get('email')}")
    print(f"发件人白名单: {config.get('allowed_senders') or '未配置'}")
    print()
    
    # 启动 Web 服务
    start_web_server()


if __name__ == "__main__":
    main()
