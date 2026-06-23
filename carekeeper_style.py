# -*- coding: utf-8 -*-
from __future__ import annotations


CONSOLE_STYLESHEET = """
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
    background: transparent;
    border: none;
}
QFrame#StatusPill, QFrame#BatteryPill {
    background: #07090c;
    border: 1px solid #1f2937;
    border-radius: 14px;
}
QLabel#ConsoleBatteryLabel { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 14px; font-weight: 900; color: #ffffff; }

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
QPushButton#BtnManualCard {
    background: transparent;
    color: #e5e7eb;
    border: none;
    font-size: 15px;
    font-weight: 900;
}
QPushButton#BtnManualCard:hover { color: #79f1ff; }
QFrame#ManualCidPanel {
    background: transparent;
    border: none;
}
QLabel#ManualCidTitle {
    font-size: 20px;
    font-weight: 900;
    color: #e5e7eb;
}
QLineEdit#ManualCidInput {
    background: #030405;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 10px;
    font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif;
    font-size: 28px;
    font-weight: 900;
    min-height: 56px;
}
QLineEdit#ManualCidInput:focus {
    border: 1px solid #0b7cff;
}
QPushButton#BtnConfirmManualCid {
    background: #0b7cff;
    color: #ffffff;
    border: none;
    border-radius: 16px;
    font-size: 16px;
    font-weight: 900;
}
QPushButton#BtnConfirmManualCid:hover { background: #2490ff; }
QPushButton#BtnCancelManualCid {
    background: transparent;
    color: #e5e7eb;
    border: 1px solid #334155;
    border-radius: 16px;
    font-size: 16px;
    font-weight: 900;
}
QPushButton#BtnCancelManualCid:hover {
    border: 1px solid #79f1ff;
    color: #79f1ff;
}

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
QLabel#MetricUnitLarge { font-size: 26px; font-weight: 900; color: #f8fafc; padding-top: 22px; }
QLabel#ValueYellow { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 74px; font-weight: 900; color: #fff11a; }
QLabel#ValueYellowSmall { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 58px; font-weight: 900; color: #fff11a; }
QLabel#ValueBlue { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 88px; font-weight: 900; color: #79f1ff; }
QLabel#ValueGreen { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 88px; font-weight: 900; color: #19c464; }

QPushButton#BtnNIBP {
    background: #fff200;
    color: #050505;
    border: none;
    border-radius: 0px;
    font-size: 22px;
    font-weight: 900;
}
QPushButton#BtnSpO2Console {
    background: #6deeff;
    color: #050505;
    border: none;
    border-radius: 0px;
    font-size: 20px;
    font-weight: 900;
}
QPushButton#BtnTempConsole {
    background: #19c85d;
    color: #050505;
    border: none;
    border-radius: 0px;
    font-size: 20px;
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

QLabel#SummaryTitle { font-size: 22px; font-weight: 900; color: #ffffff; }
QFrame#SummaryTable {
    background: #030405;
    border: 1px solid #20242a;
    border-radius: 0px;
}
QLabel#SummaryName { font-size: 18px; font-weight: 900; color: #f8fafc; }
QLabel#SummaryUnit { font-size: 18px; font-weight: 900; color: #f8fafc; }
QLabel#SummaryValueYellow { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 42px; font-weight: 900; color: #fff11a; }
QLabel#SummaryValueBlue { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 42px; font-weight: 900; color: #79f1ff; }
QLabel#SummaryValueGreen { font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif; font-size: 42px; font-weight: 900; color: #19c464; }

QFrame#ConsoleHeader {
    border-radius: 12px;
}
QLabel#HeaderNameConsole { font-size: 22px; font-weight: 900; color: #ffffff; }
QLabel#HeaderCidConsole { font-size: 18px; font-weight: 900; color: #79f1ff; }
QLabel#HeaderSubConsole { font-size: 16px; font-weight: 900; color: #f8fafc; }

QFrame#StatusPill, QFrame#BatteryPill {
    border-radius: 18px;
}
QLabel#StatusText {
    font-size: 10px;
    font-weight: 900;
    color: #ffffff;
}

QFrame#ScanPanel {
    border: 2px solid #334155;
    border-radius: 18px;
}
QFrame#ScanIconFrame {
    background: transparent;
    border: 4px solid #ffffff;
    border-radius: 10px;
}
QPushButton#BtnScanCard {
    border-radius: 18px;
}

QLabel#SectionTitleYellow { color: #ffed00; }
QLabel#ValueYellow {
    font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif;
    color: #fff11a;
}
QLabel#ValueYellowSmall, QLabel#ValuePulsePink {
    font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif;
    font-size: 74px;
    font-weight: 900;
    color: #FD3A9E;
}
QLabel#SummaryValueYellow {
    font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif;
    color: #fff11a;
}
QLabel#SummaryValuePulsePink {
    font-family: "__NUMBER_FONT__", "__APP_FONT__", sans-serif;
    font-size: 42px;
    font-weight: 900;
    color: #FD3A9E;
}

QPushButton#BtnNIBP {
    background: #fff200;
    color: #050505;
    border-radius: 18px;
}
QPushButton#BtnNIBPBusy {
    background: #9f9700;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnSpO2Busy {
    background: #2d9baa;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnTempBusy {
    background: #128342;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnNIBPDone {
    background: #c8bd12;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnSpO2Done {
    background: #50c7d6;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnTempDone {
    background: #14a855;
    color: #050505;
    border: none;
    border-radius: 18px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnNIBPFail, QPushButton#BtnSpO2Fail, QPushButton#BtnTempFail {
    background: #dc2626;
    color: #ffffff;
    border: none;
    border-radius: 18px;
    font-size: 18px;
    font-weight: 900;
}
QPushButton#BtnNIBPBusy:disabled {
    background: #9f9700;
    color: #050505;
}
QPushButton#BtnSpO2Busy:disabled {
    background: #2d9baa;
    color: #050505;
}
QPushButton#BtnTempBusy:disabled {
    background: #128342;
    color: #050505;
}
QPushButton#BtnSpO2Console, QPushButton#BtnTempConsole {
    border-radius: 18px;
}
QPushButton#BtnSummaryReady, QPushButton#BtnSummaryDisabled {
    border-radius: 22px;
    font-size: 18px;
}
QPushButton#BtnSummarySmall, QPushButton#BtnFinish, QPushButton#BtnBack {
    border-radius: 18px;
}

QFrame#HistoryPanel {
    background: #050709;
    border: 1px solid #334155;
    border-radius: 12px;
}
QScrollArea#HistoryScroll {
    background: transparent;
    border: none;
}
QWidget#HistoryBody {
    background: transparent;
}
QLabel#HistoryTitle {
    font-size: 18px;
    font-weight: 900;
    color: #79f1ff;
}
QLabel#HistoryRow {
    background: #071016;
    border: 1px solid #1f3a46;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 15px;
    font-weight: 900;
    color: #f8fafc;
}

QPushButton#BtnSummarySmall {
    background: #0b7cff;
    color: #ffffff;
    border: 1px solid #38bdf8;
    border-radius: 21px;
    font-size: 16px;
    font-weight: 900;
    padding: 0px 18px;
}
QPushButton#BtnSummarySmall:hover {
    background: #2490ff;
}

QPushButton#BtnNIBP,
QPushButton#BtnSpO2Console,
QPushButton#BtnTempConsole,
QPushButton#BtnNIBPBusy,
QPushButton#BtnSpO2Busy,
QPushButton#BtnTempBusy,
QPushButton#BtnNIBPDone,
QPushButton#BtnSpO2Done,
QPushButton#BtnTempDone,
QPushButton#BtnNIBPFail,
QPushButton#BtnSpO2Fail,
QPushButton#BtnTempFail {
    border-radius: 0px;
    border: 2px solid transparent;
    margin: 0px;
    font-size: 19px;
    font-weight: 900;
}
QPushButton#BtnNIBP:disabled,
QPushButton#BtnSpO2Console:disabled,
QPushButton#BtnTempConsole:disabled,
QPushButton#BtnNIBPBusy:disabled,
QPushButton#BtnSpO2Busy:disabled,
QPushButton#BtnTempBusy:disabled,
QPushButton#BtnNIBPDone:disabled,
QPushButton#BtnSpO2Done:disabled,
QPushButton#BtnTempDone:disabled,
QPushButton#BtnNIBPFail:disabled,
QPushButton#BtnSpO2Fail:disabled,
QPushButton#BtnTempFail:disabled {
    border-radius: 0px;
    border: 2px solid transparent;
    margin: 0px;
}

QFrame#ConsoleFooter {
    min-height: 72px;
}
QPushButton#BtnSummaryReady,
QPushButton#BtnSummaryDisabled {
    font-size: 19px;
    font-weight: 900;
    border-radius: 24px;
}
QPushButton#BtnFinish {
    font-size: 18px;
    font-weight: 900;
    border-radius: 24px;
}
QPushButton#BtnBack {
    font-size: 16px;
    font-weight: 900;
    border-radius: 24px;
}
"""


def build_stylesheet(font_family: str, number_font_family: str | None = None) -> str:
    number_font = number_font_family or font_family
    return (
        CONSOLE_STYLESHEET
        .replace("__APP_FONT__", font_family)
        .replace("__NUMBER_FONT__", number_font)
    )
