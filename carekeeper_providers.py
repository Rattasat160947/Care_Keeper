# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import random
import re
import subprocess
import sys
import time
import uuid
import requests
from dataclasses import dataclass
from pathlib import Path


# ยังไม่ได้เอาใส่ .env เพราะจะได้เทสง่าย
TEST_DEVICE_MAC = "11.11.11.11"
TEST_BP_PORT = "/dev/ttyUSB0"
TEST_H59_DEVICE_NAME = "H59_D105"
TEST_H59_DEVICE_ADDRESS = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D"
TEST_API_URL = "https://telemed-be-maua72ti2a-as.a.run.app/api/v2/device/add_health"
TEST_API_KEY_HEADER = "api-key"
TEST_API_KEY = "test"


def read_device_mac() -> str:
    for address_file in sorted(Path("/sys/class/net").glob("*/address")):
        if address_file.parent.name == "lo":
            continue
        try:
            mac = address_file.read_text(encoding="utf-8").strip().lower()
            if re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac) and mac != "00:00:00:00:00:00":
                return mac
        except Exception:
            continue

    try:
        output = subprocess.check_output(["ip", "link"], text=True, errors="ignore")
        match = re.search(r"link/ether\s+([0-9a-f:]{17})", output, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    except Exception:
        pass

    node = uuid.getnode()
    if node and (node >> 40) % 2 == 0:
        return ":".join(f"{(node >> shift) & 0xff:02x}" for shift in range(40, -1, -8))

    return TEST_DEVICE_MAC


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

    def scan_wifi_networks(self) -> list[str]:
        return []

    def connect_wifi(self, ssid: str, password: str | None = None) -> bool:
        raise NotImplementedError

    def scan_bluetooth_devices(self) -> list[tuple[str, str]]:
        return []

    def connect_bluetooth(self, address: str) -> bool:
        raise NotImplementedError

    def reboot_device(self) -> bool:
        raise NotImplementedError

    def shutdown_device(self) -> bool:
        raise NotImplementedError


class MockCareKeeperProvider(CareKeeperProvider):
    """Development provider for UI preview without real hardware."""

    def __init__(self) -> None:
        self._battery_percent = 100
        self.device_mac = read_device_mac()

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

    def scan_wifi_networks(self) -> list[str]:
        time.sleep(0.5)
        return ["CareKeeper-Lab", "Hospital-WiFi", "Mobile-Hotspot"]

    def connect_wifi(self, ssid: str, password: str | None = None) -> bool:
        print(f"[Mock Wi-Fi] connect to {ssid}")
        return True

    def scan_bluetooth_devices(self) -> list[tuple[str, str]]:
        time.sleep(0.5)
        return [("H59_D105", TEST_H59_DEVICE_ADDRESS), ("Demo Oximeter", "AA:BB:CC:DD:EE:FF")]

    def connect_bluetooth(self, address: str) -> bool:
        print(f"[Mock Bluetooth] connect to {address}")
        return True

    def reboot_device(self) -> bool:
        print("[Mock] Reboot device")
        return True

    def shutdown_device(self) -> bool:
        print("[Mock] Shutdown device")
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
        self.device_mac = read_device_mac()
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
        if TEST_API_KEY:
            headers[TEST_API_KEY_HEADER] = TEST_API_KEY
        
        response = requests.post(self.api_url, json=payload, headers=headers, timeout=8)
        
        if 200 <= response.status_code < 300:
            return True

        raise RuntimeError(f"Server ปฏิเสธข้อมูล (Status Code: {response.status_code})")

    def toggle_wifi(self) -> None:
        current_state = self._is_wifi_connected()
        cmd = "off" if current_state else "on"
        try:
            subprocess.run(["nmcli", "radio", "wifi", cmd], check=True)
        except Exception as e:
            print(f"Failed to toggle WiFi: {e}")

    def scan_wifi_networks(self) -> list[str]:
        try:
            output = subprocess.check_output(
                ["nmcli", "-t", "-f", "SSID", "device", "wifi", "list"],
                text=True,
                errors="ignore",
            )
            networks = []
            for line in output.splitlines():
                ssid = line.strip()
                if ssid and ssid not in networks:
                    networks.append(ssid)
            return networks
        except Exception as e:
            raise RuntimeError(f"ไม่สามารถสแกน Wi-Fi ได้: {e}")

    def connect_wifi(self, ssid: str, password: str | None = None) -> bool:
        command = ["nmcli", "device", "wifi", "connect", ssid]
        if password:
            command.extend(["password", password])
        try:
            subprocess.run(command, check=True, text=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            message = e.stderr.strip() or e.stdout.strip() or str(e)
            raise RuntimeError(f"เชื่อมต่อ Wi-Fi ไม่สำเร็จ: {message}")

    def toggle_bluetooth(self) -> None:
        current_state = self._is_bluetooth_connected()
        cmd = "power off" if current_state else "power on"
        try:
            subprocess.run(["bluetoothctl", cmd.split()[0], cmd.split()[1]], check=True)
        except Exception as e:
            print(f"Failed to toggle Bluetooth: {e}")

    def scan_bluetooth_devices(self) -> list[tuple[str, str]]:
        try:
            subprocess.run(["bluetoothctl", "scan", "on"], timeout=8, capture_output=True, text=True)
        except Exception:
            pass

        try:
            output = subprocess.check_output(["bluetoothctl", "devices"], text=True, errors="ignore")
            devices = []
            for line in output.splitlines():
                parts = line.strip().split(" ", 2)
                if len(parts) >= 3 and parts[0] == "Device":
                    devices.append((parts[2], parts[1]))
            return devices
        except Exception as e:
            raise RuntimeError(f"ไม่สามารถสแกน Bluetooth ได้: {e}")

    def connect_bluetooth(self, address: str) -> bool:
        try:
            subprocess.run(["bluetoothctl", "pair", address], timeout=15, capture_output=True, text=True)
            subprocess.run(["bluetoothctl", "trust", address], timeout=10, capture_output=True, text=True)
            subprocess.run(["bluetoothctl", "connect", address], timeout=15, check=True, capture_output=True, text=True)
            self.h59_device_address = address
            return True
        except subprocess.CalledProcessError as e:
            message = e.stderr.strip() or e.stdout.strip() or str(e)
            raise RuntimeError(f"เชื่อมต่อ Bluetooth ไม่สำเร็จ: {message}")

    def reboot_device(self) -> bool:
        try:
            subprocess.run(["systemctl", "reboot"], check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            message = e.stderr.strip() or e.stdout.strip() or str(e)
            raise RuntimeError(f"รีสตาร์ทเครื่องไม่สำเร็จ: {message}")
        except Exception as e:
            raise RuntimeError(f"รีสตาร์ทเครื่องไม่สำเร็จ: {e}")

    def shutdown_device(self) -> bool:
        try:
            subprocess.run(["systemctl", "poweroff"], check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            message = e.stderr.strip() or e.stdout.strip() or str(e)
            raise RuntimeError(f"ปิดเครื่องไม่สำเร็จ: {message}")
        except Exception as e:
            raise RuntimeError(f"ปิดเครื่องไม่สำเร็จ: {e}")
