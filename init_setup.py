#!/usr/bin/env python3
"""
Email AI Assistant - 初始化脚本
帮助用户配置邮箱账号、白名单和 AI 设置
"""

import json
import os
import sys
import getpass
from pathlib import Path

CONFIG_FILE = "config.json"

def print_banner():
    print("=" * 50)
    print("   Email AI Assistant 初始化向导")
    print("=" * 50)
    print()

def get_input(prompt: str, default: str = "") -> str:
    """获取用户输入"""
    if default:
        user_input = input(f"{prompt} [{default}]: ").strip()
        return user_input if user_input else default
    return input(f"{prompt}: ").strip()

def get_email(prompt: str) -> str:
    """获取邮箱地址"""
    while True:
        email = get_input(prompt)
        if "@" in email and "." in email:
            return email
        print("⚠️  请输入有效的邮箱地址！")

def get_password(prompt: str) -> str:
    """获取密码（不显示）"""
    import getpass
    while True:
        pwd = getpass.getpass(f"{prompt}: ")
        if pwd:
            return pwd
        print("⚠️  密码不能为空！")

def main():
    print_banner()
    
    print("📧 第一部分：邮箱配置")
    print("-" * 30)
    
    # 邮箱选择
    print("支持的邮箱类型：")
    print("  1. QQ邮箱")
    print("  2. 163邮箱")
    print("  3. 126邮箱")
    print("  4. Gmail")
    print("  5. 自定义 SMTP/IMAP")
    
    email_type = get_input("选择邮箱类型 (1-5)", "1")
    
    imap_host = ""
    smtp_host = ""
    
    if email_type == "1":  # QQ
        imap_host = "imap.qq.com"
        smtp_host = "smtp.qq.com"
    elif email_type == "2":  # 163
        imap_host = "imap.163.com"
        smtp_host = "smtp.163.com"
    elif email_type == "3":  # 126
        imap_host = "imap.126.com"
        smtp_host = "smtp.126.com"
    elif email_type == "4":  # Gmail
        imap_host = "imap.gmail.com"
        smtp_host = "smtp.gmail.com"
    else:
        imap_host = get_input("IMAP 服务器地址")
        smtp_host = get_input("SMTP 服务器地址")
    
    email_addr = get_email("你的邮箱地址")
    email_password = get_password("邮箱密码或授权码")
    
    print()
    print("🔐 第二部分：安全设置")
    print("-" * 30)
    
    # 白名单
    print("\n白名单：只有白名单中的邮箱才能发送任务给你")
    print("（输入空行结束，输入多个邮箱按回车）")
    
    whitelist = []
    while True:
        addr = input("添加白名单邮箱 (直接回车结束): ").strip()
        if not addr:
            break
        if "@" in addr and "." in addr:
            whitelist.append(addr)
            print(f"  ✅ 已添加: {addr}")
        else:
            print("  ⚠️  无效邮箱格式")
    
    if not whitelist:
        print("⚠️  警告：白名单为空！所有邮件都会被处理！")
        confirm = input("确定继续吗？(y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ 已取消初始化")
            return
    
    superuser = get_email("超级管理员邮箱（用于特殊命令）", whitelist[0] if whitelist else "")
    
    print()
    print("🤖 第三部分：AI 配置")
    print("-" * 30)
    
    claude_cmd = get_input("Claude CLI 命令", "claude")
    model = get_input("使用的模型", "sonnet")
    timeout = get_input("超时时间（秒）", "300")
    persona = get_input("AI 人设（描述 AI 的角色）", "一个有用的 AI 助手")
    
    print()
    print("📝 第四部分：检查间隔")
    print("-" * 30)
    
    check_interval = get_input("邮件检查间隔（秒）", "30")
    
    # 构建配置
    config = {
        "imap": {
            "host": imap_host,
            "port": 993,
            "username": email_addr,
            "password": email_password
        },
        "smtp": {
            "host": smtp_host,
            "port": 465,
            "username": email_addr,
            "password": email_password
        },
        "whitelist": whitelist,
        "superuser": superuser,
        "check_interval": int(check_interval),
        "reply_subject_prefix": "Re: ",
        "claude_model": model,
        "claude_timeout": int(timeout),
        "claude_command": claude_cmd,
        "claude_args": ["--print"],
        "persona": persona
    }
    
    # 写入配置文件
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print()
    print("=" * 50)
    print("✅ 配置完成！")
    print(f"📄 配置文件: {os.path.abspath(CONFIG_FILE)}")
    print()
    print("下一步：")
    print("  1. 运行: python email_ai_assistant.py")
    print("  2. 或者: python email_ai_assistant.py --once (单次运行)")
    print()
    print("⚠️  注意：请妥善保管配置文件，不要提交到 GitHub！")
    print("=" * 50)

if __name__ == "__main__":
    main()
