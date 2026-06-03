from lib.ups import UPSHat

ups = UPSHat()
info = ups.get_all()

print("=" * 50)
print("Status :", info["status"])
print("Percent :", info["battery_percent"], "%")
print("Voltage :", info["battery_voltage"], "mV")
print("Current :", info["battery_current"], "mA")
print("Remaining Capacity :", info["remaining_capacity"], "mAh")
print("Cells")
print(info["cells"] ,'mV')
print()
