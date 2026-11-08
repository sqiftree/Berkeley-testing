"""Uji peluncur satu perintah, 3 proses client, HTTP, dan skenario dashboard."""
import json
from pathlib import Path
import signal
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
process = subprocess.Popen([sys.executable, "-u", str(ROOT / "app.py"),
                            "--port", "0", "--no-browser"],
                           stdout=subprocess.PIPE, text=True)
try:
    url = None
    for line in process.stdout:
        if line.startswith("Buka "):
            url = line.strip().split()[1]
            break
    assert url, "Server gagal dimulai"

    def request(path, payload=None):
        req = Request(url + path, data=None if payload is None else json.dumps(payload).encode(),
                      headers={} if payload is None else {"Content-Type": "application/json"})
        with urlopen(req, timeout=15) as response:
            return response.read()

    assert b"Berkeley" in request("/")
    assert b"function render" in request("/app.js")
    assert b":root" in request("/style.css")
    state = json.loads(request("/api/state"))
    assert len(state["nodes"]) == 3
    assert all(n["online"] for n in state["nodes"])
    result = json.loads(request("/api/sync", {}))
    assert abs(result["average"] - 11.25) < .1
    assert all(n["applied"] for n in result["nodes"])
    state = json.loads(request("/api/state"))
    assert all(abs(n["offset"]) < .1 for n in state["nodes"])
    json.loads(request("/api/reset", {"preset": "outlier"}))
    result = json.loads(request("/api/sync", {}))
    assert abs(result["average"] - 10 / 3) < .1
    assert not result["nodes"][2]["included"]
    assert result["nodes"][2]["applied"]
    print("PASS: peluncur, 3 proses TCP, aset HTTP, sinkronisasi normal, reset, outlier")
finally:
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
