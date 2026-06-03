"""
SpO2Reader — reads blood oxygen saturation (SpO2) from the H59 smartwatch.

Protocol notes (reverse-engineered):
  - Send 69 03 01 to start measurement.
  - Watch responds with 69 03 00 00 ... (measuring) every 0.5s.
  - When byte[3] > 0 and byte[4] == 0x01, measurement is complete.
  - Send 69 03 00 to stop the measurement stream.
  - Typical time to result: 20–30 seconds.
"""

import asyncio
import logging
from typing import Optional

from .device import H59Device, WRITE_UART1, _build

logger = logging.getLogger(__name__)

_SPO2_START = _build(0x69, 0x03, [0x01])
_SPO2_STOP  = _build(0x69, 0x03, [0x00])


class SpO2Reader:
    """
    Reads blood oxygen saturation (SpO2 %) from the H59 smartwatch.

    Parameters
    ----------
    device : H59Device
        A connected H59Device instance.
    timeout : float
        Maximum seconds to wait for a reading (default 60).

    Examples
    --------
    >>> device = H59Device()
    >>> await device.connect()
    >>> reader = SpO2Reader(device)
    >>> spo2 = await reader.read()
    >>> print(f"SpO2: {spo2}%")
    """

    def __init__(self, device: H59Device, timeout: float = 60.0):
        self._device  = device
        self._timeout = timeout
        self._event   = asyncio.Event()
        self._value: Optional[int] = None

        device.add_notify_handler(self._on_notify)

    # ── Public API ─────────────────────────────────────

    @property
    def last_value(self) -> Optional[int]:
        """Last successfully read SpO2 percentage, or None."""
        return self._value

    async def read(self) -> Optional[int]:
        """
        Trigger an SpO2 measurement and wait for the result.

        Sends the start command to the watch, waits up to ``timeout``
        seconds for the watch to respond, then sends the stop command.

        Returns
        -------
        int or None
            SpO2 as a percentage (70–100), or None if timed out.

        Raises
        ------
        RuntimeError
            If the device is not connected.
        """
        if not self._device.is_connected:
            raise RuntimeError("Device is not connected")

        logger.info("Starting SpO2 measurement ...")
        self._event.clear()
        self._value = None

        ok = await self._device.write(_SPO2_START, uart="UART1")
        if not ok:
            logger.warning("Failed to send SpO2 start command")
            return None

        logger.info("Waiting for SpO2 response (max %.0fs) ...", self._timeout)
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning("SpO2 measurement timed out")

        # Stop the measurement stream
        await self._device.write(_SPO2_STOP, uart="UART1")

        if self._value is not None:
            logger.info("SpO2: %d%%", self._value)
        else:
            logger.warning("No SpO2 value received")

        return self._value

    def close(self) -> None:
        """Unregister this reader's notify handler from the device."""
        self._device.remove_notify_handler(self._on_notify)

    # ── Internal ───────────────────────────────────────

    def _on_notify(self, data: bytearray) -> None:
        if len(data) < 2:
            return
        cmd, sub = data[0], data[1]

        # Pattern 1: 69 03 00 [SpO2] 01 — measurement complete
        if cmd == 0x69 and sub == 0x03:
            if len(data) >= 5 and data[4] == 0x01:
                spo2 = data[3]
                if 70 <= spo2 <= 100:
                    self._value = spo2
                    logger.debug("SpO2 (69 03 pattern): %d%%", spo2)
                    self._event.set()

        # Pattern 2: 6A 03 [SpO2] — confirmed final value
        elif cmd == 0x6A and sub == 0x03:
            if len(data) >= 3:
                spo2 = data[2]
                if 70 <= spo2 <= 100:
                    self._value = spo2
                    logger.debug("SpO2 (6A 03 confirmed): %d%%", spo2)
                    self._event.set()
