"""
H59 BLE Library
Python library for reading Heart Rate and SpO2 from LIGE VITRO H59 smartwatch.
"""

from .heart_rate import HeartRateReader
from .spo2 import SpO2Reader
from .device import H59Device

__version__ = "1.0.0"
__all__ = ["H59Device", "HeartRateReader", "SpO2Reader"]
