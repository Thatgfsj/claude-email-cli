"""
日志清理脚本 - 定时清理机器人日志文件
保留最近 N 天的日志，删除旧的日志
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# 配置
LOG_DIR = Path(__file__).parent
SCRIPT_DIR = LOG_DIR

# 日志文件模式
LOG_PATTERNS = [
    "email_ai.log",
    ".playwright-mcp/console-*.log",
]

# 保留最近 7 天的日志
DAYS_TO_KEEP = 7


def get_file_age_days(file_path):
    """获取文件年龄（天）"""
    try:
        mtime = os.path.getmtime(file_path)
        file_date = datetime.fromtimestamp(mtime)
        age = datetime.now() - file_date
        return age.days
    except Exception:
        return 0


def clean_logs():
    """清理过期日志文件"""
    cleaned_count = 0
    total_size = 0

    # 清理主日志文件
    main_log = SCRIPT_DIR / "email_ai.log"
    if main_log.exists():
        age = get_file_age_days(main_log)
        if age > DAYS_TO_KEEP:
            size = main_log.stat().st_size
            main_log.unlink()
            cleaned_count += 1
            total_size += size
            print(f"已删除: {main_log.name} ({size/1024:.1f}KB, {age}天前)")

    # 清理 Playwright MCP 日志
    playwright_dir = SCRIPT_DIR / ".playwright-mcp"
    if playwright_dir.exists():
        for log_file in playwright_dir.glob("console-*.log"):
            age = get_file_age_days(log_file)
            if age > DAYS_TO_KEEP:
                size = log_file.stat().st_size
                log_file.unlink()
                cleaned_count += 1
                total_size += size
                print(f"已删除: {log_file.name} ({size/1024:.1f}KB, {age}天前)")

    # 也可以清理 works 目录下的旧文件夹
    works_dir = SCRIPT_DIR / "works"
    if works_dir.exists():
        for item in works_dir.iterdir():
            if item.is_dir():
                age = get_file_age_days(item)
                if age > DAYS_TO_KEEP:
                    # 递归删除文件夹
                    import shutil
                    try:
                        shutil.rmtree(item)
                        print(f"已删除目录: {item.name} ({age}天前)")
                    except Exception as e:
                        print(f"删除失败 {item.name}: {e}")

    print(f"\n清理完成: 共删除 {cleaned_count} 个文件，释放 {total_size/1024:.1f}KB")


if __name__ == "__main__":
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始清理日志...")
    clean_logs()
