"""ESP32 sensor input device firmware for QA-Tool v2.5b (JSON-lines over UART0).

Protocol (see core/devices/protocol.py):
  PC -> device : {"type":"hello","device_id":...,"device_type":...,"fw_version":...}
  device -> PC : {"type":"hello","device_id":...,"device_type":"esp32_in","fw_version":...}
  device -> PC : {"type":"meta","device_id":...,"channels":[{"name","unit","kind"},...]}
  PC -> device : {"type":"ping",...}   device -> PC : {"type":"pong","device_id":...}
  device -> PC : {"type":"data","device_id":...,"timestamp":...,"values":[...]}
                 (values order == channels order)

Wiring (ESP32 DevKit, no extra adapter):
  UART0 runs over the onboard CP210x bridge (GPIO1 TX / GPIO3 RX) - plug USB
  cable, the PC sees it as a COM port.  NOTE: taking UART0 disables the
  MicroPython REPL.
  REPL escape hatch: hold BOOT (GPIO0 low) during startup -> this script exits
  early and the REPL stays available for maintenance.

Channels (edit CHANNELS below):
  kind "adc"     : analog input, value 0-4095 raw (ATTN_11DB, 0-3.3V)
  kind "ds18b20" : 1-Wire temperature, value in C (first ROM found on the bus)
  kind "digital" : digital input (value 0/1), optional "pull":"up"|"down"

Flash: copy this file to the board as main.py (esptool.py only installs
MicroPython itself).  Set DEVICE_ID below or leave "" for auto (unique_id).
"""

import contextlib
import json
import machine
import time

BAUDRATE = 115200

DEVICE_ID = ""
FW_VERSION = "1.1.0"
SAMPLE_MS = 1000

CHANNELS = [
    {"name": "temp_ds", "unit": "C", "kind": "ds18b20", "pin": 4},
    {"name": "adc32", "unit": "raw", "kind": "adc", "pin": 32},
    {"name": "adc33", "unit": "raw", "kind": "adc", "pin": 33},
    {"name": "adc34", "unit": "raw", "kind": "adc", "pin": 34},
    {"name": "adc35", "unit": "raw", "kind": "adc", "pin": 35},
    {"name": "adc36", "unit": "raw", "kind": "adc", "pin": 36},
    {"name": "adc39", "unit": "raw", "kind": "adc", "pin": 39},
]
SCALE_TO_VOLTS = False

if not DEVICE_ID:
    DEVICE_ID = "esp32_in_" + machine.unique_id().hex()

_REPL_HATCH_PIN = 0
REPL_MODE = machine.Pin(_REPL_HATCH_PIN, machine.Pin.IN, machine.Pin.PULL_UP).value() == 0

uart = None
_adc_map = {}
_dig_map = {}
_ds_driver = None
ds18b20_roms = []
_ds_pending_convert = False

if not REPL_MODE:
    try:
        from os import dupterm
        dupterm(None)
    except Exception:
        pass
    uart = machine.UART(1, baudrate=BAUDRATE, tx=1, rx=3)
    while uart.any():
        uart.read()
    for ch in CHANNELS:
        kind = ch.get("kind")
        pin_no = ch.get("pin")
        try:
            if kind == "adc":
                adc = machine.ADC(machine.Pin(pin_no))
                adc.atten(machine.ADC.ATTN_11DB)
                _adc_map[pin_no] = adc
            elif kind == "digital":
                pull = None
                if ch.get("pull") == "up":
                    pull = machine.Pin.PULL_UP
                elif ch.get("pull") == "down":
                    try:
                        pull = machine.Pin.PULL_DOWN
                    except Exception:
                        pull = None
                _dig_map[pin_no] = machine.Pin(pin_no, machine.Pin.IN, pull)
            elif kind == "ds18b20":
                try:
                    import onewire
                    import ds18x20
                    _ds_driver = ds18x20.DS18X20(onewire.OneWire(machine.Pin(pin_no)))
                    ds18b20_roms = _ds_driver.scan()
                except Exception:
                    _ds_driver = None
                    ds18b20_roms = []
        except Exception as e:
            print("channel init failed:", ch.get("name"), repr(e))


def send(msg):
    line = json.dumps(msg) + "\n"
    uart.write(line.encode("utf-8"))


def announce():
    send({
        "type": "hello",
        "device_id": DEVICE_ID,
        "device_type": "esp32_in",
        "fw_version": FW_VERSION,
    })


def send_meta():
    send({
        "type": "meta",
        "device_id": DEVICE_ID,
        "channels": [
            {"name": c.get("name", ""), "unit": c.get("unit", ""),
             "kind": c.get("kind", "")}
            for c in CHANNELS
        ],
    })


def read_sensors():
    global _ds_pending_convert
    values = []
    for ch in CHANNELS:
        kind = ch.get("kind")
        pin_no = ch.get("pin")
        if kind == "adc":
            raw = _adc_map[pin_no].read()
            if SCALE_TO_VOLTS:
                values.append(round(raw / 4095.0 * 3.3, 4))
            else:
                values.append(raw)
        elif kind == "digital":
            values.append(_dig_map[pin_no].value())
        elif kind == "ds18b20":
            if _ds_driver and ds18b20_roms:
                if _ds_pending_convert:
                    values.append(round(_ds_driver.read_temp(ds18b20_roms[0]), 2))
                else:
                    _ds_driver.convert_temp()
                    values.append(None)
                _ds_pending_convert = not _ds_pending_convert
            else:
                values.append(None)
        else:
            values.append(None)
    return values


def main():
    if REPL_MODE or uart is None:
        print("BOOT held: REPL mode, UART0 not taken")
        return
    try:
        announce()
        send_meta()
    except Exception as e:
        with contextlib.suppress(Exception):
            uart.write(("ERRMETA " + repr(e) + "\n").encode("utf-8"))
    buf = b""
    last_stream = time.ticks_ms()
    while True:
        try:
            if uart.any():
                data = uart.read()
                if data:
                    buf += data
                    if len(buf) > 65536:
                        buf = b""
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        msg = json.loads(line.decode("utf-8", "replace"))
                    except Exception:
                        continue
                    mtype = msg.get("type")
                    if mtype == "hello":
                        announce()
                        send_meta()
                    elif mtype == "ping":
                        send({"type": "pong", "device_id": DEVICE_ID})

            if time.ticks_diff(time.ticks_ms(), last_stream) >= SAMPLE_MS:
                send({
                    "type": "data",
                    "device_id": DEVICE_ID,
                    "timestamp": time.time(),
                    "values": read_sensors(),
                })
                last_stream = time.ticks_ms()
        except Exception as e:
            with contextlib.suppress(Exception):
                uart.write(("ERR " + repr(e) + "\n").encode("utf-8"))

        time.sleep_ms(50)


if __name__ == "__main__":
    main()
