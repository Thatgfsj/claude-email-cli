#!/usr/bin/env python3
"""
Windows 一键部署脚本

从零开始在 Windows 上部署 Email AI Assistant
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def run_cmd(cmd, shell=True):
    """运行命令并打印输出"""
    print(f"\n>>> {cmd}")
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def check_python():
    """检查 Python 是否安装"""
    print("\n[1/6] 检查 Python...")
    result = subprocess.run("python --version", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Python 已安装: {result.stdout.strip()}")
        return True
    else:
        print("✗ Python 未安装")
        print("请先安装 Python: https://www.python.org/downloads/")
        return False


def check_git():
    """检查 Git 是否安装"""
    print("\n[2/6] 检查 Git...")
    result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"✓ Git 已安装: {result.stdout.strip()}")
        return True
    else:
        print("✗ Git 未安装")
        return False


def clone_project():
    """克隆项目"""
    print("\n[3/6] 克隆项目...")
    
    project_dir = Path(__file__).parent
    
    if (project_dir / ".git").exists():
        print("✓ 项目已存在")
        return True
    
    # 尝试克隆
    repo_url = "https://github.com/Thatgfsj/claude-email-cli.git"
    print(f"从 {repo_url} 克隆...")
    
    result = subprocess.run(
        f'git clone "{repo_url}" "{project_dir}"',
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ 项目克隆成功")
        return True
    else:
        print(f"✗ 克隆失败: {result.stderr}")
        return False


def install_dependencies():
    """安装依赖"""
    print("\n[4/6] 安装依赖...")
    
    project_dir = Path(__file__).parent
    req_file = project_dir / "requirements.txt"
    
    if not req_file.exists():
        print("✗ requirements.txt 不存在")
        return False
    
    # 检查是否有 Flask
    try:
        import flask
        print("✓ Flask 已安装")
    except ImportError:
        print("安装 Flask...")
        run_cmd("pip install flask")
    
    print("✓ 依赖安装完成")
    return True


def setup_config():
    """配置"""
    print("\n[5/6] 配置...")
    
    project_dir = Path(__file__).parent
    config_file = project_dir / "config.json"
    example_file = project_dir / "config.example.json"
    
    if config_file.exists():
        print("✓ 配置文件已存在")
        return True
    
    if example_file.exists():
        print("请编辑 config.example.json 并保存为 config.json")
        print(f"配置文件位置: {config_file}")
        return True
    
    print("✗ 配置文件不存在")
    return False


def start_service():
    """启动服务"""
    print("\n[6/6] 启动服务...")
    
    project_dir = Path(__file__).parent
    run_file = project_dir / "run.py"
    
    if not run_file.exists():
        print("✗ run.py 不存在")
        return False
    
    print("\n" + "=" * 50)
    print("部署完成！")
    print("=" * 50)
    print(f"配置文件: {project_dir / 'config.json'}")
    print("启动命令: python run.py")
    print("=" * 50)
    
    return True


def main():
    """主函数"""
    print("""
╔══════════════════════════════════════════════════╗
║   Email AI Assistant - Windows 部署脚本        ║
╚══════════════════════════════════════════════════╝
""")
    
    # 检查 Python
    if not check_python():
        print("\n请先安装 Python 后再运行此脚本")
        sys.exit(1)
    
    # 检查 Git
    check_git()
    
    # 克隆项目
    clone_project()
    
    # 安装依赖
    install_dependencies()
    
    # 配置
    setup_config()
    
    # 启动
    start_service()
    
    print("\n下一步:")
    print("1. 编辑 config.json 配置文件")
    print("2. 运行 python run.py 启动服务")


if __name__ == "__main__":
    main()
