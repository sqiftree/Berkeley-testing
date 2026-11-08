"""Client Berkeley dengan jam virtual, dapat dijalankan di laptop terpisah."""
import argparse
import json
import math
import socket
import socketserver
from berkeley import VirtualClock


def rpc(host, port, message):
    with socket.create_connection((host, port), timeout=1.5) as connection:
        connection.settimeout(1.5)
        connection.sendall((json.dumps(message) + "\n").encode())
        with connection.makefile("rb") as stream:
            result = json.loads(stream.readline(8192))
        if "error" in result:
            raise ValueError(result["error"])
        return result


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            message = json.loads(self.rfile.readline(8192))
            action = message.get("action")
            if action in ("adjust", "reset"):
                value = float(message["value"])
                if not math.isfinite(value) or abs(value) > 1e7:
                    raise ValueError("Nilai koreksi tidak valid")
                if action == "adjust":
                    self.server.clock.adjust(value)
                else:
                    self.server.clock.reset(value)
            elif action != "time":
                raise ValueError("Perintah tidak dikenal")
            result = {"time": self.server.clock.now()}
        except (ValueError, KeyError, TypeError, OSError) as error:
            result = {"error": str(error)}
        self.wfile.write((json.dumps(result) + "\n").encode())


class NodeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, offset=0):
        super().__init__(address, Handler)
        self.clock = VirtualClock(offset)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9101)
    parser.add_argument("--offset", type=float, default=20)
    args = parser.parse_args()
    if not math.isfinite(args.offset) or abs(args.offset) > 86400:
        parser.error("Offset harus antara -86400 dan 86400 detik")
    with NodeServer((args.host, args.port), args.offset) as server:
        print(f"Client siap di {args.host}:{server.server_address[1]} (offset {args.offset:+g} detik)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
