# Raspberry Pi Test Guide

คู่มือนี้ใช้สำหรับวันที่เอาโปรเจค Care Keeper ไปลง Raspberry Pi และลองเชื่อมต่ออุปกรณ์จริง

## 1. เช็กค่าที่ต้องแก้ก่อนรันจริง

ไฟล์ที่ต้องดูคือ:

```text
carekeeper_providers.py
```

ค่าทดสอบจริงถูก hardcode ไว้ด้านบนไฟล์:

```python
TEST_BP_PORT = "/dev/ttyUSB0"
TEST_H59_DEVICE_NAME = "H59_D105"
TEST_H59_DEVICE_ADDRESS = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D"
TEST_API_URL = "https://telemed-be-maua72ti2a-as.a.run.app/api/v2/device/add_health"
TEST_API_KEY_HEADER = "api-key"
TEST_API_KEY = "test"
```

ถ้า backend อยู่เครื่องอื่น ห้ามใช้ `localhost` ให้เปลี่ยนเป็น IP หรือ domain ของ backend:

```python
TEST_API_URL = "https://your-backend-domain.com/api/v1/carekeeper"
```

หรือถ้า backend อยู่ในวง LAN:

```python
TEST_API_URL = "http://192.168.1.50:8000/api/v1/carekeeper"
```

ตอนส่งสรุป ระบบจะส่ง JSON ตามรูปแบบทดสอบใน PDF:

```json
{
  "mac": "11.11.11.11",
  "spo2": 98,
  "heart_rate": 75,
  "pr_bpm": 75,
  "sys": 120,
  "dia": 80,
  "pulse": 75
}
```

ถ้าต้องเปลี่ยน API key ให้แก้ `TEST_API_KEY` และถ้า backend ใช้ชื่อ header อื่น ให้แก้ `TEST_API_KEY_HEADER`

## 2. เอาโปรเจคลง Raspberry Pi

เอาโฟลเดอร์โปรเจคไปไว้บน Pi เช่น:

```bash
~/Desktop/Care_Keeper
```

เข้าโฟลเดอร์โปรเจค:

```bash
cd ~/Desktop/Care_Keeper
```

## 3. ติดตั้ง package ระบบ

```bash
sudo apt update
sudo apt install python3-venv python3-pip python3-dev swig
sudo apt install python3-smbus i2c-tools
sudo apt install bluetooth bluez
sudo apt install pcscd libpcsclite-dev
```

เปิด service สำหรับ smart card reader:

```bash
sudo systemctl enable pcscd
sudo systemctl start pcscd
```

เพิ่มสิทธิ์ user ให้ใช้ serial, bluetooth และ i2c:

```bash
sudo usermod -aG dialout,bluetooth,i2c $USER
```

จากนั้น reboot:

```bash
sudo reboot
```

## 4. เปิด I2C บน Raspberry Pi

หลัง reboot ให้เปิด config:

```bash
sudo raspi-config
```

เลือก:

```text
Interface Options > I2C > Enable
```

ถ้าระบบขอ reboot ให้ reboot อีกครั้ง

## 5. สร้าง Python virtual environment

กลับเข้าโฟลเดอร์โปรเจค:

```bash
cd ~/Desktop/Care_Keeper
```

สร้าง env:

```bash
python3 -m venv .venv
```

เปิดใช้งาน env:

```bash
source .venv/bin/activate
```

ติดตั้ง Python dependencies:

```bash
pip install --upgrade pip
pip install -r requirement.txt
```

## 6. ทดสอบอุปกรณ์แยกทีละตัว

ควรทดสอบ script แยกก่อนรัน GUI จริง เพื่อรู้ว่า error มาจากอุปกรณ์ไหน

### 6.1 ทดสอบเครื่องอ่านบัตรประชาชน

```bash
python idcard.py
```

ถ้าสำเร็จควรเห็นข้อมูลบัตร เช่น CID, ชื่อ, วันเกิด, ที่อยู่

### 6.2 ทดสอบเครื่องวัดความดัน

เช็กพอร์ต serial:

```bash
ls /dev/ttyUSB*
```

ถ้าได้ `/dev/ttyUSB0` ใช้ค่าเดิมได้

ถ้าเป็น `/dev/ttyUSB1` ให้แก้ใน `carekeeper_providers.py`:

```python
TEST_BP_PORT = "/dev/ttyUSB1"
```

ทดสอบ:

```bash
python BP.py
```

### 6.3 ทดสอบ BLE / SpO2

สแกนหาอุปกรณ์ BLE:

```bash
python ble_scaner.py
```

ถ้าเจอ address ใหม่ ให้เอาไปแก้:

```python
TEST_H59_DEVICE_ADDRESS = "ADDRESS_ที่เจอ"
```

ทดสอบอ่านค่า:

```bash
python H59_BLE.py
```

### 6.4 ทดสอบแบตเตอรี่ / UPS

```bash
python battery.py
```

ถ้าอ่านไม่ได้ ให้เช็กว่าเปิด I2C แล้วหรือยัง:

```bash
i2cdetect -y 1
```

## 7. ทดสอบ backend API

ถ้า backend deploy อยู่ข้างนอก ให้ใช้ URL จริงใน:

```python
TEST_API_URL = "https://your-backend-domain.com/api/v1/carekeeper"
```

ถ้า backend อยู่ใน LAN:

```python
TEST_API_URL = "http://192.168.1.50:8000/api/v1/carekeeper"
```

ทดสอบว่า Pi เข้าถึง backend ได้:

```bash
curl http://192.168.1.50:8000/api/v1/carekeeper
```

ถ้า endpoint รับเฉพาะ POST แล้ว GET ไม่ได้ อาจขึ้น 404 หรือ method not allowed ได้ อันนี้ไม่แปลว่า backend พังเสมอไป แค่ต้องดูว่า Pi ต่อถึง server ได้หรือไม่

## 8. รัน GUI แบบ mock ก่อน

ใช้ตรวจว่า GUI เปิดได้บน Pi:

```bash
python main_demo.py
```

โหมดนี้ไม่ต้องต่ออุปกรณ์จริง

## 9. รัน GUI กับอุปกรณ์จริง

เมื่อทดสอบอุปกรณ์แยกผ่านแล้ว ค่อยรัน:

```bash
python main_real.py
```

ลำดับใช้งาน:

1. สแกนบัตรประชาชน
2. วัดความดัน
3. วัด SpO2
4. วัดอุณหภูมิ ถ้ามี sensor จริงต่อแล้ว
5. กดดูสรุปผล
6. กดส่งข้อมูลและเสร็จสิ้นการตรวจ

## 10. หมายเหตุสำคัญ

- ตัว GUI ไม่ต้อง deploy รัน local บน Raspberry Pi ได้เลย
- Backend สามารถ deploy อยู่ข้างนอกได้ ขอแค่ Pi ต่อถึง URL นั้น
- ถ้าใช้ `localhost` ใน Pi จะหมายถึง Raspberry Pi เอง ไม่ใช่เครื่อง backend
- ถ้า backend อยู่เครื่องเพื่อน ให้ใช้ IP ของเครื่องเพื่อนใน network เดียวกัน
- ถ้า backend deploy เป็น domain ให้ใช้ `https://...`
- อุณหภูมิใน real provider ยังเป็น placeholder ถ้ายังไม่มี module sensor จริง กดแล้วจะขึ้น error

## 11. ลำดับแนะนำวันทดสอบจริง

```text
1. เปิด Raspberry Pi
2. เสียบ ID card reader
3. เสียบเครื่องวัดความดัน
4. เปิดเครื่อง SpO2 / BLE
5. เช็ก backend URL
6. รัน idcard.py
7. รัน BP.py
8. รัน ble_scaner.py
9. รัน H59_BLE.py
10. รัน battery.py
11. รัน main_demo.py
12. รัน main_real.py
```

ถ้าติด error ให้ดูว่า error เกิดจาก script ตัวไหนก่อน แล้วค่อยแก้เฉพาะส่วนนั้น
