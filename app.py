"""
ESP32-S3 camera relay
=====================
Receives JPEG frames from one (or many) ESP32 uploads and
re-streams them to browsers as multipart-MJPEG.

Author : BUBT Researcher
Date   : July 2025
"""

from flask import Flask, request, Response, abort, render_template_string
import threading, time, os

app = Flask(__name__)

# ───── configurable via Render's Environment settings ─────
TOKEN   = os.getenv("RELAY_TOKEN",  "changeme")  # same token in ESP32 sketch
TIMEOUT = float(os.getenv("FRAME_TIMEOUT",  "10"))  # seconds before frame deemed stale

# ───── shared state ─────
frame_lock = threading.Lock()
latest_jpeg: bytes = b''
last_ts:     float = 0.0

# ───── minimal viewer page ─────
PAGE_HTML = """
<!doctype html><html><head><meta charset='utf-8'>
<title>ESP32 Relay Stream</title>
<style>
body{margin:0;background:#111;color:#eee;text-align:center;font-family:sans-serif}
img{max-width:96%;border:2px solid #444;margin-top:1em}
</style></head><body>
<h2>Cloud Relay Stream</h2>
<img src="/stream">
</body></html>"""


# ──────────────────────────────────────────────────────────
#  /upload  – ESP32 POSTs JPEG here
# ──────────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload():
    if request.args.get("token") != TOKEN:
        abort(401, description="Bad token")
    data = request.get_data()
    if not data or data[:2] != b'\xff\xd8':        # crude JPEG signature
        abort(400, description="No JPEG")

    global latest_jpeg, last_ts
    with frame_lock:
        latest_jpeg = data
        last_ts     = time.time()

    return "OK", 200


# ──────────────────────────────────────────────────────────
#  /stream  – Browser MJPEG endpoint
# ──────────────────────────────────────────────────────────
@app.route("/stream")
def stream():
    def generator():
        boundary = b"--frame\r\n"
        while True:
            with frame_lock:
                frame = latest_jpeg
                age   = time.time() - last_ts
            if frame and age < TIMEOUT:
                yield boundary
                yield b"Content-Type: image/jpeg\r\n"
                yield f"Content-Length: {len(frame)}\r\n\r\n".encode()
                yield frame + b"\r\n"
            else:
                # no fresh frame – slow down polling
                time.sleep(0.25)

    return Response(generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ──────────────────────────────────────────────────────────
#  /          – viewer HTML
# ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string(PAGE_HTML)


# ─── local dev ───
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, threaded=True)
