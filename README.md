# Email AI Assistant (claude-email-cli)

邮件 AI 助手 - 通过邮件与 Claude Code CLI 对话

## 简介

一个轻量级的邮件 AI 网关：通过 IMAP 接收白名单发件人的邮件，将正文交给本地 Claude Code CLI（print 模式）处理，再把结果通过 SMTP 回复到邮箱。

**本质是：邮件网关 → 本地 AI CLI 代理**

## 功能特性

### 安全
- ✅ 发件人白名单（大小写不敏感的**精确匹配**，防伪造绕过）
- ✅ 陌生发件人静默丢弃（不回复，防止被当作垃圾邮件跳板）
- ✅ 破坏性指令关键词过滤（尽力而为的启发式第一道防线）
- ✅ 敏感信息脱敏（路径、API 密钥）
- ✅ 强制环境变量 / .env 配置（密码不进代码库）
- ✅ Claude 调用使用参数列表 + stdin 传参，无 shell 注入面

### 可靠性
- ✅ IMAP 断线自动恢复（关闭坏连接，下轮轮询重连）
- ✅ SMTP 发送失败自动重连重试一次
- ✅ 邮件 UID 持久化去重（at-least-once 处理，崩溃不丢任务）
- ✅ 死信处理（连续失败达到上限后放弃）
- ✅ 超大邮件/回复自动截断

### 性能与工程化
- ✅ 单任务队列（防止 Claude CLI 并发阻塞）
- ✅ 子进程超时强制终止
- ✅ 模块化架构、结构化 JSON 日志（按大小轮转）
- ✅ Web 管理面板（真实心跳、处理记录、日志查看）

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

> CLI 模式仅使用 Python 标准库；Flask 仅 Web 面板需要。

### 2. 配置

```bash
# 方式一：交互式向导（推荐）
python init_setup.py

# 方式二：手动复制 .env.example 为 .env 并填写
```

> 前置要求：本机已安装并登录 [Claude Code CLI](https://docs.claude.com/zh-CN/docs/claude-code/overview)（命令行可运行 `claude -p "hi"`）。

### 3. 检查配置

```bash
python -c "from core.config import check_config; check_config()"
```

### 4. 启动

```bash
# CLI 模式（仅邮件服务）
python run.py

# Web 模式（邮件服务 + 管理面板 http://127.0.0.1:5000）
python run_web.py
```

## 项目结构

```
claude-email-cli/
├── main.py              # 主程序（轮询 + 任务队列 + 处理管道）
├── run.py               # CLI 启动脚本
├── run_web.py           # Web 启动脚本（后台服务 + 面板）
├── web_app.py           # Flask Web 面板
├── init_setup.py        # 交互式配置向导（生成 .env）
├── deploy.py            # Windows 部署脚本
├── DEPLOY.md            # 部署文档
├── .env.example         # 环境变量示例
├── core/
│   ├── config.py        # 配置加载（环境变量 + .env）
│   └── constants.py     # 常量定义
├── mailer/
│   ├── imap.py          # IMAP 收件（UID 去重、断线重连）
│   └── smtp.py          # SMTP 发件（TLS 自适应、断线重试）
├── claude/
│   └── client.py        # Claude CLI 调用（stdin 传参，防注入）
├── utils/
│   └── security.py      # 白名单校验、危险指令过滤、脱敏
├── tests/               # 离线单元测试（pytest）
├── logs/                # 日志目录（运行时生成）
└── data/                # 数据目录：UID 去重、心跳、处理记录
```

## 配置项说明

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| EMAIL_USER | ✅ | - | 邮箱地址 |
| EMAIL_PWD | ✅ | - | 邮箱授权码（QQ/163 为授权码，非登录密码） |
| IMAP_HOST | ✅ | - | IMAP 服务器 |
| SMTP_HOST | ✅ | - | SMTP 服务器 |
| ALLOWED_SENDERS | 强烈建议 | - | 白名单邮箱（逗号分隔）。**不设置则处理所有来信** |
| IMAP_PORT | | 993 | IMAP 端口 |
| SMTP_PORT | | 465 | SMTP 端口（465 走隐式 TLS，其他端口走 STARTTLS） |
| POLL_INTERVAL | | 30 | 轮询间隔（秒，10-3600） |
| CLAUDE_TIMEOUT | | 300 | Claude 超时（秒，30-3600） |
| MAX_RETRIES | | 3 | 最大重试次数 |
| CLAUDE_PATH | | claude | Claude CLI 路径 |
| WEB_PORT | | 5000 | Web 面板端口 |

## 邮件处理流程

1. 轮询 INBOX 中未读邮件（UID 搜索，幂等）
2. 白名单精确匹配 → 陌生发件人静默丢弃
3. 破坏性指令过滤 → 命中则回复"拒绝"
4. 正文脱敏后交给 `claude -p`（stdin 传入）
5. 回复邮件引用原主题；失败自动重试（指数退避）
6. 处理完成：UID 持久化 + 标记已读 + 写入处理记录

## 安全边界（务必阅读）

- **Claude 在你的机器上以你的权限运行**：邮件内容会驱动本地 AI 执行任务，请只把白名单给完全信任的邮箱，并建议在 Claude Code 中配置受限的权限（如 permission mode / allowlist）。
- 关键词过滤只是启发式第一道防线，不能替代上述权限控制。
- Web 面板默认只绑定 `127.0.0.1`，请勿直接暴露公网；如需远程访问，请自行加反代 + 认证。
- `.env` 含授权码，已在 `.gitignore` 中忽略，请勿手动提交。

## 测试

```bash
pip install pytest
pytest
```

测试全部离线运行，不连接任何邮件服务器。

## 许可证

[AGPL-3.0](./LICENSE)
