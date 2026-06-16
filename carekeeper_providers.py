# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import random
import subprocess
import sys
import time
import requests
from dataclasses import dataclass


# ยังไม่ได้เอาใส่ .env เพราะจะได้เทสง่าย
TEST_BP_PORT = "/dev/ttyUSB0"
TEST_H59_DEVICE_NAME = "H59_D105"
TEST_H59_DEVICE_ADDRESS = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D"
TEST_API_URL = "http://localhost:8000/api/v1/carekeeper"


@dataclass
class PatientInfo:
    cid: str = "-"
    th_name: str = "-"
    en_name: str = "-"
    birth_date: str = "-"
    address: str = "-"


@dataclass
class BloodPressureReading:
    systolic: int
    diastolic: int
    pulse: int


@dataclass
class DeviceStatus:
    battery_percent: int = 100
    wifi_connected: bool = False
    bluetooth_connected: bool = False


class CareKeeperProvider:
    """Interface for all data sources used by the GUI."""

    def read_patient(self) -> PatientInfo:
        raise NotImplementedError

    def measure_blood_pressure(self) -> BloodPressureReading:
        raise NotImplementedError

    def measure_spo2(self) -> int:
        raise NotImplementedError

    def measure_temperature(self) -> float:
        raise NotImplementedError

    def get_device_status(self) -> DeviceStatus:
        raise NotImplementedError
    
    def send_data(self, payload: dict) -> bool:
        raise NotImplementedError


class MockCareKeeperProvider(CareKeeperProvider):
    """Development provider for UI preview without real hardware."""

    def __init__(self) -> None:
        self._battery_percent = 100

    def read_patient(self) -> PatientInfo:
        time.sleep(1.0)
        return PatientInfo(
            cid="1-2345-67890-12-3",
            th_name="นายสมชาย ใจดี",
            en_name="Mr. Somchai Jaidee",
            birth_date="1 มกราคม 2530",
            address="123 ถนนสุขุมวิท เขตเมือง จังหวัดนครราชสีมา 30000",
        )

    def measure_blood_pressure(self) -> BloodPressureReading:
        time.sleep(1.2)
        return BloodPressureReading(
            systolic=random.randint(108, 132),
            diastolic=random.randint(68, 86),
            pulse=random.randint(66, 92),
        )

    def measure_spo2(self) -> int:
        time.sleep(0.9)
        return random.randint(96, 100)

    def measure_temperature(self) -> float:
        time.sleep(0.9)
        return round(random.uniform(36.2, 37.4), 1)

    def get_device_status(self) -> DeviceStatus:
        self._battery_percent = max(10, self._battery_percent - random.choice([0, 0, 1]))
        return DeviceStatus(
            battery_percent=self._battery_percent,
            wifi_connected=True,
            bluetooth_connected=True,
        )
    
    def send_data(self, payload: dict) -> bool:
        time.sleep(3.0)
        print("====== [Mock API Sent] ======")
        print(payload)
        print("=============================")
        return True


class RealCareKeeperProvider(CareKeeperProvider):
    """Hardware provider for Raspberry Pi / connected devices.

    This provider intentionally does not mock values. If a device is missing,
    the caller receives an exception so the GUI can show a clear error.
    """

    def __init__(
        self,
        bp_port: str | None = None,
        h59_device_name: str | None = None,
        h59_device_address: str | None = None,
        api_url: str | None = None,
    ) -> None:
        self.bp_port = bp_port or TEST_BP_PORT
        self.h59_device_name = h59_device_name or TEST_H59_DEVICE_NAME
        self.h59_device_address = h59_device_address or TEST_H59_DEVICE_ADDRESS
        self.api_url = api_url or TEST_API_URL

    def read_patient(self) -> PatientInfo:
        from lib.thaiidcard.card import ThaiIDCard

        info = ThaiIDCard().read()
        return PatientInfo(
            cid=info.cid,
            th_name=info.th_name,
            en_name=info.en_name,
            birth_date=info.birth_date,
            address=info.address,
        )

    def measure_blood_pressure(self) -> BloodPressureReading:
        from lib.bp_monitor import BPMonitor

        monitor = BPMonitor(port=self.bp_port, timeout=120)
        try:
            monitor.connect()
            result = monitor.measure()
        finally:
            monitor.disconnect()

        if not result:
            raise RuntimeError("ไม่สามารถอ่านค่าความดันได้")

        return BloodPressureReading(
            systolic=result.sys,
            diastolic=result.dia,
            pulse=result.pul,
        )

    def measure_spo2(self) -> int:
        return asyncio.run(self._measure_spo2_async())

    async def _measure_spo2_async(self) -> int:
        from lib.h59_ble import H59Device, SpO2Reader

        device = H59Device(
            device_name=self.h59_device_name,
            device_address=self.h59_device_address,
        )
        reader = SpO2Reader(device, timeout=60)

        try:
            await device.ensure_connected()
            value = await reader.read()
            if value is None:
                raise RuntimeError("ไม่สามารถอ่านค่า SpO2 ได้")
            return int(value)
        finally:
            reader.close()
            if device.is_connected:
                await device.disconnect()

    def measure_temperature(self) -> float:
        raise NotImplementedError("ยังไม่ได้เชื่อมต่อโมดูลวัดอุณหภูมิจริง")

    def get_device_status(self) -> DeviceStatus:
        return DeviceStatus(
            battery_percent=self._read_battery_percent(),
            wifi_connected=self._is_wifi_connected(),
            bluetooth_connected=self._is_bluetooth_connected(),
        )

    def _read_battery_percent(self) -> int:
        try:
            from lib.ups import UPSHat

            return int(UPSHat().get_battery_percent())
        except Exception:
            return 0

    def _is_wifi_connected(self) -> bool:
        if sys.platform == "win32":
            try:
                output = subprocess.check_output(
                    ["netsh", "wlan", "show", "interfaces"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    text=True,
                    errors="ignore",
                )
                return "State" in output and "connected" in output.lower()
            except Exception:
                return False

        try:
            output = subprocess.check_output(["iwgetid", "-r"], text=True, errors="ignore")
            return bool(output.strip())
        except Exception:
            return False

    def _is_bluetooth_connected(self) -> bool:
        try:
            output = subprocess.check_output(["bluetoothctl", "devices", "Connected"], text=True, errors="ignore")
            return bool(output.strip())
        except Exception:
            return False
        
    def send_data(self, payload: dict) -> bool:
        if not self.api_url:
            raise RuntimeError("ยังไม่ได้ตั้งค่า CAREKEEPER_API_URL สำหรับ backend")

        headers = {"Content-Type": "application/json"}
        
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=8)
        
        if 200 <= response.status_code < 300:
            return True

        raise RuntimeError(f"Server ปฏิเสธข้อมูล (Status Code: {response.status_code})")
