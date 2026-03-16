# Email AI Assistant

邮件 AI 助手 - 通过邮件与 Claude 对话

## 简介

一个轻量级的邮件 AI 代理工具，通过 IMAP/SMTP 接收邮件，将内容发送给本地 Claude CLI 处理，并返回结果。

**本质是：邮件网关 → 本地 AI CLI 代理**

## 功能特性

### 安全特性
- ✅ 发件人白名单校验
- ✅ 邮件 UID 去重（防止重复处理）
- ✅ 危险命令过滤
- ✅ 敏感信息脱敏
- ✅ 配置支持环境变量（不存储明文密码）

### 稳定性
- ✅ IMAP/SMTP 异常自动重连
- ✅ 结构化日志记录
- ✅ 进程守护

### 工程化
- ✅ 模块化架构
- ✅ 类型注解
- ✅ Markdown 转纯文本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

#### 方式一：交互式配置
```bash
python init_setup.py
```

#### 方式二：环境变量（推荐）
```bash
export EMAIL_USER="your@email.com"
export EMAIL_PWD="your_password"
export IMAP_HOST="imap.qq.com"
export SMTP_HOST="smtp.qq.com"
export ALLOWED_SENDERS="friend@qq.com,admin@example.com"
```

#### 方式三：配置文件
复制 `config.example.json` 为 `config.json` 并编辑。

### 3. 启动

#### CLI 模式（命令行）
```bash
python run.py
```

#### Web 模式（带管理界面）
```bash
python run_web.py
```
然后访问 http://localhost:5000

## 项目结构

```
claude-email-cli/
├── main.py              # CLI 主程序
├── run.py               # CLI 启动脚本
├── run_web.py           # Web 启动脚本
├── web_app.py           # Flask Web 应用
├── core/
│   ├── __init__.py
│   └── config.py        # 配置加载
├── email/
│   ├── __init__.py
│   ├── imap.py         # IMAP 收件
│   └── smtp.py         # SMTP 发件
├── claude/
│   └── client.py       # Claude CLI 调用
├── utils/
│   └── security.py     # 安全检查
├── logs/                # 日志目录
├── config.example.json  # 配置示例
└── requirements.txt     # Python 依赖
```

## 使用方法

1. 配置好邮箱和允许的发件人
2. 启动服务
3. 给你的邮箱发送邮件
4. Claude 会处理邮件并回复你

## 安全建议

1. **一定要配置发件人白名单** - 只允许信任的邮箱地址
2. **使用环境变量** - 不要在配置文件中明文存储密码
3. **限制 AI 权限** - 建议只允许对话，不执行 shell 命令

## 许可证

[AGPL-3.0](./LICENSE)
