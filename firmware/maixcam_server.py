"""MaixCAM TCP bridge server for AKIA v2.6.2 (JSON-lines over TCP :9000).

Protocol (same JSON-lines grammar as firmware/esp32_out.py, see
core/devices/protocol.py):
  PC -> device : {"type":"hello",...}
  device -> PC : {"type":"hello","device_id":...,"device_type":"maixcam","fw_version":...}
  PC -> device : {"type":"ping",...}   device -> PC : {"type":"pong","device_id":...}
  PC -> device : {"type":"command","command":"<name>[:<value>]","device_id":...}
  device -> PC : {"type":"ack","device_id":...,"command":...,"result":"ok"|\"error: ...\"}

Command grammar (phase 1, pure software — memory red line: no maix.nn):
  echo:<text>   -> ack ok (round-trip check)
  info          -> ack ok, plus a "meta" message describing the server
  stream:on     -> periodic {"type":"recognition","class":"demo","confidence":0.9}
  stream:off    -> stop the recognition stream

Deploy (WiFi, SSH root@<ip>):
  scp firmware/maixcam_server.py root@<ip>:/root/akia_server.py
  python /root/akia_server.py            # foreground test
  nohup python /root/akia_server.py >/root/akia_server.log 2>&1 &

Memory budget: stdlib only (socket/threading/json/time), ~80MB available on
the 128MB board; do NOT import maix.nn in this server.
"""

import contextlib
import json
import socket
import threading

HOST = "0.0.0.0"
PORT = 9000
FW_VERSION = "1.0.0"
STREAM_INTERVAL = 2.0
MAX_LINE = 65536

DEVICE_ID = ""


def _read_device_id() -> str:
    try:
        with open("/sys/class/net/wlan0/address") as f:
            mac = f.read().strip().replace(":", "")
        return "maixcam_" + mac[-6:] if mac else "maixcam"
    except Exception:
        return "maixcam"


if not DEVICE_ID:
    DEVICE_ID = _read_device_id()


def send_msg(sock, msg):
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    sock.sendall(line.encode("utf-8"))


def handle_message(msg, state):
    """Process one decoded message; return list of reply messages.

    Pure function (no socket I/O) so it is unit-testable on the PC side.
    state: dict with "stream_on" flag (mutated by stream:on/off commands).
    """
    mtype = msg.get("type")
    if mtype == "hello":
        return [{
            "type": "hello",
            "device_id": DEVICE_ID,
            "device_type": "maixcam",
            "fw_version": FW_VERSION,
        }]
    if mtype == "ping":
        return [{"type": "pong", "device_id": DEVICE_ID}]
    if mtype == "command":
        command = msg.get("command", "")
        result = run_command(command, state)
        return [{
            "type": "ack",
            "device_id": DEVICE_ID,
            "command": command,
            "result": result,
        }]
    return []


def run_command(command, state):
    if not isinstance(command, str) or not command:
        return "error: empty command"
    parts = command.split(":", 1)
    name = parts[0].strip().lower()
    value = parts[1].strip() if len(parts) > 1 else ""
    if name == "echo":
        return "ok" if value else "error: echo needs text"
    if name == "info":
        return "ok"
    if name == "stream":
        if value == "on":
            state["stream_on"] = True
            return "ok"
        if value == "off":
            state["stream_on"] = False
            return "ok"
        return "error: stream value must be on/off"
    return "error: unknown command " + name


def streamer(sock, state, stop_event):
    """Send demo recognition records while stream_on is set."""
    n = 0
    while not stop_event.is_set():
        if state.get("stream_on"):
            try:
                send_msg(sock, {
                    "type": "recognition",
                    "device_id": DEVICE_ID,
                    "class": "demo",
                    "confidence": 0.90 + 0.05 * (n % 2),
                    "seq": n,
                })
                n += 1
            except Exception:
                return
        stop_event.wait(STREAM_INTERVAL)


def handle_client(conn, addr):
    state = {"stream_on": False}
    stop_event = threading.Event()
    stream_thread = threading.Thread(
        target=streamer, args=(conn, state, stop_event), daemon=True)
    stream_thread.start()
    buf = b""
    try:
        send_msg(conn, {
            "type": "hello",
            "device_id": DEVICE_ID,
            "device_type": "maixcam",
            "fw_version": FW_VERSION,
        })
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
            if len(buf) > MAX_LINE:
                buf = b""
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                try:
                    msg = json.loads(line.decode("utf-8", "replace"))
                except Exception:
                    continue
                for reply in handle_message(msg, state):
                    send_msg(conn, reply)
    except Exception:
        pass
    finally:
        stop_event.set()
        with contextlib.suppress(Exception):
            conn.close()


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(2)
    print(f"akia_server listening on {HOST}:{PORT} as {DEVICE_ID}")
    while True:
        conn, addr = srv.accept()
        threading.Thread(
            target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
