# Email AI Assistant

邮件 AI 助手 - 通过邮件与 Claude 对话

## 简介

一个轻量级的邮件 AI 代理工具，通过 IMAP/SMTP 接收邮件，将内容发送给本地 Claude CLI 处理，并返回结果。

**本质是：邮件网关 → 本地 AI CLI 代理**

## 功能特性

### 安全特性
- ✅ 发件人白名单校验（小写精确匹配）
- ✅ UID 持久化去重（文件存储）
- ✅ 危险命令过滤
- ✅ 敏感信息脱敏
- ✅ **强制环境变量配置**（不再支持明文配置文件）

### 可靠性
- ✅ IMAP/SMTP 异常自动重连（指数退避）
- ✅ 邮件 UID 持久化去重
- ✅ 按异常类型分级重试
- ✅ 死信处理（连续失败不再重试）
- ✅ 超大邮件自动截断

### 性能
- ✅ 单任务队列（防止 Claude CLI 并发阻塞）
- ✅ 子进程超时强制终止
- ✅ 回复内容长度限制

### 工程化
- ✅ 模块化架构
- ✅ 全量类型注解
- ✅ 结构化 JSON 日志（按大小轮转）
- ✅ 常量统一管理
- ✅ 配置自检脚本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置（环境变量方式）

#### 方式一：创建 .env 文件（推荐）
```bash
copy .env.example .env
notepad .env
```

#### 方式二：直接设置环境变量
```cmd
set EMAIL_USER=your@email.com
set EMAIL_PWD=your_auth_code
set IMAP_HOST=imap.qq.com
set SMTP_HOST=smtp.qq.com
set ALLOWED_SENDERS=your@email.com
```

#### 方式三：检查配置
```bash
python -c "from core.config import check_config; check_config()"
```

### 3. 启动

```bash
# CLI 模式
python run.py

# Web 模式
python run_web.py
```

## 项目结构

```
claude-email-cli/
├── main.py              # 主程序
├── run.py               # CLI 启动脚本
├── run_web.py           # Web 启动脚本
├── web_app.py           # Flask Web 应用
├── deploy.py            # 部署脚本
├── DEPLOY.md            # 部署文档
├── .env.example         # 环境变量示例
├── core/
│   ├── __init__.py
│   ├── config.py        # 配置加载（强制环境变量）
│   └── constants.py     # 常量定义
├── email/
│   ├── __init__.py
│   ├── imap.py         # IMAP 收件（可靠性强化）
│   └── smtp.py         # SMTP 发件
├── claude/
│   └── client.py       # Claude CLI 调用
├── utils/
│   └── security.py     # 安全检查
├── logs/                # 日志目录
└── data/                # 数据目录（UID存储）
```

## 配置项说明

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| EMAIL_USER | ✅ | - | 邮箱地址 |
| EMAIL_PWD | ✅ | - | 邮箱授权码 |
| IMAP_HOST | ✅ | - | IMAP 服务器 |
| SMTP_HOST | ✅ | - | SMTP 服务器 |
| IMAP_PORT | | 993 | IMAP 端口 |
| SMTP_PORT | | 465 | SMTP 端口 |
| ALLOWED_SENDERS | | - | 白名单邮箱（逗号分隔） |
| POLL_INTERVAL | | 30 | 轮询间隔（秒） |
| CLAUDE_TIMEOUT | | 300 | Claude 超时（秒） |
| MAX_RETRIES | | 3 | 最大重试次数 |
| CLAUDE_PATH | | claude | Claude CLI 路径 |

## 安全警告

⚠️ **不再支持 config.json 明文存储密码！**

请使用环境变量或 .env 文件配置敏感信息。

## 日志

- 位置：`logs/email_ai.log`
- 格式：JSON（结构化）
- 轮转：10MB/文件，保留 5 个

## 许可证

[AGPL-3.0](./LICENSE)
