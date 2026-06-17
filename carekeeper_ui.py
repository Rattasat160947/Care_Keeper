# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QBrush , QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from carekeeper_providers import (
    BloodPressureReading,
    CareKeeperProvider,
    DeviceStatus,
    PatientInfo,
)


WINDOW_WIDTH = 1010
WINDOW_HEIGHT = 503


@dataclass
class VitalState:
    systolic: int | None = None
    diastolic: int | None = None
    pulse: int | None = None
    spo2: int | None = None
    temperature: float | None = None


class ProviderTask(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, action: Callable[[], object], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.action = action

    def run(self) -> None:
        try:
            self.completed.emit(self.action())
        except Exception as exc:
            self.failed.emit(str(exc))


class WifiIndicator(QWidget):
    clicked = Signal()
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.connected = False
        self.scale = 1.5  
        self.setFixedSize(int(26 * self.scale), int(20 * self.scale))
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def set_connected(self, connected: bool) -> None:
        self.connected = connected
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale, self.scale) # <--- สั่งขยายภาพวาด

        color = QColor("#0f8b8d") if self.connected else QColor("#cbd5e1")
        cx = 26 / 2  # ล็อกพิกัดเดิมไว้ไม่ให้เพี้ยน
        cy = 20 - 3

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(cx - 1.5, cy - 1.5, 3, 3)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap))
        for radius, span in ((4, 75), (8, 75), (12, 75)):
            start_angle = int((90 - span / 2) * 16)
            painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, start_angle, span * 16)


class BluetoothIndicator(QWidget):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.connected = False
        self.scale = 1.5  
        self.setFixedSize(int(20 * self.scale), int(20 * self.scale))
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def set_connected(self, connected: bool) -> None:
        self.connected = connected
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale, self.scale) # <--- สั่งขยายภาพวาด

        color = QColor("#0f8b8d") if self.connected else QColor("#cbd5e1")
        painter.setPen(QPen(color, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(10, 3, 10, 17)
        painter.drawLine(10, 3, 15, 7)
        painter.drawLine(15, 7, 5, 14)
        painter.drawLine(10, 17, 15, 13)
        painter.drawLine(15, 13, 5, 6)


class BatteryIndicator(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.percent = 0
        self.scale = 1.5  
        self.setFixedSize(int(30 * self.scale), int(15 * self.scale))

    def set_percent(self, percent: int) -> None:
        self.percent = max(0, min(100, percent))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.scale(self.scale, self.scale) # <--- สั่งขยายภาพวาด

        border = QColor("#16324f")
        fill = QColor("#0f8b8d") if self.percent > 20 else QColor("#94a3b8")
        painter.setPen(QPen(border, 1.2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(1, 1, 24, 13, 3, 3)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(border))
        painter.drawRoundedRect(26, 4, 2, 6, 1, 1)

        fill_width = int((self.percent / 100) * 20)
        if fill_width:
            painter.setBrush(QBrush(fill))
            painter.drawRoundedRect(3, 3, fill_width, 9, 1.5, 1.5)


class ToastLabel(QLabel):
    def mousePressEvent(self, event) -> None:
        self.hide()


class CareKeeperWindow(QMainWindow):
    def __init__(self, provider: CareKeeperProvider, mode_name: str = "Mock") -> None:
        super().__init__()
        self.provider = provider
        self.mode_name = mode_name
        self.patient = PatientInfo()
        self.vitals = VitalState()
        self.tasks: list[ProviderTask] = []
        self.status_task: ProviderTask | None = None
        self.bp_cooldown_seconds = 0

        self.setWindowTitle(f"CareKeeper - {mode_name}")
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self._build_scan_page()
        self._build_dashboard_page()
        self._build_summary_page()
        self._apply_styles()
        self._build_toast()
        self._refresh_patient()
        self._refresh_values()

        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._request_device_status)
        self.status_timer.start(6000)
        self._request_device_status()

        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.timeout.connect(self._bp_cooldown_tick)

    def _add_soft_shadow(self, widget: QWidget) -> None:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(15, 23, 42, 18))
        shadow.setOffset(0, 6)
        widget.setGraphicsEffect(shadow)

    def _make_card(self, object_name: str = "Card") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName(object_name)
        self._add_soft_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(0)
        return card, layout

    def _build_toast(self) -> None:
        self.toast = ToastLabel(self)
        self.toast.setAlignment(Qt.AlignCenter)
        self.toast.setWordWrap(True)
        self.toast.setCursor(Qt.PointingHandCursor)
        self.toast.hide()

    def _show_toast(self, message: str, success: bool = True, duration_ms: int = 2000) -> None:
        background = "#d1fae5" if success else "#fee2e2"
        color = "#065f46" if success else "#991b1b"
        border = "#86efac" if success else "#fecaca"
        self.toast.setText(message)
        self.toast.setStyleSheet(
            f"background:{background}; color:{color}; border:1px solid {border}; "
            "border-radius:12px; padding:10px 18px; font-size:17px; font-weight:800;"
        )
        width = min(680, self.width() - 80)
        self.toast.setGeometry((self.width() - width) // 2, self.height() - 92, width, 54)
        self.toast.raise_()
        self.toast.show()
        QTimer.singleShot(duration_ms, self.toast.hide)

    def _build_scan_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setAlignment(Qt.AlignCenter)

        card, layout = self._make_card("WelcomeCard")
        card.setFixedSize(540, 360)
        layout.setContentsMargins(50, 45, 50, 45)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("CareKeeper")
        logo.setObjectName("WelcomeLogo")
        logo.setAlignment(Qt.AlignCenter)

        title = QLabel("กรุณาสแกนบัตรประชาชน")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("ระบบจะอ่านข้อมูลผู้รับบริการเพื่อยืนยันตัวตนก่อนตรวจร่างกาย")
        subtitle.setObjectName("WelcomeSub")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        self.btn_card = QPushButton("เริ่มอ่านข้อมูลบัตร")
        self.btn_card.setObjectName("BtnWelcomeAction")
        self.btn_card.setFixedHeight(52)
        self.btn_card.clicked.connect(self._read_card)

        layout.addWidget(logo)
        layout.addSpacing(18)
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(subtitle)
        layout.addSpacing(35)
        layout.addWidget(self.btn_card)

        outer.addWidget(card)
        self.stack.addWidget(root)

    def _build_dashboard_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(self._build_patient_header(summary=False))

        grid = QGridLayout()
        grid.setSpacing(12)

        # --- กล่องความดันโลหิต ---
        bp_card, bp = self._make_card()
        bp.addWidget(self._tag("ความดันโลหิต (BLOOD PRESSURE)"))
        
        row_bp = QHBoxLayout()
        row_bp.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.lbl_bp_value = self._value_label("-- / --", "ValueBP")
        row_bp.addWidget(self.lbl_bp_value)
        row_bp.addWidget(self._unit("mmHg"))
        row_bp.addStretch()
        bp.addLayout(row_bp)
        
        bp.addSpacing(4)
        bp.addWidget(self._tag("ชีพจร (PULSE)"))
        
        row_pulse = QHBoxLayout()
        row_pulse.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.lbl_pulse_value = self._value_label("--", "ValuePulse")
        row_pulse.addWidget(self.lbl_pulse_value)
        row_pulse.addWidget(self._unit("bpm"))
        row_pulse.addStretch()
        bp.addLayout(row_pulse)
        
        bp.addStretch()
        self.btn_bp = self._measure_button("วัดความดัน")
        self.btn_bp.clicked.connect(self._measure_bp)
        bp.addWidget(self.btn_bp)

        # --- กล่องออกซิเจน ---
        spo2_card, spo2 = self._make_card()
        spo2.addWidget(self._tag("ออกซิเจนในเลือด (SpO2)"))
        
        row_spo2 = QHBoxLayout()
        row_spo2.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.lbl_spo2_value = self._value_label("--", "ValueSpO2")
        row_spo2.addWidget(self.lbl_spo2_value)
        row_spo2.addWidget(self._unit("%"))
        row_spo2.addStretch()
        spo2.addLayout(row_spo2)
        
        spo2.addStretch()
        self.btn_spo2 = self._measure_button("วัดออกซิเจน")
        self.btn_spo2.clicked.connect(self._measure_spo2)
        spo2.addWidget(self.btn_spo2)

        # --- กล่องอุณหภูมิ ---
        temp_card, temp = self._make_card()
        temp.addWidget(self._tag("อุณหภูมิร่างกาย (TEMPERATURE)"))
        
        row_temp = QHBoxLayout()
        row_temp.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.lbl_temp_value = self._value_label("--", "ValueTemp")
        row_temp.addWidget(self.lbl_temp_value)
        row_temp.addWidget(self._unit("°C"))
        row_temp.addStretch()
        temp.addLayout(row_temp)
        
        temp.addStretch()
        self.btn_temp = self._measure_button("วัดอุณหภูมิ")
        self.btn_temp.clicked.connect(self._measure_temperature)
        temp.addWidget(self.btn_temp)

        grid.addWidget(bp_card, 0, 0)
        grid.addWidget(spo2_card, 0, 1)
        grid.addWidget(temp_card, 0, 2)
        layout.addLayout(grid)
        layout.addSpacing(5)

        self.btn_summary = QPushButton("วัดค่าอย่างน้อย 1 รายการก่อน")
        self.btn_summary.setObjectName("BtnSummaryDisabled")
        self.btn_summary.setFixedHeight(48)
        self.btn_summary.setEnabled(False)
        self.btn_summary.clicked.connect(self._show_summary)
        layout.addWidget(self.btn_summary)

        self.stack.addWidget(root)

    def _build_summary_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        layout.addWidget(self._build_patient_header(summary=True))

        title = QLabel("สรุปผลการวัด")
        title.setObjectName("SumTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(12)

        bp_card, self.sum_bp_value, self.sum_pulse_value, self.sum_bp_badge = self._summary_card(
            "ความดันโลหิต (BLOOD PRESSURE)",
            "mmHg",
            "ValueBP",
            has_pulse=True,
        )
        spo2_card, self.sum_spo2_value, _, self.sum_spo2_badge = self._summary_card(
            "ออกซิเจนในเลือด (SpO2)",
            "%",
            "ValueSpO2",
        )
        temp_card, self.sum_temp_value, _, self.sum_temp_badge = self._summary_card(
            "อุณหภูมิร่างกาย (TEMPERATURE)",
            "°C",
            "ValueTemp",
        )

        grid.addWidget(bp_card, 0, 0)
        grid.addWidget(spo2_card, 0, 1)
        grid.addWidget(temp_card, 0, 2)
        layout.addLayout(grid)

        self.btn_finish = QPushButton("ส่งข้อมูลและเสร็จสิ้นการตรวจ")
        self.btn_finish.setObjectName("BtnFinish")
        self.btn_finish.setFixedHeight(44)
        self.btn_finish.clicked.connect(self._submit_data) #เรียกใช้ฟังก์ชันส่งข้อมูลไปยังเซิร์ฟเวอร์เมื่อคลิก
        layout.addSpacing(4)
        layout.addWidget(self.btn_finish)

        self.stack.addWidget(root)

    def _build_patient_header(self, summary: bool) -> QFrame:
        header = QFrame()
        header.setObjectName("Header")
        self._add_soft_shadow(header)

        row = QHBoxLayout(header)
        row.setContentsMargins(20, 14, 20, 14)
        row.setSpacing(12)

        patient_col = QVBoxLayout()
        patient_col.setSpacing(3)

        lbl_name = QLabel("ผู้รับบริการ: -")
        lbl_cid = QLabel("เลขบัตร: -")
        lbl_dob = QLabel("วันเกิด: -")
        lbl_address = QLabel("ที่อยู่: -")
        lbl_name.setObjectName("HeaderName")
        lbl_cid.setObjectName("HeaderSub")
        lbl_dob.setObjectName("HeaderSub")
        lbl_address.setObjectName("HeaderAddress")

        for label in (lbl_name, lbl_cid, lbl_dob, lbl_address):
            label.setWordWrap(True)
            patient_col.addWidget(label)

        row.addLayout(patient_col, 1)

        if summary:
            self.sum_lbl_name = lbl_name
            self.sum_lbl_cid = lbl_cid
            self.sum_lbl_dob = lbl_dob
            self.sum_lbl_address = lbl_address

            btn_back = QPushButton("วัดซ้ำ")
            btn_back.setObjectName("BtnSecondary")
            btn_back.setFixedSize(100, 36)
            btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))
            row.addWidget(btn_back, alignment=Qt.AlignRight | Qt.AlignTop)
            return header

        self.lbl_name = lbl_name
        self.lbl_cid = lbl_cid
        self.lbl_dob = lbl_dob
        self.lbl_address = lbl_address

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.setAlignment(Qt.AlignVCenter)

        self.bluetooth_indicator = BluetoothIndicator()
        self.wifi_indicator = WifiIndicator()
        self.wifi_indicator.clicked.connect(self._open_wifi_selector)
        self.bluetooth_indicator.clicked.connect(self._open_bluetooth_selector)
        self.battery_indicator = BatteryIndicator()
        self.lbl_battery_text = QLabel("0%")
        self.lbl_battery_text.setObjectName("BatteryLabel")

        status_row.addWidget(self.bluetooth_indicator)
        status_row.addWidget(self.wifi_indicator)
        status_row.addSpacing(4)
        status_row.addWidget(self.lbl_battery_text)
        status_row.addWidget(self.battery_indicator)
        row.addLayout(status_row)
        return header

    def _summary_card(
        self,
        title: str,
        unit: str,
        value_object_name: str,
        has_pulse: bool = False,
    ) -> tuple[QFrame, QLabel, QLabel | None, QLabel]:
        card, layout = self._make_card()
        layout.addWidget(self._tag(title))
        
        row_val = QHBoxLayout()
        row_val.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        value = self._value_label("--", value_object_name)
        row_val.addWidget(value)
        row_val.addWidget(self._unit(unit))
        row_val.addStretch()
        layout.addLayout(row_val)

        pulse_label = None
        if has_pulse:
            layout.addSpacing(6)
            layout.addWidget(self._tag("ชีพจร (PULSE)"))
            
            row_pulse = QHBoxLayout()
            row_pulse.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
            pulse_label = self._value_label("--", "ValuePulse")
            row_pulse.addWidget(pulse_label)
            row_pulse.addWidget(self._unit("bpm"))
            row_pulse.addStretch()
            layout.addLayout(row_pulse)

        layout.addStretch()
        badge = QLabel("ยังไม่มีข้อมูล")
        badge.setObjectName("StatusBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedHeight(34)
        layout.addWidget(badge)
        return card, value, pulse_label, badge

    def _tag(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("CardTag")
        label.setWordWrap(False) # ปิดการปัดบรรทัด บังคับให้อยู่บรรทัดเดียว
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _unit(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("CardUnit")
        # จัดให้อยู่ชิดฐานล่าง เพื่อให้พอดีกับตัวเลขใหญ่ๆ
        label.setAlignment(Qt.AlignLeft | Qt.AlignBottom) 
        return label

    def _value_label(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _measure_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("BtnMeasureBase")
        button.setFixedHeight(36)
        return button

    def _start_task(
        self,
        action: Callable[[], object],
        on_success: Callable[[object], None],
        on_failed: Callable[[str], None],
    ) -> None:
        task = ProviderTask(action, self)
        task.completed.connect(on_success)
        task.failed.connect(on_failed)
        task.finished.connect(lambda: self._release_task(task))
        self.tasks.append(task)
        task.start()

    def _release_task(self, task: ProviderTask) -> None:
        if task in self.tasks:
            self.tasks.remove(task)
        if self.status_task is task:
            self.status_task = None
        task.deleteLater()

    def _read_card(self) -> None:
        self.btn_card.setText("กำลังอ่านข้อมูลบัตร...")
        self.btn_card.setEnabled(False)
        self._start_task(self.provider.read_patient, self._on_patient_read, self._on_patient_failed)

    def _on_patient_read(self, result: object) -> None:
        self.patient = result if isinstance(result, PatientInfo) else PatientInfo()
        self.vitals = VitalState()
        self.btn_card.setText("เริ่มอ่านข้อมูลบัตร")
        self.btn_card.setEnabled(True)
        self._refresh_patient()
        self._refresh_values()
        self.stack.setCurrentIndex(1)

    def _on_patient_failed(self, message: str) -> None:
        self.btn_card.setText("เริ่มอ่านข้อมูลบัตร")
        self.btn_card.setEnabled(True)
        QMessageBox.warning(self, "อ่านบัตรไม่สำเร็จ", message)

    def _measure_bp(self) -> None:
        if self.bp_cooldown_seconds > 0:
            return
        self.btn_bp.setText("กำลังวัด...")
        self.btn_bp.setEnabled(False)
        self._start_task(self.provider.measure_blood_pressure, self._on_bp_done, self._on_bp_failed)

    def _on_bp_done(self, result: object) -> None:
        if isinstance(result, BloodPressureReading):
            self.vitals.systolic = result.systolic
            self.vitals.diastolic = result.diastolic
            self.vitals.pulse = result.pulse
        self.bp_cooldown_seconds = 60
        self.cooldown_timer.start(1000)
        self.btn_bp.setText(f"พักเครื่อง {self.bp_cooldown_seconds} วินาที")
        self._refresh_values()

    def _on_bp_failed(self, message: str) -> None:
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("วัดความดัน")
        QMessageBox.warning(self, "วัดความดันไม่สำเร็จ", message)

    def _measure_spo2(self) -> None:
        self.btn_spo2.setText("กำลังวัด...")
        self.btn_spo2.setEnabled(False)
        self._start_task(self.provider.measure_spo2, self._on_spo2_done, self._on_spo2_failed)

    def _on_spo2_done(self, result: object) -> None:
        self.vitals.spo2 = int(result)
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("วัดออกซิเจน")
        self._refresh_values()

    def _on_spo2_failed(self, message: str) -> None:
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("วัดออกซิเจน")
        QMessageBox.warning(self, "วัดออกซิเจนไม่สำเร็จ", message)

    def _measure_temperature(self) -> None:
        self.btn_temp.setText("กำลังวัด...")
        self.btn_temp.setEnabled(False)
        self._start_task(self.provider.measure_temperature, self._on_temperature_done, self._on_temperature_failed)

    def _on_temperature_done(self, result: object) -> None:
        self.vitals.temperature = float(result)
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("วัดอุณหภูมิ")
        self._refresh_values()

    def _on_temperature_failed(self, message: str) -> None:
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("วัดอุณหภูมิ")
        QMessageBox.warning(self, "วัดอุณหภูมิไม่สำเร็จ", message)

    def _request_device_status(self) -> None:
        if self.status_task and self.status_task.isRunning():
            return
        task = ProviderTask(self.provider.get_device_status, self)
        self.status_task = task
        task.completed.connect(self._on_status_done)
        task.failed.connect(lambda message: None)
        task.finished.connect(lambda: self._release_task(task))
        task.start()

    def _on_status_done(self, result: object) -> None:
        if not isinstance(result, DeviceStatus):
            return
        self.lbl_battery_text.setText(f"{result.battery_percent}%")
        self.battery_indicator.set_percent(result.battery_percent)
        self.wifi_indicator.set_connected(result.wifi_connected)
        self.bluetooth_indicator.set_connected(result.bluetooth_connected)

    def _open_wifi_selector(self) -> None:
        self._show_toast("กำลังสแกน Wi-Fi...", success=True, duration_ms=1200)
        self._start_task(self.provider.scan_wifi_networks, self._on_wifi_scan_done, self._on_wifi_action_failed)

    def _on_wifi_scan_done(self, result: object) -> None:
        networks = list(result) if isinstance(result, list) else []
        if not networks:
            self._show_toast("ไม่พบ Wi-Fi ที่เลือกได้", success=False)
            return

        ssid, ok = QInputDialog.getItem(self, "เลือก Wi-Fi", "Wi-Fi network:", networks, 0, False)
        if not ok or not ssid:
            return

        password, ok = QInputDialog.getText(
            self,
            "รหัสผ่าน Wi-Fi",
            f"Password for {ssid}:",
            QLineEdit.Password,
        )
        if not ok:
            return

        self._show_toast(f"กำลังเชื่อมต่อ Wi-Fi: {ssid}", success=True, duration_ms=1200)
        self._start_task(
            lambda: self.provider.connect_wifi(ssid, password or None),
            lambda result: self._on_network_connected("เชื่อมต่อ Wi-Fi สำเร็จ"),
            self._on_wifi_action_failed,
        )

    def _open_bluetooth_selector(self) -> None:
        self._show_toast("กำลังสแกน Bluetooth...", success=True, duration_ms=1200)
        self._start_task(
            self.provider.scan_bluetooth_devices,
            self._on_bluetooth_scan_done,
            self._on_bluetooth_action_failed,
        )

    def _on_bluetooth_scan_done(self, result: object) -> None:
        devices = list(result) if isinstance(result, list) else []
        if not devices:
            self._show_toast("ไม่พบ Bluetooth device ที่เลือกได้", success=False)
            return

        labels = [f"{name} ({address})" for name, address in devices]
        selected, ok = QInputDialog.getItem(self, "เลือก Bluetooth", "Bluetooth device:", labels, 0, False)
        if not ok or not selected:
            return

        index = labels.index(selected)
        address = devices[index][1]
        self._show_toast(f"กำลังเชื่อมต่อ Bluetooth: {address}", success=True, duration_ms=1200)
        self._start_task(
            lambda: self.provider.connect_bluetooth(address),
            lambda result: self._on_network_connected("เชื่อมต่อ Bluetooth สำเร็จ"),
            self._on_bluetooth_action_failed,
        )

    def _on_network_connected(self, message: str) -> None:
        self._show_toast(message, success=True)
        self._request_device_status()

    def _on_wifi_action_failed(self, message: str) -> None:
        self._show_toast(f"Wi-Fi: {message}", success=False, duration_ms=3000)

    def _on_bluetooth_action_failed(self, message: str) -> None:
        self._show_toast(f"Bluetooth: {message}", success=False, duration_ms=3000)

    def _refresh_patient(self) -> None:
        display_name = self.patient.th_name
        if self.patient.en_name and self.patient.en_name != "-":
            display_name = f"{self.patient.th_name} ({self.patient.en_name})"

        for name, cid, dob, address in (
            (self.lbl_name, self.lbl_cid, self.lbl_dob, self.lbl_address),
            (self.sum_lbl_name, self.sum_lbl_cid, self.sum_lbl_dob, self.sum_lbl_address),
        ):
            name.setText(f"ผู้รับบริการ: {display_name}")
            cid.setText(f"เลขบัตร: {self.patient.cid}")
            dob.setText(f"วันเกิด: {self.patient.birth_date}")
            address.setText(f"ที่อยู่: {self.patient.address}")

    def _refresh_values(self) -> None:
        bp_text = "-- / --"
        if self.vitals.systolic is not None and self.vitals.diastolic is not None:
            bp_text = f"{self.vitals.systolic} / {self.vitals.diastolic}"

        pulse_text = self._format_int(self.vitals.pulse)
        spo2_text = self._format_int(self.vitals.spo2)
        temp_text = "--" if self.vitals.temperature is None else f"{self.vitals.temperature:.1f}"

        self.lbl_bp_value.setText(bp_text)
        self.lbl_pulse_value.setText(pulse_text)
        self.lbl_spo2_value.setText(spo2_text)
        self.lbl_temp_value.setText(temp_text)

        self.sum_bp_value.setText(bp_text)
        if self.sum_pulse_value:
            self.sum_pulse_value.setText(pulse_text)
        self.sum_spo2_value.setText(spo2_text)
        self.sum_temp_value.setText(temp_text)

        self._refresh_summary_badges()
        self._refresh_summary_button()

    def _refresh_summary_button(self) -> None:
        has_data = any(
            value is not None
            for value in (
                self.vitals.systolic,
                self.vitals.diastolic,
                self.vitals.spo2,
                self.vitals.temperature,
            )
        )
        self.btn_summary.setEnabled(has_data)
        self.btn_summary.setObjectName("BtnSummaryReady" if has_data else "BtnSummaryDisabled")
        self.btn_summary.setText("ดูสรุปผลการวัด" if has_data else "วัดค่าอย่างน้อย 1 รายการก่อน")
        self.btn_summary.style().unpolish(self.btn_summary)
        self.btn_summary.style().polish(self.btn_summary)

    def _refresh_summary_badges(self) -> None:
        if self.vitals.systolic is not None and self.vitals.diastolic is not None:
            self._set_badge(self.sum_bp_badge, "วัดเสร็จสิ้น", "#047857", "#d1fae5")
        else:
            self._set_badge(self.sum_bp_badge, "ยังไม่มีข้อมูล", "#64748b", "#f1f5f9")

        if self.vitals.spo2 is not None:
            self._set_badge(self.sum_spo2_badge, "วัดเสร็จสิ้น", "#047857", "#d1fae5")
        else:
            self._set_badge(self.sum_spo2_badge, "ยังไม่มีข้อมูล", "#64748b", "#f1f5f9")

        if self.vitals.temperature is not None:
            self._set_badge(self.sum_temp_badge, "วัดเสร็จสิ้น", "#047857", "#d1fae5")
        else:
            self._set_badge(self.sum_temp_badge, "ยังไม่มีข้อมูล", "#64748b", "#f1f5f9")

    def _show_summary(self) -> None:
        self._refresh_values()
        self.stack.setCurrentIndex(2)

    def _reset_session(self) -> None:
        self.patient = PatientInfo()
        self.vitals = VitalState()
        self.bp_cooldown_seconds = 0
        self.cooldown_timer.stop()
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("วัดความดัน")
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("วัดออกซิเจน")
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("วัดอุณหภูมิ")
        self._refresh_patient()
        self._refresh_values()
        self.stack.setCurrentIndex(0)

    def _bp_cooldown_tick(self) -> None:
        if self.bp_cooldown_seconds > 0:
            self.bp_cooldown_seconds -= 1
            self.btn_bp.setText(f"พักเครื่อง {self.bp_cooldown_seconds} วินาที")
            return
        self.cooldown_timer.stop()
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("วัดความดัน")

    @staticmethod
    def _format_int(value: int | None) -> str:
        return "--" if value is None else str(value)

    @staticmethod
    def _set_badge(label: QLabel, text: str, color: str, background: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"color:{color}; background:{background}; border-radius:10px; "
            "font-size:13px; font-weight:600; padding:4px 12px;"
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            * { font-family: "Prompt", sans-serif; font-size: 19px; }
            QWidget#RootBg { background-color: #f7fbff; }

            QFrame#WelcomeCard {
                background: #ffffff;
                border-radius: 24px;
                border: 1px solid #d8ecf3;
            }
            QLabel#WelcomeLogo {
                font-size: 28px;
                font-weight: 800;
                color: #0f8b8d;
                letter-spacing: 0.8px;
            }
            QLabel#WelcomeTitle {
                font-size: 28px;
                font-weight: 700;
                color: #16324f;
            }
            QLabel#WelcomeSub {
                font-size: 19px;
                color: #334155;
            }

            QFrame#Header {
                background: #ffffff;
                border-radius: 16px;
                border: 1px solid #d8ecf3;
            }
            QLabel#HeaderName {
                font-size: 20px;
                font-weight: 800;
                color: #16324f;
            }
            QLabel#HeaderSub {
                font-size: 16px;
                color: #334155;
            }
            QLabel#HeaderAddress {
                font-size: 15px;
                color: #475569;
            }
            QLabel#BatteryLabel {
                font-size: 20px;
                font-weight: 800;
                color: #16324f;
            }
            QLabel#SumTitle {
                font-size: 20px;
                font-weight: 700;
                color: #16324f;
                padding-left: 2px;
            }

            QFrame#Card {
                background: #ffffff;
                border-radius: 20px;
                border: 1px solid #d8ecf3;
                min-height: 220px;
            }
            QLabel#CardTag {
                font-size: 17px;
                font-weight: 800;
                letter-spacing: 0.5px;
                color: #334155;
            }
            QLabel#CardUnit {
                font-size: 18px;
                font-weight: 700;
                color: #64748b;
                padding-bottom: 8px; /* ดันให้ฐานตัวอักษรเสมอกับตัวเลขใหญ่ๆ */
                padding-left: 4px;
            }
            QLabel#ValueBP {
                font-size: 52px;
                font-weight: 900;
                color: #2563eb;
                letter-spacing: -1.2px;
            }
            QLabel#ValuePulse {
                font-size: 42px;
                font-weight: 900;
                color: #2563eb;
                letter-spacing: -0.6px;
            }
            QLabel#ValueSpO2 {
                font-size: 52px;
                font-weight: 900;
                color: #2563eb;
                letter-spacing: -1.2px;
            }
            QLabel#ValueTemp {
                font-size: 52px;
                font-weight: 900;
                color: #2563eb;
                letter-spacing: -1.2px;
            }

            QPushButton#BtnWelcomeAction {
                background-color: #0f8b8d;
                color: #ffffff;
                border: none;
                border-radius: 14px;
                font-size: 19px;
                font-weight: 800;
            }
            QPushButton#BtnWelcomeAction:hover { background-color: #0b7476; }

            QPushButton#BtnMeasureBase {
                background-color: #ecf8fb;
                color: #047857;
                border: 2px solid #34d399;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 900;
            }
            QPushButton#BtnMeasureBase:hover { background-color: #d1fae5; }
            QPushButton#BtnMeasureBase:disabled {
                background-color: #f8fafc;
                color: #94a3b8;
                border-color: #dbe7ee;
            }

            QPushButton#BtnSummaryDisabled {
                background-color: #dbe7ee;
                color: #7c92a4;
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#BtnSummaryReady {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#BtnSummaryReady:hover { background-color: #1d4ed8; }

            QPushButton#BtnSecondary {
                background-color: #ffffff;
                color: #047857;
                border: 2px solid #34d399;
                border-radius: 10px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton#BtnSecondary:hover { background-color: #ecf8fb; }

            QPushButton#BtnFinish {
                background-color: #16324f;
                color: #ffffff;
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: 700;
            }
            QPushButton#BtnFinish:hover { background-color: #0f253d; }
            """
        )
    
    # จัดการส่งข้อมูลเข้า Server
    def _submit_data(self) -> None:
        payload = {
            "mac": getattr(self.provider, "device_mac", "11.11.11.11"),
            "spo2": self.vitals.spo2,
            "heart_rate": self.vitals.pulse,
            "pr_bpm": self.vitals.pulse,
            "sys": self.vitals.systolic,
            "dia": self.vitals.diastolic,
            "pulse": self.vitals.pulse,
        }
        
        self.btn_finish.setText("กำลังส่งข้อมูลเข้าระบบ...")
        self.btn_finish.setEnabled(False)
        
        self._start_task(
            lambda: self.provider.send_data(payload),
            self._on_submit_success,
            self._on_submit_failed
        )

    def _on_submit_success(self, result: object) -> None:
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("ส่งข้อมูลและเสร็จสิ้นการตรวจ")
        self._show_toast("ส่งข้อมูลสำเร็จ", success=True)
        QTimer.singleShot(2000, self._reset_session)

    def _on_submit_failed(self, message: str) -> None:
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("ส่งข้อมูลและเสร็จสิ้นการตรวจ")
        self._show_toast(f"ส่งข้อมูลไม่สำเร็จ: {message}", success=False, duration_ms=3000)


def run_app(provider: CareKeeperProvider, mode_name: str = "Mock") -> None:
    app = QApplication(sys.argv)
    font_id = QFontDatabase.addApplicationFont("NotoSansThai-Regular.ttf")
    if font_id != -1:
        QFontDatabase.applicationFontFamilies(font_id)[0]
    window = CareKeeperWindow(provider, mode_name=mode_name)
    window.show()
    sys.exit(app.exec())
