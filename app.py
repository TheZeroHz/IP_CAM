from flask import Flask, request, Response, render_template_string, abort
import threading, time, os

app = Flask(__name__)

UPLOAD_TOKEN = os.getenv("UPLOAD_TOKEN", "changeme")
FLAG_TOKEN   = os.getenv("FLAG_TOKEN",   "changeme")  # same for ESP & dashboard

frame_lock   = threading.Lock()
latest_jpeg  = b""
need_frame   = False           # <— pull flag

# ───────── HTML dashboard ─────────
HTML = """
<!doctype html><html><head><meta charset='utf-8'><title>ESP32 Snapshot</title>
<style>body{background:#111;color:#eee;text-align:center;font-family:sans-serif}
img{max-width:96%;border:2px solid #666;margin-top:10px}
button{padding:.6em 1.2em;font-size:1.1em;margin-top:8px}</style>
<script>
function update(){fetch('/request?token={{t}}').then(()=>console.log('asked'))}
setInterval(()=>{document.getElementById('snap').src='/latest?'+Date.now()},1000);
</script></head><body>
<h2>ESP32 Snapshot Dashboard</h2>
<button onclick="update()">Update Frame</button><br>
<img id="snap" src="/latest"><br>
</body></html>
"""

# ───────── ESP uploads here ─────────
@app.route("/upload", methods=["POST"])
def upload():
    if request.args.get("token") != UPLOAD_TOKEN:
        abort(401)
    data = request.get_data()
    if not data or data[:2] != b'\xff\xd8':
        abort(400, "no jpeg")
    global latest_jpeg, need_frame
    with frame_lock:
        latest_jpeg = data
        need_frame  = False        # reset flag after success
    return "OK", 200

# ───────── ESP polls this flag ─────────
@app.route("/flag")
def flag():
    if request.args.get("token") != FLAG_TOKEN:
        abort(401)
    return ("1" if need_frame else "0"), 200

# ───────── Dashboard button hits /request ─────────
@app.route("/request")
def req():
    if request.args.get("token") != FLAG_TOKEN:
        abort(401)
    global need_frame
    need_frame = True
    return "OK", 200

# ───────── Serve latest image ─────────
@app.route("/latest")
def latest():
    if not latest_jpeg:
        abort(404, "no image yet")
    return Response(latest_jpeg, mimetype="image/jpeg")

# ───────── Dashboard page ─────────
@app.route("/")
def index():
    return render_template_string(HTML, t=FLAG_TOKEN)
