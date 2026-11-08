"""Satu perintah untuk demo Berkeley Kelompok 8. Python 3.9+, tanpa pip."""
import argparse
import functools
import json
import math
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from berkeley import VirtualClock, calculate
from node import rpc

ROOT = Path(__file__).resolve().parent
PRESETS = {"normal": [20, -10, 35], "outlier": [20, -10, 300]}


class Coordinator:
    def __init__(self, endpoints):
        self.clock = VirtualClock()
        self.endpoints = endpoints
        self.lock = threading.Lock()
        self.history = []
        self.threshold = 120

    def sample(self):
        rows = []
        for index, (host, port) in enumerate(self.endpoints, 1):
            row = {"name": f"Client {index}", "address": f"{host}:{port}", "online": False}
            try:
                start = time.monotonic()
                reply = rpc(host, port, {"action": "time"})
                rtt = time.monotonic() - start
                # Timestamp client diambil sebelum balasan; estimasi perjalanan pulang RTT/2.
                delta = float(reply["time"]) + rtt / 2 - self.clock.now()
                if not math.isfinite(delta):
                    raise ValueError("Jam tidak valid")
                row.update(online=True, offset=delta, rtt=rtt)
            except (OSError, ValueError, KeyError, TypeError):
                pass
            rows.append(row)
        return rows

    def state(self):
        rows = self.sample()
        return {"time": self.clock.now(), "nodes": rows, "history": self.history,
                "threshold": self.threshold}

    def synchronize(self):
        rows = self.sample()
        offsets = {r["name"]: r["offset"] for r in rows if r["online"]}
        if not offsets:
            raise ValueError("Tidak ada client online. Jalankan client dahulu.")
        average, corrections, accepted = calculate(offsets, self.threshold)
        for row, endpoint in zip(rows, self.endpoints):
            row["included"] = row["name"] in accepted
            row["applied"] = False
            if row["online"]:
                row["correction"] = corrections[row["name"]]
                try:
                    rpc(*endpoint, {"action": "adjust", "value": row["correction"]})
                    row["applied"] = True
                except (OSError, ValueError):
                    pass
        self.clock.adjust(average)
        record = {"round": (self.history[-1]["round"] if self.history else 0) + 1, "average": average,
                  "count": len(accepted) + 1, "nodes": rows}
        self.history.append(record)
        self.history = self.history[-50:]
        return record

    def reset(self, preset):
        if preset not in PRESETS:
            raise ValueError("Skenario tidak dikenal")
        self.clock.reset(0)
        failed = []
        for i, endpoint in enumerate(self.endpoints):
            try:
                rpc(*endpoint, {"action": "reset", "value": PRESETS[preset][i % 3]})
            except (OSError, ValueError):
                failed.append(f"Client {i + 1}")
        self.history.clear()
        return {"failed": failed}


class WebHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, data, status=200):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            with self.server.coordinator.lock:
                self.respond(self.server.coordinator.state())
        else:
            super().do_GET()

    def do_POST(self):
        # Local dashboard only; cross-origin form submissions are rejected.
        if self.headers.get("Content-Type") != "application/json":
            self.respond({"error": "Gunakan JSON"}, 415)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 4096:
                raise ValueError("Ukuran permintaan tidak valid")
            data = json.loads(self.rfile.read(length))
            with self.server.coordinator.lock:
                if self.path == "/api/sync":
                    result = self.server.coordinator.synchronize()
                elif self.path == "/api/reset":
                    result = self.server.coordinator.reset(data.get("preset", "normal"))
                else:
                    self.respond({"error": "Endpoint tidak ditemukan"}, 404)
                    return
            self.respond(result)
        except (ValueError, TypeError, AttributeError) as error:
            self.respond({"error": str(error)}, 400)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000, help="Port dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Alamat bind dashboard; Docker: 0.0.0.0")
    parser.add_argument("--clients", nargs="+", help="Client LAN, contoh 192.168.1.11:9101")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    children = []
    try:
        endpoints = []
        if args.clients:
            for value in args.clients:
                host, port = value.rsplit(":", 1)
                endpoints.append((host, int(port)))
        else:
            # Port 0 membiarkan OS memilih port bebas; client mengumumkannya lewat stdout.
            for offset in PRESETS["normal"]:
                child = subprocess.Popen([sys.executable, "-u", str(ROOT / "node.py"),
                                          "--port", "0", "--offset", str(offset)],
                                         stdout=subprocess.PIPE, text=True)
                children.append(child)
                line = child.stdout.readline()
                if not line:
                    raise RuntimeError("Client gagal dimulai")
                port = int(line.split()[3].rsplit(":", 1)[1])
                endpoints.append(("127.0.0.1", port))
        handler = functools.partial(WebHandler, directory=str(ROOT / "static"))
        with ThreadingHTTPServer((args.host, args.port), handler) as server:
            server.coordinator = Coordinator(endpoints)
            url = f"http://127.0.0.1:{server.server_port}"
            print(f"\nBerkeley • Kelompok 8\nBuka {url}\nTekan Ctrl+C untuk berhenti.", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nDemo dihentikan.")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Gagal menjalankan: {error}", file=sys.stderr)
        return 1
    finally:
        for child in children:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
