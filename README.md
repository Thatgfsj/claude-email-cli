# Claude Email CLI 📧🤖

一个通过邮件远程控制 Claude / AI 助手的命令行工具。

## 与 OpenClaw 的区别

| 特性 | Claude Email CLI | OpenClaw |
|------|------------------|-----------|
| **控制方式** | 邮件收发 | 多种（QQ/Telegram/Discord等） |
| **部署** | 只需一个邮箱 | 需要配置消息平台 |
| **复杂度** | 轻量简单 | 功能更全面 |
| **适用场景** | 远程邮件控制 | 多平台即时通讯 |
| **依赖** | Python + 邮箱 | Python + 各种插件 |

简单来说：
- **Claude Email CLI**：轻量级，用邮件就能远程控制 AI，适合简单场景
- **OpenClaw**：功能强大，支持多种聊天平台，适合需要即时交互的场景

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/Thatgfsj/claude-email-cli.git
cd claude-email-cli
```

### 2. 初始化配置

```bash
python init_setup.py
```

按照向导填写：
- 邮箱地址和密码/授权码
- 白名单（只有这些邮箱能发送任务）
- AI 人设
- 检查间隔等

### 3. 运行服务

```bash
# 持续运行（推荐）
python email_ai_assistant.py

# 单次运行（处理一封邮件后退出）
python email_ai_assistant.py --once
```

## 配置说明

配置文件 `config.json` 关键项：

```json
{
    "imap": {
        "host": "imap.qq.com",
        "port": 993,
        "username": "your@email.com",
        "password": "your_password"
    },
    "smtp": {
        "host": "smtp.qq.com",
        "port": 465,
        "username": "your@email.com",
        "password": "your_password"
    },
    "whitelist": [
        "trusted@example.com"
    ],
    "superuser": "trusted@example.com",
    "claude_command": "claude",
    "claude_model": "sonnet",
    "persona": "一个有用的 AI 助手"
}
```

### 各配置项说明

| 配置项 | 说明 |
|--------|------|
| `imap.host` | IMAP 服务器地址 |
| `smtp.host` | SMTP 服务器地址 |
| `whitelist` | 白名单邮箱列表 |
| `superuser` | 超级管理员，可执行特殊命令 |
| `claude_command` | Claude CLI 命令路径 |
| `claude_model` | 使用的模型 |
| `persona` | AI 人设描述 |
| `check_interval` | 邮件检查间隔（秒） |

## 使用方法

### 发送任务邮件

向配置的邮箱发送邮件：
- **主题**：任意
- **内容**：你的任务描述
- **发件人**：必须在白名单中

### 特殊命令（超级管理员）

发送给 superuser 邮箱：
- `!status` - 查看服务状态
- `!restart` - 重启服务
- `!stop` - 停止服务

### 工作流程

1. 白名单用户发送邮件
2. 程序创建工作目录 `works/月日_主题/`
3. 将邮件内容发送给 Claude
4. Claude 回复后自动邮件回复用户
5. 等待下一封邮件

## 依赖

- Python 3.8+
- imaplib, smtplib (标准库)
- Claude CLI

## 常见问题

### Q: 邮箱登录失败？
A: 大部分邮箱需要使用"授权码"而非登录密码。请在邮箱设置中生成授权码。

### Q: 如何使用其他 AI？
A: 修改 `config.json` 中的 `claude_command` 和 `claude_args`，指向你的 AI CLI。

### Q: 一直收不到邮件？
A: 检查垃圾邮件文件夹，确保发件人在白名单中。

## 开源许可

本项目基于 **AGPL-3.0** 开源许可证。

## 致谢

- Claude (Anthropic)
- 灵感来自各种 AI 助手项目
