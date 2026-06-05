# Care Keeper

Care Keeper is a Python-based graphical user interface for a health monitoring device. The application is designed to run on a Raspberry Pi and display vital sign measurements from connected medical sensors.

## Project Overview

This project provides a GUI dashboard for monitoring and operating health measurement sensors, including:

- Blood pressure
- Heart rate
- Blood oxygen saturation (SpO2)
- Body temperature
- Battery status
- Wi-Fi / connection status

The intended workflow is for the user to start sensor measurement from the dashboard, view the live results, and navigate to a summary page that displays the collected measurement results.

## Main Features

- Dashboard for displaying device and sensor status
- Sensor activation controls
- Measurement result display
- Battery status display
- Wi-Fi / connectivity status display
- Settings access for Raspberry Pi configuration
- Summary page for completed health measurements

## Project Structure

```text
Care_Keeper/
├── main.py              # Application entry point
├── gui.py               # Generated Python UI file
├── main_GUI.ui          # Qt Designer UI file
├── requirement.txt      # Python package requirements
├── BP.py                # Blood pressure test script
├── H59_BLE.py           # Heart rate and SpO2 BLE test script
├── battery.py           # Battery / UPS test script
├── ble_scaner.py        # BLE scanner script
├── idcard.py            # Thai ID card test script
└── lib/
    ├── bp_monitor.py    # Blood pressure monitor module
    ├── ups.py           # UPS / battery module
    ├── h59_ble/         # BLE health sensor modules
    └── thaiidcard/      # Thai ID card reader modules
```

## Requirements

- Python 3.11 or newer
- Raspberry Pi for hardware operation
- Bluetooth support for BLE sensors
- Serial connection for the blood pressure monitor
- I2C support for UPS / battery status
- Smart card reader support, if using the Thai ID card module

## Installation

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```bash
pip install -r requirement.txt
```

## Raspberry Pi System Packages

Some hardware features require system packages on Raspberry Pi:

```bash
sudo apt update
sudo apt install python3-smbus i2c-tools bluetooth bluez pcscd libpcsclite-dev
```

The user may also need permission to access serial, Bluetooth, and I2C devices:

```bash
sudo usermod -aG dialout,bluetooth,i2c $USER
```

Reboot the Raspberry Pi after changing user groups:

```bash
sudo reboot
```

## Running the Application

Run the main GUI application:

```bash
python main.py
```

## Hardware Test Scripts

The project includes separate scripts for testing individual hardware modules:

```bash
python BP.py
python H59_BLE.py
python battery.py
python ble_scaner.py
python idcard.py
```

These scripts are intended for development and hardware verification before integrating the sensors into the main GUI workflow.

## Development Notes

- The current GUI is generated from `main_GUI.ui`.
- If the UI is edited in Qt Designer, `gui.py` should be regenerated from the updated `.ui` file.
- Hardware-related modules may not work correctly on a normal Windows development machine because they require Raspberry Pi interfaces or connected external devices.
- The GUI can be developed and tested separately from the hardware by running `main.py`.

## Project Goal

The goal of this project is to provide a simple and accessible interface for operating a Raspberry Pi-based health monitoring device. The system should allow users to start measurements, view current health values, check device status, and review a summarized result page after measurement is complete.
