# ──────────────────────────────────────────────────────────────
#  Flask MJPEG relay – multi-thread, zero-refresh viewer
#  Author: BUBT Researcher • July 2025
# ──────────────────────────────────────────────────────────────
from flask import Flask, request, Response, render_template_string, abort
import threading, time, os

app = Flask(__name__)

# ───── settings ─────
TOKEN = os.getenv("UPLOAD_TOKEN", "changeme")   # shared secret with ESP32
BOUND = b"--frame\r\n"                          # multipart boundary
TIMEOUT = 15                                    # seconds before client drops

# ───── shared state ─────
cond   = threading.Condition()
latest = b""            # newest JPEG bytes
stamp  = time.time()    # arrival time of latest frame

# ──────────────────────────────────────────────────────────────
#  ESP32  →  POST /upload   (Content-Type: image/jpeg)
# ──────────────────────────────────────────────────────────────
@app.route("/upload", methods=["POST"])
def upload():
    if request.args.get("token") != TOKEN:
        abort(401, "bad token")

    data = request.get_data()
    if not data or data[:2] != b"\xff\xd8":     # crude JPEG check
        abort(400, "no jpeg")

    global latest, stamp
    with cond:
        latest, stamp = data, time.time()
        cond.notify_all()                       # wake every viewer

    return "OK", 200


# ──────────────────────────────────────────────────────────────
#  Browser  →  GET /stream   (multipart MJPEG)
# ──────────────────────────────────────────────────────────────
@app.route("/stream")
def stream():
    def gen():
        last = 0        # last sent timestamp
        while True:
            with cond:
                cond.wait_for(lambda: stamp != last, timeout=TIMEOUT)
                if time.time() - stamp > TIMEOUT:
                    break                    # no frames for a while → quit
                frame = latest               # copy ref under lock
                last  = stamp
            yield BOUND
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(frame)}\r\n\r\n".encode()
            yield frame + b"\r\n"
    return Response(gen(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ──────────────────────────────────────────────────────────────
#  Simple viewer  →  GET /
# ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template_string("""
<!doctype html><html><head><meta charset="utf-8">
<title>ESP32 Live Stream</title>
<style>body{margin:0;background:#111;color:#eee;text-align:center;font-family:sans-serif}
img{max-width:96%;border:2px solid #444}</style></head><body>
<h2>ESP32 Live Stream</h2>
<img src="/stream">
</body></html>
""")


if __name__ == "__main__":                     # local test
    app.run("0.0.0.0", 8000, threaded=True)
