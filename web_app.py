"""
Claude Email CLI - Web Dashboard
Simple web interface for managing your email AI assistant
"""

import json
import os
from flask import Flask, render_template_string, request, jsonify
from pathlib import Path

app = Flask(__name__)

CONFIG_FILE = "config.json"
WORKS_DIR = Path("works")

# HTML Template
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
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            text-align: center;
            padding: 40px 0;
        }
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
            display: flex;
            justify-content: space-between;
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
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            margin: 5px;
            transition: transform 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .btn-danger { background: linear-gradient(90deg, #ef4444, #f97316); }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }
        .card h3 {
            color: #a855f7;
            margin-bottom: 15px;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 14px;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #00d9ff;
        }
        .task-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .task-item {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
        }
        .task-time { color: #888; font-size: 0.85rem; }
        .task-subject { font-weight: bold; margin: 8px 0; }
        .task-preview { color: #aaa; font-size: 0.9rem; }
        .logs {
            background: #0d1117;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📧 Claude Email CLI</h1>
            <p>通过网页控制你的 AI 邮件助手</p>
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
                <span class="label">AI 人设</span>
                <span class="value">{{ persona }}</span>
            </div>
        </div>
        
        <div style="text-align: center; margin: 20px 0;">
            <button class="btn" onclick="refreshTasks()">🔄 刷新任务</button>
            <button class="btn btn-danger" onclick="clearWorks()">🗑️ 清理任务</button>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>📝 发送新任务</h3>
                <input type="text" id="taskEmail" placeholder="发送到 (默认: 管理员邮箱)">
                <textarea id="taskContent" rows="5" placeholder="输入任务描述..."></textarea>
                <button class="btn" onclick="sendTask()">🚀 发送任务</button>
            </div>
            
            <div class="card">
                <h3>📬 最近任务</h3>
                <div class="task-list" id="taskList">
                    {% for task in tasks %}
                    <div class="task-item">
                        <div class="task-time">{{ task.time }}</div>
                        <div class="task-subject">{{ task.subject }}</div>
                        <div class="task-preview">{{ task.preview }}</div>
                    </div>
                    {% else %}
                    <p style="color: #888;">暂无任务</p>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-top: 20px;">
            <h3>📜 运行日志</h3>
            <div class="logs" id="logs">{{ logs }}</div>
        </div>
    </div>
    
    <script>
        function refreshTasks() {
            fetch('/api/tasks')
                .then(r => r.json())
                .then(data => {
                    const list = document.getElementById('taskList');
                    list.innerHTML = data.tasks.map(t => `
                        <div class="task-item">
                            <div class="task-time">${t.time}</div>
                            <div class="task-subject">${t.subject}</div>
                            <div class="task-preview">${t.preview}</div>
                        </div>
                    `).join('') || '<p style="color: #888;">暂无任务</p>';
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
                    alert('✅ 任务已发送！');
                    document.getElementById('taskContent').value = '';
                    refreshTasks();
                } else {
                    alert('❌ 发送失败: ' + data.error);
                }
            });
        }
        
        function clearWorks() {
            if (!confirm('确定要清理所有任务记录吗？')) return;
            fetch('/api/clear', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    alert('✅ 已清理');
                    refreshTasks();
                });
        }
        
        // Auto refresh
        setInterval(refreshTasks, 30000);
    </script>
</body>
</html>
'''

def load_config():
    """Load configuration"""
    if not Path(CONFIG_FILE).exists():
        return None
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_tasks():
    """Get recent tasks from works directory"""
    tasks = []
    if not WORKS_DIR.exists():
        return tasks
    
    for task_dir in sorted(WORKS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
        if task_dir.is_dir():
            input_file = task_dir / "input.txt"
            time_str = task_dir.name.split('_')[0] if '_' in task_dir.name else task_dir.name
            
            preview = ""
            subject = task_dir.name
            if input_file.exists():
                with open(input_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    preview = content[:100] + "..." if len(content) > 100 else content
                    if '\n' in content:
                        first_line = content.split('\n')[0]
                        if len(first_line) < 50:
                            subject = first_line
            
            tasks.append({
                'time': time_str,
                'subject': subject,
                'preview': preview
            })
    return tasks

def get_logs():
    """Get recent logs"""
    log_file = Path("email_ai.log")
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return ''.join(lines[-100:])
    return "暂无日志"

@app.route('/')
def index():
    config = load_config()
    if not config:
        return render_template_string(HTML_TEMPLATE,
            running=False,
            email="未配置",
            whitelist_count=0,
            interval=30,
            persona="未配置",
            tasks=[],
            logs="请先运行 init_setup.py 配置")
    
    tasks = get_tasks()
    logs = get_logs()
    
    return render_template_string(HTML_TEMPLATE,
        running=True,
        email=config.get('imap', {}).get('username', 'Unknown'),
        whitelist_count=len(config.get('whitelist', [])),
        interval=config.get('check_interval', 30),
        persona=config.get('persona', 'AI Assistant'),
        tasks=tasks,
        logs=logs)

@app.route('/api/tasks')
def api_tasks():
    return jsonify({'tasks': get_tasks()})

@app.route('/api/send', methods=['POST'])
def api_send():
    data = request.json
    # Note: This is a demo - actual email sending would need proper implementation
    return jsonify({'success': True, 'message': '任务已添加到队列（演示模式）'})

@app.route('/api/clear', methods=['POST'])
def api_clear():
    import shutil
    if WORKS_DIR.exists():
        for item in WORKS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
    return jsonify({'success': True})

if __name__ == '__main__':
    print("=" * 50)
    print("🎉 Claude Email CLI Web Dashboard")
    print("📍 http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
