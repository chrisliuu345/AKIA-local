"""ESP32 output (actuator) device firmware for QA-Tool v2.5b (JSON-lines over UART0).

Protocol (see core/devices/protocol.py):
  PC -> device : {"type":"hello",...}
  device -> PC : {"type":"hello","device_id":...,"device_type":"esp32_out","fw_version":...}
  PC -> device : {"type":"ping",...}   device -> PC : {"type":"pong","device_id":...}
  PC -> device : {"type":"command","command":"<name>:<value>","device_id":...}
  device -> PC : {"type":"ack","device_id":...,"command":...,"result":"ok"}

Command grammar (value per ACTUATORS mode):
  digital : on | off
  pwm     : duty 0-1023

Wiring (ESP32 DevKit, no extra adapter):
  UART0 runs over the onboard CP210x bridge (GPIO1 TX / GPIO3 RX) - plug USB
  cable, the PC sees it as a COM port.  NOTE: taking UART0 disables the
  MicroPython REPL.
  REPL escape hatch: hold BOOT (GPIO0 low) during startup -> this script exits
  early and the REPL stays available for maintenance.
  Built-in LED pin 2. Relay module signal pin 25 (active-low board usually).

Flash: copy this file to the board as main.py (esptool.py only installs
MicroPython itself).  Set DEVICE_ID below or leave "" for auto (unique_id).
"""

import json
import machine
import time

BAUDRATE = 115200

DEVICE_ID = ""
FW_VERSION = "1.1.0"

ACTUATORS = [
    {"name": "led", "pin": 2, "mode": "digital"},
    {"name": "relay", "pin": 25, "mode": "digital"},
    {"name": "servo", "pin": 13, "mode": "pwm"},
]

if not DEVICE_ID:
    DEVICE_ID = "esp32_out_" + machine.unique_id().hex()

_REPL_HATCH_PIN = 0
REPL_MODE = machine.Pin(_REPL_HATCH_PIN, machine.Pin.IN, machine.Pin.PULL_UP).value() == 0

uart = None
pins = {}

if not REPL_MODE:
    try:
        from os import dupterm
        dupterm(None)
    except Exception:
        pass
    uart = machine.UART(1, baudrate=BAUDRATE, tx=1, rx=3)
    while uart.any():
        uart.read()
    for act in ACTUATORS:
        pin = machine.Pin(act["pin"], machine.Pin.OUT)
        pin.value(0)
        if act["mode"] == "pwm":
            pins[act["name"]] = (machine.PWM(pin, freq=50), "pwm")
        else:
            pins[act["name"]] = (pin, "digital")


def send(msg):
    line = json.dumps(msg) + "\n"
    uart.write(line.encode("utf-8"))


def announce():
    send({
        "type": "hello",
        "device_id": DEVICE_ID,
        "device_type": "esp32_out",
        "fw_version": FW_VERSION,
    })


def run_command(command):
    if ":" not in command:
        return "error: malformed command (expected <name>:<value>)"
    name, value = command.split(":", 1)
    entry = pins.get(name)
    if entry is None:
        return "error: unknown actuator " + name
    dev, mode = entry
    value = value.strip().lower()
    if mode == "digital":
        if value == "on":
            dev.value(1)
        elif value == "off":
            dev.value(0)
        else:
            return "error: digital value must be on/off"
    else:
        try:
            duty = int(value)
        except ValueError:
            return "error: pwm value must be 0-1023"
        if not 0 <= duty <= 1023:
            return "error: pwm value must be 0-1023"
        dev.duty(duty)
    return "ok"


def main():
    if REPL_MODE or uart is None:
        print("BOOT held: REPL mode, UART0 not taken")
        return
    try:
        announce()
    except Exception:
        pass
    buf = b""
    while True:
        if uart.any():
            data = uart.read()
            if data:
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    mtype = msg.get("type")
                    if mtype == "hello":
                        announce()
                    elif mtype == "ping":
                        send({"type": "pong", "device_id": DEVICE_ID})
                    elif mtype == "command":
                        result = run_command(msg.get("command", ""))
                        send({
                            "type": "ack",
                            "device_id": DEVICE_ID,
                            "command": msg.get("command", ""),
                            "result": result,
                        })

        time.sleep_ms(20)


if __name__ == "__main__":
    main()
