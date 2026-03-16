# Windows 虚拟机部署指南

> 从零开始部署 Email AI Assistant

## 环境要求

- Windows 10/11 或 Windows Server
- Python 3.8+
- 网络连接（用于收发邮件）

---

## 第一步：安装 Python

### 方法一：官网下载
1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.11 或更高版本
3. 运行时勾选 `Add Python to PATH`

### 方法二：PowerShell 安装
```powershell
winget install Python.Python.3.11
```

### 验证安装
```cmd
python --version
```

---

## 第二步：克隆项目

```cmd
git clone https://github.com/Thatgfsj/claude-email-cli.git
cd claude-email-cli
```

或者直接下载 ZIP：
1. 访问 https://github.com/Thatgfsj/claude-email-cli
2. 点击 Code → Download ZIP
3. 解压到目录

---

## 第三步：安装依赖

```cmd
pip install -r requirements.txt
```

**注意**：如果使用 Web 界面，Flask 已在 requirements.txt 中。

---

## 第四步：配置

### 方式一：交互式配置（推荐）
```cmd
python init_setup.py
```
按提示输入：
- 邮箱地址
- 授权码/密码
- IMAP/SMTP 服务器地址
- 发件人白名单

### 方式二：手动配置

1. 复制配置示例：
```cmd
copy config.example.json config.json
```

2. 编辑 `config.json`：
```json
{
    "imap_host": "imap.qq.com",
    "imap_port": 993,
    "smtp_host": "smtp.qq.com",
    "smtp_port": 465,
    "email": "your@qq.com",
    "password": "your_auth_code",
    "allowed_senders": ["your@qq.com"],
    "claude_path": "claude",
    "poll_interval": 30,
    "timeout": 300
}
```

### 方式三：环境变量（最安全）
```cmd
set EMAIL_USER=your@qq.com
set EMAIL_PWD=your_auth_code
set IMAP_HOST=imap.qq.com
set SMTP_HOST=smtp.qq.com
set ALLOWED_SENDERS=your@qq.com
```

---

## 第五步：安装 Claude CLI

确保本地已安装 Claude CLI：
```cmd
claude --version
```

如果没有，请访问 https://github.com/anthropics/claude-code

---

## 第六步：启动服务

### CLI 模式
```cmd
python run.py
```

### Web 模式
```cmd
python run_web.py
```
然后浏览器访问 http://localhost:5000

---

## 常见问题

### Q: 邮件发送失败
A: 
1. 检查邮箱是否开启了 SMTP/IMAP
2. QQ 邮箱需要使用"授权码"而非登录密码
3. 检查防火墙是否阻止了端口 465/993

### Q: Claude 调用失败
A:
1. 确认 Claude CLI 已安装并在 PATH 中
2. 尝试手动运行 `claude --help`

### Q: 如何后台运行？
A: 使用 Windows 任务计划程序或 `start /b python run.py`

### Q: 如何开机自启？
A: 
1. 创建快捷方式到启动文件夹
2. 或使用任务计划程序

---

## 防火墙设置

如果遇到连接问题，检查：
```cmd
netsh advfirewall firewall add rule name="Python Email AI" dir=in action=allow program="C:\Python311\python.exe"
```

---

## 完整部署脚本

```powershell
# 1. 安装 Python
winget install Python.Python.3.11

# 2. 克隆项目
git clone https://github.com/Thatgfsj/claude-email-cli.git
cd claude-email-cli

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置（手动编辑 config.json）
notepad config.json

# 5. 启动
python run.py
```
