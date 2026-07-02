import asyncio
from bleak import BleakScanner

async def main():
    devices = await BleakScanner.discover(timeout=10)

    for d in devices:
        print(f"Name: {d.name}")
        print(f"Address: {d.address}")
        print("-" * 50)

asyncio.run(main())

