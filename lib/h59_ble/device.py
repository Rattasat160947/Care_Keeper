"""
H59Device — BLE connection manager for H59 smartwatch.
Handles scanning, connecting, subscribing, keepalive, and reconnection.
"""

import asyncio
import logging
from typing import Callable, Optional
from bleak import BleakClient, BleakScanner

logger = logging.getLogger(__name__)

# ── BLE UUIDs ─────────────────────────────────────────
NOTIFY_UART1 = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
NOTIFY_UART2 = "de5bf729-d711-4e47-af26-65e3012a5dc7"
WRITE_UART1  = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
WRITE_UART2  = "de5bf72a-d711-4e47-af26-65e3012a5dc7"

# ── Keepalive packet ──────────────────────────────────
_KEEPALIVE = bytes([0x04, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x04])


def _build(cmd: int, sub: int = 0x00,
           payload: list = [], length: int = 16) -> bytes:
    """Build a 16-byte H59 packet with checksum."""
    data = [cmd, sub] + payload
    while len(data) < length - 1:
        data.append(0x00)
    data.append(sum(data) & 0xFF)
    return bytes(data)


class H59Device:
    """
    BLE connection manager for the H59 smartwatch (H59_D105).

    Manages connection lifecycle, GATT subscriptions, and keepalive.
    HeartRateReader and SpO2Reader use this class as their transport layer.

    Parameters
    ----------
    device_name : str
        Advertised BLE name to scan for (default "H59_D105").
    device_address : str, optional
        MAC / UUID address used as fallback when scan by name fails.
    keepalive_interval : float
        Seconds between keepalive packets (default 20).
    scan_timeout : float
        BleakScanner discover timeout in seconds (default 8).
    connect_timeout : float
        BleakClient connection timeout in seconds (default 20).
    """

    def __init__(
        self,
        device_name: str = "H59_D105",
        device_address: str = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D",
        keepalive_interval: float = 20.0,
        scan_timeout: float = 8.0,
        connect_timeout: float = 20.0,
    ):
        self.device_name        = device_name
        self.device_address     = device_address
        self.keepalive_interval = keepalive_interval
        self.scan_timeout       = scan_timeout
        self.connect_timeout    = connect_timeout

        self._client: Optional[BleakClient] = None
        self._connected = False
        self._keepalive_task: Optional[asyncio.Task] = None
        self._notify_handlers: list[Callable[[bytearray], None]] = []

    # ── Public API ─────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        return self._connected and (
            self._client is not None and self._client.is_connected
        )

    def add_notify_handler(self, handler: Callable[[bytearray], None]) -> None:
        """Register a callback invoked for every incoming BLE notification."""
        if handler not in self._notify_handlers:
            self._notify_handlers.append(handler)

    def remove_notify_handler(self, handler: Callable[[bytearray], None]) -> None:
        self._notify_handlers = [h for h in self._notify_handlers if h != handler]

    async def connect(self, max_retries: int = 0) -> None:
        """
        Scan and connect to the device.

        Parameters
        ----------
        max_retries : int
            Maximum retry attempts (0 = retry forever).
        """
        attempt = 0
        while True:
            attempt += 1
            if max_retries and attempt > max_retries:
                raise RuntimeError(
                    f"Failed to connect after {max_retries} attempts"
                )
            logger.info("Scan attempt %d ...", attempt)
            try:
                device = await self._scan()
                if device is None:
                    logger.warning("Device not found — retry in 3s")
                    await asyncio.sleep(3)
                    continue

                self._client = BleakClient(
                    device,
                    timeout=self.connect_timeout,
                    disconnected_callback=self._on_disconnect,
                )
                await self._client.connect()
                if self._client.is_connected:
                    self._connected = True
                    logger.info("Connected to %s [%s]",
                                device.name, device.address)
                    await self._subscribe()
                    self._start_keepalive()
                    return

            except Exception as exc:
                logger.warning("Connection error: %s — retry in 3s", exc)
                await asyncio.sleep(3)

    async def disconnect(self) -> None:
        """Disconnect from the device and cancel keepalive."""
        self._stop_keepalive()
        if self._client and self._client.is_connected:
            await self._client.disconnect()
        self._connected = False
        logger.info("Disconnected")

    async def ensure_connected(self) -> None:
        """Reconnect if the connection has been lost."""
        if not self.is_connected:
            logger.info("Reconnecting ...")
            try:
                await self.disconnect()
            except Exception:
                pass
            await self.connect()

    async def write(self, data: bytes,
                    uart: str = "UART1") -> bool:
        """
        Write raw bytes to the device.

        Parameters
        ----------
        data : bytes
            Packet to send.
        uart : str
            "UART1" (default) or "UART2".

        Returns
        -------
        bool
            True if write succeeded.
        """
        uuid = WRITE_UART1 if uart == "UART1" else WRITE_UART2
        try:
            await self._client.write_gatt_char(uuid, data, response=False)
            return True
        except Exception as exc:
            logger.debug("Write failed: %s", exc)
            return False

    # ── Internal helpers ───────────────────────────────

    async def _scan(self):
        found = await BleakScanner.discover(timeout=self.scan_timeout)
        device = next(
            (d for d in found
             if d.name and self.device_name.lower() in d.name.lower()),
            None,
        )
        if device is None and self.device_address:
            device = await BleakScanner.find_device_by_address(
                self.device_address, timeout=self.scan_timeout
            )
        return device

    async def _subscribe(self) -> None:
        def _handler(sender, data: bytearray):
            for h in self._notify_handlers:
                try:
                    h(data)
                except Exception as exc:
                    logger.debug("Notify handler error: %s", exc)

        for uuid in [NOTIFY_UART1, NOTIFY_UART2]:
            try:
                await self._client.start_notify(uuid, _handler)
            except Exception as exc:
                logger.debug("Subscribe %s failed: %s", uuid[:8], exc)
        await asyncio.sleep(0.5)

    def _on_disconnect(self, _client: BleakClient) -> None:
        self._connected = False
        logger.warning("Device disconnected")

    def _start_keepalive(self) -> None:
        self._stop_keepalive()
        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

    def _stop_keepalive(self) -> None:
        if self._keepalive_task:
            self._keepalive_task.cancel()
            self._keepalive_task = None

    async def _keepalive_loop(self) -> None:
        while True:
            await asyncio.sleep(self.keepalive_interval)
            if self._client and self._client.is_connected:
                try:
                    await self._client.write_gatt_char(
                        WRITE_UART1, _KEEPALIVE, response=False
                    )
                    logger.debug("Keepalive sent")
                except Exception:
                    pass
