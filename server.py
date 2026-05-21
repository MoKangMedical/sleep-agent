#!/usr/bin/env python3
"""
睡神 Agent 后端服务
- 静态文件服务 (index.html)
- POST /api/sleep-log    → 保存睡前记录
- GET  /api/morning-report → 获取晨间简报
"""

import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
SLEEP_LOG = DATA_DIR / 'sleep-log.json'
MORNING_REPORT = DATA_DIR / 'morning-report.json'

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


class SleepAgentHandler(SimpleHTTPRequestHandler):
    """Custom handler: serves static files from BASE_DIR + API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        if self.path == '/api/morning-report':
            self.serve_morning_report()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/sleep-log':
            self.handle_sleep_log()
        else:
            self.send_error(404)

    def serve_morning_report(self):
        if MORNING_REPORT.exists():
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(MORNING_REPORT.read_bytes())
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No report yet'}).encode())

    def handle_sleep_log(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
            SLEEP_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'message': 'Sleep log saved'}).encode())
        except json.JSONDecodeError:
            self.send_error(400, 'Invalid JSON')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging noise
        pass


def main():
    port = 8888
    server = HTTPServer(('0.0.0.0', port), SleepAgentHandler)
    print(f'🌙 睡神 Agent 服务已启动 → http://localhost:{port}')
    print(f'   📝 POST /api/sleep-log    保存睡前记录')
    print(f'   📋 GET  /api/morning-report 获取晨间简报')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n🌙 睡神已休眠...')
        server.shutdown()


if __name__ == '__main__':
    main()
