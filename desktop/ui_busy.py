# ui_busy.py
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPainter, QPen, QColor


class BusySpinner(QWidget):
    def __init__(self, parent=None, size=36, line_width=3, color="#9ca3af", speed_ms=60, span_deg=270):
        super().__init__(parent)
        self._angle = 0
        self._size = int(size)
        self._span = int(span_deg)          # длина дуги в градусах (0..360)
        self._pen = QPen(QColor(color), float(line_width), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(self._size, self._size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.hide()

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

    def start(self):
        if not self.isVisible():
            self.show()
        if not self._timer.isActive():
            self._timer.start(60)  # скорость; можно менять через speed_ms в __init__

    def stop(self):
        self._timer.stop()
        self.hide()
        self._angle = 0
        self.update()

    def _tick(self):
        self._angle = (self._angle + 15) % 360  # шаг поворота
        self.update()

    def paintEvent(self, _):
        r = self._size
        radius = (r - self._pen.widthF()) / 2.0 - 1.0
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.translate(r/2, r/2)
        painter.rotate(self._angle)
        painter.setPen(self._pen)
        # Qt-углы в шестнадцатых долях градуса и идут по часовой отрицательным span
        start_angle = 0 * 16
        span_angle = -self._span * 16
        x = int(-radius)
        y = int(-radius)
        d = int(2*radius)
        painter.drawArc(x, y, d, d, start_angle, span_angle)
        painter.end()
