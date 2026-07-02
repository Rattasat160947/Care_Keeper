import asyncio
import logging

from _project_path import ensure_project_root

ensure_project_root()

from lib.h59_ble import H59Device, HeartRateReader, SpO2Reader

logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    device      = H59Device(
        device_name    = "H59_D105",
        device_address = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D",
    )
    hr_reader   = HeartRateReader(device, timeout=30, disconnect_after=True)
    spo2_reader = SpO2Reader(device, timeout=60)

    cycle = 0
    try:
        while True:
            cycle += 1
            print(f"\n--- Cycle {cycle} ---")

            # ── HR ───────────────────────────────────────
            # ensure_connected() reconnects if previous cycle disconnected
            await device.ensure_connected()
            hr = await hr_reader.read()
            # hr_reader.read() disconnects after reading (disconnect_after=True)
            print(f"Heart Rate : {hr if hr else 'N/A'} bpm")

            # ── SpO2 ─────────────────────────────────────
            await device.ensure_connected()
            spo2 = await spo2_reader.read()
            print(f"SpO2       : {spo2 if spo2 else 'N/A'} %")

            print(f"--- End Cycle {cycle} ---")
            await asyncio.sleep(2)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        hr_reader.close()
        spo2_reader.close()
        if device.is_connected:
            await device.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
