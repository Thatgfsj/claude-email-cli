"""
Claude Email CLI - Web Dashboard

本地管理面板：
- 展示服务运行状态（读取 data/heartbeat.json 心跳）
- 展示最近处理记录（data/history.jsonl）
- 展示运行日志（logs/email_ai.log）
- 发送任务邮件（走 SMTP，由运行中的服务接收处理）

安全说明：
- 默认仅绑定 127.0.0.1，请勿直接暴露到公网
"""
import json
import logging
from datetime import datetime, timezone

from flask import Flask, render_template_string, request, jsonify

from core.config import load_config, ConfigError
from core.constants import (
    DATA_DIR,
    HEARTBEAT_FILE,
    HISTORY_FILE,
    LOG_FILE,
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
)
from mailer.smtp import SMTPClient

app = Flask(__name__)

# 心跳超过该秒数视为服务离线
# 默认轮询间隔 30s（750s ≈ 25 个周期）；上限放宽以兼容较大轮询间隔的部署
HEARTBEAT_STALE_SECONDS = 750


# ---------- HTML ----------

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Email CLI - Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { text-align: center; padding: 40px 0; }
        header h1 {
            font-size: 2.5rem;
            background: linear-gradient(90deg, #00d9ff, #a855f7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }
        .status-card {
            background: rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .status-item {
            display: flex; justify-content: space-between;
            padding: 15px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .status-item:last-child { border-bottom: none; }
        .label { color: #888; }
        .value { font-weight: bold; color: #00d9ff; }
        .online { color: #10b981; }
        .offline { color: #ef4444; }
        .btn {
            background: linear-gradient(90deg, #00d9ff, #a855f7);
            border: none; padding: 12px 24px; border-radius: 8px;
            color: white; font-weight: bold; cursor: pointer;
            margin: 5px; transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .btn-danger { background: linear-gradient(90deg, #ef4444, #f97316); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px; margin-top: 20px;
        }
        .card { background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; }
        .card h3 { color: #a855f7; margin-bottom: 15px; }
        input, textarea {
            width: 100%; padding: 12px; margin: 8px 0;
            border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;
            background: rgba(255,255,255,0.1); color: #fff; font-size: 14px;
        }
        input:focus, textarea:focus { outline: none; border-color: #00d9ff; }
        .task-list { max-height: 400px; overflow-y: auto; }
        .task-item {
            background: rgba(255,255,255,0.05);
            padding: 15px; border-radius: 8px; margin-bottom: 10px;
        }
        .task-time { color: #888; font-size: 0.85rem; }
        .task-subject { font-weight: bold; margin: 8px 0; }
        .task-meta { color: #aaa; font-size: 0.9rem; }
        .task-meta.success { color: #10b981; }
        .task-meta.failed { color: #ef4444; }
        .task-meta.rejected { color: #f97316; }
        .logs {
            background: #0d1117; padding: 15px; border-radius: 8px;
            font-family: monospace; font-size: 12px; max-height: 300px;
            overflow-y: auto; white-space: pre-wrap; color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📧 Claude Email CLI</h1>
            <p>通过网页管理你的 AI 邮件助手</p>
        </header>

        <div class="status-card">
            <h2>📊 服务状态</h2>
            <div class="status-item">
                <span class="label">服务状态</span>
                <span class="value {% if running %}online{% else %}offline{% endif %}">
                    {% if running %}🟢 运行中{% else %}🔴 未运行{% endif %}
                </span>
            </div>
            <div class="status-item">
                <span class="label">邮箱</span>
                <span class="value">{{ email }}</span>
            </div>
            <div class="status-item">
                <span class="label">白名单</span>
                <span class="value">{{ whitelist_count }} 个用户</span>
            </div>
            <div class="status-item">
                <span class="label">检查间隔</span>
                <span class="value">{{ interval }} 秒</span>
            </div>
            <div class="status-item">
                <span class="label">累计处理</span>
                <span class="value">{{ processed }} 封</span>
            </div>
            <div class="status-item">
                <span class="label">最近轮询</span>
                <span class="value">{{ last_poll }}</span>
            </div>
        </div>

        <div style="text-align: center; margin: 20px 0;">
            <button class="btn" onclick="refreshTasks()">🔄 刷新任务</button>
            <button class="btn btn-danger" onclick="clearHistory()">🗑️ 清理记录</button>
        </div>

        <div class="grid">
            <div class="card">
                <h3>📝 发送新任务</h3>
                <input type="text" id="taskEmail" placeholder="发送到 (留空则发给自己)">
                <textarea id="taskContent" rows="5" placeholder="输入任务描述..."></textarea>
                <button class="btn" onclick="sendTask()">🚀 发送任务</button>
            </div>

            <div class="card">
                <h3>📬 最近任务</h3>
                <div class="task-list" id="taskList"></div>
            </div>
        </div>

        <div class="card" style="margin-top: 20px;">
            <h3>📜 运行日志</h3>
            <div class="logs" id="logs">{{ logs }}</div>
        </div>
    </div>

    <script>
        // 用 textContent 渲染，避免任务内容（来自邮件正文）造成 XSS
        function renderTask(item, container) {
            const div = document.createElement('div');
            div.className = 'task-item';

            const time = document.createElement('div');
            time.className = 'task-time';
            time.textContent = item.time;

            const subject = document.createElement('div');
            subject.className = 'task-subject';
            subject.textContent = item.subject;

            const meta = document.createElement('div');
            meta.className = 'task-meta ' + (item.status || '');
            meta.textContent = item.sender + ' · ' + (item.status || '');

            div.appendChild(time);
            div.appendChild(subject);
            div.appendChild(meta);
            container.appendChild(div);
        }

        function refreshTasks() {
            fetch('/api/tasks')
                .then(r => r.json())
                .then(data => {
                    const list = document.getElementById('taskList');
                    list.textContent = '';
                    if (!data.tasks.length) {
                        const p = document.createElement('p');
                        p.style.color = '#888';
                        p.textContent = '暂无任务';
                        list.appendChild(p);
                        return;
                    }
                    data.tasks.forEach(t => renderTask(t, list));
                });
        }

        function sendTask() {
            const email = document.getElementById('taskEmail').value;
            const content = document.getElementById('taskContent').value;

            if (!content) {
                alert('请输入任务内容');
                return;
            }

            fetch('/api/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, content})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('✅ 任务已发送，等待服务处理！');
                    document.getElementById('taskContent').value = '';
                    refreshTasks();
                } else {
                    alert('❌ 发送失败: ' + data.error);
                }
            });
        }

        function clearHistory() {
            if (!confirm('确定要清理所有任务记录吗？')) return;
            fetch('/api/clear', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    alert('✅ 已清理');
                    refreshTasks();
                });
        }

        setInterval(refreshTasks, 30000);
        refreshTasks();
    </script>
</body>
</html>
'''


# ---------- 数据读取 ----------

def get_config_safe():
    """加载配置；未配置时返回 None（面板显示引导信息）"""
    try:
        return load_config()
    except ConfigError:
        return None


def get_heartbeat():
    """读取服务心跳文件"""
    if not HEARTBEAT_FILE.exists():
        return None
    try:
        return json.loads(HEARTBEAT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def is_service_running(heartbeat) -> bool:
    """根据心跳判断服务是否存活"""
    if not heartbeat or not heartbeat.get("running"):
        return False
    last_poll = heartbeat.get("last_poll")
    if not last_poll:
        return False
    age = datetime.now(timezone.utc).timestamp() - last_poll
    return age < HEARTBEAT_STALE_SECONDS


def get_history(limit: int = 10):
    """读取最近的任务处理记录（新记录在前）"""
    if not HISTORY_FILE.exists():
        return []
    try:
        lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        entries = []
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
            if len(entries) >= limit:
                break
        return entries
    except OSError:
        return []


def get_logs(tail: int = 100) -> str:
    """读取运行日志尾部，解析 JSON 行为可读文本"""
    if not LOG_FILE.exists():
        return "暂无日志"
    try:
        lines = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-tail:]
    except OSError:
        return "暂无日志"

    rendered = []
    for line in lines:
        try:
            entry = json.loads(line)
            rendered.append(
                f"[{entry.get('timestamp', '')}] {entry.get('level', '')} {entry.get('message', '')}"
            )
        except ValueError:
            rendered.append(line)
    return "\n".join(rendered) or "暂无日志"


# ---------- 路由 ----------

def _render(config, heartbeat):
    running = is_service_running(heartbeat)
    last_poll_ts = (heartbeat or {}).get("last_poll")
    if last_poll_ts:
        last_poll = datetime.fromtimestamp(last_poll_ts).strftime("%Y-%m-%d %H:%M:%S")
    else:
        last_poll = "-"

    return render_template_string(
        HTML_TEMPLATE,
        running=running,
        email=config["email"] if config else "未配置（请运行 python init_setup.py）",
        whitelist_count=len((config or {}).get("allowed_senders") or []),
        interval=(config or {}).get("poll_interval", 30),
        processed=(heartbeat or {}).get("emails_processed", 0),
        last_poll=last_poll,
        logs=get_logs(),
    )


@app.route('/')
def index():
    config = get_config_safe()
    return _render(config, get_heartbeat())


@app.route('/api/tasks')
def api_tasks():
    return jsonify({'tasks': get_history()})


@app.route('/api/send', methods=['POST'])
def api_send():
    """发送任务邮件（由运行中的服务在下一轮轮询时接收处理）"""
    config = get_config_safe()
    if not config:
        return jsonify({'success': False, 'error': '服务未配置，请先运行 python init_setup.py'})

    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    to_addr = (data.get('email') or '').strip() or config['email']

    if not content:
        return jsonify({'success': False, 'error': '任务内容不能为空'})

    client = SMTPClient(
        host=config['smtp_host'],
        port=config['smtp_port'],
        email=config['email'],
        password=config['password'],
    )
    subject = f"[任务] {datetime.now().strftime('%m-%d %H:%M')}"
    if client.send(to_addr, subject, content):
        return jsonify({'success': True, 'message': '任务已发送'})
    return jsonify({'success': False, 'error': 'SMTP 发送失败，请查看服务日志'})


@app.route('/api/clear', methods=['POST'])
def api_clear():
    """清理任务处理记录"""
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        return jsonify({'success': True})
    except OSError as e:
        return jsonify({'success': False, 'error': str(e)})


def run_app(host: str = DEFAULT_WEB_HOST, port: int = DEFAULT_WEB_PORT):
    """启动 Web 面板（生产模式：非 debug）"""
    app.run(host=host, port=port, debug=False)


if __name__ == '__main__':
    print("=" * 50)
    print("Claude Email CLI Web Dashboard")
    print(f"http://{DEFAULT_WEB_HOST}:{DEFAULT_WEB_PORT}")
    print("=" * 50)
    run_app()
