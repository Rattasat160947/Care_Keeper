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
"""


def build_stylesheet(font_family: str, number_font_family: str | None = None) -> str:
    number_font = number_font_family or font_family
    return (
        CONSOLE_STYLESHEET
        .replace("__APP_FONT__", font_family)
        .replace("__NUMBER_FONT__", number_font)
    )
