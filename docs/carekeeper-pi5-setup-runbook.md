# CareKeeper — คู่มือตั้งค่าเครื่อง Pi5 ใหม่ (Setup Runbook)

รวมขั้นตอนที่จำเป็นสำหรับตั้งเครื่อง Raspberry Pi 5 ใหม่ทั้งใบ ทำตามลำดับ Phase 1 – 10 ได้เลย
**เครื่องหมาย `<USER>` ทุกจุดในเอกสารนี้ให้แทนด้วยชื่อ user จริงที่ใช้ (เช่น `cpe05`)**

---

## Phase 0 — ก่อนเริ่ม

ตั้งเครื่องผ่าน Raspberry Pi Imager ให้เรียบร้อยก่อน (เลือก Raspberry Pi OS แบบมี Desktop, ตั้ง username/password/hostname/wifi ใน Imager เลยจะสะดวกที่สุด) เพื่อเลี่ยงหน้าจอตั้งค่าตอนบูตครั้งแรกที่มากับตัวเครื่องเอง

---

## Phase 1 — ตั้งค่าระบบพื้นฐานผ่าน raspi-config

```bash
sudo raspi-config
```
- **System Options → Boot / Autologin → Desktop Autologin** (ให้ boot เข้า desktop อัตโนมัติ)
- **Interface Options → VNC → Enable** (ถ้าจะใช้/เผื่อ `wayvnc` ให้เข้าถึงอัตโนมัติ)

reboot แล้วเข้าไปตรวจว่า login เข้า desktop ได้เอง และต่อ VNC จากเครื่องอื่นได้ปกติ (เก็บ baseline ให้เท่าก่อนต่อยอดขั้นตอนอื่น)

```bash
sudo reboot
```

---

## Phase 2 — ติดตั้ง package ที่ต้องใช้

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip pcscd pcsc-tools libccid libpcsclite-dev swig
```

(`pcscd`/`pcsc-tools`/`libccid` = อ่านตัวอ่านการ์ด, `libpcsclite-dev`/`swig` = ใช้ตอน pip install `pyscard`)

---

## Phase 3 — ก็อปปี้ไฟล์โปรเจกต์

ก็อปโค้ดหล่าทั้งหมดไปวางที่ `/home/<USER>/Care_Keeper/`:
```
Care_Keeper/
├── main_real.py
├── carekeeper_ui.py
├── carekeeper_providers.py
├── lib/
    ├── __init__.py
    ├── ups.py
    ├── bp_monitor.py
    ├── h59_ble.py
    ├── thaiidcard/
        ├── __init__.py
        ├── card.py        <-- ไฟล์นี้ต้องเป็นเวอร์ชันล่าสุด (format_thai_birth_date)
        ├── apdu.py
```

---

## Phase 4 — สร้าง Python venv + ลง package

```bash
cd ~/Care_Keeper
python3 -m venv carekeeper
source carekeeper/bin/activate
pip install PySide6 pyscard requests
# เช็คในไฟล์ lib/bp_monitor.py, lib/h59_ble.py, lib/ups.py ว่า import อะไรเพิ่ม
# (เช่น pyserial, bleak, ฯลฯ) แล้ว pip install ให้ครบตามที่เจอจริง
deactivate
```

---

## Phase 5 — สิทธิ์เข้าถึง USB (เครื่องอ่านบัตร/sensor ต่างๆ)

```bash
sudo usermod -aG dialout <USER>

sudo tee /etc/udev/rules.d/99-thaiidcard.rules << 'EOF'
SUBSYSTEM=="usb", ENV{ID_USB_INTERFACES}=="*:0b0000:*", MODE="0666"
SUBSYSTEM=="usb", MODE="0666"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
```
ถ้ามีรุ่นเครื่องอ่านบัตร CCID อื่นให้ต่อ ตรวจสอบกลุ่ม USB sensor อื่นที่จะมาต่อภายหลังด้วย (กัน access denied ล่วงหน้า)

---

## Phase 6 — polkit rule ให้ pcscd อนุญาต client ที่ไม่มี active session

(จุดนี้สำคัญมาก ถ้าข้ามจะเจอ "access denied" ตอนอ่านการ์ดเพราะ pcscd default จะอนุญาตเฉพาะ session ที่ login มีหน้าจอจริงเท่านั้น)

```bash
sudo tee /etc/polkit-1/rules.d/50-pcscd.rules << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id == "org.debian.pcsc-lite.access_pcsc" ||
        action.id == "org.debian.pcsc-lite.access_card") {
        return polkit.Result.YES;
    }
});
EOF

sudo systemctl restart polkit
sudo systemctl restart pcscd
```

---

## Phase 7 — จำกัด log ไม่ให้กิน disk

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/carekeeper-journal.conf << 'EOF'
[Journal]
SystemMaxUse=200M
MaxRetentionSec=14day
EOF
sudo systemctl restart systemd-journald
```

---

## Phase 8 — Reboot อัตโนมัติตอนตี 3 (กัน cache/memory คั่งค้างรันยาว)

```bash
sudo tee /etc/systemd/system/carekeeper-restart.service << 'EOF'
[Unit]
Description=Nightly reboot to keep memory/cache fresh on Pi5

[Service]
Type=oneshot
ExecStart=/bin/systemctl reboot
EOF

sudo tee /etc/systemd/system/carekeeper-restart.timer << 'EOF'
[Unit]
Description=Run CareKeeper nightly restart at 03:00

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now carekeeper-restart.timer
```

---

## Phase 9 — Kiosk mode: boot ตรงเข้าโปรแกรมเลย ไม่ให้เห็นเดสก์ท็อป

**ห้ามสร้าง/เขียน systemd service ใหม่สำหรับหน้าจอ (`carekeeper.service`) อีกเล่ม** — วิธีนี้เคยไม่เสถียรกับ Wayland/labwc ลองมาแล้ว ให้แก้วิธี autostart ของ labwc แทนตามนี้:

**9.1 แก้ system autostart ของ labwc (ไฟล์ที่สำคัญที่สุด ห้ามลืม):**
```bash
sudo nano /etc/xdg/labwc/autostart
```
เดิมจะมี:
```
/usr/bin/lwrespawn /usr/bin/pcmanfm-pi &
/usr/bin/lwrespawn /usr/bin/wf-panel-pi &
/usr/bin/kanshi &
/usr/bin/lxsession-xdg-autostart
```
แก้เป็น (comment 2 บรรทัดแรกออก):
```
# /usr/bin/lwrespawn /usr/bin/pcmanfm-pi &
# /usr/bin/lwrespawn /usr/bin/wf-panel-pi &
/usr/bin/kanshi &
/usr/bin/lxsession-xdg-autostart
```

> หมายเหตุ: labwc รับทั้งไฟล์ system (`/etc/xdg/labwc/autostart`) และไฟล์ของ user (`~/.config/labwc/autostart`) **พร้อมกันทั้ง 2 ไฟล์** ไม่ได้เลือกอันใดอันหนึ่ง ต้องแก้ไฟล์ system ตรงจุดนี้ด้วยเสมอ ไม่ใช่แก้ไฟล์ user เพียงอย่างเดียว

**9.2 สร้างไฟล์ autostart ของ user สำหรับเปิดโปรแกรมเรา:**
```bash
mkdir -p ~/.config/labwc
cat > ~/.config/labwc/autostart << 'EOF'
(
  while true; do
    /home/<USER>/Care_Keeper/carekeeper/bin/python3 /home/<USER>/Care_Keeper/main_real.py
    sleep 2
  done
) &
EOF
chmod +x ~/.config/labwc/autostart
```

> **ห้ามลืม `chmod +x`** — ถ้าไฟล์นี้ไม่มีสิทธิ์ executable labwc จะไม่รัน script ที่เพิ่ง (ตอนปัญหาที่มาเจอแล้วรอบก่อนหน้า)

---

## Phase 9.5 — เอาข้อความ "Welcome to the Raspberry Pi Desktop" ออก

ตอนบูตช่วงก่อนเข้า desktop/เดสก์ท็อป จะมีของ **Plymouth** เข้ามาแวบหนึ่ง (โลโก้เรสเบอร์รี + ข้อความ "Welcome to the Raspberry Pi Desktop") ข้อความนี้เป็นภาพ raster ฝังอยู่ในไฟล์ `splash.png` เลย ไม่ใช่ text ที่วางสด ดังนั้นวิธีที่เร็วและตรงที่สุดคือทำให้กลายเป็นสีเรียบ (สีเดียวกับพื้นหลัง) แทน

> หมายเหตุ: จอ **"No signal"** ที่อาจให้เจอก่อนหน้านี้อีกที เป็นข้อความจากตัวจอภาพ (monitor) เองต่างหาก ยังไม่เกี่ยวกับสัญญาณ HDMI ไม่เกี่ยวกับ Pi/Plymouth เลย เช็คจากตัว Pi เองว่าเปิดและไม่ค้างก่อนอะไร

**1) เช็คว่ามี Python + Pillow:**
```bash
python3 -c "import PIL; print(PIL.__version__)"
# ถ้า error ให้ลงเพิ่ม:
sudo apt install -y python3-pil
```

**2) backup ไฟล์เดิมไว้ก่อนเสมอ:**
```bash
sudo cp /usr/share/plymouth/themes/pix/splash.png /usr/share/plymouth/themes/pix/splash.png.bak
```

**3) เขียนทับด้วยสีเรียบ (อ่านจาก/สีจากไฟล์ backup อัตโนมัติ ไม่ต้องเดา):**
```bash
sudo python3 -c "
from PIL import Image
img = Image.open('/usr/share/plymouth/themes/pix/splash.png.bak')
bg = img.convert('RGB').getpixel((2, 2))
blank = Image.new('RGB', img.size, bg)
blank.save('/usr/share/plymouth/themes/pix/splash.png')
print('Done. Size:', img.size, 'Background color:', bg)
"
```

**4) reboot ทดสอบ:**
```bash
sudo reboot
```

ผลลัพธ์: ช่วง Plymouth จะเหลือแค่พื้นสีเรียบๆ ไม่มีโลโก้/ข้อความ "Welcome to..." อีกเลย ถ้าอยากกลับไปหน้าเดิมกลับมา มี `.bak` เก็บไว้เสมอ คืนกลับด้วย:
```bash
sudo cp /usr/share/plymouth/themes/pix/splash.png.bak /usr/share/plymouth/themes/pix/splash.png
```

> **เครื่องใหม่เอาม่านออก → เลี่ยง piwiz wizard ตั้งแต่ต้นเลย:** ถ้าตอน flash SD card ด้วย **Raspberry Pi Imager** กดปุ่มเฟือง (⚙️) ตั้งค่า hostname/username/password/wifi/locale/timezone ให้ครบตั้งแต่ก่อน flash เลย ตัว first-run wizard (`piwiz`) จะไม่ค้างขึ้นมาอีกครั้งเลยและข้ามตัวเลือกอัตโนมัติ ไม่ต้องเข้าไปแก้อะไรที่หลัง

---

## Phase 10 — Reboot แล้วเช็คให้ครบ

```bash
sudo reboot
```

เช็คหลัง reboot:
- [ ] เข้าถึงเดสก์ท็อปอัตโนมัติ ไม่ให้เห็น wallpaper/taskbar เลยไม่เห็นเลยแม้แต่นิดเดียว
- [ ] เข้า boot ไม่มีโลโก้/ข้อความ "Welcome to the Raspberry Pi Desktop" เข้ามาแล้ว (Phase 9.5)
- [ ] อ่าน "เริ่มอ่านค่าบัตรประชาชน" แล้ววันเกิดออกมาเป็น "1 มกราคม 2530" (ไม่ใช่ `25300101`)
- [ ] ต่อ VNC จากเครื่องอื่นถูกต้องปกติ
- [ ] `systemctl status carekeeper-restart.timer` → active
- [ ] `ps aux | grep -E "pcmanfm-pi|wf-panel-pi"` → ไม่เจอ

ถ้าถึงจุดครบถ้วนแล้ว โปรแกรมค่าเครื่องใหม่พร้อมสมบูรณ์ตามเครื่องเดิมแล้วครับ
