# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QRectF, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPen, QBrush, QPixmap
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
PROJECT_DIR = Path(__file__).resolve().parent
STYLE_DIR = PROJECT_DIR / "style"
APP_FONT_FAMILY = "Noto Sans Thai"
ICON_BLOOD_PRESSURE = "heart-pulse-svgrepo-com.svg"
ICON_SPO2 = "rain-drops-svgrepo-com.svg"
ICON_TEMPERATURE = "thermometer-5-svgrepo-com.svg"


def _style_asset(name: str) -> Path:
    return STYLE_DIR / name


def _load_app_font(app: QApplication) -> str:
    family = APP_FONT_FAMILY

    font_candidates = (
        STYLE_DIR / "IBMPlexSansThai-Regular.ttf",
        PROJECT_DIR / "IBMPlexSansThai-Regular.ttf",
        STYLE_DIR / "NotoSansThai-Regular.ttf",
        PROJECT_DIR / "NotoSansThai-Regular.ttf",
    )
    for font_path in font_candidates:
        if not font_path.exists():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                family = families[0]
                break

    app.setFont(QFont(family, 12))
    return family


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
        self.scale = 2.2  
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

        color = QColor("#0f8b8d") if self.connected else QColor("#7c92a4")
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
        self.scale = 2.2  
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

        color = QColor("#0f8b8d") if self.connected else QColor("#7c92a4")
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
        fill = QColor("#0f8b8d") if self.percent > 20 else QColor("#64748b")
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


class PowerButton(QWidget):
    """Hand-drawn power icon (avoids relying on a font glyph that may render as a box)."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(56, 56)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("รีสตาร์ท / ปิดเครื่อง")
        self.hovered = False

    def enterEvent(self, event) -> None:
        self.hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self.hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.isEnabled() and event.button() == Qt.LeftButton:
            self.clicked.emit()

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if not self.isEnabled():
            bg, border, icon = QColor("#f1f5f9"), QColor("#cbd5e1"), QColor("#94a3b8")
        elif self.hovered:
            bg, border, icon = QColor("#fee2e2"), QColor("#fca5a5"), QColor("#b91c1c")
        else:
            bg, border, icon = QColor("#ffffff"), QColor("#9ec9d6"), QColor("#475569")

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QPen(border, 2))
        painter.setBrush(QBrush(bg))
        painter.drawEllipse(rect)

        cx, cy = rect.center().x(), rect.center().y()
        radius = rect.width() * 0.22
        painter.setPen(QPen(icon, 2.6, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        arc_rect = QRectF(cx - radius, cy - radius + 1, radius * 2, radius * 2)
        start_angle = int((90 + 35) * 16)
        span_angle = int((360 - 70) * 16)
        painter.drawArc(arc_rect, start_angle, span_angle)
        painter.drawLine(int(cx), int(cy - radius - 3), int(cx), int(cy - 1))


class ToastLabel(QLabel):
    def mousePressEvent(self, event) -> None:
        self.hide()


class PopupOverlay(QWidget):
    """Full-window dimmed overlay with a centered message card (used for important confirmations)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: rgba(11, 31, 51, 165);")
        self.setCursor(Qt.PointingHandCursor)

        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("PopupCard")
        self.card.setMinimumWidth(420)
        self.card.setMaximumWidth(620)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(48, 40, 48, 40)
        card_layout.setSpacing(16)
        card_layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel(self.card)
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.message_label = QLabel(self.card)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setWordWrap(True)

        card_layout.addWidget(self.icon_label)
        card_layout.addWidget(self.message_label)
        outer.addWidget(self.card)

        self.hide()

    def show_message(self, message: str, success: bool = True) -> None:
        accent = "#0ea672" if success else "#dc2626"
        self.icon_label.setText("✓" if success else "✕")
        self.icon_label.setStyleSheet(
            f"font-size:64px; font-weight:900; color:{accent}; background:transparent;"
        )
        self.message_label.setText(message)
        self.message_label.setStyleSheet(
            "font-size:24px; font-weight:800; color:#0b1f33; background:transparent;"
        )
        self.card.setStyleSheet(
            f"QFrame#PopupCard {{ background:#ffffff; border-radius:24px; border:3px solid {accent}; }}"
        )

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
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setMinimumSize(WINDOW_WIDTH, WINDOW_HEIGHT)

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
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(15, 23, 42, 60))
        shadow.setOffset(0, 8)
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

        self.popup_overlay = PopupOverlay(self)

    def _show_popup(self, message: str, success: bool = True, duration_ms: int = 2200) -> None:
        self.popup_overlay.show_message(message, success=success)
        self.popup_overlay.setGeometry(self.rect())
        self.popup_overlay.raise_()
        self.popup_overlay.show()
        QTimer.singleShot(duration_ms, self.popup_overlay.hide)

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
        outer.setSpacing(0)

        # --- ส่วนที่ดึงไอคอนสถานะมาไว้หน้าแรก ---
        top_row = QHBoxLayout()
        status_bg = QFrame()
        status_bg.setObjectName("Header") 
        self._add_soft_shadow(status_bg)
        status_layout = QHBoxLayout(status_bg)
        status_layout.setContentsMargins(16, 8, 16, 8)
        
        self.bt_ind_welcome = BluetoothIndicator()
        self.wifi_ind_welcome = WifiIndicator()
        self.bat_ind_welcome = BatteryIndicator()
        self.lbl_bat_welcome = QLabel("0%")
        self.lbl_bat_welcome.setObjectName("BatteryLabel")
        
        self.wifi_ind_welcome.clicked.connect(self._open_wifi_selector)
        self.bt_ind_welcome.clicked.connect(self._open_bluetooth_selector)
        
        status_layout.addWidget(self.bt_ind_welcome)
        status_layout.addSpacing(4)
        status_layout.addWidget(self.wifi_ind_welcome)
        status_layout.addSpacing(12)
        status_layout.addWidget(self.lbl_bat_welcome)
        status_layout.addWidget(self.bat_ind_welcome)
        
        top_row.addWidget(status_bg)
        top_row.addStretch()
        self.btn_power = PowerButton()
        self.btn_power.clicked.connect(self._open_power_menu)
        self._add_soft_shadow(self.btn_power)
        top_row.addWidget(self.btn_power)
        outer.addLayout(top_row)
        # -----------------------------------

        outer.addStretch(1)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        card, layout = self._make_card("WelcomeCard")
        card.setFixedSize(700, 420)
        layout.setContentsMargins(70, 40, 70, 40)
        layout.setAlignment(Qt.AlignCenter)

        logo = QLabel("CareKeeper")
        logo.setObjectName("WelcomeLogo")
        logo.setAlignment(Qt.AlignCenter)

        title = QLabel("กรุณาสแกนบัตรประชาชน")
        title.setObjectName("WelcomeTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("เพื่อยืนยันตัวตนก่อนตรวจร่างกาย")
        subtitle.setObjectName("WelcomeSub")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        self.btn_card = QPushButton("เริ่มอ่านข้อมูลบัตร")
        self.btn_card.setObjectName("BtnWelcomeAction")
        self.btn_card.setFixedHeight(64)
        self.btn_card.clicked.connect(self._read_card)

        layout.addWidget(logo)
        layout.addSpacing(22)
        layout.addWidget(title)
        layout.addSpacing(12)
        layout.addWidget(subtitle)
        layout.addSpacing(44)
        layout.addWidget(self.btn_card)

        center_row.addWidget(card)
        center_row.addStretch(1)
        outer.addLayout(center_row)
        outer.addStretch(1)
        self.stack.addWidget(root)

    def _build_dashboard_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(self._build_patient_header(summary=False))

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 10) # กล่องความดันกว้างสุด
        grid.setColumnStretch(1, 7)
        grid.setColumnStretch(2, 7)

        # --- กล่องความดันโลหิต (มีเส้นคั่นกลาง) ---
        bp_card, bp = self._make_card()
        bp.setSpacing(4)
        bp.addLayout(self._card_header("❤", "#fee2e2", "#dc2626", "ความดันโลหิต & ชีพจร", "BLOOD PRESSURE & PULSE"))
        bp.addSpacing(12)
        
        self.lbl_bp_value = self._value_label("--/--", "ValueBP")
        self.lbl_pulse_value = self._value_label("--", "ValuePulse")
        bp.addWidget(self._bp_value_area(self.lbl_bp_value, self.lbl_pulse_value, "mmHg"), 1)
        self.btn_bp = self._measure_button("วัดความดัน (MEASURE)", "BtnBP")
        self.btn_bp.clicked.connect(self._measure_bp)
        bp.addWidget(self.btn_bp)

        # --- กล่องออกซิเจน ---
        spo2_card, spo2 = self._make_card()
        spo2.setSpacing(4)
        spo2.addLayout(self._card_header("💨", "#e0f2fe", "#0284c7", "ออกซิเจนในเลือด", "SPO2"))
        spo2.addSpacing(12)
        
        self.lbl_spo2_value = self._value_label("--", "ValueSpO2")
        spo2.addWidget(self._single_value_area(self.lbl_spo2_value, "%"), 1)
        self.btn_spo2 = self._measure_button("วัดออกซิเจน (MEASURE)", "BtnSpO2")
        self.btn_spo2.clicked.connect(self._measure_spo2)
        spo2.addWidget(self.btn_spo2)

        # --- กล่องอุณหภูมิ ---
        temp_card, temp = self._make_card()
        temp.setSpacing(4)
        temp.addLayout(self._card_header("🌡", "#dcfce7", "#16a34a", "อุณหภูมิร่างกาย", "TEMPERATURE"))
        temp.addSpacing(12)
        
        self.lbl_temp_value = self._value_label("--", "ValueTemp")
        temp.addWidget(self._single_value_area(self.lbl_temp_value, "°C"), 1)
        self.btn_temp = self._measure_button("วัดอุณหภูมิ (MEASURE)", "BtnTemp")
        self.btn_temp.clicked.connect(self._measure_temperature)
        temp.addWidget(self.btn_temp)

        grid.addWidget(bp_card, 0, 0)
        grid.addWidget(spo2_card, 0, 1)
        grid.addWidget(temp_card, 0, 2)
        layout.addLayout(grid, 1)

        # แถบควบคุมด้านล่าง (ตีกรอบขาวเหมือนในรูป)
        bottom_frame = QFrame()
        bottom_frame.setObjectName("Header")
        self._add_soft_shadow(bottom_frame)
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(24, 12, 24, 12)
        
        self.lbl_summary_hint = QLabel("วัดค่าอย่างน้อย 1 รายการก่อน (MEASURE AT LEAST 1 ITEM BEFORE PROCEEDING)")
        self.lbl_summary_hint.setObjectName("SummaryHint")
        bottom_layout.addWidget(self.lbl_summary_hint)
        bottom_layout.addStretch()
        
        self.btn_summary = QPushButton("ถัดไป (NEXT) >")
        self.btn_summary.setObjectName("BtnSummaryDisabled")
        self.btn_summary.setFixedSize(220, 52)
        self.btn_summary.setEnabled(False)
        self.btn_summary.clicked.connect(self._show_summary)
        bottom_layout.addWidget(self.btn_summary)
        
        layout.addWidget(bottom_frame)
        self.stack.addWidget(root)

    def _build_summary_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        layout.addWidget(self._build_patient_header(summary=True))

        title = QLabel("สรุปผลการวัด (SUMMARY)")
        title.setObjectName("SumTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setColumnStretch(0, 10)
        grid.setColumnStretch(1, 7)
        grid.setColumnStretch(2, 7)

        bp_card, self.sum_bp_value, self.sum_pulse_value, self.sum_bp_badge = self._summary_card(
            "❤", "#fee2e2", "#dc2626", "ความดันโลหิต & ชีพจร", "BLOOD PRESSURE & PULSE",
            "mmHg", "ValueBP", has_pulse=True,
        )
        spo2_card, self.sum_spo2_value, _, self.sum_spo2_badge = self._summary_card(
            "💨", "#e0f2fe", "#0284c7", "ออกซิเจนในเลือด", "SPO2",
            "%", "ValueSpO2",
        )
        temp_card, self.sum_temp_value, _, self.sum_temp_badge = self._summary_card(
            "🌡", "#dcfce7", "#16a34a", "อุณหภูมิร่างกาย", "TEMPERATURE",
            "°C", "ValueTemp",
        )

        grid.addWidget(bp_card, 0, 0)
        grid.addWidget(spo2_card, 0, 1)
        grid.addWidget(temp_card, 0, 2)
        layout.addLayout(grid)

        self.btn_finish = QPushButton("ส่งข้อมูลและเสร็จสิ้นการตรวจ")
        self.btn_finish.setObjectName("BtnFinish")
        self.btn_finish.setFixedHeight(52)
        self.btn_finish.clicked.connect(self._submit_data)
        layout.addWidget(self.btn_finish)

        self.stack.addWidget(root)

    def _build_patient_header(self, summary: bool) -> QFrame:
        header = QFrame()
        header.setObjectName("HeaderFlat")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 0, 8, 16) # เว้นระยะด้านล่างให้เส้นคั่น
        
        info_col = QVBoxLayout()
        info_col.setSpacing(6)
        
        # แถวที่ 1: ชื่อ-สกุล + รหัสบัตรประชาชน
        row1 = QHBoxLayout()
        row1.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        lbl_name = QLabel("-")
        lbl_cid = QLabel("-")
        lbl_name.setObjectName("HeaderNameNew")
        lbl_cid.setObjectName("HeaderCidNew")
        row1.addWidget(lbl_name)
        row1.addSpacing(16)
        row1.addWidget(lbl_cid)
        row1.addStretch()
        
        # แถวที่ 2: วันเกิด + ที่อยู่
        row2 = QHBoxLayout()
        row2.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        lbl_dob = QLabel("เกิด: -")
        lbl_address = QLabel("-")
        lbl_dob.setObjectName("HeaderSubNew")
        lbl_address.setObjectName("HeaderSubNew")
        row2.addWidget(lbl_dob)
        row2.addSpacing(24)
        row2.addWidget(lbl_address)
        row2.addStretch()
        
        info_col.addLayout(row1)
        info_col.addLayout(row2)
        
        layout.addLayout(info_col, 1)

        if summary:
            self.sum_lbl_name = lbl_name
            self.sum_lbl_cid = lbl_cid
            self.sum_lbl_dob = lbl_dob
            self.sum_lbl_address = lbl_address

            # ปุ่มสำหรับหน้าสรุปผล
            btn_back = QPushButton("วัดซ้ำ (RE-MEASURE)")
            btn_back.setObjectName("BtnSecondary")
            btn_back.setFixedSize(220, 48)
            btn_back.clicked.connect(lambda: self.stack.setCurrentIndex(1))
            layout.addWidget(btn_back, alignment=Qt.AlignRight | Qt.AlignVCenter)
            return header

        self.lbl_name = lbl_name
        self.lbl_cid = lbl_cid
        self.lbl_dob = lbl_dob
        self.lbl_address = lbl_address

        return header

    def _summary_card(
        self,
        icon: str,
        icon_bg: str,
        icon_color: str,
        title_th: str,
        title_en: str,
        unit: str,
        value_object_name: str,
        has_pulse: bool = False,
    ) -> tuple[QFrame, QLabel, QLabel | None, QLabel]:
        card, layout = self._make_card()
        layout.setSpacing(4)
        layout.addLayout(self._card_header(icon, icon_bg, icon_color, title_th, title_en))
        layout.addSpacing(12)
        
        if has_pulse:
            value = self._value_label("--/--", value_object_name)
            pulse_label = self._value_label("--", "ValuePulse")
            layout.addWidget(self._bp_value_area(value, pulse_label, unit), 1)
        else:
            value = self._value_label("--", value_object_name)
            pulse_label = None
            layout.addWidget(self._single_value_area(value, unit), 1)

        
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

    def _unit(self, text: str, object_name: str = "CardUnit") -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        # จัดให้อยู่ชิดฐานล่าง เพื่อให้พอดีกับตัวเลขใหญ่ๆ
        label.setAlignment(Qt.AlignLeft | Qt.AlignBottom) 
        return label

    def _value_label(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _metric_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("CardMetricLabel")
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _value_with_unit(self, value_label: QLabel, unit: str, unit_object_name: str) -> QWidget:
        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        row.addWidget(value_label)
        row.addWidget(self._unit(unit, unit_object_name))
        row.addStretch(1)
        return wrapper

    def _bp_value_area(self, bp_value: QLabel, pulse_value: QLabel, bp_unit: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardValueArea")
        frame.setMinimumHeight(102)

        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(18)
        row.setAlignment(Qt.AlignVCenter)

        bp_col = QVBoxLayout()
        bp_col.setSpacing(4)
        bp_col.addWidget(self._metric_label("SYS / DIA"))
        bp_col.addWidget(self._value_with_unit(bp_value, bp_unit, "CardUnitInline"))

        pulse_col = QVBoxLayout()
        pulse_col.setSpacing(4)
        pulse_col.addWidget(self._metric_label("HEART RATE"))
        pulse_col.addWidget(self._value_with_unit(pulse_value, "/min", "CardUnitInline"))

        row.addLayout(bp_col, 5)
        row.addLayout(pulse_col, 3)
        return frame

    def _single_value_area(self, value_label: QLabel, unit: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("CardValueArea")
        frame.setMinimumHeight(104)

        row = QHBoxLayout(frame)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.setAlignment(Qt.AlignCenter)
        row.addStretch(1)
        row.addWidget(value_label)
        row.addWidget(self._unit(unit, "CardUnitLarge"))
        row.addStretch(1)
        return frame

    def _measure_button(self, text: str, obj_name: str = "BtnMeasureBase") -> QPushButton:
        button = QPushButton(text)
        button.setObjectName(obj_name)
        button.setFixedHeight(52)
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

    def _card_header(self, icon: str, bg_color: str, fg_color: str, title_th: str, title_en: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        icon_name_by_card = {
            "BLOOD PRESSURE & PULSE": ICON_BLOOD_PRESSURE,
            "SPO2": ICON_SPO2,
            "TEMPERATURE": ICON_TEMPERATURE,
        }
        icon_name = icon if icon.lower().endswith((".svg", ".png", ".jpg", ".jpeg")) else icon_name_by_card.get(title_en)
        icon_path = _style_asset(icon_name) if icon_name else None

        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignCenter)
        lbl_icon.setFixedSize(48, 48)
        lbl_icon.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; border-radius: 24px;")
        if icon_path and icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                lbl_icon.setPixmap(pixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                lbl_icon.setText(icon)
        else:
            lbl_icon.setText(icon)
        
        col_text = QVBoxLayout()
        col_text.setSpacing(0)
        lbl_th = QLabel(title_th)
        lbl_th.setObjectName("CardTitleTH")
        lbl_en = QLabel(title_en)
        lbl_en.setObjectName("CardTitleEN")
        col_text.addWidget(lbl_th)
        col_text.addWidget(lbl_en)
        
        row.addWidget(lbl_icon)
        row.addSpacing(12)
        row.addLayout(col_text)
        row.addStretch()
        return row

    def _on_status_done(self, result: object) -> None:
        if not isinstance(result, DeviceStatus):
            return
        # อัปเดตหน้า Dashboard
        self.lbl_battery_text.setText(f"{result.battery_percent}%")
        self.battery_indicator.set_percent(result.battery_percent)
        self.wifi_indicator.set_connected(result.wifi_connected)
        self.bluetooth_indicator.set_connected(result.bluetooth_connected)
        
        # อัปเดตหน้า Scan Page แรกสุดด้วย
        if hasattr(self, 'lbl_bat_welcome'):
            self.lbl_bat_welcome.setText(f"{result.battery_percent}%")
            self.bat_ind_welcome.set_percent(result.battery_percent)
            self.wifi_ind_welcome.set_connected(result.wifi_connected)
            self.bt_ind_welcome.set_connected(result.bluetooth_connected)

    def _on_status_done(self, result: object) -> None:
        if not isinstance(result, DeviceStatus):
            return
        self.lbl_battery_text.setText(f"{result.battery_percent}%")
        self.battery_indicator.set_percent(result.battery_percent)
        self.wifi_indicator.set_connected(result.wifi_connected)
        self.bluetooth_indicator.set_connected(result.bluetooth_connected)

    def _styled_input_dialog(self, title: str) -> QInputDialog:
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(620, 460)
        dialog.setStyleSheet(
            """
            QInputDialog { background-color: #ffffff; }
            QLabel { font-size: 22px; font-weight: 700; color: #0b1f33; }
            QComboBox {
                font-size: 22px;
                min-height: 56px;
                padding: 6px 14px;
                border: 2px solid #9ec9d6;
                border-radius: 10px;
            }
            QComboBox QAbstractItemView {
                font-size: 22px;
                min-height: 50px;
                selection-background-color: #d1fae5;
                selection-color: #0b1f33;
            }
            QLineEdit {
                font-size: 22px;
                min-height: 56px;
                padding: 6px 14px;
                border: 2px solid #9ec9d6;
                border-radius: 10px;
            }
            QPushButton {
                font-size: 20px;
                font-weight: 800;
                min-height: 52px;
                min-width: 130px;
                border-radius: 12px;
                background-color: #0f8b8d;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover { background-color: #0b7476; }
            """
        )
        return dialog

    def _select_from_list(self, title: str, label: str, items: list[str]) -> tuple[str, bool]:
        dialog = self._styled_input_dialog(title)
        dialog.setComboBoxItems(items)
        dialog.setLabelText(label)
        dialog.setComboBoxEditable(False)
        ok = bool(dialog.exec())
        return dialog.textValue(), ok

    def _ask_password(self, title: str, label: str) -> tuple[str, bool]:
        dialog = self._styled_input_dialog(title)
        dialog.setLabelText(label)
        dialog.setTextEchoMode(QLineEdit.Password)
        ok = bool(dialog.exec())
        return dialog.textValue(), ok

    def _open_power_menu(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("รีสตาร์ท / ปิดเครื่อง")
        box.setText("ต้องการดำเนินการใด?")
        box.setIcon(QMessageBox.Question)
        btn_reboot = box.addButton("รีสตาร์ทเครื่อง", QMessageBox.ActionRole)
        btn_shutdown = box.addButton("ปิดเครื่อง", QMessageBox.DestructiveRole)
        btn_cancel = box.addButton("ยกเลิก", QMessageBox.RejectRole)
        box.setDefaultButton(btn_cancel)
        box.setStyleSheet(
            """
            QMessageBox { background-color: #ffffff; }
            QLabel { font-size: 21px; font-weight: 700; color: #0b1f33; }
            QPushButton {
                font-size: 19px;
                font-weight: 800;
                min-height: 48px;
                min-width: 150px;
                border-radius: 12px;
                background-color: #eef2f6;
                color: #0b1f33;
                border: 2px solid #9ec9d6;
                padding: 4px 10px;
            }
            QPushButton:hover { background-color: #dbe7ee; }
            """
        )
        box.exec()
        clicked = box.clickedButton()
        if clicked == btn_reboot:
            self._do_reboot()
        elif clicked == btn_shutdown:
            self._do_shutdown()

    def _do_reboot(self) -> None:
        self.btn_power.setEnabled(False)
        self._show_toast("กำลังรีสตาร์ทเครื่อง...", success=True, duration_ms=4000)
        self._start_task(self.provider.reboot_device, self._on_power_action_done, self._on_power_action_failed)

    def _do_shutdown(self) -> None:
        self.btn_power.setEnabled(False)
        self._show_toast("กำลังปิดเครื่อง...", success=True, duration_ms=4000)
        self._start_task(self.provider.shutdown_device, self._on_power_action_done, self._on_power_action_failed)

    def _on_power_action_done(self, result: object) -> None:
        # เครื่องกำลังจะรีสตาร์ท/ปิดตัวเอง ไม่ต้องอัปเดต UI เพิ่ม
        pass

    def _on_power_action_failed(self, message: str) -> None:
        self.btn_power.setEnabled(True)
        self._show_toast(f"ดำเนินการไม่สำเร็จ: {message}", success=False, duration_ms=3000)

    def _open_wifi_selector(self) -> None:
        self._show_toast("กำลังสแกน Wi-Fi...", success=True, duration_ms=1200)
        self._start_task(self.provider.scan_wifi_networks, self._on_wifi_scan_done, self._on_wifi_action_failed)

    def _on_wifi_scan_done(self, result: object) -> None:
        networks = list(result) if isinstance(result, list) else []
        if not networks:
            self._show_toast("ไม่พบ Wi-Fi ที่เลือกได้", success=False)
            return

        ssid, ok = self._select_from_list("เลือก Wi-Fi", "Wi-Fi network:", networks)
        if not ok or not ssid:
            return

        password, ok = self._ask_password("รหัสผ่าน Wi-Fi", f"Password for {ssid}:")
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
        selected, ok = self._select_from_list("เลือก Bluetooth", "Bluetooth device:", labels)
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
            name.setText(display_name)
            cid.setText(self.patient.cid)
            dob.setText(f"เกิด: {self.patient.birth_date}")
            address.setText(self.patient.address)

    def _refresh_values(self) -> None:
        bp_text = "--/--"
        if self.vitals.systolic is not None and self.vitals.diastolic is not None:
            bp_text = f"{self.vitals.systolic}/{self.vitals.diastolic}"

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
            self._set_badge(self.sum_bp_badge, "วัดเสร็จสิ้น", "#047857", "#bbf7d0")
        else:
            self._set_badge(self.sum_bp_badge, "ยังไม่มีข้อมูล", "#334155", "#dbe7ee")

        if self.vitals.spo2 is not None:
            self._set_badge(self.sum_spo2_badge, "วัดเสร็จสิ้น", "#047857", "#bbf7d0")
        else:
            self._set_badge(self.sum_spo2_badge, "ยังไม่มีข้อมูล", "#334155", "#dbe7ee")

        if self.vitals.temperature is not None:
            self._set_badge(self.sum_temp_badge, "วัดเสร็จสิ้น", "#047857", "#bbf7d0")
        else:
            self._set_badge(self.sum_temp_badge, "ยังไม่มีข้อมูล", "#334155", "#dbe7ee")

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
            "border: 2px solid transparent; font-size:15px; font-weight:800; padding:4px 12px;"
        )

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            * { font-family: "__APP_FONT__", "Noto Sans Thai", sans-serif; font-size: 19px; color: #0b1f33; }
            QWidget#RootBg { background-color: #f8fafc; }

            QFrame#WelcomeCard {
                background: #ffffff;
                border-radius: 24px;
                border: 2px solid #e2e8f0;
            }
            QLabel#WelcomeLogo { font-size: 38px; font-weight: 900; color: #0056b3; }
            QLabel#WelcomeTitle { font-size: 36px; font-weight: 800; color: #0b1f33; }
            QLabel#WelcomeSub { font-size: 24px; font-weight: 600; color: #475569; }

            QFrame#Header {
                background: #ffffff;
                border-radius: 16px;
                border: 2px solid #e2e8f0;
            }
            QLabel#HeaderName { font-size: 20px; font-weight: 900; color: #0b1f33; }
            QLabel#HeaderSub { font-size: 16px; font-weight: 700; color: #475569; }
            QLabel#HeaderAddress { font-size: 15px; font-weight: 600; color: #64748b; }
            QLabel#BatteryLabel { font-size: 20px; font-weight: 900; color: #0b1f33; }
            QLabel#SumTitle { font-size: 20px; font-weight: 800; color: #0b1f33; padding-left: 2px; }

            QFrame#Card {
                background: #ffffff;
                border-radius: 20px;
                border: 2px solid #e2e8f0;
                min-height: 245px;
            }
            QLabel#CardTitleTH { font-size: 19px; font-weight: 900; color: #0b1f33; }
            QLabel#CardTitleEN { font-size: 13px; font-weight: 800; color: #64748b; letter-spacing: 1px; }
            QLabel#CardUnit { font-size: 18px; font-weight: 800; color: #64748b; padding-bottom: 6px; padding-left: 4px; }
            QFrame#CardValueArea { background: transparent; border: none; }
            QLabel#CardMetricLabel { font-size: 16px; font-weight: 900; color: #334155; letter-spacing: 0.8px; }
            QLabel#CardUnitInline { font-size: 18px; font-weight: 900; color: #334155; padding-bottom: 9px; padding-left: 2px; }
            QLabel#CardUnitLarge { font-size: 26px; font-weight: 900; color: #334155; padding-bottom: 16px; padding-left: 4px; }
            
            /* สีของค่าที่วัดได้เป็นสีเดิมตามที่ตกลงกันไว้ครับ */
            QLabel#ValueBP { font-size: 52px; font-weight: 900; color: #1d4ed8; letter-spacing: -1px; }
            QLabel#ValuePulse { font-size: 52px; font-weight: 900; color: #1d4ed8; letter-spacing: -1px; }
            QLabel#ValueSpO2 { font-size: 74px; font-weight: 900; color: #1d4ed8; letter-spacing: -1.2px; }
            QLabel#ValueTemp { font-size: 74px; font-weight: 900; color: #1d4ed8; letter-spacing: -1.2px; }
            
            QLabel#SummaryHint { font-size: 17px; font-weight: 800; color: #007982; }

            QPushButton#BtnWelcomeAction { background-color: #0056b3; color: white; border-radius: 14px; font-size: 24px; font-weight: 900; }
            QPushButton#BtnWelcomeAction:hover { background-color: #004494; }

            /* แยกสีปุ่มตามดีไซน์ใหม่ */
            QPushButton#BtnBP { background-color: #0056b3; color: white; border: none; border-radius: 12px; font-size: 18px; font-weight: 900; }
            QPushButton#BtnBP:hover { background-color: #004494; }
            QPushButton#BtnBP:disabled { background-color: #eef2f6; color: #64748b; }
            
            QPushButton#BtnSpO2 { background-color: #007982; color: white; border: none; border-radius: 12px; font-size: 18px; font-weight: 900; }
            QPushButton#BtnSpO2:hover { background-color: #006067; }
            QPushButton#BtnSpO2:disabled { background-color: #eef2f6; color: #64748b; }
            
            QPushButton#BtnTemp { background-color: #007a33; color: white; border: none; border-radius: 12px; font-size: 18px; font-weight: 900; }
            QPushButton#BtnTemp:hover { background-color: #005f27; }
            QPushButton#BtnTemp:disabled { background-color: #eef2f6; color: #64748b; }

            QPushButton#BtnSummaryDisabled { background-color: #e2e8f0; color: #64748b; border-radius: 14px; font-size: 18px; font-weight: 800; }
            QPushButton#BtnSummaryReady { background-color: #0056b3; color: #ffffff; border-radius: 14px; font-size: 18px; font-weight: 900; }
            QPushButton#BtnSummaryReady:hover { background-color: #004494; }

            QPushButton#BtnSecondary { background-color: #ffffff; color: #0056b3; border: 2px solid #0056b3; border-radius: 10px; font-size: 18px; font-weight: 900; }
            QPushButton#BtnSecondary:hover { background-color: #eff6ff; }

            QPushButton#BtnFinish { background-color: #0b1f33; color: #ffffff; border-radius: 14px; font-size: 18px; font-weight: 800; }
            QPushButton#BtnFinish:hover { background-color: #061626; }

            QFrame#HeaderFlat {
                background: transparent;
                border: none;
                border-bottom: 2px solid #cbd5e1; /* สร้างเส้นคั่นสีเทาอ่อนด้านล่าง */
            }
            QLabel#HeaderNameNew { font-size: 26px; font-weight: 900; color: #0b1f33; }
            QLabel#HeaderCidNew { font-size: 24px; font-weight: 900; color: #007982; } /* สีเขียวอมฟ้าแบบในรูป */
            QLabel#HeaderSubNew { font-size: 17px; font-weight: 600; color: #0b1f33; }
            """
            .replace("__APP_FONT__", APP_FONT_FAMILY)
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
        self._show_popup("ส่งข้อมูลสำเร็จ", success=True)
        QTimer.singleShot(2000, self._reset_session)

    def _on_submit_failed(self, message: str) -> None:
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("ส่งข้อมูลและเสร็จสิ้นการตรวจ")
        self._show_popup(f"ส่งข้อมูลไม่สำเร็จ: {message}", success=False, duration_ms=3000)

    # Redesign override methods for the dark medical-console UI.
    def _status_cluster(self, welcome: bool = False) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatusCluster")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        bt = BluetoothIndicator()
        wifi = WifiIndicator()
        battery = BatteryIndicator()
        battery_text = QLabel("0%")
        battery_text.setObjectName("ConsoleBatteryLabel")

        wifi.clicked.connect(self._open_wifi_selector)
        bt.clicked.connect(self._open_bluetooth_selector)

        layout.addWidget(bt)
        layout.addWidget(wifi)
        layout.addWidget(battery_text)
        layout.addWidget(battery)

        if not hasattr(self, "_status_widgets"):
            self._status_widgets = []
        self._status_widgets.append((bt, wifi, battery, battery_text))

        if welcome:
            self.bt_ind_welcome = bt
            self.wifi_ind_welcome = wifi
            self.bat_ind_welcome = battery
            self.lbl_bat_welcome = battery_text
        else:
            self.bluetooth_indicator = bt
            self.wifi_indicator = wifi
            self.battery_indicator = battery
            self.lbl_battery_text = battery_text

        return frame

    def _on_status_done(self, result: object) -> None:
        if not isinstance(result, DeviceStatus):
            return

        for bt, wifi, battery, battery_text in getattr(self, "_status_widgets", []):
            battery_text.setText(f"{result.battery_percent}%")
            battery.set_percent(result.battery_percent)
            wifi.set_connected(result.wifi_connected)
            bt.set_connected(result.bluetooth_connected)

    def _read_card(self) -> None:
        self.btn_card.setText("กำลังอ่านข้อมูลบัตร...")
        self.btn_card.setEnabled(False)
        self._set_system_message("กำลังอ่านข้อมูลจากบัตรประชาชน", success=None)
        self._start_task(self.provider.read_patient, self._on_patient_read, self._on_patient_failed)

    def _refresh_patient(self) -> None:
        display_name = self.patient.th_name
        if self.patient.en_name and self.patient.en_name != "-":
            display_name = f"{self.patient.th_name} ({self.patient.en_name})"

        for name, cid, dob, address in (
            (self.lbl_name, self.lbl_cid, self.lbl_dob, self.lbl_address),
            (self.sum_lbl_name, self.sum_lbl_cid, self.sum_lbl_dob, self.sum_lbl_address),
        ):
            name.setText(display_name)
            cid.setText(self.patient.cid)
            dob.setText(f"เกิด: {self.patient.birth_date}")
            address.setText(self.patient.address)

    def _console_label(self, text: str, object_name: str, alignment: Qt.AlignmentFlag = Qt.AlignLeft | Qt.AlignVCenter) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        label.setAlignment(alignment)
        return label

    def _metric_row(self, name: str, value_label: QLabel, unit: str, value_color_name: str) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        lbl_name = self._console_label(name, "MetricName")
        lbl_name.setFixedWidth(54)
        unit_label = self._console_label(unit, "MetricUnit")
        unit_label.setFixedWidth(58)
        value_label.setObjectName(value_color_name)
        row.addWidget(lbl_name)
        row.addWidget(value_label, 1)
        row.addWidget(unit_label)
        return row

    def _build_scan_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(12)

        top = QHBoxLayout()
        brand = self._console_label("carekeeper", "ScanBrand")
        top.addWidget(brand)
        top.addStretch()
        top.addWidget(self._status_cluster(welcome=True))
        self.btn_power = PowerButton()
        self.btn_power.clicked.connect(self._open_power_menu)
        top.addWidget(self.btn_power)
        outer.addLayout(top)

        card = QFrame()
        card.setObjectName("ScanPanel")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(58, 34, 58, 34)
        card_layout.setSpacing(18)

        title = self._console_label("สแกนบัตรประชาชน", "ScanTitle", Qt.AlignCenter)
        subtitle = self._console_label(
            "วางบัตรประชาชนบนเครื่องอ่านบัตรเพื่อเริ่มการตรวจ",
            "ScanSubtitle",
            Qt.AlignCenter,
        )
        subtitle.setWordWrap(True)

        self.btn_card = QPushButton("อ่านข้อมูลบัตร")
        self.btn_card.setObjectName("BtnScanCard")
        self.btn_card.setFixedHeight(62)
        self.btn_card.clicked.connect(self._read_card)

        self.lbl_scan_message = self._console_label("SYSTEM: พร้อมอ่านข้อมูลบัตร", "SystemMessageNeutral", Qt.AlignCenter)
        self.lbl_scan_message.setWordWrap(True)

        card_layout.addStretch(1)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(18)
        card_layout.addWidget(self.btn_card)
        card_layout.addWidget(self.lbl_scan_message)
        card_layout.addStretch(1)

        outer.addWidget(card, 1)
        self.stack.addWidget(root)

    def _build_dashboard_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._build_patient_header(summary=False))

        panel = QFrame()
        panel.setObjectName("ConsolePanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        measure = QFrame()
        measure.setObjectName("MeasureGrid")
        measure_layout = QHBoxLayout(measure)
        measure_layout.setContentsMargins(0, 0, 0, 0)
        measure_layout.setSpacing(0)

        self.btn_bp = QPushButton("START\nNIBP")
        self.btn_bp.setObjectName("BtnNIBP")
        self.btn_bp.setFixedWidth(112)
        self.btn_bp.clicked.connect(self._measure_bp)
        measure_layout.addWidget(self.btn_bp)

        nibp = QFrame()
        nibp.setObjectName("NibpSection")
        nibp_layout = QVBoxLayout(nibp)
        nibp_layout.setContentsMargins(28, 18, 26, 18)
        nibp_layout.setSpacing(8)
        nibp_layout.addWidget(self._console_label("NIBP", "SectionTitleYellow"))
        self.lbl_sys_value = self._console_label("--", "ValueYellow")
        self.lbl_dia_value = self._console_label("--", "ValueYellow")
        self.lbl_pulse_value = self._console_label("--", "ValueYellowSmall")
        nibp_layout.addLayout(self._metric_row("SYS", self.lbl_sys_value, "mmHg", "ValueYellow"))
        nibp_layout.addLayout(self._metric_row("DIA", self.lbl_dia_value, "mmHg", "ValueYellow"))
        nibp_layout.addLayout(self._metric_row("PUL", self.lbl_pulse_value, "bpm", "ValueYellowSmall"))
        measure_layout.addWidget(nibp, 5)

        right = QFrame()
        right.setObjectName("RightMeasureColumn")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        spo2_row = QFrame()
        spo2_row.setObjectName("RightMetricRow")
        spo2_layout = QHBoxLayout(spo2_row)
        spo2_layout.setContentsMargins(22, 15, 0, 15)
        spo2_layout.setSpacing(0)
        spo2_box = QVBoxLayout()
        spo2_box.setSpacing(2)
        spo2_box.addWidget(self._console_label("SPO2", "SectionTitleBlue"))
        spo2_value_row = QHBoxLayout()
        spo2_value_row.setSpacing(14)
        self.lbl_spo2_value = self._console_label("--", "ValueBlue")
        spo2_value_row.addWidget(self.lbl_spo2_value)
        spo2_value_row.addWidget(self._console_label("%", "MetricUnitLarge"))
        spo2_value_row.addStretch()
        spo2_box.addLayout(spo2_value_row)
        spo2_layout.addLayout(spo2_box, 1)
        self.btn_spo2 = QPushButton("START\nSpO2")
        self.btn_spo2.setObjectName("BtnSpO2Console")
        self.btn_spo2.setFixedWidth(112)
        self.btn_spo2.clicked.connect(self._measure_spo2)
        spo2_layout.addWidget(self.btn_spo2)
        right_layout.addWidget(spo2_row, 1)

        temp_row = QFrame()
        temp_row.setObjectName("RightMetricRow")
        temp_layout = QHBoxLayout(temp_row)
        temp_layout.setContentsMargins(22, 15, 0, 15)
        temp_layout.setSpacing(0)
        temp_box = QVBoxLayout()
        temp_box.setSpacing(2)
        temp_box.addWidget(self._console_label("TEMP", "SectionTitleGreen"))
        temp_value_row = QHBoxLayout()
        temp_value_row.setSpacing(10)
        self.lbl_temp_value = self._console_label("--", "ValueGreen")
        temp_value_row.addWidget(self.lbl_temp_value)
        temp_value_row.addWidget(self._console_label("°C", "MetricUnitLarge"))
        temp_value_row.addStretch()
        temp_box.addLayout(temp_value_row)
        temp_layout.addLayout(temp_box, 1)
        self.btn_temp = QPushButton("START\nTEMP")
        self.btn_temp.setObjectName("BtnTempConsole")
        self.btn_temp.setFixedWidth(112)
        self.btn_temp.clicked.connect(self._measure_temperature)
        temp_layout.addWidget(self.btn_temp)
        right_layout.addWidget(temp_row, 1)

        measure_layout.addWidget(right, 6)
        panel_layout.addWidget(measure, 1)

        footer = QFrame()
        footer.setObjectName("ConsoleFooter")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 14, 8)
        footer_layout.setSpacing(12)
        self.lbl_system_message = self._console_label("SYSTEM: รอคำสั่งวัดค่า", "SystemMessageNeutral")
        self.lbl_measure_count = self._console_label("วัดค่าสำเร็จแล้ว 0 รายการ", "FooterHint")
        footer_layout.addWidget(self.lbl_system_message, 2)
        footer_layout.addWidget(self.lbl_measure_count, 1)
        self.btn_summary = QPushButton("สรุปผลการวัด  >")
        self.btn_summary.setObjectName("BtnSummaryDisabled")
        self.btn_summary.setFixedSize(230, 40)
        self.btn_summary.setEnabled(False)
        self.btn_summary.clicked.connect(self._show_summary)
        footer_layout.addWidget(self.btn_summary)
        panel_layout.addWidget(footer)

        layout.addWidget(panel, 1)
        self.stack.addWidget(root)

    def _build_summary_page(self) -> None:
        root = QWidget()
        root.setObjectName("RootBg")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._build_patient_header(summary=True))

        panel = QFrame()
        panel.setObjectName("SummaryPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 18, 24, 16)
        panel_layout.setSpacing(12)

        top = QHBoxLayout()
        top.addWidget(self._console_label("ข้อมูลผลการวัด (Measurement Summary)", "SummaryTitle"))
        top.addStretch()
        btn_remeasure = QPushButton("เริ่มวัดอีกครั้ง")
        btn_remeasure.setObjectName("BtnSummarySmall")
        btn_remeasure.setFixedSize(170, 34)
        btn_remeasure.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        top.addWidget(btn_remeasure)
        panel_layout.addLayout(top)

        table = QFrame()
        table.setObjectName("SummaryTable")
        grid = QGridLayout(table)
        grid.setContentsMargins(38, 18, 38, 18)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(12)

        self.sum_bp_value = self._console_label("--/--", "SummaryValueYellow", Qt.AlignRight | Qt.AlignVCenter)
        self.sum_pulse_value = self._console_label("--", "SummaryValueYellow", Qt.AlignRight | Qt.AlignVCenter)
        self.sum_spo2_value = self._console_label("--", "SummaryValueBlue", Qt.AlignRight | Qt.AlignVCenter)
        self.sum_temp_value = self._console_label("--", "SummaryValueGreen", Qt.AlignRight | Qt.AlignVCenter)

        rows = [
            ("ความดันโลหิต Blood Pressure", self.sum_bp_value, "mmHg"),
            ("อัตราการเต้นของหัวใจ Pulse", self.sum_pulse_value, "bpm"),
            ("ออกซิเจนในเลือด Oxygen Saturation", self.sum_spo2_value, "%SpO2"),
            ("อุณหภูมิร่างกาย Body Temperature", self.sum_temp_value, "°C"),
        ]
        for row_index, (name, value, unit) in enumerate(rows):
            grid.addWidget(self._console_label(name, "SummaryName"), row_index, 0)
            grid.addWidget(value, row_index, 1)
            grid.addWidget(self._console_label(unit, "SummaryUnit"), row_index, 2)

        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)
        panel_layout.addWidget(table, 1)

        self.lbl_summary_system_message = self._console_label("SYSTEM: ตรวจสอบข้อมูลก่อนบันทึก", "SystemMessageNeutral")
        panel_layout.addWidget(self.lbl_summary_system_message)

        footer = QHBoxLayout()
        self.btn_back_home = QPushButton("ย้อนกลับหน้าแรก")
        self.btn_back_home.setObjectName("BtnBack")
        self.btn_back_home.setFixedSize(170, 40)
        self.btn_back_home.clicked.connect(self._reset_session)
        footer.addWidget(self.btn_back_home)
        footer.addStretch()
        self.btn_finish = QPushButton("บันทึกข้อมูล  >")
        self.btn_finish.setObjectName("BtnFinish")
        self.btn_finish.setFixedSize(260, 42)
        self.btn_finish.clicked.connect(self._submit_data)
        footer.addWidget(self.btn_finish)
        panel_layout.addLayout(footer)

        layout.addWidget(panel, 1)
        self.stack.addWidget(root)

    def _build_patient_header(self, summary: bool) -> QFrame:
        header = QFrame()
        header.setObjectName("ConsoleHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        info = QVBoxLayout()
        info.setSpacing(2)
        row1 = QHBoxLayout()
        row1.setSpacing(10)
        lbl_name = self._console_label("-", "HeaderNameConsole")
        lbl_cid = self._console_label("-", "HeaderCidConsole")
        row1.addWidget(lbl_name)
        row1.addWidget(lbl_cid)
        row1.addStretch()
        row2 = QHBoxLayout()
        row2.setSpacing(12)
        lbl_dob = self._console_label("เกิด: -", "HeaderSubConsole")
        lbl_address = self._console_label("-", "HeaderSubConsole")
        row2.addWidget(lbl_dob)
        row2.addWidget(lbl_address, 1)
        info.addLayout(row1)
        info.addLayout(row2)
        layout.addLayout(info, 1)
        layout.addWidget(self._status_cluster(welcome=False))
        
        if summary:
            self.sum_lbl_name = lbl_name
            self.sum_lbl_cid = lbl_cid
            self.sum_lbl_dob = lbl_dob
            self.sum_lbl_address = lbl_address
        else:
            self.lbl_name = lbl_name
            self.lbl_cid = lbl_cid
            self.lbl_dob = lbl_dob
            self.lbl_address = lbl_address

        return header

    def _measured_count(self) -> int:
        return sum(
            1
            for done in (
                self.vitals.systolic is not None and self.vitals.diastolic is not None,
                self.vitals.spo2 is not None,
                self.vitals.temperature is not None,
            )
            if done
        )

    def _set_system_message(self, message: str, success: bool | None = None) -> None:
        object_name = "SystemMessageNeutral"
        prefix = "SYSTEM"
        if success is True:
            object_name = "SystemMessageSuccess"
            prefix = "SUCCESSFUL"
        elif success is False:
            object_name = "SystemMessageFail"
            prefix = "FAIL"

        text = f"{prefix}: {message}"
        for label_name in ("lbl_system_message", "lbl_summary_system_message", "lbl_scan_message"):
            label = getattr(self, label_name, None)
            if label is None:
                continue
            label.setObjectName(object_name)
            label.setText(text)
            label.style().unpolish(label)
            label.style().polish(label)

    def _refresh_values(self) -> None:
        sys_text = self._format_int(self.vitals.systolic)
        dia_text = self._format_int(self.vitals.diastolic)
        bp_text = "--/--"
        if self.vitals.systolic is not None and self.vitals.diastolic is not None:
            bp_text = f"{self.vitals.systolic}/{self.vitals.diastolic}"

        pulse_text = self._format_int(self.vitals.pulse)
        spo2_text = self._format_int(self.vitals.spo2)
        temp_text = "--" if self.vitals.temperature is None else f"{self.vitals.temperature:.1f}"

        if hasattr(self, "lbl_sys_value"):
            self.lbl_sys_value.setText(sys_text)
            self.lbl_dia_value.setText(dia_text)
            self.lbl_pulse_value.setText(pulse_text)
            self.lbl_spo2_value.setText(spo2_text)
            self.lbl_temp_value.setText(temp_text)

        self.sum_bp_value.setText(bp_text)
        self.sum_pulse_value.setText(pulse_text)
        self.sum_spo2_value.setText(spo2_text)
        self.sum_temp_value.setText(temp_text)

        self._refresh_summary_badges()
        self._refresh_summary_button()

    def _refresh_summary_button(self) -> None:
        count = self._measured_count()
        has_data = count > 0
        if hasattr(self, "lbl_measure_count"):
            self.lbl_measure_count.setText(f"วัดค่าสำเร็จแล้ว {count} รายการ")
        self.btn_summary.setEnabled(has_data)
        self.btn_summary.setObjectName("BtnSummaryReady" if has_data else "BtnSummaryDisabled")
        self.btn_summary.setText("สรุปผลการวัด  >" if has_data else "รอผลการวัด")
        self.btn_summary.style().unpolish(self.btn_summary)
        self.btn_summary.style().polish(self.btn_summary)

    def _refresh_summary_badges(self) -> None:
        return

    def _on_patient_read(self, result: object) -> None:
        self.patient = result if isinstance(result, PatientInfo) else PatientInfo()
        self.vitals = VitalState()
        self.btn_card.setText("อ่านข้อมูลบัตร")
        self.btn_card.setEnabled(True)
        self._refresh_patient()
        self._refresh_values()
        self._set_system_message("อ่านข้อมูลบัตรสำเร็จ", success=True)
        self.stack.setCurrentIndex(1)

    def _on_patient_failed(self, message: str) -> None:
        self.btn_card.setText("อ่านข้อมูลบัตร")
        self.btn_card.setEnabled(True)
        self._set_system_message(f"อ่านบัตรไม่สำเร็จ: {message}", success=False)
        self._show_popup(f"อ่านบัตรไม่สำเร็จ: {message}", success=False, duration_ms=2500)

    def _measure_bp(self) -> None:
        if self.bp_cooldown_seconds > 0:
            return
        self.btn_bp.setText("MEASURING\nNIBP")
        self.btn_bp.setEnabled(False)
        self._set_system_message("กำลังวัดความดันโลหิต", success=None)
        self._start_task(self.provider.measure_blood_pressure, self._on_bp_done, self._on_bp_failed)

    def _on_bp_done(self, result: object) -> None:
        if isinstance(result, BloodPressureReading):
            self.vitals.systolic = result.systolic
            self.vitals.diastolic = result.diastolic
            self.vitals.pulse = result.pulse
        self.bp_cooldown_seconds = 60
        self.cooldown_timer.start(1000)
        self.btn_bp.setText(f"WAIT\n{self.bp_cooldown_seconds}s")
        self._set_system_message("วัดความดันโลหิตสำเร็จ", success=True)
        self._refresh_values()

    def _on_bp_failed(self, message: str) -> None:
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("START\nNIBP")
        self._set_system_message(f"วัดความดันไม่สำเร็จ: {message}", success=False)
        self._show_popup(f"วัดความดันไม่สำเร็จ: {message}", success=False, duration_ms=2500)

    def _measure_spo2(self) -> None:
        self.btn_spo2.setText("MEASURING\nSpO2")
        self.btn_spo2.setEnabled(False)
        self._set_system_message("กำลังวัดออกซิเจนในเลือด", success=None)
        self._start_task(self.provider.measure_spo2, self._on_spo2_done, self._on_spo2_failed)

    def _on_spo2_done(self, result: object) -> None:
        self.vitals.spo2 = int(result)
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("START\nSpO2")
        self._set_system_message("วัดออกซิเจนในเลือดสำเร็จ", success=True)
        self._refresh_values()

    def _on_spo2_failed(self, message: str) -> None:
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("START\nSpO2")
        self._set_system_message(f"วัดออกซิเจนไม่สำเร็จ: {message}", success=False)
        self._show_popup(f"วัดออกซิเจนไม่สำเร็จ: {message}", success=False, duration_ms=2500)

    def _measure_temperature(self) -> None:
        self.btn_temp.setText("MEASURING\nTEMP")
        self.btn_temp.setEnabled(False)
        self._set_system_message("กำลังวัดอุณหภูมิร่างกาย", success=None)
        self._start_task(self.provider.measure_temperature, self._on_temperature_done, self._on_temperature_failed)

    def _on_temperature_done(self, result: object) -> None:
        self.vitals.temperature = float(result)
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("START\nTEMP")
        self._set_system_message("วัดอุณหภูมิร่างกายสำเร็จ", success=True)
        self._refresh_values()

    def _on_temperature_failed(self, message: str) -> None:
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("START\nTEMP")
        self._set_system_message(f"วัดอุณหภูมิไม่สำเร็จ: {message}", success=False)
        self._show_popup(f"วัดอุณหภูมิไม่สำเร็จ: {message}", success=False, duration_ms=2500)

    def _reset_session(self) -> None:
        self.patient = PatientInfo()
        self.vitals = VitalState()
        self.bp_cooldown_seconds = 0
        self.cooldown_timer.stop()
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("START\nNIBP")
        self.btn_spo2.setEnabled(True)
        self.btn_spo2.setText("START\nSpO2")
        self.btn_temp.setEnabled(True)
        self.btn_temp.setText("START\nTEMP")
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("บันทึกข้อมูล  >")
        self._refresh_patient()
        self._refresh_values()
        self._set_system_message("พร้อมอ่านข้อมูลบัตร", success=None)
        self.stack.setCurrentIndex(0)

    def _bp_cooldown_tick(self) -> None:
        if self.bp_cooldown_seconds > 0:
            self.bp_cooldown_seconds -= 1
            self.btn_bp.setText(f"WAIT\n{self.bp_cooldown_seconds}s")
            return
        self.cooldown_timer.stop()
        self.btn_bp.setEnabled(True)
        self.btn_bp.setText("START\nNIBP")

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

        self.btn_finish.setText("กำลังบันทึกข้อมูล...")
        self.btn_finish.setEnabled(False)
        self._set_system_message("กำลังส่งข้อมูลเข้าสู่ระบบ", success=None)
        self._start_task(
            lambda: self.provider.send_data(payload),
            self._on_submit_success,
            self._on_submit_failed,
        )

    def _on_submit_success(self, result: object) -> None:
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("บันทึกข้อมูล  >")
        self._set_system_message("บันทึกข้อมูลสัญญาณชีพสำเร็จ", success=True)
        self._show_popup("บันทึกข้อมูลสำเร็จ", success=True)
        QTimer.singleShot(2000, self._reset_session)

    def _on_submit_failed(self, message: str) -> None:
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("บันทึกข้อมูล  >")
        self._set_system_message(f"ส่งข้อมูลไม่สำเร็จ: {message}", success=False)
        self._show_popup(f"ส่งข้อมูลไม่สำเร็จ: {message}", success=False, duration_ms=3000)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            * { font-family: "__APP_FONT__", "Noto Sans Thai", sans-serif; color: #f8fafc; font-weight: 700; }
            QWidget#RootBg { background-color: #1f2328; }

            QFrame#ConsoleHeader {
                background: #050709;
                border: 1px solid #262b31;
                border-radius: 0px;
            }
            QLabel#HeaderNameConsole { font-size: 19px; font-weight: 900; color: #ffffff; }
            QLabel#HeaderCidConsole { font-size: 16px; font-weight: 900; color: #0b63ff; }
            QLabel#HeaderSubConsole { font-size: 13px; font-weight: 700; color: #d8dee9; }
            QFrame#StatusCluster {
                background: #07090c;
                border: 1px solid #1f2937;
                border-radius: 14px;
            }
            QLabel#ConsoleBatteryLabel { font-size: 13px; font-weight: 900; color: #ffffff; }

            QLabel#ScanBrand { font-size: 28px; font-weight: 900; color: #9aff2d; letter-spacing: 0.5px; }
            QFrame#ScanPanel {
                background: #050709;
                border: 1px solid #252a31;
                border-radius: 0px;
            }
            QLabel#ScanTitle { font-size: 44px; font-weight: 900; color: #f8fafc; }
            QLabel#ScanSubtitle { font-size: 22px; font-weight: 800; color: #cbd5e1; }
            QPushButton#BtnScanCard {
                background: #0b7cff;
                color: #ffffff;
                border: none;
                border-radius: 20px;
                font-size: 24px;
                font-weight: 900;
            }
            QPushButton#BtnScanCard:hover { background: #2490ff; }
            QPushButton#BtnScanCard:disabled { background: #1f2937; color: #94a3b8; }

            QFrame#ConsolePanel, QFrame#SummaryPanel {
                background: #050709;
                border: 1px solid #252a31;
                border-radius: 0px;
            }
            QFrame#MeasureGrid {
                background: #030405;
                border-bottom: 1px solid #20242a;
            }
            QFrame#NibpSection, QFrame#RightMeasureColumn, QFrame#RightMetricRow {
                background: #030405;
                border-left: 1px solid #20242a;
            }
            QLabel#SectionTitleYellow { font-size: 16px; font-weight: 900; color: #ffed00; }
            QLabel#SectionTitleBlue { font-size: 16px; font-weight: 900; color: #75efff; }
            QLabel#SectionTitleGreen { font-size: 16px; font-weight: 900; color: #16c75a; }
            QLabel#MetricName { font-size: 15px; font-weight: 900; color: #d1d5db; }
            QLabel#MetricUnit { font-size: 14px; font-weight: 900; color: #e5e7eb; }
            QLabel#MetricUnitLarge { font-size: 22px; font-weight: 900; color: #f8fafc; padding-top: 18px; }
            QLabel#ValueYellow { font-size: 56px; font-weight: 900; color: #fff11a; }
            QLabel#ValueYellowSmall { font-size: 42px; font-weight: 900; color: #fff11a; }
            QLabel#ValueBlue { font-size: 64px; font-weight: 900; color: #79f1ff; }
            QLabel#ValueGreen { font-size: 64px; font-weight: 900; color: #19c464; }

            QPushButton#BtnNIBP {
                background: #fff200;
                color: #050505;
                border: none;
                border-radius: 0px;
                font-size: 20px;
                font-weight: 900;
            }
            QPushButton#BtnSpO2Console {
                background: #6deeff;
                color: #050505;
                border: none;
                border-radius: 0px;
                font-size: 18px;
                font-weight: 900;
            }
            QPushButton#BtnTempConsole {
                background: #19c85d;
                color: #050505;
                border: none;
                border-radius: 0px;
                font-size: 18px;
                font-weight: 900;
            }
            QPushButton:disabled { background: #374151; color: #a8b3c2; }

            QFrame#ConsoleFooter {
                background: #050709;
                border-top: 1px solid #20242a;
            }
            QLabel#FooterHint { font-size: 14px; font-weight: 900; color: #ffffff; }
            QLabel#SystemMessageNeutral { font-size: 14px; font-weight: 900; color: #f8fafc; }
            QLabel#SystemMessageSuccess { font-size: 14px; font-weight: 900; color: #4ade80; }
            QLabel#SystemMessageFail { font-size: 14px; font-weight: 900; color: #fb7185; }

            QPushButton#BtnSummaryDisabled {
                background: #1f2937;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 18px;
                font-size: 16px;
                font-weight: 900;
            }
            QPushButton#BtnSummaryReady, QPushButton#BtnFinish, QPushButton#BtnSummarySmall {
                background: #0b7cff;
                color: #ffffff;
                border: none;
                border-radius: 18px;
                font-size: 16px;
                font-weight: 900;
            }
            QPushButton#BtnSummaryReady:hover, QPushButton#BtnFinish:hover, QPushButton#BtnSummarySmall:hover {
                background: #2490ff;
            }
            QPushButton#BtnBack {
                background: transparent;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 900;
            }

            QLabel#SummaryTitle { font-size: 18px; font-weight: 900; color: #ffffff; }
            QFrame#SummaryTable {
                background: #030405;
                border: 1px solid #20242a;
                border-radius: 0px;
            }
            QLabel#SummaryName { font-size: 15px; font-weight: 900; color: #f8fafc; }
            QLabel#SummaryUnit { font-size: 15px; font-weight: 900; color: #f8fafc; }
            QLabel#SummaryValueYellow { font-size: 26px; font-weight: 900; color: #fff11a; }
            QLabel#SummaryValueBlue { font-size: 26px; font-weight: 900; color: #79f1ff; }
            QLabel#SummaryValueGreen { font-size: 26px; font-weight: 900; color: #19c464; }
            """
            .replace("__APP_FONT__", APP_FONT_FAMILY)
        )


def run_app(provider: CareKeeperProvider, mode_name: str = "Mock") -> None:
    global APP_FONT_FAMILY

    app = QApplication(sys.argv)
    APP_FONT_FAMILY = _load_app_font(app)
    window = CareKeeperWindow(provider, mode_name=mode_name)
    window.showFullScreen()
    sys.exit(app.exec())
