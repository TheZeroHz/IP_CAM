#  ─────────────────────────────────────────────
#  Flask MJPEG relay (single persistent upload)
#  Author: BUBT Researcher  •  July 2025
#  ─────────────────────────────────────────────
from flask import Flask, request, Response, render_template_string, abort
import threading, queue, os

app = Flask(__name__)

TOKEN    = os.getenv("STREAM_TOKEN", "changeme")      # shared secret
BOUNDARY = b"--cam\r\n"                               # uploader's boundary

# each viewer gets its own Queue; uploader puts frames in broadcast list
viewers  = set()            # set[queue.Queue]
view_lock = threading.Lock()

# ───────── uploader ─────────
@app.route("/upload_stream", methods=["POST"])
def upload_stream():
    if request.args.get("token") != TOKEN:
        abort(401, "bad token")

    # read raw stream; split by boundary and broadcast
    stream = request.environ["wsgi.input"]
    buff   = b""
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        buff += chunk
        while True:
            idx = buff.find(BOUNDARY)
            if idx == -1:
                break
            jpg = buff[:idx]               # <header + jpeg + \r\n>
            buff = buff[idx + len(BOUNDARY):]
            # parse size / skip empty headers
            split = jpg.split(b"\r\n\r\n", 1)
            if len(split) != 2:
                continue
            body = split[1].rstrip(b"\r\n")
            with view_lock:
                for q in list(viewers):
                    try:
                        q.put_nowait(body)
                    except queue.Full:
                        pass
    return "stream ended", 200

# ───────── browser viewer ─────────
@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=5)
    with view_lock:
        viewers.add(q)

    def gen():
        try:
            while True:
                frame = q.get()
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(frame)).encode() +
                       b"\r\n\r\n" + frame + b"\r\n")
        finally:
            with view_lock:
                viewers.discard(q)

    return Response(gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame")

# ───────── tiny viewer page ─────────
HTML = """
<!doctype html><html><head><meta charset='utf-8'>
<title>Live MJPEG</title>
<style>body{background:#111;color:#eee;text-align:center;font-family:sans-serif}
img{max-width:96%;border:2px solid #555}</style></head><body>
<h2>ESP32 Live Stream</h2>
<img src="/stream">
</body></html>
"""
@app.route("/")
def index(): return render_template_string(HTML)
