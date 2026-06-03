"""
HeartRateReader — reads Heart Rate from the H59 smartwatch.

Protocol (confirmed by testing):
  - Send sequence of safe commands first (69/6A/15) as warm-up.
  - Send 1E 01 → watch starts streaming 1E [bpm] every ~1s.
  - Watch streams for ~75s then disconnects itself (hardware timer).
  - There is NO stop command — 1E 00 does not stop the stream.

Strategy (Option B):
  - Send 1E 01, wait for first HR value.
  - Once received, disconnect immediately (before 75s timer).
  - Reconnect on next measurement cycle via ensure_connected().
  - This avoids the forced disconnect and keeps connection clean.
"""

import asyncio
import logging
from typing import Optional

from .device import H59Device, WRITE_UART1, WRITE_UART2, _build

logger = logging.getLogger(__name__)

# ── Warm-up commands (safe, no disconnect risk) ───────
_HR_WARMUP = [
    ("hr_69_U1", WRITE_UART1, _build(0x69, 0x01, [0x01])),
    ("hr_6A_U1", WRITE_UART1, _build(0x6A, 0x01, [0x01])),
    ("hr_69_U2", WRITE_UART2, _build(0x69, 0x01, [0x01])),
    ("hr_15_U1", WRITE_UART1, _build(0x15, 0x01, [0x01])),
]

# ── HR stream trigger (causes watch to stream 1E [bpm] every ~1s) ─
_HR_START = _build(0x1E, 0x01)

# ── NOTE: No reliable stop command exists for 1E stream.
#    We disconnect after getting the value instead. ────


class HeartRateReader:
    """
    Reads Heart Rate (bpm) from the H59 smartwatch.

    Strategy: trigger HR stream with 1E 01, read first stable value,
    then disconnect immediately to avoid the watch's 75s forced disconnect.

    Parameters
    ----------
    device : H59Device
        A connected H59Device instance.
    timeout : float
        Maximum seconds to wait for a reading (default 30).
    warmup_delay : float
        Seconds between each warm-up command (default 1.0).
    disconnect_after : bool
        If True (default), disconnect after reading to prevent the watch's
        75s forced disconnect. Set False only if you need to chain readings.
    """

    def __init__(self, device: H59Device, timeout: float = 30.0,
                 warmup_delay: float = 1.0,
                 disconnect_after: bool = True):
        self._device          = device
        self._timeout         = timeout
        self._warmup_delay    = warmup_delay
        self._disconnect_after = disconnect_after

        self._event  = asyncio.Event()
        self._value: Optional[int] = None
        self._locked = False

        device.add_notify_handler(self._on_notify)

    # ── Public API ─────────────────────────────────────

    @property
    def last_value(self) -> Optional[int]:
        """Last successfully read Heart Rate in bpm, or None."""
        return self._value

    async def read(self) -> Optional[int]:
        """
        Trigger a Heart Rate measurement and wait for the result.

        Sends warm-up commands, triggers 1E 01 stream, waits for first
        stable HR value, then disconnects to prevent the 75s forced disconnect.

        Returns
        -------
        int or None
            Heart Rate in bpm, or None if timed out.

        Raises
        ------
        RuntimeError
            If the device is not connected.
        """
        if not self._device.is_connected:
            raise RuntimeError("Device is not connected")

        logger.info("Starting Heart Rate measurement ...")
        self._event.clear()
        self._locked = False
        self._value  = None

        # Step 1: warm-up commands (safe)
        for name, uart, cmd in _HR_WARMUP:
            ch = "UART1" if uart == WRITE_UART1 else "UART2"
            logger.debug("Warmup %s via %s", name, ch)
            ok = await self._device.write(cmd, uart=ch)
            if not ok:
                logger.warning("Warmup write failed for %s", name)
                return None
            await asyncio.sleep(self._warmup_delay)

        # Step 2: trigger 1E 01 stream
        logger.info("Sending 1E 01 — starting HR stream ...")
        ok = await self._device.write(_HR_START, uart="UART1")
        if not ok:
            logger.warning("Failed to send HR start command")
            return None

        # Step 3: wait for first HR value
        logger.info("Waiting for HR value (max %.0fs) ...", self._timeout)
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning("Heart Rate measurement timed out")

        self._locked = True

        if self._value:
            logger.info("Heart Rate: %d bpm", self._value)
        else:
            logger.warning("No Heart Rate value received")

        # Step 4: disconnect immediately to prevent 75s forced disconnect
        if self._disconnect_after and self._device.is_connected:
            logger.info("Disconnecting to reset HR stream timer ...")
            await self._device.disconnect()

        return self._value

    def close(self) -> None:
        """Unregister this reader's notify handler from the device."""
        self._device.remove_notify_handler(self._on_notify)

    # ── Internal ───────────────────────────────────────

    def _on_notify(self, data: bytearray) -> None:
        if len(data) < 2 or self._locked:
            return
        cmd, sub = data[0], data[1]

        # Primary pattern: 1E [HR] — confirmed streaming packet
        if cmd == 0x1E and sub != 0x00:
            if 30 <= sub <= 220:
                self._value = sub
                logger.debug("HR (1E stream): %d bpm", sub)
                self._event.set()

        # Fallback pattern: 6A 01 [HR]
        elif cmd == 0x6A and sub == 0x01:
            if len(data) >= 3 and 30 <= data[2] <= 220:
                self._value = data[2]
                logger.debug("HR (6A fallback): %d bpm", data[2])
                self._event.set()

        # Fallback pattern: 0C health snapshot byte[7]
        elif cmd == 0x0C and len(data) >= 8:
            hr = data[7]
            if 30 <= hr <= 220:
                self._value = hr
                logger.debug("HR (0C snapshot): %d bpm", hr)
                self._event.set()