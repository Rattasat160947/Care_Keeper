import sys
import time
import subprocess
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QStackedWidget,
                               QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
                               QPushButton, QFrame, QGraphicsDropShadowEffect, QMenu)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QAction

# =====================================================================
# THREADS
# =====================================================================
class IDCardThread(QThread):
    card_read_complete = Signal(dict)
    def run(self):
        time.sleep(2)
        self.card_read_complete.emit({
            "cid":      "1-30xx-xxxxx-xx-x",
            "name_th":  "นายสมชาย รักดี",
            "name_en":  "MR. SOMCHAI RAKDEE",
            "dob":      "1 มกราคม 2530",
            "address":  "123 ถ.สุรนารายณ์ ต.ในเมือง อ.เมือง จ.นครราชสีมา 30000"
        })

class BPThread(QThread):
    bp_complete = Signal(int, int, int)
    def run(self):
        time.sleep(3)
        self.bp_complete.emit(120, 80, 75)

class OximeterThread(QThread):
    ox_complete = Signal(int, int)
    ox_error    = Signal(str)
    def run(self):
        time.sleep(2)
        self.ox_complete.emit(98, 72)

class TempThread(QThread):
    temp_complete = Signal(float)
    def run(self):
        time.sleep(2)
        self.temp_complete.emit(36.8)

class BatteryThread(QThread):
    battery_updated = Signal(int)
    def run(self):
        pct = 100
        while True:
            self.battery_updated.emit(pct)
            time.sleep(10)
            pct -= 5
            if pct < 10: pct = 100

# =====================================================================
# 📶 1. IOS STYLE WIFI INDICATOR
# =====================================================================
class WifiIndicator(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = True
        self._device_name = self.get_real_wifi_ssid()
        self.setFixedSize(26, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True) 
        
        self.menu = QMenu(self)
        self.menu.setStyleSheet("QMenu { background-color: white; border-radius: 8px; border: 1px solid #EAEAEA; } QMenu::item { padding: 5px 20px; }")
        
        self.action_name = QAction(f"เครือข่าย: {self._device_name}", self)
        self.action_name.setEnabled(False)
        self.action_toggle = QAction("ปิด Wi-Fi", self)
        self.action_toggle.triggered.connect(self.toggle_wifi)
        
        self.menu.addAction(self.action_name)
        self.menu.addSeparator()
        self.menu.addAction(self.action_toggle)
        self.setMenu(self.menu)

    def get_real_wifi_ssid(self):
        if sys.platform == "win32":
            try:
                result = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces'], creationflags=subprocess.CREATE_NO_WINDOW).decode('utf-8', errors='ignore')
                for line in result.split('\n'):
                    if " SSID" in line and "BSSID" not in line:
                        return line.split(':')[1].strip()
            except Exception: pass
        elif sys.platform == "darwin": 
            try:
                result = subprocess.check_output(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I']).decode('utf-8')
                for line in result.split('\n'):
                    if " SSID:" in line:
                        return line.split(':')[1].strip()
            except Exception: pass
        return "Unknown Network"

    def toggle_wifi(self):
        self._connected = not self._connected
        self.action_toggle.setText("ปิด Wi-Fi" if self._connected else "เปิด Wi-Fi")
        self.action_name.setText(f"เครือข่าย: {self._device_name}" if self._connected else "สถานะ: ปิดการใช้งาน")
        self.update()

    def set_connected(self, connected: bool):
        if self._connected != connected:
            self.toggle_wifi()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        color = QColor("#0F172A") if self._connected else QColor("#CBD5E1")
        cx = self.width() / 2
        cy = self.height() - 3

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(color))
        p.drawEllipse(cx - 1.5, cy - 1.5, 3, 3)

        p.setBrush(Qt.NoBrush)
        pen = QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap)
        p.setPen(pen)

        for r, span in [(4, 75), (8, 75), (12, 75)]:
            start_angle = 90 - (span / 2)
            p.drawArc(cx - r, cy - r, r * 2, r * 2, int(start_angle * 16), int(span * 16))
        p.end()

# =====================================================================
# 🔵 2. IOS STYLE BLUETOOTH INDICATOR
# =====================================================================
class BluetoothIndicator(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = True
        self._device_name = "Oximeter (SpO2-Pulse)" 
        self.setFixedSize(20, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        
        self.menu = QMenu(self)
        self.menu.setStyleSheet("QMenu { background-color: white; border-radius: 8px; border: 1px solid #EAEAEA; } QMenu::item { padding: 5px 20px; }")
        
        self.action_name = QAction(f"อุปกรณ์: {self._device_name}", self)
        self.action_name.setEnabled(False)
        self.action_toggle = QAction("ปิด Bluetooth", self)
        self.action_toggle.triggered.connect(self.toggle_bt)
        
        self.menu.addAction(self.action_name)
        self.menu.addSeparator()
        self.menu.addAction(self.action_toggle)
        self.setMenu(self.menu)

    def toggle_bt(self):
        self._connected = not self._connected
        self.action_toggle.setText("ปิด Bluetooth" if self._connected else "เปิด Bluetooth")
        self.action_name.setText(f"อุปกรณ์: {self._device_name}" if self._connected else "สถานะ: ปิดการใช้งาน")
        self.update()

    def is_connected(self):
        return self._connected

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        color = QColor("#0F172A") if self._connected else QColor("#CBD5E1")
        pen = QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        
        p.drawLine(10, 3, 10, 17)
        p.drawLine(10, 3, 15, 7)
        p.drawLine(15, 7, 5, 14)
        p.drawLine(10, 17, 15, 13)
        p.drawLine(15, 13, 5, 6)
        p.end()

# =====================================================================
# 🔋 3. IOS STYLE BATTERY INDICATOR
# =====================================================================
class BatteryIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._percent = 100
        self.setFixedSize(30, 15)

    def set_percent(self, percent: int):
        self._percent = max(0, min(100, percent))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # ใช้เฉดสีเทาดำและขาวตามโจทย์ มินิมอล 2 สี
        fill_color = QColor("#0F172A")
        border_color = QColor("#0F172A")

        p.setPen(QPen(border_color, 1.2))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(1, 1, 24, 13, 3, 3)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(border_color))
        p.drawRoundedRect(26, 4, 2, 6, 1, 1)

        max_width = 20
        fill_width = int((self._percent / 100.0) * max_width)
        
        if fill_width > 0:
            if self._percent <= 20: 
                # ถ้าวิกฤต เปลี่ยนเป็นสีเทาอ่อนเพื่อให้ดูกะพริบ/ต่างออกไปในธีม Monochrome
                p.setBrush(QBrush(QColor("#94A3B8"))) 
            else:
                p.setBrush(QBrush(fill_color))
            p.drawRoundedRect(3, 3, fill_width, 9, 1.5, 1.5)

        p.end()


# =====================================================================
# MAIN APP
# =====================================================================
class CareKeeperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CareKeeper")
        self.resize(1024, 600)

        self._patient = {}
        self._results = {}

        self.bp_cooldown_counter = 0
        self.cooldown_timer = QTimer()
        self.cooldown_timer.timeout.connect(self._bp_cooldown_tick)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._build_welcome()    
        self._build_dashboard()  
        self._build_summary()    
        self._apply_styles()

        self.bat_thread = BatteryThread()
        self.bat_thread.battery_updated.connect(self._update_battery)
        self.bat_thread.start()

    def _add_soft_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(15, 23, 42, 15)) # เงาสีเทาเข้มโปร่งใส  
        shadow.setOffset(0, 6)
        widget.setGraphicsEffect(shadow)

    # ------------------------------------------------------------------
    # หน้า 1: Welcome
    # ------------------------------------------------------------------
    def _build_welcome(self):
        root = QWidget()
        root.setObjectName("RootBg")  
        outer = QVBoxLayout(root)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("WelcomeCard")
        card.setFixedSize(540, 360)
        self._add_soft_shadow(card)  
        
        vbox = QVBoxLayout(card)
        vbox.setContentsMargins(50, 45, 50, 45)
        vbox.setAlignment(Qt.AlignCenter)
        vbox.setSpacing(0)

        logo = QLabel("CareKeeper")
        logo.setObjectName("WelcomeLogo")

        title = QLabel("กรุณาเสียบบัตรประชาชน")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignCenter)

        sub = QLabel("ระบบจะทำการอ่านข้อมูลเพื่อยืนยันตัวตนก่อนตรวจร่างกาย")
        sub.setObjectName("WelcomeSub")
        sub.setAlignment(Qt.AlignCenter)

        self.btn_card = QPushButton("💳  เริ่มต้นอ่านข้อมูลบัตร")
        self.btn_card.setObjectName("BtnWelcomeAction")
        self.btn_card.setFixedHeight(52)
        self.btn_card.clicked.connect(self._read_card)

        vbox.addWidget(logo, alignment=Qt.AlignCenter)
        vbox.addSpacing(18)
        vbox.addWidget(title)
        vbox.addSpacing(8)
        vbox.addWidget(sub)
        vbox.addSpacing(35)
        vbox.addWidget(self.btn_card)

        outer.addWidget(card)
        self.stack.addWidget(root)

    # ------------------------------------------------------------------
    # หน้า 2: Dashboard
    # ------------------------------------------------------------------
    def _build_dashboard(self):
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("Header")
        self._add_soft_shadow(header)
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(20, 14, 20, 14)
        hrow.setSpacing(12)

        patient_col = QVBoxLayout()
        patient_col.setSpacing(3)
        self.lbl_name    = QLabel("ผู้รับบริการ: —")
        self.lbl_name.setObjectName("HeaderName")
        self.lbl_cid     = QLabel("เลขบัตร: —")
        self.lbl_cid.setObjectName("HeaderSub")
        self.lbl_dob     = QLabel("วันเกิด: —")
        self.lbl_dob.setObjectName("HeaderSub")
        self.lbl_address = QLabel("ที่อยู่: —")
        self.lbl_address.setObjectName("HeaderAddress")
        patient_col.addWidget(self.lbl_name)
        patient_col.addWidget(self.lbl_cid)
        patient_col.addWidget(self.lbl_dob)
        patient_col.addWidget(self.lbl_address)

        right_col = QVBoxLayout()
        right_col.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_col.setSpacing(6)
        
        self.bluetooth_indicator = BluetoothIndicator()
        self.wifi_indicator = WifiIndicator()
        self.battery_indicator = BatteryIndicator()
        
        self.lbl_battery_text = QLabel("100%")
        self.lbl_battery_text.setObjectName("BatteryLabel")

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.setAlignment(Qt.AlignVCenter)
        
        status_row.addWidget(self.bluetooth_indicator)
        status_row.addWidget(self.wifi_indicator)
        status_row.addSpacing(4)
        status_row.addWidget(self.lbl_battery_text)
        status_row.addWidget(self.battery_indicator) 
        right_col.addLayout(status_row)

        hrow.addLayout(patient_col)
        hrow.addStretch()
        hrow.addLayout(right_col)
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(12)

        # ==========================================
        # การ์ด 1: ความดันโลหิต (เพิ่มภาษาไทย)
        # ==========================================
        card_bp = QFrame()
        card_bp.setObjectName("Card")
        self._add_soft_shadow(card_bp)
        bp = QVBoxLayout(card_bp)
        bp.setContentsMargins(22, 20, 22, 20)
        bp.setSpacing(0)

        lbl_bp_tag = QLabel("ความดันโลหิต (BLOOD PRESSURE)")
        lbl_bp_tag.setObjectName("CardTag")
        self.lbl_bp_val = QLabel("— / —")
        self.lbl_bp_val.setObjectName("CardValue")
        lbl_bp_unit = QLabel("mmHg")
        lbl_bp_unit.setObjectName("CardUnit")
        
        # เพิ่มส่วนหัวข้อและค่าของชีพจร
        lbl_bp_pulse_tag = QLabel("ชีพจร (PULSE)")
        lbl_bp_pulse_tag.setObjectName("CardTag")
        self.lbl_bp_pulse = QLabel("—")
        self.lbl_bp_pulse.setObjectName("CardValue")
        lbl_bp_pulse_unit = QLabel("bpm")
        lbl_bp_pulse_unit.setObjectName("CardUnit")
        
        self.btn_bp = QPushButton("วัดความดัน")
        self.btn_bp.setObjectName("BtnMeasureBase") # ใช้โทนสีน้ำเงิน/เทา ที่รวมไว้ด้วยกัน
        self.btn_bp.setFixedHeight(36)
        self.btn_bp.clicked.connect(self._measure_bp)

        bp.addWidget(lbl_bp_tag)
        bp.addSpacing(12)
        bp.addWidget(self.lbl_bp_val)
        bp.addWidget(lbl_bp_unit)
        
        bp.addSpacing(30) # ขยับชีพจรขึ้นมาให้ห่างจากความดันเล็กน้อย
        bp.addWidget(lbl_bp_pulse_tag) # ใส่หัวข้อชีพจร
        bp.addSpacing(4) # ระยะห่างให้เลขชิดหัวข้อ
        bp.addWidget(self.lbl_bp_pulse)
        bp.addWidget(lbl_bp_pulse_unit)
        
        bp.addStretch() # ดันปุ่มวัดลงไปอยู่ล่างสุด
        bp.addWidget(self.btn_bp)

        # ==========================================
        # การ์ด 2: ออกซิเจน (เพิ่มภาษาไทย)
        # ==========================================
        card_ox = QFrame()
        card_ox.setObjectName("Card")
        self._add_soft_shadow(card_ox)
        ox = QVBoxLayout(card_ox)
        ox.setContentsMargins(22, 20, 22, 20)
        ox.setSpacing(0)

        lbl_ox_tag = QLabel("ปริมาณออกซิเจนในเลือด (SpO\u2082)")
        lbl_ox_tag.setObjectName("CardTag")
        self.lbl_ox_val = QLabel("—")
        self.lbl_ox_val.setObjectName("CardValue")
        lbl_ox_unit = QLabel("% oxygen saturation")
        lbl_ox_unit.setObjectName("CardUnit")

        self.btn_ox = QPushButton("วัดออกซิเจน")
        self.btn_ox.setObjectName("BtnMeasureBase")
        self.btn_ox.setFixedHeight(36)
        self.btn_ox.clicked.connect(self._measure_ox)

        ox.addWidget(lbl_ox_tag)
        ox.addSpacing(12)
        ox.addWidget(self.lbl_ox_val)
        ox.addWidget(lbl_ox_unit)
        ox.addStretch() 
        ox.addSpacing(8)
        ox.addWidget(self.btn_ox)

        # ==========================================
        # การ์ด 3: อุณหภูมิ (เพิ่มภาษาไทย)
        # ==========================================
        card_temp = QFrame()
        card_temp.setObjectName("Card")
        self._add_soft_shadow(card_temp)
        tmp = QVBoxLayout(card_temp)
        tmp.setContentsMargins(22, 20, 22, 20)
        tmp.setSpacing(0)

        lbl_temp_tag = QLabel("อุณหภูมิร่างกาย (TEMPERATURE)")
        lbl_temp_tag.setObjectName("CardTag")
        self.lbl_temp_val = QLabel("—")
        self.lbl_temp_val.setObjectName("CardValue")
        lbl_temp_unit = QLabel("°C")
        lbl_temp_unit.setObjectName("CardUnit")
        self.btn_temp = QPushButton("วัดอุณหภูมิ")
        self.btn_temp.setObjectName("BtnMeasureBase")
        self.btn_temp.setFixedHeight(36)
        self.btn_temp.clicked.connect(self._measure_temp)

        tmp.addWidget(lbl_temp_tag)
        tmp.addSpacing(12)
        tmp.addWidget(self.lbl_temp_val)
        tmp.addWidget(lbl_temp_unit)
        tmp.addStretch()
        tmp.addSpacing(10)
        tmp.addWidget(self.btn_temp)

        self.btn_summary = QPushButton("วัดค่าอย่างน้อย 1 รายการก่อน")
        self.btn_summary.setObjectName("BtnSummaryDisabled")
        self.btn_summary.setFixedHeight(45)
        self.btn_summary.setEnabled(False)
        self.btn_summary.clicked.connect(self._show_summary)

        grid.addWidget(card_bp,   0, 0)
        grid.addWidget(card_ox,   0, 1)
        grid.addWidget(card_temp, 0, 2)
        layout.addLayout(grid)
        layout.addSpacing(5)
        layout.addWidget(self.btn_summary)

        self.stack.addWidget(root)

    # ------------------------------------------------------------------
    # หน้า 3: Summary
    # ------------------------------------------------------------------
    def _build_summary(self):
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("Header")
        self._add_soft_shadow(header)
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(20, 14, 20, 14)
        
        patient_s_col = QVBoxLayout()
        patient_s_col.setSpacing(3)
        self.sum_lbl_name    = QLabel("ผู้รับบริการ: —")
        self.sum_lbl_name.setObjectName("HeaderName")
        self.sum_lbl_cid     = QLabel("เลขบัตร: —")
        self.sum_lbl_cid.setObjectName("HeaderSub")
        self.sum_lbl_dob     = QLabel("วันเกิด: —")
        self.sum_lbl_dob.setObjectName("HeaderSub")
        self.sum_lbl_address = QLabel("ที่อยู่: —")
        self.sum_lbl_address.setObjectName("HeaderAddress")
        patient_s_col.addWidget(self.sum_lbl_name)
        patient_s_col.addWidget(self.sum_lbl_cid)
        patient_s_col.addWidget(self.sum_lbl_dob)
        patient_s_col.addWidget(self.sum_lbl_address)
        
        # แก้ไข 1: เปลี่ยนปุ่มวัดซ้ำเป็นไอคอนลูกศรหมุน และเปลี่ยนคลาสไม่ใช้สีแดง
        btn_back = QPushButton("↻ วัดซ้ำ")
        btn_back.setObjectName("BtnSecondary")
        btn_back.setFixedSize(100, 36)
        btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        hrow.addLayout(patient_s_col)
        hrow.addStretch()
        hrow.addWidget(btn_back, alignment=Qt.AlignRight | Qt.AlignTop)
        layout.addWidget(header)

        sum_title = QLabel("สรุปผลการวัด")
        sum_title.setObjectName("SumTitle")
        layout.addWidget(sum_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # ลบพารามิเตอร์สีแยกย่อยออก เพื่อให้คุมโทน 2 สีได้เบ็ดเสร็จ
        def _make_result_card(tag, val_attr, unit_text, pulse_attr=None, pulse_src=None):
            card = QFrame()
            card.setObjectName("Card")
            self._add_soft_shadow(card)
            v = QVBoxLayout(card)
            v.setContentsMargins(22, 20, 22, 20)
            v.setSpacing(0)
            
            tag_lbl = QLabel(tag)
            tag_lbl.setObjectName("CardTag")
            val_lbl = QLabel("—")
            val_lbl.setObjectName("CardValue")
            setattr(self, val_attr, val_lbl)
            unit_lbl = QLabel(unit_text)
            unit_lbl.setObjectName("CardUnit")
            
            v.addWidget(tag_lbl)
            v.addSpacing(12)
            v.addWidget(val_lbl)
            v.addWidget(unit_lbl)
            
            if pulse_attr:
                v.addSpacing(20) # ขยับชุดข้อมูลชีพจรขึ้นมา
                
                p_tag = QLabel("ชีพจร (PULSE)")
                p_tag.setObjectName("CardTag")
                
                p_lbl = QLabel("—")
                p_lbl.setObjectName("CardValue")
                setattr(self, pulse_attr, p_lbl)
                p_unit = QLabel(pulse_src or "bpm")
                p_unit.setObjectName("CardUnit")
                
                v.addWidget(p_tag)
                v.addSpacing(4) # ให้เลขชิดหัวข้อ
                v.addWidget(p_lbl)
                v.addWidget(p_unit)
                
                v.addStretch() # ดัน Card สถานะความปกติลงไปล่างสุด
            else:
                v.addStretch()
                
            return card

        card_r_bp   = _make_result_card("ความดันโลหิต (BLOOD PRESSURE)", "sum_bp_val", "mmHg", "sum_bp_pulse", "bpm")
        card_r_ox   = _make_result_card("ปริมาณออกซิเจนในเลือด (SpO\u2082)", "sum_ox_val", "% oxygen saturation")
        card_r_temp = _make_result_card("อุณหภูมิร่างกาย (TEMPERATURE)", "sum_temp_val", "°C")

        self.sum_bp_status   = self._make_status_badge()
        self.sum_ox_status   = self._make_status_badge()
        self.sum_temp_status = self._make_status_badge()
        for card, badge in [(card_r_bp,   self.sum_bp_status),
                             (card_r_ox,   self.sum_ox_status),
                             (card_r_temp, self.sum_temp_status)]:
            card.layout().addWidget(badge)

        grid.addWidget(card_r_bp,   0, 0)
        grid.addWidget(card_r_ox,   0, 1)
        grid.addWidget(card_r_temp, 0, 2)
        layout.addLayout(grid)

        btn_finish = QPushButton("เสร็จสิ้นการตรวจ")
        btn_finish.setObjectName("BtnFinish")
        btn_finish.setFixedHeight(44)
        btn_finish.clicked.connect(self._logout)
        layout.addSpacing(4)
        layout.addWidget(btn_finish)

        self.stack.addWidget(root)

    def _make_status_badge(self):
        lbl = QLabel("ยังไม่มีข้อมูล")
        lbl.setObjectName("StatusBadge")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFixedHeight(30)
        return lbl

    # ------------------------------------------------------------------
    # Logic
    # ------------------------------------------------------------------
    def _read_card(self):
        self.btn_card.setText("⏳ กำลังอ่านบัตรประชาชน...")
        self.btn_card.setEnabled(False)
        self.id_thread = IDCardThread()
        self.id_thread.card_read_complete.connect(self._on_card_done)
        self.id_thread.start()

    def _on_card_done(self, data):
        self.btn_card.setText("💳  เริ่มต้นอ่านข้อมูลบัตร")
        self.btn_card.setEnabled(True)
        self._patient = data
        self._results = {}
        self._refresh_summary_btn()
        for lbl_name, lbl_cid, lbl_dob, lbl_addr in [
            (self.lbl_name,     self.lbl_cid,     self.lbl_dob,     self.lbl_address),
            (self.sum_lbl_name, self.sum_lbl_cid, self.sum_lbl_dob, self.sum_lbl_address),
        ]:
            lbl_name.setText(f"ผู้รับบริการ:  {data['name_th']}  ({data['name_en']})")
            lbl_cid.setText(f"เลขบัตร:  {data['cid']}")
            lbl_dob.setText(f"วันเกิด:  {data['dob']}")
            lbl_addr.setText(f"ที่อยู่:  {data['address']}")
        self.stack.setCurrentIndex(1)

    def _logout(self):
        for lbl_name, lbl_cid, lbl_dob, lbl_addr in [
            (self.lbl_name,     self.lbl_cid,     self.lbl_dob,     self.lbl_address),
            (self.sum_lbl_name, self.sum_lbl_cid, self.sum_lbl_dob, self.sum_lbl_address),
        ]:
            lbl_name.setText("ผู้รับบริการ: —")
            lbl_cid.setText("เลขบัตร: —")
            lbl_dob.setText("วันเกิด: —")
            lbl_addr.setText("ที่อยู่: —")
        self.lbl_bp_val.setText("— / —")
        self.lbl_bp_pulse.setText("—")
        self.lbl_ox_val.setText("—")
        self.lbl_temp_val.setText("—")
        self.bp_cooldown_counter = 0
        self.cooldown_timer.stop()
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("วัดความดัน")
        self._patient = {}
        self._results = {}
        self._refresh_summary_btn()
        self.stack.setCurrentIndex(0)

    def _refresh_summary_btn(self):
        has_data = len(self._results) > 0
        self.btn_summary.setEnabled(has_data)
        if has_data:
            keys = [k for k in self._results if k != "pulse_bp" and k != "pulse_ox"]
            n = len(keys)
            self.btn_summary.setText(f"ดูสรุปผลการวัด")
            self.btn_summary.setObjectName("BtnSummaryReady")
        else:
            self.btn_summary.setText("วัดค่าอย่างน้อย 1 รายการก่อน")
            self.btn_summary.setObjectName("BtnSummaryDisabled")
        self.btn_summary.style().unpolish(self.btn_summary)
        self.btn_summary.style().polish(self.btn_summary)

    def _measure_bp(self):
        if self.bp_cooldown_counter > 0: return
        self.btn_bp.setEnabled(False)
        self.btn_bp.setText("กำลังวัด...")
        self.bp_thread = BPThread()
        self.bp_thread.bp_complete.connect(self._on_bp_done)
        self.bp_thread.start()

    def _measure_ox(self):
        if not self.bluetooth_indicator.is_connected():
            self.btn_ox.setText("โปรดเปิด Bluetooth มุมขวาบน")
            QTimer.singleShot(2000, lambda: self.btn_ox.setText("วัดออกซิเจน"))
            return

        self.btn_ox.setEnabled(False)
        self.btn_ox.setText("กำลังเชื่อมต่อเซนเซอร์...")
        self.ox_thread = OximeterThread()
        self.ox_thread.ox_complete.connect(self._on_ox_done)
        self.ox_thread.ox_error.connect(self._on_ox_error)
        self.ox_thread.start()

    def _measure_temp(self):
        self.btn_temp.setEnabled(False)
        self.btn_temp.setText("กำลังจำลองค่า...")
        self.temp_thread = TempThread()
        self.temp_thread.temp_complete.connect(self._on_temp_done)
        self.temp_thread.start()

    def _on_bp_done(self, sys_v, dia_v, pulse):
        self.lbl_bp_val.setText(f"{sys_v} / {dia_v}")
        self.lbl_bp_pulse.setText(str(pulse))
        self.bp_cooldown_counter = 60
        self.cooldown_timer.start(1000)
        self.btn_bp.setText(f"พักเครื่อง — รออีก {self.bp_cooldown_counter} วิ")
        self._results["bp"] = (sys_v, dia_v)
        self._results["pulse_bp"] = pulse
        self._refresh_summary_btn()

    def _on_ox_done(self, spo2, pulse):
        self.lbl_ox_val.setText(str(spo2))
        self.btn_ox.setEnabled(True)
        self.btn_ox.setText("วัดออกซิเจน")
        self._results["spo2"] = spo2
        self._results["pulse_ox"] = pulse
        self._refresh_summary_btn()

    def _on_temp_done(self, val):
        self.lbl_temp_val.setText(f"{val:.1f}")
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("วัดอุณหภูมิ")
        self._results["temp"] = val
        self._refresh_summary_btn()

    def _on_ox_error(self, msg):
        self.lbl_ox_val.setText("—")
        self.btn_ox.setEnabled(True)
        self.btn_ox.setText("เชื่อมต่อไม่ได้ ลองอีกครั้ง")

    def _bp_cooldown_tick(self):
        if self.bp_cooldown_counter > 0:
            self.bp_cooldown_counter -= 1
            self.btn_bp.setText(f"พักเครื่อง  {self.bp_cooldown_counter} วิ")
        else:
            self.cooldown_timer.stop()
            self.btn_bp.setEnabled(True)
            self.btn_bp.setText("วัดความดัน")

    def _update_summary(self):
        r = self._results
        if "bp" in r:
            sys_v, dia_v = r["bp"]
            self.sum_bp_val.setText(f"{sys_v} / {dia_v}")
            self.sum_bp_pulse.setText(str(r.get("pulse_bp", "—")))
            status, color, bg = self._bp_status(sys_v, dia_v)
            self._set_badge(self.sum_bp_status, status, color, bg)
        else:
            self.sum_bp_val.setText("— / —")
            self.sum_bp_pulse.setText("—")
            self._set_badge(self.sum_bp_status, "ยังไม่มีข้อมูล", "#64748B", "#F1F5F9")

        if "spo2" in r:
            spo2 = r["spo2"]
            self.sum_ox_val.setText(str(spo2))
            status, color, bg = self._spo2_status(spo2)
            self._set_badge(self.sum_ox_status, status, color, bg)
        else:
            self.sum_ox_val.setText("—")
            self._set_badge(self.sum_ox_status, "ยังไม่มีข้อมูล", "#64748B", "#F1F5F9")

        if "temp" in r:
            temp = r["temp"]
            self.sum_temp_val.setText(f"{temp:.1f}")
            status, color, bg = self._temp_status(temp)
            self._set_badge(self.sum_temp_status, status, color, bg)
        else:
            self.sum_temp_val.setText("—")
            self._set_badge(self.sum_temp_status, "ยังไม่มีข้อมูล", "#64748B", "#F1F5F9")

    @staticmethod
    def _set_badge(lbl, text, color, bg):
        lbl.setText(text)
        lbl.setStyleSheet(f"color: {color}; background: {bg}; border-radius: 10px; font-size: 13px; font-weight: 600; padding: 4px 12px;")

    # แก้ไข 3: ลดจำนวนสี เปลี่ยนมาใช้ความเข้ม-อ่อน (เฉด) ของสี Blue และ Slate เท่านั้นในการบอกสถานะ
    @staticmethod
    def _bp_status(sys_v, dia_v):
        if sys_v < 120 and dia_v < 80: return "ปกติ", "#0284C7", "#E0F2FE"         # Blue
        elif sys_v < 130 and dia_v < 80: return "ค่อนข้างสูง", "#475569", "#F1F5F9"  # Light Slate
        elif sys_v < 140 or dia_v < 90: return "ความดันสูงระดับ 1", "#1E293B", "#CBD5E1" # Dark Slate
        else: return "ความดันสูงระดับ 2", "#FFFFFF", "#0F172A"                     # Inverted Dark Slate (วิกฤต)

    @staticmethod
    def _spo2_status(spo2):
        if spo2 >= 95: return "ปกติ", "#0284C7", "#E0F2FE"
        elif spo2 >= 90: return "ต่ำกว่าเกณฑ์", "#475569", "#F1F5F9"
        else: return "ต่ำวิกฤต — ควรพบแพทย์ด่วน", "#FFFFFF", "#0F172A"

    @staticmethod
    def _temp_status(temp):
        if temp < 37.5: return "ปกติ", "#0284C7", "#E0F2FE"
        elif temp < 38.5: return "มีไข้ต่ำ", "#475569", "#F1F5F9"
        else: return "มีไข้สูง — ควรพบแพทย์", "#FFFFFF", "#0F172A"

    def _show_summary(self):
        self._update_summary()
        self.stack.setCurrentIndex(2)

    def _update_battery(self, pct):
        self.lbl_battery_text.setText(f"{pct}%")
        self.battery_indicator.set_percent(pct)

    # ------------------------------------------------------------------
    # Stylesheet (TWO COLORS MAIN: Blue #0284C7 & Slate #0F172A)
    # ------------------------------------------------------------------
    def _apply_styles(self):
        self.setStyleSheet("""
            * { font-size: 15px; }
            QWidget#RootBg { background-color: #F8FAFC; } /* Light Slate Bg */

            QFrame#WelcomeCard { background: #FFFFFF; border-radius: 24px; border: 1px solid #E2E8F0; }
            QLabel#WelcomeLogo { font-size: 24px; font-weight: 800; color: #0284C7; letter-spacing: 0.8px; }
            QLabel#WelcomeTitle { font-size: 26px; font-weight: 700; color: #0F172A; }
            QLabel#WelcomeSub { font-size: 15px; color: #64748B; }
            QPushButton#BtnWelcomeAction { background-color: #0F172A; color: #FFFFFF; border: none; border-radius: 14px; font-size: 16px; font-weight: 600; }
            QPushButton#BtnWelcomeAction:hover { background-color: #1E293B; }

            QFrame#Header { background: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0; }
            QLabel#HeaderName    { font-size: 16px; font-weight: 700; color: #0F172A; }
            QLabel#HeaderSub     { font-size: 13px; color: #64748B; }
            QLabel#HeaderAddress { font-size: 12px; color: #94A3B8; }
            QLabel#BatteryLabel  { font-size: 14px; font-weight: 600; color: #0F172A; }
            QLabel#SumTitle      { font-size: 18px; font-weight: 700; color: #0F172A; padding-left: 2px; }

            QFrame#Card { background: #FFFFFF; border-radius: 20px; border: 1px solid #E2E8F0; min-height: 220px; }
            QLabel#CardTag { font-size: 15px; font-weight: 700; letter-spacing: 0.5px; color: #64748B; }
            QLabel#CardValue { font-size: 46px; font-weight: 700; color: #0F172A; letter-spacing: -1.5px; }
            QLabel#CardUnit      { font-size: 14px; color: #64748B; margin-top: 2px; }
            QLabel#CardSub       { font-size: 13px; color: #475569; background: #F1F5F9; padding: 6px 12px; border-radius: 8px; }

            /* ยุบรวมปุ่มวัดทุกอันให้เป็นสีเดียวกัน (Light Blue) */
            QPushButton#BtnMeasureBase { 
                background-color: #F0F9FF; color: #0284C7; 
                border: 1px solid #BAE6FD; border-radius: 10px; 
                font-size: 14px; font-weight: 600; 
            }
            QPushButton#BtnMeasureBase:hover    { background-color: #E0F2FE; }
            QPushButton#BtnMeasureBase:disabled { background-color: #F8FAFC; color: #94A3B8; border-color: #E2E8F0; }

            QPushButton#BtnSummaryDisabled { background-color: #E2E8F0; color: #94A3B8; border: none; border-radius: 14px; font-size: 15px; font-weight: 600; }
            QPushButton#BtnSummaryReady { background-color: #0284C7; color: #FFFFFF; border: none; border-radius: 14px; font-size: 15px; font-weight: 600; }
            QPushButton#BtnSummaryReady:hover { background-color: #0369A1; }

            /* ปุ่มวัดซ้ำใหม่ สไตล์ Outline เทา/น้ำเงิน ไม่ใช้สีแดงแล้ว */
            QPushButton#BtnSecondary { 
                background-color: #FFFFFF; color: #475569; 
                border: 1px solid #CBD5E1; border-radius: 10px; 
                font-size: 14px; font-weight: 600; 
            }
            QPushButton#BtnSecondary:hover { background-color: #F1F5F9; color: #0F172A; }

            QPushButton#BtnFinish { background-color: #0F172A; color: #FFFFFF; border: none; border-radius: 14px; font-size: 15px; font-weight: 600; }
            QPushButton#BtnFinish:hover { background-color: #1E293B; }
        """)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CareKeeperApp()
    window.show()
    sys.exit(app.exec())