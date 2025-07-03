from flask import Flask, request, render_template_string

app = Flask(__name__)
latest_ip = "192.168.4.1"  # default if not registered

@app.route("/register")
def register():
    global latest_ip
    ip = request.args.get("ip")
    if ip:
        latest_ip = ip
        print(f"[REGISTERED] ESP32 IP: {ip}")
    return "OK"

@app.route("/view")
def view():
    stream_url = f"http://{latest_ip}/stream"
    return render_template_string(f"""
    <!doctype html><html><head><title>ESP32 Camera</title></head>
    <body style='background:#111;color:#eee;text-align:center'>
    <h2>ESP32 Live Stream</h2>
    <img src='{stream_url}' width='640' style='border:2px solid #ccc'><br>
    <p>Streaming from <b>{stream_url}</b></p>
    </body></html>
    """)

@app.route("/")
def index():
    return "<h3>Use /view to access camera viewer</h3>"
