# Care Keeper

Care Keeper is a Python / PySide6 graphical user interface for a Raspberry Pi based health monitoring device. The application reads patient information from a Thai ID card, displays vital sign measurements, and shows a measurement summary.

## Current Workflow

1. Scan Thai national ID card
2. Show patient information
3. Measure vital signs from the dashboard
4. Review the summary page

## Supported Measurements

- Blood pressure: systolic / diastolic
- Pulse from the blood pressure monitor
- Blood oxygen saturation: SpO2
- Body temperature
- Battery status
- Wi-Fi status
- Bluetooth status

## Application Files

```text
Care_Keeper/
+-- main_demo.py             # Runs the GUI with mock data for UI preview
+-- main_real.py             # Runs the GUI with real hardware providers
+-- carekeeper_ui.py         # Main PySide6 GUI
+-- carekeeper_providers.py  # Mock and real data providers
+-- requirement.txt          # Python dependencies
+-- BP.py                    # Standalone blood pressure test script
+-- H59_BLE.py               # Standalone BLE SpO2 / heart-rate test script
+-- battery.py               # Standalone UPS / battery test script
+-- ble_scaner.py            # BLE scanner script
+-- idcard.py                # Standalone Thai ID card test script
+-- lib/
    +-- bp_monitor.py        # Blood pressure monitor module
    +-- ups.py               # UPS / battery module
    +-- h59_ble/             # H59 BLE sensor modules
    +-- thaiidcard/          # Thai ID card reader modules
```

## Python Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate it on Raspberry Pi / Linux:

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r requirement.txt
```

## Run Mock UI

Use this mode while designing or testing the interface without connected hardware:

```bash
python main_demo.py
```

This mode uses `MockCareKeeperProvider` and generates sample patient data and vital signs.

## Run With Real Hardware

Use this mode on the Raspberry Pi after connecting the required devices:

```bash
python main_real.py
```

This mode uses `RealCareKeeperProvider`. It does not generate fake measurement values. If a device is missing or cannot be read, the GUI will show an error message.

## Raspberry Pi System Packages

Install system packages required by the hardware modules:

```bash
sudo apt update
sudo apt install python3-smbus i2c-tools bluetooth bluez pcscd libpcsclite-dev
```

Add the current user to hardware access groups:

```bash
sudo usermod -aG dialout,bluetooth,i2c $USER
```

Reboot after changing groups:

```bash
sudo reboot
```

## Hardware Configuration

The real provider reads optional environment variables:

```bash
export BP_PORT=/dev/ttyUSB0
export H59_DEVICE_NAME=H59_D105
export H59_DEVICE_ADDRESS=EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D
```

Defaults are already set in `carekeeper_providers.py`, but these variables are useful if the serial port or BLE device changes.

## Hardware Notes

- Thai ID card data is read through `lib/thaiidcard/card.py`.
- Blood pressure is read through `lib/bp_monitor.py`.
- SpO2 is read through the H59 BLE module in `lib/h59_ble/`.
- Battery percentage is read through `lib/ups.py`.
- Temperature currently has a placeholder in the real provider and must be connected to the actual temperature sensor module before real temperature measurement is available.

## Standalone Hardware Tests

Run these scripts to test hardware modules separately before using the full GUI:

```bash
python idcard.py
python BP.py
python H59_BLE.py
python battery.py
python ble_scaner.py
```

## Development Notes

- UI layout and styling are in `carekeeper_ui.py`.
- Data access is separated into `carekeeper_providers.py`.
- Use `main_demo.py` for interface development.
- Use `main_real.py` only when the Raspberry Pi and hardware sensors are connected.
