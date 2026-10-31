from flask import Flask, jsonify, render_template, request
from scraper import get_live_data
from datetime import datetime, timezone
import os, threading, time

app = Flask(__name__)
lock = threading.Lock()
CACHE_TTL = int(os.environ.get("CACHE_TTL_SECONDS", "60"))
cache = {"ts": 0, "payload": None}

def live(force=False):
    now = time.time()
    if not force and cache["payload"] and now - cache["ts"] < CACHE_TTL:
        return cache["payload"]
    with lock:
        now = time.time()
        if not force and cache["payload"] and now - cache["ts"] < CACHE_TTL:
            return cache["payload"]
        payload = get_live_data()
        payload["fetched_at"] = datetime.now(timezone.utc).isoformat()
        cache["payload"] = payload
        cache["ts"] = time.time()
        return payload

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/live")
def api_live():
    force = request.args.get("force") == "1"
    return jsonify(live(force))

@app.post("/api/refresh")
def api_refresh():
    return jsonify(live(True))

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "source": "InvestorGain", "cache_ttl_seconds": CACHE_TTL})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
