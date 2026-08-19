"""Local Preview Server for Looker Embedded Dashboards & A2UI Preview."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import resolve_auth_token, resolve_looker_base_url
from app.config import settings
from app.importer import dashboard_importer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Looker Dashboard Local Embed Preview</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --primary: #1a73e8;
      --primary-hover: #1557b0;
      --bg: #f8f9fa;
      --card-bg: #ffffff;
      --border: #dadce0;
      --text: #202124;
      --text-secondary: #5f6368;
      --success: #1e8e3e;
      --warning: #f29900;
      --danger: #d93025;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Google Sans', 'Roboto', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 24px;
    }
    .container {
      max-width: 1400px;
      margin: 0 auto;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 {
      font-size: 24px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      background: #e8f0fe;
      color: var(--primary);
    }
    .controls-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .form-row {
      display: flex;
      gap: 16px;
      align-items: flex-end;
      flex-wrap: wrap;
    }
    .form-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      flex: 1;
      min-width: 200px;
    }
    label {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
    }
    input[type="text"] {
      padding: 10px 14px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    input[type="text"]:focus {
      border-color: var(--primary);
    }
    .btn {
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .btn-primary {
      background: var(--primary);
      color: white;
    }
    .btn-primary:hover {
      background: var(--primary-hover);
    }
    .btn-secondary {
      background: #ffffff;
      color: var(--text);
      border: 1px solid var(--border);
    }
    .btn-secondary:hover {
      background: #f1f3f4;
    }
    .info-bar {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid #f1f3f4;
      font-size: 13px;
      color: var(--text-secondary);
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
    }
    .info-item {
      display: flex;
      gap: 6px;
    }
    .info-item strong {
      color: var(--text);
    }
    .preview-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .preview-header {
      padding: 16px 20px;
      background: #fafafa;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .preview-title {
      font-size: 16px;
      font-weight: 500;
    }
    .status-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--warning);
    }
    .status-dot.active {
      background: var(--success);
    }
    .iframe-wrapper {
      position: relative;
      width: 100%;
      height: 800px;
      background: #fff;
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
    }
    .diagnostics-box {
      margin-top: 24px;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      font-family: monospace;
      font-size: 12px;
      max-height: 200px;
      overflow-y: auto;
    }
    .diagnostics-title {
      font-family: 'Google Sans', sans-serif;
      font-size: 14px;
      font-weight: 500;
      margin-bottom: 8px;
      color: var(--text);
    }
    .alert-tip {
      background: #e8f4fd;
      border-left: 4px solid var(--primary);
      padding: 12px 16px;
      border-radius: 0 6px 6px 0;
      margin-top: 16px;
      font-size: 13px;
      color: #0b57d0;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>📊 Looker Dashboard Embed Preview <span class="badge">Local Testbench</span></h1>
      <div>
        <a href="__LOOKER_URL__" target="_blank" class="btn btn-secondary">Open Directly in Looker ↗</a>
      </div>
    </header>

    <div class="controls-card">
      <form method="GET" action="/">
        <div class="form-row">
          <div class="form-group">
            <label for="dashboard_id">Dashboard ID or Slug</label>
            <input type="text" id="dashboard_id" name="dashboard_id" value="__DASHBOARD_ID__" placeholder="e.g. 1 or my_dashboard_slug" required>
          </div>
          <div class="form-group" style="max-width: 180px;">
            <label for="mode">Embed Mode</label>
            <input type="text" id="mode" name="mode" value="__EMBED_MODE__" placeholder="signed or direct">
          </div>
          <button type="submit" class="btn btn-primary">🔄 Reload Preview</button>
        </div>
      </form>

      <div class="info-bar">
        <div class="info-item"><span>Instance:</span> <strong>__LOOKER_HOST__</strong></div>
        <div class="info-item"><span>Dashboard ID:</span> <strong>__DASHBOARD_ID__</strong></div>
        <div class="info-item"><span>Embed Mode:</span> <strong>__EMBED_MODE_LABEL__</strong></div>
        <div class="info-item"><span>Status:</span> <span id="event-status" style="color: var(--primary); font-weight: 500;">Connecting...</span></div>
      </div>

      <div class="alert-tip">
        <strong>💡 Embedding Note:</strong> If the iframe shows a blank screen or connection refused, ensure 
        <code>http://localhost:8088</code> and <code>http://127.0.0.1:8088</code> are added under 
        <strong>Looker Admin ➔ Platform ➔ Embed ➔ Embedded Domain Allowlist</strong>.
      </div>
    </div>

    <div class="preview-card">
      <div class="preview-header">
        <div class="preview-title">Embedded Looker Dashboard View</div>
        <div class="status-indicator">
          <span class="status-dot" id="live-dot"></span>
          <span id="live-text">Listening for Looker postMessage events</span>
        </div>
      </div>
      <div class="iframe-wrapper">
        <iframe 
          id="looker-iframe" 
          src="__EMBED_SRC__" 
          allow="fullscreen" 
          allowfullscreen="true">
        </iframe>
      </div>
    </div>

    <div class="diagnostics-box">
      <div class="diagnostics-title">🔍 Embed Event & URL Diagnostics</div>
      <div><strong>Target Embed Source:</strong> <a href="__EMBED_SRC__" target="_blank" style="color: var(--primary);">__EMBED_SRC__</a></div>
      <div id="log-output" style="margin-top: 8px;"></div>
    </div>
  </div>

  <script>
    const logBox = document.getElementById('log-output');
    const statusText = document.getElementById('event-status');
    const liveDot = document.getElementById('live-dot');
    const liveText = document.getElementById('live-text');

    function addLog(msg) {
      const line = document.createElement('div');
      line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
      logBox.appendChild(line);
      logBox.scrollTop = logBox.scrollHeight;
    }

    addLog("Initialized local embed iframe container.");

    window.addEventListener('message', (event) => {
      try {
        let data = event.data;
        if (typeof data === 'string') {
          try { data = JSON.parse(data); } catch(e) {}
        }
        if (data && (data.type || data.action || data.looker)) {
          const type = data.type || data.action || 'looker_event';
          addLog(`Looker Event: ${type} ${JSON.stringify(data).substring(0, 120)}`);
          statusText.textContent = `Event received: ${type}`;
          liveDot.classList.add('active');
          liveText.textContent = 'Active Looker Embed Session';
        }
      } catch (err) {
        console.error(err);
      }
    });

    const iframe = document.getElementById('looker-iframe');
    iframe.onload = () => {
      addLog("Iframe DOM element loaded.");
    };
  </script>
</body>
</html>
"""


class EmbedPreviewHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        dashboard_id = qs.get("dashboard_id", ["1"])[0].strip()
        mode = qs.get("mode", ["signed"])[0].strip().lower()

        base_url = resolve_looker_base_url()
        token = resolve_auth_token()

        if mode == "direct":
            embed_src = f"{base_url}/embed/dashboards/{dashboard_id}"
            mode_label = "Direct URL (/embed/dashboards/)"
        else:
            try:
                embed_src = dashboard_importer.create_embed_url(dashboard_id)
                mode_label = "Signed SSO URL (/login/embed?t=...)"
            except Exception as e:
                logger.error("Failed to generate signed embed URL: %s", e)
                embed_src = f"{base_url}/embed/dashboards/{dashboard_id}"
                mode_label = f"Fallback URL (Error: {e})"

        looker_url = f"{base_url}/dashboards/{dashboard_id}"

        html = (
            HTML_TEMPLATE.replace("__DASHBOARD_ID__", dashboard_id)
            .replace("__LOOKER_HOST__", base_url)
            .replace("__EMBED_MODE__", mode)
            .replace("__EMBED_MODE_LABEL__", mode_label)
            .replace("__EMBED_SRC__", embed_src)
            .replace("__LOOKER_URL__", looker_url)
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        logger.info("%s - %s", self.client_address[0], format % args)


def run_server(port: int = 8088, dashboard_id: str = "1", open_browser: bool = True):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, EmbedPreviewHandler)

    preview_url = f"http://localhost:{port}/?dashboard_id={dashboard_id}"
    print("\n" + "=" * 80)
    print("🚀 LOOKER DASHBOARD LOCAL EMBED PREVIEW SERVER")
    print(f"🔗 URL: {preview_url}")
    print("=" * 80 + "\n")
    print(f"Press Ctrl+C to stop the server.\n")

    if open_browser:
        try:
            webbrowser.open(preview_url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping preview server...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Looker Dashboard Local Embed Preview Server")
    parser.add_argument("--port", type=int, default=8088, help="Port to run the preview server on (default: 8088)")
    parser.add_argument("--dashboard-id", type=str, default="1", help="Dashboard ID or slug to preview (default: 1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")

    args = parser.parse_args()
    run_server(port=args.port, dashboard_id=args.dashboard_id, open_browser=not args.no_browser)
