#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MagicPanelMax Install Helper + Web Server
يعمل على الرسيفر:
  - يستقبل طلبات التثبيت من صفحة الويب
  - يقدّم صفحة index.html على نفس البورت (8765)

الاستخدام:
  python mpm_helper.py              # المنفذ 8765
  python mpm_helper.py 9000         # منفذ مخصص

من الموبايل (نفس الشبكة):
  http://IP_الرسيفر:8765/

API:
  GET  /status
  GET  /install?url=<script_url>
  POST /install
  GET  /  أو /index.html  → صفحة الكتالوج
"""

from __future__ import print_function
import sys
import os
import json
import time
import threading
import subprocess
import traceback

try:
    from urllib.parse import urlparse, parse_qs, unquote
except ImportError:
    from urlparse import urlparse, parse_qs
    from urllib import unquote

try:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
except ImportError:
    from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8765
if len(sys.argv) > 1:
    try:
        PORT = int(sys.argv[1])
    except ValueError:
        pass

# مجلد صفحة الويب (بجانب السكربت أو /usr/script/mpm_web)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIRS = [
    os.path.join(_SCRIPT_DIR, "mpm_web"),
    os.path.join(_SCRIPT_DIR),
    "/usr/script/mpm_web",
    "/tmp/mpm_web",
]

def find_web_file(name):
    for d in WEB_DIRS:
        p = os.path.join(d, name)
        if os.path.isfile(p):
            return p
    return None

MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".txt": "text/plain; charset=utf-8",
}

INSTALL_LOCK = threading.Lock()
LAST_RESULT = {
    "status": "idle",
    "message": "جاهز",
    "url": "",
    "time": "",
    "log": []
}


def log_msg(msg):
    ts = time.strftime("%H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    LAST_RESULT["log"].append(line)
    if len(LAST_RESULT["log"]) > 50:
        LAST_RESULT["log"] = LAST_RESULT["log"][-50:]


def run_install(script_url):
    """تنزيل وتشغيل سكربت التثبيت"""
    global LAST_RESULT

    with INSTALL_LOCK:
        LAST_RESULT = {
            "status": "installing",
            "message": "جاري التثبيت...",
            "url": script_url,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "log": []
        }
        log_msg("بدء التثبيت: %s" % script_url)

        tmp_script = "/tmp/mpm_install_%d.sh" % int(time.time())
        try:
            # تنظيف أي ملف قديم
            if os.path.exists(tmp_script):
                os.remove(tmp_script)

            # 1) تنزيل السكربت
            log_msg("تنزيل السكربت...")
            dl = subprocess.Popen(
                ["wget", "-q", "--no-check-certificate", "-O", tmp_script, script_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            out, err = dl.communicate()
            if dl.returncode != 0:
                # تجربة curl كبديل
                log_msg("wget فشل، تجربة curl...")
                dl2 = subprocess.Popen(
                    ["curl", "-fsSL", "-o", tmp_script, script_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                out2, err2 = dl2.communicate()
                if dl2.returncode != 0:
                    raise Exception("فشل التنزيل (wget/curl). تأكد من الاتصال بالإنترنت.")

            if not os.path.exists(tmp_script) or os.path.getsize(tmp_script) < 10:
                raise Exception("الملف المنزّل فارغ أو غير موجود")

            # 2) صلاحيات التنفيذ
            os.chmod(tmp_script, 0o755)
            log_msg("تم التنزيل (%d بايت)" % os.path.getsize(tmp_script))

            # 3) تشغيل السكربت
            log_msg("تشغيل سكربت التثبيت...")
            proc = subprocess.Popen(
                ["bash", tmp_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd="/tmp"
            )
            stdout, _ = proc.communicate()
            output = stdout.decode("utf-8", "replace") if isinstance(stdout, bytes) else str(stdout)

            for line in output.splitlines()[-20:]:
                log_msg("  | " + line[:120])

            if proc.returncode != 0:
                LAST_RESULT["status"] = "error"
                LAST_RESULT["message"] = "انتهى السكربت برمز خطأ: %d" % proc.returncode
                log_msg("فشل التثبيت (code=%d)" % proc.returncode)
            else:
                LAST_RESULT["status"] = "ok"
                LAST_RESULT["message"] = "تم التثبيت بنجاح"
                log_msg("تم التثبيت بنجاح")

        except Exception as e:
            LAST_RESULT["status"] = "error"
            LAST_RESULT["message"] = str(e)
            log_msg("خطأ: %s" % e)
            traceback.print_exc()
        finally:
            try:
                if os.path.exists(tmp_script):
                    os.remove(tmp_script)
            except Exception:
                pass

    return LAST_RESULT


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code, html):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        if path == "/status":
            self._json(200, LAST_RESULT)
            return

        if path == "/install":
            url = ""
            if "url" in qs:
                url = qs["url"][0]
                try:
                    url = unquote(url)
                except Exception:
                    pass
            if not url or not url.startswith("http"):
                self._json(400, {"status": "error", "message": "رابط غير صالح. استخدم ?url=https://..."})
                return
            if INSTALL_LOCK.locked():
                self._json(409, {"status": "busy", "message": "جاري تثبيت آخر، انتظر..."})
                return
            # تشغيل في خيط منفصل حتى لا يعلق الطلب
            t = threading.Thread(target=run_install, args=(url,))
            t.daemon = True
            t.start()
            self._json(200, {
                "status": "started",
                "message": "بدأ التثبيت في الخلفية",
                "url": url
            })
            return

        
        # ===== ملفات الويب الثابتة (index.html وغيرها) =====
        rel = path.lstrip("/") or "index.html"
        if rel == "" or rel == "/":
            rel = "index.html"
        # منع path traversal
        rel = rel.replace("..", "").replace("\\", "/").lstrip("/")
        fpath = find_web_file(rel)
        if fpath:
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                ext = os.path.splitext(fpath)[1].lower()
                ctype = MIME.get(ext, "application/octet-stream")
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self._cors()
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                log_msg("خطأ قراءة ملف ويب: %s" % e)

        # صفحة حالة المساعد إن لم توجد index.html
        html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MPM Helper</title>
<style>
body{font-family:sans-serif;background:#0a0e1a;color:#e8f4ff;padding:24px;max-width:600px;margin:auto}
h1{color:#00d4ff} .ok{color:#51cf66} .err{color:#ff6b6b}
pre{background:#152238;padding:12px;border-radius:8px;overflow:auto;font-size:12px;direction:ltr;text-align:left}
a{color:#00d4ff}
</style></head>
<body>
<h1>MagicPanelMax Helper</h1>
<p>الحالة: <b>%s</b> — %s</p>
<p>المنفذ: <b>%d</b></p>
<p>ضع ملف <code>index.html</code> في <code>/usr/script/mpm_web/</code> لعرض الكتالوج هنا.</p>
<pre>%s</pre>
<p style="color:#888;font-size:13px">API: /status &nbsp;|&nbsp; /install?url=...</p>
</body></html>""" % (
            LAST_RESULT["status"],
            LAST_RESULT["message"],
            PORT,
            "\n".join(LAST_RESULT.get("log", [])[-15:])
        )
        self._html(200, html)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        length = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(length).decode("utf-8", "replace") if length else ""

        url = ""
        if path == "/install":
            # form or JSON
            if body.startswith("{"):
                try:
                    data = json.loads(body)
                    url = data.get("url", "")
                except Exception:
                    pass
            else:
                qs = parse_qs(body)
                if "url" in qs:
                    url = qs["url"][0]

            if not url or not url.startswith("http"):
                self._json(400, {"status": "error", "message": "رابط غير صالح"})
                return
            if INSTALL_LOCK.locked():
                self._json(409, {"status": "busy", "message": "جاري تثبيت آخر"})
                return
            t = threading.Thread(target=run_install, args=(url,))
            t.daemon = True
            t.start()
            self._json(200, {"status": "started", "message": "بدأ التثبيت", "url": url})
            return

        self._json(404, {"status": "error", "message": "not found"})

    def log_message(self, fmt, *args):
        print("[HTTP] " + (fmt % args))


def main():
    web = find_web_file("index.html")
    print("=" * 50)
    print("  MagicPanelMax Helper + Web")
    print("  Listening on 0.0.0.0:%d" % PORT)
    print("  Web UI:  http://<IP>:%d/" % PORT)
    print("  Status:  http://<IP>:%d/status" % PORT)
    print("  Install: http://<IP>:%d/install?url=..." % PORT)
    if web:
        print("  index.html: %s" % web)
    else:
        print("  [!] index.html not found — put it in /usr/script/mpm_web/")
    print("=" * 50)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
