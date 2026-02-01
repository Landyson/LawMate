from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QTextBrowser, QFrame

def _color_for_light(light: str) -> QColor:
    if light == "green":
        return QColor(46, 204, 113)
    if light == "yellow":
        return QColor(241, 196, 15)
    return QColor(231, 76, 60)

class TrafficLightBadge(QWidget):
    def __init__(self, light: str, parent=None):
        super().__init__(parent)
        dot = QFrame()
        dot.setFixedSize(14, 14)
        c = _color_for_light(light)
        dot.setStyleSheet(f"border-radius:7px; background-color: rgb({c.red()},{c.green()},{c.blue()});")

        label = QLabel({
            "green": "Zelená: nízké riziko",
            "yellow": "Žlutá: raději konzultace",
            "red": "Červená: řeš s právníkem",
        }.get(light, "Semafor"))

        label.setStyleSheet("color:#333; font-size:12px;")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(8)
        lay.addWidget(dot)
        lay.addWidget(label)
        lay.addStretch(1)

class ChatBubble(QWidget):
    def __init__(self, role: str, html: str, traffic_light: str | None = None, parent=None):
        super().__init__(parent)

        bubble = QTextBrowser()
        bubble.setOpenExternalLinks(True)
        bubble.setFrameShape(QFrame.NoFrame)
        bubble.setHtml(html.replace("\n", "<br>"))

        bubble.setStyleSheet("""
            QTextBrowser{
                padding:10px;
                border-radius:12px;
                font-size:13px;
                color:#111;
            }
            QTextBrowser a{ color:#0a58ca; }
        """)

        if role == "user":
            bubble.setStyleSheet(bubble.styleSheet() + "QTextBrowser{background:#e8f3ff; color:#111;}")
        else:
            bubble.setStyleSheet(bubble.styleSheet() + "QTextBrowser{background:#f3f3f3; color:#111;}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(6)

        if traffic_light and role == "assistant":
            root.addWidget(TrafficLightBadge(traffic_light))

        root.addWidget(bubble)
