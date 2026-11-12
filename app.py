# Language: Python 3.10+
# Target: Production Flask Web App for Render.com

import os
import threading
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for
from dumper_engine import GodTierDumperEngine

app = Flask(__name__)

STATUS_LOG = "Hệ thống sẵn sàng. Vui lòng nhập URL để bắt đầu."
IS_RUNNING = False
RESULT_FILE = "acccheck.txt"

HTML_LAYOUT = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>God-Tier Cloud Dumper Dashboard</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: monospace; padding: 20px; margin: 0; }
        .container { max-width: 1000px; margin: auto; background: #1e293b; padding: 25px; border-radius: 12px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }
        h2 { color: #38bdf8; margin-top: 0; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; color: #94a3b8; font-weight: bold; }
        input[type="text"] { width: 100%; background: #0f172a; color: #38bdf8; border: 1px solid #334155; padding: 12px; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { background: #2563eb; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
        button:hover { background: #1d4ed8; }
        button:disabled { background: #475569; cursor: not-allowed; }
        .status-box { background: #0f172a; border: 1px solid #334155; padding: 15px; border-radius: 6px; color: #fbbf24; white-space: pre-wrap; height: 120px; overflow-y: auto; margin-bottom: 20px; }
        pre { background: #0f172a; border: 1px solid #334155; padding: 15px; border-radius: 6px; overflow-x: auto; color: #4ade80; max-height: 400px; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .badge.idle { background: #334155; color: #94a3b8; }
        .badge.running { background: #16a34a; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚡ God-Tier Web Dumper & Credential Extractor</h2>
        <div style="margin-bottom: 20px;">
            Trạng thái: 
            {% if is_running %}
                <span class="badge running">Đang thực thi cào sâu...</span>
            {% else %}
                <span class="badge idle">Sẵn sàng</span>
            {% endif %}
        </div>

        <form method="POST" action="/start">
            <div class="form-group">
                <label>Nhập URL mục tiêu cần Dump:</label>
                <input type="text" name="target_url" value="{{ default_url }}" placeholder="https://example.com" required>
            </div>
            <button type="submit" {% if is_running %}disabled{% endif %}>🚀 Bắt Đầu Dump & Trích Xuất Data</button>
        </form>

        <hr style="border-color: #334155; margin: 25px 0;">

        <label>⚡ Log Tiến Trình Real-time:</label>
        <div class="status-box">{{ status_log }}</div>

        <label>📁 Dữ liệu kết quả sạch ({{ result_filename }}):</label>
        <pre>{{ file_content }}</pre>
    </div>
</body>
</html>
"""

def update_status(msg: str):
    global STATUS_LOG
    STATUS_LOG = msg

def background_task(target_url: str):
    global IS_RUNNING
    IS_RUNNING = True
    try:
        engine = GodTierDumperEngine(target_url, status_callback=update_status)
        engine.run()
    except Exception as e:
        update_status(f"[-] Lỗi hệ thống: {str(e)}")
    finally:
        IS_RUNNING = False

@app.route("/")
def index():
    file_content = ""
    log_path = Path(RESULT_FILE)
    if log_path.exists():
        file_content = log_path.read_text(encoding="utf-8", errors="ignore")
    return render_template_string(
        HTML_LAYOUT,
        is_running=IS_RUNNING,
        default_url="https://tainguyenmmo.com",
        status_log=STATUS_LOG,
        result_filename=RESULT_FILE,
        file_content=file_content || "Chưa có dữ liệu trích xuất..."
    )

@app.route("/start", methods=["POST"])
def start():
    global IS_RUNNING
    if IS_RUNNING:
        return redirect(url_for("index"))
    target_url = request.form.get("target_url", "").strip()
    if target_url:
        threading.Thread(target=background_task, args=(target_url,)).start()
    return redirect(url_for("index"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
