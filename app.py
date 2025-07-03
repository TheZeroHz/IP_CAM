import os, subprocess, threading, queue, time
from flask import Flask, request, Response, abort

app = Flask(__name__)

# ──────  settings  ──────
TOKEN   = os.getenv("RELAY_TOKEN", "changeme")
YT_URL  = os.getenv("YT_URL", "rtmp://a.rtmp.youtube.com/live2")
YT_KEY  = os.getenv("YT_KEY", "9b82-ukfh-atk7-qr76-50hs9b82-ukfh-atk7-qr76-50hs")
FPS     = 5

# ──────  JPEG queue & FFmpeg ──────
jpeg_q = queue.Queue(maxsize=20)

def ffmpeg_worker():
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-re", "-f", "mjpeg", "-r", str(FPS), "-i", "-",
        "-vf", "format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
        "-g", str(FPS*10), "-b:v", "1M",
        "-f", "flv", f"{YT_URL}/{YT_KEY}"
    ]
    print("[FFmpeg worker] Starting FFmpeg stream to YouTube...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    while True:
        frame = jpeg_q.get()
        if frame is None: break
        try:
            proc.stdin.write(frame)
        except BrokenPipeError:
            print("[FFmpeg worker] Broken pipe – restarting...")
            proc.kill()
            time.sleep(2)
            return ffmpeg_worker()

threading.Thread(target=ffmpeg_worker, daemon=True).start()

@app.route("/upload", methods=["POST"])
def upload():
    if request.args.get("token") != TOKEN:
        abort(401)
    data = request.get_data()
    if not data or data[:2] != b'\xff\xd8':
        abort(400)
    try:
        jpeg_q.put_nowait(data)
    except queue.Full:
        jpeg_q.get_nowait()
        jpeg_q.put_nowait(data)
    return "OK", 200

@app.route("/")
def index():
    return "<h2>ESP32 YouTube Relay is Running</h2>"
