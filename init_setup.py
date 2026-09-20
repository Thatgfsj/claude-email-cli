#!/usr/bin/env python3
"""
Email AI Assistant - 初始化向导

交互式生成 .env 配置文件（敏感信息不进代码库）
"""

import getpass
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

# 常见邮箱服务商预设
PROVIDERS = {
    "1": ("QQ邮箱", "imap.qq.com", "smtp.qq.com"),
    "2": ("163邮箱", "imap.163.com", "smtp.163.com"),
    "3": ("126邮箱", "imap.126.com", "smtp.126.com"),
    "4": ("Gmail", "imap.gmail.com", "smtp.gmail.com"),
    "5": ("Outlook", "outlook.office365.com", "smtp.office365.com"),
}


def get_input(prompt: str, default: str = "") -> str:
    """获取用户输入"""
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def get_email(prompt: str, default: str = "") -> str:
    """获取邮箱地址"""
    while True:
        value = get_input(prompt, default)
        if "@" in value and "." in value:
            return value
        print("⚠️  请输入有效的邮箱地址！")


def get_password(prompt: str) -> str:
    """获取密码（不回显）"""
    while True:
        pwd = getpass.getpass(f"{prompt}: ")
        if pwd:
            return pwd
        print("⚠️  密码不能为空！")


def main():
    print("=" * 50)
    print("   Email AI Assistant 初始化向导")
    print("   配置将写入 .env 文件（已在 .gitignore 中忽略）")
    print("=" * 50)
    print()

    # ---- 邮箱服务 ----
    print("📧 第一部分：邮箱服务")
    print("-" * 30)
    print("支持的邮箱类型：")
    for key, (name, _, _) in PROVIDERS.items():
        print(f"  {key}. {name}")
    print("  6. 自定义 IMAP/SMTP")

    choice = get_input("选择邮箱类型 (1-6)", "1")
    if choice in PROVIDERS:
        _, imap_host, smtp_host = PROVIDERS[choice]
        print(f"  IMAP: {imap_host} | SMTP: {smtp_host}")
    else:
        imap_host = get_input("IMAP 服务器地址")
        smtp_host = get_input("SMTP 服务器地址")

    email_addr = get_email("你的邮箱地址")
    email_password = get_password("邮箱密码或授权码（QQ/163 需使用授权码，非登录密码）")

    # ---- 安全区 ----
    print()
    print("🔐 第二部分：安全设置")
    print("-" * 30)
    print("白名单：只有白名单中的邮箱发来的邮件才会被处理")
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
        whitelist = [email_addr]
        print(f"  ℹ️  未添加白名单，默认加入你自己的邮箱: {email_addr}")

    # ---- AI 配置 ----
    print()
    print("🤖 第三部分：AI 与轮询配置")
    print("-" * 30)
    claude_path = get_input("Claude CLI 命令/路径", "claude")
    timeout = get_input("Claude 超时时间（秒）", "300")
    poll_interval = get_input("邮件检查间隔（秒）", "30")

    # ---- 写入 .env ----
    lines = [
        "# 由 init_setup.py 生成 —— 请勿提交到代码库",
        "",
        "# ========== 必需配置 ==========",
        f"EMAIL_USER={email_addr}",
        f"EMAIL_PWD={email_password}",
        f"IMAP_HOST={imap_host}",
        f"SMTP_HOST={smtp_host}",
        "",
        "# ========== 安全配置 ==========",
        f"ALLOWED_SENDERS={','.join(whitelist)}",
        "",
        "# ========== 可选配置 ==========",
        f"CLAUDE_PATH={claude_path}",
        f"CLAUDE_TIMEOUT={timeout}",
        f"POLL_INTERVAL={poll_interval}",
        "",
    ]

    if ENV_FILE.exists():
        confirm = input(f"⚠️  {ENV_FILE.name} 已存在，覆盖？(y/N): ").strip().lower()
        if confirm != "y":
            print("❌ 已取消")
            return

    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("=" * 50)
    print(f"✅ 配置完成: {ENV_FILE}")
    print()
    print("下一步：")
    print("  1. 检查配置: python -c \"from core.config import check_config; check_config()\"")
    print("  2. 启动 CLI 模式: python run.py")
    print("  3. 启动 Web 模式: python run_web.py")
    print()
    print("⚠️  .env 包含密码，请确认 .gitignore 已忽略它（项目默认已忽略）")
    print("=" * 50)


if __name__ == "__main__":
    main()
