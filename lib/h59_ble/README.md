# h59_ble

Python BLE library for reading **Heart Rate** and **SpO2** from the
**LIGE VITRO H59** smartwatch (`H59_D105`) — no companion app required.

---

## Requirements

| Requirement | Version |
|-------------|---------|
| Python | >= 3.10 |
| bleak | >= 0.21.0 |
| OS | macOS, Linux, Windows (with BLE adapter) |

---

## Installation

```bash
pip install bleak
pip install -e .          # install h59_ble in editable mode
```

---

## Quick Start

```python
import asyncio
from h59_ble import H59Device, HeartRateReader, SpO2Reader

async def main():
    device      = H59Device()
    hr_reader   = HeartRateReader(device, timeout=60)
    spo2_reader = SpO2Reader(device, timeout=60)

    await device.connect()

    hr   = await hr_reader.read()
    spo2 = await spo2_reader.read()

    print(f"Heart Rate : {hr} bpm")
    print(f"SpO2       : {spo2} %")

    hr_reader.close()
    spo2_reader.close()
    await device.disconnect()

asyncio.run(main())
```

---

## API Reference

### `H59Device`

Connection manager. Handles scanning, connecting, keepalive, and reconnection.

```python
H59Device(
    device_name        = "H59_D105",
    device_address     = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D",
    keepalive_interval = 20.0,   # seconds between keepalive packets
    scan_timeout       = 8.0,    # BLE scan timeout
    connect_timeout    = 20.0,   # BLE connection timeout
)
```

| Method | Description |
|--------|-------------|
| `await connect(max_retries=0)` | Scan and connect. `max_retries=0` retries forever. |
| `await disconnect()` | Disconnect and cancel keepalive. |
| `await ensure_connected()` | Reconnect if connection was lost. |
| `await write(data, uart="UART1")` | Send raw bytes to UART1 or UART2. |
| `add_notify_handler(fn)` | Register `fn(data: bytearray)` for BLE notifications. |
| `remove_notify_handler(fn)` | Unregister a previously registered handler. |
| `is_connected` | `True` if the device is currently connected. |

---

### `HeartRateReader`

Triggers and reads Heart Rate from the watch.

```python
HeartRateReader(device: H59Device, timeout: float = 60.0)
```

| Method / Property | Description |
|-------------------|-------------|
| `await read()` | Start measurement, wait for result. Returns `int` (bpm) or `None`. |
| `last_value` | Last successfully read value, or `None`. |
| `close()` | Unregister notify handler from the device. Always call when done. |

**How it works internally:**

```
Python sends (in order):
  69 01 01 → UART1   trigger HR sensor
  6A 01 01 → UART1   request current HR value
  69 01 01 → UART2   trigger on secondary channel
  15 01 01 → UART1   start measurement (ACK: 15 FF)

Watch responds with any of:
  1E [HR]         → HR realtime (byte[1] = bpm)
  6A 01 [HR]      → HR confirmed (byte[2] = bpm)
  0C ... [HR] ... → Health snapshot (byte[7] = bpm)
```

> **Note:** Command `1E 01 00` triggers HR stream but causes the watch
> to disconnect after ~75 seconds — it is intentionally excluded.

---

### `SpO2Reader`

Triggers and reads SpO2 from the watch.

```python
SpO2Reader(device: H59Device, timeout: float = 60.0)
```

| Method / Property | Description |
|-------------------|-------------|
| `await read()` | Start measurement, wait for result. Returns `int` (%) or `None`. |
| `last_value` | Last successfully read value, or `None`. |
| `close()` | Unregister notify handler from the device. Always call when done. |

**How it works internally:**

```
Python sends:
  69 03 01 → UART1   start SpO2 measurement

Watch responds every 0.5s:
  69 03 00 00 ...          → measuring (no result yet)
  69 03 00 [SpO2] 01 ...   → result ready (byte[3]=%, byte[4]=0x01)
  6A 03 [SpO2] ...         → confirmed final value

Python sends after result:
  69 03 00 → UART1   stop measurement stream
```

Typical time to result: **20–30 seconds**.

---

## Cyclic Monitoring Example

```python
import asyncio
from h59_ble import H59Device, HeartRateReader, SpO2Reader

async def monitor():
    device      = H59Device()
    hr_reader   = HeartRateReader(device, timeout=60)
    spo2_reader = SpO2Reader(device, timeout=60)

    await device.connect()

    try:
        for cycle in range(1, 6):          # run 5 cycles
            print(f"\n--- Cycle {cycle} ---")

            await device.ensure_connected()
            hr = await hr_reader.read()
            print(f"Heart Rate : {hr if hr else 'N/A'} bpm")

            await device.ensure_connected()
            spo2 = await spo2_reader.read()
            print(f"SpO2       : {spo2 if spo2 else 'N/A'} %")

    finally:
        hr_reader.close()
        spo2_reader.close()
        await device.disconnect()

asyncio.run(monitor())
```

---

## Enabling Debug Logging

To see all raw BLE packets and internal decisions:

```python
import logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
```

---

## Known Limitations

| Issue | Details |
|-------|---------|
| Heart Rate timeout | HR sometimes takes a full 60s before the watch responds. |
| Disconnect | Watch drops BLE connection after ~65–100s in some scenarios. `ensure_connected()` handles reconnection automatically. |
| Battery | Battery level is broadcast passively by the watch on connect (`cmd 0x03`). No dedicated read command confirmed yet. |
| SpO2 only | SpO2 command (`69 03 01`) is confirmed working. HR still under investigation for a fully reliable trigger. |

---

## Device Protocol Summary

```
Device  : LIGE VITRO H59  (FW: H59_2.00.16)
BLE     : Nordic UART Service pattern

UART1 Write  : 6e400002-b5a3-f393-e0a9-e50e24dcca9e
UART1 Notify : 6e400003-b5a3-f393-e0a9-e50e24dcca9e
UART2 Write  : de5bf72a-d711-4e47-af26-65e3012a5dc7
UART2 Notify : de5bf729-d711-4e47-af26-65e3012a5dc7

Packet format : [CMD 1B][SUB 1B][payload 13B][CHECKSUM 1B] = 16 bytes
Checksum      : sum(all bytes except last) & 0xFF
```

---

## Project Structure

```
h59_ble/
    h59_ble/
        __init__.py      # exports H59Device, HeartRateReader, SpO2Reader
        device.py        # H59Device — connection, keepalive, write, notify
        heart_rate.py    # HeartRateReader
        spo2.py          # SpO2Reader
    example.py           # runnable example
    setup.py
    README.md
```
