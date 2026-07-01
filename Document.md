# CareKeeper Evidence Document

เอกสารนี้ใช้สำหรับเตรียมหลักฐานประกอบการนำเสนอว่าโปรแกรม CareKeeper ทำงานตามที่ออกแบบไว้จริง โดยเฉพาะประเด็นที่อาจารย์อาจถามเชิงลึก เช่น การแบ่ง thread, การไม่ทำให้ UI ค้าง, การส่งข้อมูลไป Backend, การ retry เมื่ออุปกรณ์มีปัญหา และการเก็บคิวส่งข้อมูลเมื่ออินเทอร์เน็ตหลุด

## 1. แนวคิดการทำหลักฐาน

หลักฐานที่ดีควรเชื่อมโยงจากความต้องการของระบบไปถึงผลการทดสอบจริง

| สิ่งที่ต้องพิสูจน์ | หลักฐานที่ควรมี |
| --- | --- |
| โปรแกรมมี UI ครบ 3 หน้า | Screenshot / Video |
| อ่านบัตรประชาชนได้ | Screenshot หลังอ่านบัตร / log |
| กรอกเลขบัตรเองได้เมื่ออ่านบัตรไม่ได้ | Screenshot popup / video |
| วัดความดัน, SpO2, อุณหภูมิได้ | Screenshot ค่าที่วัดได้ / video |
| ส่ง JSON ไป Backend ได้ | API payload / response / log |
| UI ไม่ค้างระหว่างรออุปกรณ์ | Video + log thread |
| งาน hardware/network ทำงานใน thread แยก | code reference + thread log + pytest |
| อินเทอร์เน็ตหลุดแล้วยังไม่ทิ้งข้อมูล | SQLite queue evidence / log |
| อุปกรณ์มีปัญหาแล้วระบบ retry/disable | log / test result |

โฟลเดอร์หลักฐานที่แนะนำ:

```text
docs/
+-- evidence/
    +-- screenshots/
    +-- videos/
    +-- logs/
    +-- api_payloads/
    +-- test_results/
    +-- threading/
```

## 2. หลักฐานเรื่อง Thread / Process

ประเด็นนี้สำคัญ เพราะโปรแกรม GUI ถ้าทำงานหนักบน main thread จะทำให้หน้าจอค้างได้ ระบบนี้จึงแยกงานที่รออุปกรณ์หรือ network ออกไปทำงานใน thread อื่น

### 2.1 หลักฐานจากโค้ด

| ส่วนของระบบ | ไฟล์/บรรทัด | คำอธิบาย |
| --- | --- | --- |
| Worker สำหรับงานอุปกรณ์ | `carekeeper_ui.py:113` | `ProviderTask(QThread)` ใช้รัน action ใน thread แยก |
| จุดเริ่มงานทั่วไป | `carekeeper_ui.py:455` | `_start_task()` สร้าง `ProviderTask` แล้วสั่ง `task.start()` |
| จุดเริ่มงาน Wi-Fi/Bluetooth | `carekeeper_ui.py:477` | `_start_network_task()` แยกงาน network และกันไม่ให้กดซ้อน |
| อ่านสถานะอุปกรณ์เป็นรอบ | `carekeeper_ui.py:496` | `_request_device_status()` อ่าน Battery/Wi-Fi/Bluetooth ผ่าน worker |
| Log thread identity | `carekeeper_logging.py:12` | `log_thread_identity()` บันทึก thread id และ thread name |
| Offline queue worker | `carekeeper_queue.py:125` | `QueueDrainWorker(threading.Thread)` เป็น background daemon thread |
| เริ่ม queue worker | `carekeeper_ui.py:384` | สร้าง worker สำหรับส่งข้อมูลค้างในคิว |
| log main thread ตอนเริ่มโปรแกรม | `carekeeper_ui.py:1954` | `log_thread_identity("main")` ใช้เทียบกับ worker thread |

สรุปเชิงเทคนิค:

- UI หลักทำงานบน main thread ของ PySide6
- งานที่อาจใช้เวลานาน เช่น อ่านบัตร วัดความดัน วัด SpO2 ส่ง API และสแกน Wi-Fi/Bluetooth จะถูกส่งเข้า `ProviderTask`
- `ProviderTask` สืบทอดจาก `QThread` จึงไม่ block main UI thread
- งานส่งข้อมูลค้าง offline ใช้ `QueueDrainWorker` ซึ่งสืบทอดจาก `threading.Thread`

### 2.2 หลักฐานจาก Log ตอนรันจริง

ให้รันโปรแกรมแล้วเก็บ log ที่มี thread id / thread name ไว้เป็นหลักฐาน เช่น

```text
[main] thread_id=1111 thread_name=MainThread
[ProviderTask:'read_patient'] thread_id=2222 thread_name=Dummy-1
[ProviderTask:'measure_blood_pressure'] thread_id=3333 thread_name=Dummy-2
[ProviderTask:'send_data'] thread_id=4444 thread_name=Dummy-3
[QueueDrainWorker] thread_id=5555 thread_name=QueueDrainWorker
```

สิ่งที่ต้องอธิบายกับอาจารย์:

- ถ้า `thread_id` ของ `main` ไม่เท่ากับ `ProviderTask` แปลว่างานนั้นไม่ได้รันบน UI thread
- ถ้า `QueueDrainWorker` มี thread name ของตัวเอง แปลว่าการ drain offline queue ทำงานเป็น background thread จริง
- เมื่อกดวัดหรือส่งข้อมูล หน้าจอยังตอบสนองอยู่ แปลว่า UI ไม่ถูก block โดยงาน hardware/network

ไฟล์หลักฐานที่ควรเก็บ:

```text
docs/evidence/threading/thread_log.txt
```

### 2.3 หลักฐานจาก Automated Test

โปรเจกต์มี test เฉพาะเรื่อง thread อยู่ที่:

```text
tests/test_threading.py
```

คำสั่งที่ใช้รันทดสอบ:

```powershell
pytest tests/test_threading.py -v
```

หมายเหตุ: ถ้า environment ยังไม่มี `pytest` ให้ติดตั้ง dependency สำหรับ test ก่อน ไม่เช่นนั้นคำสั่งนี้จะรันไม่ได้ แม้ตัว test จะมีอยู่ในโปรเจกต์แล้ว

ผลที่ควรเก็บเป็นหลักฐาน:

```text
tests/test_threading.py::... PASSED
```

แนะนำบันทึกผลไว้ที่:

```text
docs/evidence/threading/pytest_threading_result.txt
```

### 2.4 หลักฐานจากวิดีโอ

ให้ถ่ายวิดีโอสั้น ๆ ตอนใช้งานจริงบน Raspberry Pi:

1. เปิดโปรแกรม
2. กดวัดความดันหรือ SpO2
3. ระหว่างรออุปกรณ์ ให้แสดงว่าหน้าจอยังเปลี่ยนสถานะหรือยังตอบสนอง
4. เมื่อวัดเสร็จ ค่าถูกอัปเดตบนหน้าจอ

ไฟล์วิดีโอที่แนะนำ:

```text
docs/evidence/threading/ui_not_freeze_demo.mp4
```

ประโยคอธิบาย:

> ระหว่างที่โปรแกรมรอผลจากอุปกรณ์จริง UI ยังไม่ค้าง เพราะงานวัดค่าถูกส่งไปทำใน `QThread` ผ่าน `ProviderTask` ส่วน main thread รับผิดชอบเฉพาะการแสดงผลและรับ interaction จากผู้ใช้

## 3. หลักฐานการส่งข้อมูลไป Backend

จุดสำคัญในโค้ด:

| ส่วนของระบบ | ไฟล์/บรรทัด | คำอธิบาย |
| --- | --- | --- |
| ปุ่มบันทึกข้อมูล | `carekeeper_ui.py:1899` | `_submit_data()` รวมค่าที่วัดได้เป็น payload |
| ส่ง HTTP POST | `carekeeper_providers.py:475` | `send_data()` ส่ง JSON ไป Backend |
| คิว offline | `carekeeper_queue.py:43` | `SubmissionQueue` เก็บ payload ลง SQLite หากส่งไม่สำเร็จ |
| background drain queue | `carekeeper_queue.py:125` | `QueueDrainWorker` ส่งข้อมูลค้างเมื่อกลับมาออนไลน์ |

รูปแบบ JSON ที่ส่ง:

```json
{
  "mac": "1c:ce:51:9a:34:77",
  "spo2": 98,
  "heart_rate": 70,
  "pr_bpm": 70,
  "sys": 120,
  "dia": 78,
  "pulse": 70
}
```

หลักฐานที่ควรเก็บ:

```text
docs/evidence/api_payloads/submit_payload.json
docs/evidence/logs/backend_success_log.txt
docs/evidence/logs/backend_failed_queue_log.txt
```

## 4. หลักฐานการเชื่อมต่ออุปกรณ์จริง

| อุปกรณ์ | จุดเชื่อมต่อในโค้ด | หลักฐานที่ควรเก็บ |
| --- | --- | --- |
| บัตรประชาชน | `carekeeper_providers.py:288` `read_patient()` | รูปหลังอ่านบัตรสำเร็จ / log |
| ความดันโลหิต | `carekeeper_providers.py:305` `measure_blood_pressure()` | รูปค่า SYS/DIA/PUL |
| SpO2 | `carekeeper_providers.py:329` `measure_spo2()` | รูปค่า SpO2 |
| อุณหภูมิ | `carekeeper_providers.py:360` `measure_temperature()` | ตอนนี้เป็นข้อจำกัดในโหมดจริงจนกว่าจะต่อ sensor จริง |
| Wi-Fi | `carekeeper_providers.py:498` `scan_wifi_networks()` และ `carekeeper_providers.py:525` `connect_wifi()` | รูปหน้าจอเลือก Wi-Fi / log |
| Bluetooth | `carekeeper_providers.py:554` `scan_bluetooth_devices()` และ `carekeeper_providers.py:591` `connect_bluetooth()` | รูปหน้าจอเลือก Bluetooth / log |

หมายเหตุ: ถ้าอุณหภูมิจริงยังไม่ได้ต่อ sensor จริง ให้ระบุเป็นข้อจำกัดอย่างตรงไปตรงมาในรายงาน เพราะ README ระบุไว้ว่ายังเป็นส่วนที่ต้องพัฒนาต่อ

## 5. Traceability Matrix

ตารางนี้ใช้ตอบว่า requirement แต่ละข้อมี implementation และหลักฐานอะไร

| Requirement | Implementation | Evidence |
| --- | --- | --- |
| มีหน้าอ่านบัตร | `carekeeper_ui.py` `_build_scan_page()` | screenshot หน้า scan |
| อ่านบัตรประชาชนได้ | `carekeeper_providers.py:288` | screenshot หลังอ่านบัตร |
| กรอกเลขบัตรเองได้ | `carekeeper_ui.py` manual CID dialog | video / screenshot |
| มีหน้าวัดค่า | `carekeeper_ui.py` `_build_dashboard_page()` | screenshot dashboard |
| วัดความดันได้ | `carekeeper_providers.py:305` | screenshot ค่า BP |
| วัด SpO2 ได้ | `carekeeper_providers.py:329` | screenshot ค่า SpO2 |
| มีหน้าสรุปผล | `carekeeper_ui.py` `_build_summary_page()` | screenshot summary |
| ส่ง Backend ได้ | `carekeeper_ui.py:1899`, `carekeeper_providers.py:475` | JSON payload / backend log |
| UI ไม่ค้าง | `ProviderTask(QThread)` | thread log / video |
| ข้อมูลไม่หายเมื่อ network หลุด | `SubmissionQueue`, `QueueDrainWorker` | SQLite queue / log |
| อุปกรณ์มี retry | `carekeeper_retry.py` | pytest / log retry |

## 6. Test Case ตัวอย่าง

| Test ID | รายการทดสอบ | วิธีทดสอบ | ผลที่คาดหวัง | Evidence |
| --- | --- | --- | --- | --- |
| TC-001 | อ่านบัตรประชาชน | เสียบบัตรแล้วกดอ่านข้อมูล | แสดงข้อมูลผู้รับบริการ | screenshot |
| TC-002 | กรอกเลขบัตรเอง | กดกรอกเองและใส่เลข 13 หลัก | เข้าหน้าวัดได้ | screenshot |
| TC-003 | กรอกตัวอักษรในเลขบัตร | พิมพ์ภาษาไทย/อังกฤษ | ระบบแจ้งให้กรอกเฉพาะตัวเลข | screenshot |
| TC-004 | วัดความดัน | กด START NIBP | แสดง SYS/DIA/PUL | screenshot |
| TC-005 | วัด SpO2 | กด START SpO2 | แสดงค่า SpO2 | screenshot |
| TC-006 | ส่ง Backend สำเร็จ | กดบันทึกข้อมูล | Backend ได้ JSON | log/payload |
| TC-007 | ส่ง Backend ไม่สำเร็จ | ปิด network แล้วกดบันทึก | payload เข้า offline queue | log/SQLite |
| TC-008 | Thread ไม่ block UI | กดวัดค่าแล้วลองดู UI ระหว่างรอ | UI ยังตอบสนอง | video/thread log |
| TC-009 | Wi-Fi/Bluetooth ไม่ค้าง | กด scan/connect | มี timeout/แจ้งเตือน ไม่ค้างถาวร | log |
| TC-010 | Automated test | รัน pytest | test ผ่าน | test result |

## 7. หลักฐานการแจ้งเตือนผู้ใช้และเหตุการณ์ผิดปกติ

หัวข้อนี้ใช้ตอบคำถามว่าเมื่อเกิดเหตุไม่คาดคิด ระบบแจ้งผู้ใช้ครบหรือไม่ และไม่ทำให้หน้าจอค้างหรือสับสนเกินไป

| เหตุการณ์ | จุดในโค้ด | พฤติกรรมที่ควรเห็น | หลักฐานที่ควรเก็บ |
| --- | --- | --- | --- |
| กรอกเลขบัตรไม่ครบ/ไม่ใช่ตัวเลข | `carekeeper_ui.py:940`, `carekeeper_ui.py:1102` | แสดงข้อความเตือนใน popup และไม่ยอมไปหน้าวัด | screenshot popup |
| วัดความดันไม่สำเร็จ | `carekeeper_ui.py:1825` | ปุ่มวัดเปลี่ยนเป็นสถานะล้มเหลว และ system message แจ้งข้อผิดพลาด | screenshot หรือ video |
| วัด SpO2 ไม่สำเร็จ | `carekeeper_ui.py:1842` | ปุ่มวัดเปลี่ยนเป็นสถานะล้มเหลว และ system message แจ้งข้อผิดพลาด | screenshot หรือ video |
| วัดอุณหภูมิไม่สำเร็จ | `carekeeper_ui.py:1857` | ปุ่มวัดเปลี่ยนเป็นสถานะล้มเหลว และ system message แจ้งข้อผิดพลาด | screenshot หรือ video |
| โหลดข้อมูลย้อนหลังไม่สำเร็จ | `carekeeper_ui.py:1737` | ตารางขึ้นข้อความโหลดข้อมูลไม่สำเร็จ และมี toast แจ้งผู้ใช้ | screenshot |
| อ่านสถานะ Wi-Fi/Bluetooth/แบตเตอรี่ไม่ได้ | `carekeeper_ui.py:1073` | แสดง toast แบบจำกัดความถี่ เพื่อไม่ให้รบกวนซ้ำ | screenshot หรือ log |
| ส่งข้อมูลค้างใน queue ไม่สำเร็จ | `carekeeper_ui.py:914` | แสดง toast แบบจำกัดความถี่ และ worker จะลองส่งใหม่ | log |
| อ่านค่าแบตเตอรี่ไม่ได้ | `carekeeper_ui.py:1041`, `carekeeper_providers.py:435` | แสดง `--%` แทน `0%` เพื่อไม่ให้เข้าใจผิดว่าแบตเตอรี่หมด | screenshot |
| ส่ง Backend สำเร็จ | `carekeeper_ui.py:1930` | แสดง toast สำเร็จแล้ว reset session | screenshot หรือ video |
| ส่ง Backend ไม่สำเร็จ | `carekeeper_ui.py:1937` | แสดงข้อความผิดพลาด และ payload ถูกเก็บไว้ใน offline queue เพื่อ retry อัตโนมัติ | log/SQLite |

หลักฐานที่ควรเก็บเพิ่ม:

```text
docs/evidence/screenshots/toast_center_success.png
docs/evidence/screenshots/toast_center_failed.png
docs/evidence/screenshots/battery_unknown_dash_percent.png
docs/evidence/logs/status_read_failed_log.txt
docs/evidence/logs/queue_retry_failed_log.txt
```

## 8. Bug Audit / Known Risks

ตารางนี้เป็นรายการที่ตรวจพบแล้วและควรพูดตรง ๆ เวลาอธิบายงาน เพื่อให้เห็นว่าระบบมีการประเมินความเสี่ยง ไม่ใช่แค่ทำ UI ให้แสดงผลได้

| ประเด็น | สถานะปัจจุบัน | ผลกระทบ | แนวทางถัดไป |
| --- | --- | --- | --- |
| อุณหภูมิใน real mode ยังไม่มี sensor จริง | `RealCareKeeperProvider.measure_temperature()` ยังเป็นส่วนที่ต้องต่อ module จริง | ตอน demo อาจยังใช้ mock/placeholder ไม่ใช่ค่าจาก hardware จริง | เพิ่ม driver/module ของ temperature sensor แล้วเขียน test แยก |
| mock mode ใช้ queue path เดียวกับ real mode | ยังไม่ได้แยกตามที่ตกลงกันไว้ | ถ้ามี pending payload จริงแล้วเปิด `main_demo.py` อาจทำให้ mock worker drain/delete queue จริง | หลังทดสอบ sensor จริงควรลบ mock mode หรือแยก queue path mock/real |
| อาจส่ง payload ซ้ำในบางจังหวะ | `_submit_data()` enqueue ก่อน แล้วส่งทันที ขณะ `QueueDrainWorker` อาจเห็น pending row เดียวกัน | มีโอกาส backend ได้ข้อมูลซ้ำถ้าจังหวะชนกัน | เพิ่มสถานะ `sending` หรือให้ทุกการส่งผ่าน queue worker ทางเดียว |
| `.env` ไม่ถูกตั้งค่าบน Pi | โค้ดมี fallback test values | ถ้าลืมตั้งค่า อาจยิงไป endpoint/key ทดสอบ | ก่อน deploy จริงต้อง copy `.env.example` เป็น `.env` แล้วแก้ค่า |
| partial payload | ระบบส่งค่าเป็น `None` ได้ถ้าวัดไม่ครบ | backend ต้องรองรับหรือ reject ให้ชัดเจน | ยืนยัน policy กับ backend ว่าต้องวัดครบทุกค่าไหม |
| automated test ยังขึ้นกับ dependency | ต้องมี `pytest` ใน environment | ถ้าไม่ได้ติดตั้งจะไม่มีหลักฐาน test result | ติดตั้ง dev dependency ก่อนเก็บผลทดสอบ |

## 9. คำอธิบายสั้นสำหรับนำเสนอ

> ระบบ CareKeeper แยกหน้าที่ระหว่าง UI, provider, retry, queue และ logging อย่างชัดเจน โดย UI ทำงานบน main thread เพื่อรับ interaction และแสดงผล ส่วนงานที่รออุปกรณ์หรือ network เช่น อ่านบัตร วัดค่า ส่งข้อมูล และสแกน Wi-Fi/Bluetooth จะถูกส่งไปทำใน `QThread` ผ่าน `ProviderTask` เพื่อลดปัญหา UI ค้าง นอกจากนี้ยังมี `QueueDrainWorker` เป็น background thread สำหรับส่งข้อมูลที่ค้างอยู่เมื่ออินเทอร์เน็ตกลับมาใช้งานได้ หลักฐานประกอบมีทั้ง code reference, log ที่แสดง thread id, ผล pytest และวิดีโอเดโมบน Raspberry Pi

## 10. Checklist ก่อนนำเสนอ

- [ ] มี screenshot หน้าอ่านบัตร
- [ ] มี screenshot หน้า dashboard
- [ ] มี screenshot หน้าสรุปผล
- [ ] มี screenshot หรือ video กรอกเลขบัตรเอง
- [ ] มี video วัดค่าจริงบน Raspberry Pi
- [ ] มี JSON payload ที่ส่ง Backend
- [ ] มี log ส่ง Backend สำเร็จ
- [ ] มี log หรือหลักฐาน offline queue
- [ ] มี screenshot toast ตรงกลางทั้งกรณีสำเร็จและล้มเหลว
- [ ] มี screenshot กรณีอ่านแบตเตอรี่ไม่ได้แล้วแสดง `--%`
- [ ] มี thread log แสดง main thread และ worker thread
- [ ] มีผล `pytest tests/test_threading.py -v`
- [ ] มีผล pytest รวมทั้งโปรเจกต์ ถ้ามีเวลา
- [ ] ตรวจว่า `.env` บน Pi ตั้งค่า backend/API key ถูกต้อง และไฟล์ `.env` ไม่ถูก commit
- [ ] ตรวจว่าไม่มี pending queue จริงก่อนเปิด mock/demo mode
- [ ] ระบุข้อจำกัดที่ยังเหลือ เช่น temperature sensor จริง, GET history API, mock queue path และความเสี่ยง payload ซ้ำ
