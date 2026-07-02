from _project_path import ensure_project_root

ensure_project_root()

from lib.bp_monitor import BPMonitor

bp = BPMonitor(port="/dev/ttyUSB0")  
bp.connect()
result = bp.measure()

if result:
    print(f"result: {result}")
else:
    print("BP Measurement fail")

bp.disconnect()
