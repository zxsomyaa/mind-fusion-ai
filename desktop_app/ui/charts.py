"""
Small charts drawn with Qt's painter, shared by the Nutrition and Insights
pages. Colours are read from the active theme every time they paint, so a
theme switch (or a rebuilt window) needs no extra work.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from data import COLORS as C

HEAVY = "#E07A5F"
MIXED = "#D9B26F"


def _font(widget, pixels, bold=False):
    font = QFont(widget.font())
    font.setPixelSize(pixels)
    font.setBold(bold)
    return font


def _alpha(colour, alpha):
    c = QColor(colour)
    c.setAlphaF(alpha)
    return c


def nice_max(value):
    """Rounds a chart's top value up to a tidy number (37 -> 40, 830 -> 1000)."""
    if value <= 0:
        return 1
    magnitude = 10 ** math.floor(math.log10(value))
    for step in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if value <= step * magnitude:
            return step * magnitude
    return 10 * magnitude


class RingGauge(QWidget):
    """A ring that fills to a fraction, with text in the middle."""

    def __init__(self, size=124, thickness=12, parent=None):
        super().__init__(parent)
        self.thickness = thickness
        self._fraction, self._text, self._sub, self._colour = 0.0, "", "", None
        self.setFixedSize(size, size)

    def set_value(self, fraction, text, sub="", colour=None):
        self._fraction = max(0.0, min(1.0, fraction))
        self._text, self._sub, self._colour = text, sub, colour
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self.thickness
        rect = QRectF(t / 2 + 2, t / 2 + 2, self.width() - t - 4, self.height() - t - 4)
        pen = QPen(QColor(C["border"]), t)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)
        if self._fraction > 0:
            pen.setColor(QColor(self._colour or C["primary"]))
            p.setPen(pen)
            p.drawArc(rect, 90 * 16, int(-self._fraction * 360 * 16))
        p.setPen(QColor(C["text"]))
        p.setFont(_font(self, 24, True))
        p.drawText(QRectF(0, self.height() * 0.28, self.width(), 32), Qt.AlignCenter, self._text)
        if self._sub:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(_font(self, 11))
            p.drawText(QRectF(0, self.height() * 0.28 + 30, self.width(), 18), Qt.AlignCenter, self._sub)


class DonutChart(QWidget):
    """A donut with a legend on its right. Segments are (label, value, colour)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._segments, self._centre, self._sub, self._unit = [], "", "", ""
        self.setMinimumHeight(170)

    def set_segments(self, segments, centre="", sub="", unit=""):
        self._segments = [s for s in segments if s[1] > 0]
        self._centre, self._sub, self._unit = centre, sub, unit
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        diameter = min(self.height() - 12, 150)
        thickness = diameter * 0.2
        rect = QRectF(6 + thickness / 2, (self.height() - diameter) / 2 + thickness / 2,
                      diameter - thickness, diameter - thickness)
        total = sum(v for _l, v, _c in self._segments)

        pen = QPen(QColor(C["border"]), thickness)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        p.drawArc(rect, 0, 360 * 16)
        if total <= 0:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(_font(self, 12))
            p.drawText(rect, Qt.AlignCenter, "No data")
            return

        start = 90.0
        gap = 2.0 if len(self._segments) > 1 else 0.0
        for _label, value, colour in self._segments:
            span = value / total * 360
            pen.setColor(QColor(colour))
            p.setPen(pen)
            p.drawArc(rect, int((start - gap / 2) * 16), int(-max(span - gap, 0.5) * 16))
            start -= span

        cx, cy = rect.center().x(), rect.center().y()
        p.setPen(QColor(C["text"]))
        p.setFont(_font(self, 20, True))
        p.drawText(QRectF(cx - 50, cy - 22, 100, 26), Qt.AlignCenter, self._centre)
        if self._sub:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(_font(self, 10))
            p.drawText(QRectF(cx - 50, cy + 2, 100, 16), Qt.AlignCenter, self._sub)

        # legend
        x = diameter + 26
        row_h = 24
        y = (self.height() - row_h * len(self._segments)) / 2
        for label, value, colour in self._segments:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(colour))
            p.drawEllipse(QRectF(x, y + 7, 10, 10))
            p.setPen(QColor(C["text"]))
            p.setFont(_font(self, 13))
            p.drawText(QRectF(x + 18, y, self.width() - x - 90, row_h), Qt.AlignVCenter | Qt.AlignLeft, label)
            p.setPen(QColor(C["text_muted"]))
            shown = f"{value:g}{self._unit}" if self._unit else f"{round(value / total * 100)}%"
            p.drawText(QRectF(self.width() - 76, y, 70, row_h), Qt.AlignVCenter | Qt.AlignRight, shown)
            y += row_h


class BarChart(QWidget):
    """Rounded bars with a light grid, an optional shaded target band and
    tooltips on hover. Bars are {"label", "value", "tooltip", "colour"(optional)}."""

    LEFT, RIGHT, TOP, BOTTOM = 40, 10, 10, 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bars, self._band, self._y_max, self._colour, self._empty = [], None, None, None, "No data yet"
        self._hover = None
        self.setMouseTracking(True)
        self.setMinimumHeight(200)

    def set_data(self, bars, y_max=None, band=None, colour=None, empty_text="No data yet"):
        self._bars, self._y_max, self._band, self._colour, self._empty = bars, y_max, band, colour, empty_text
        self._hover = None
        self.update()

    def _plot(self):
        return QRectF(self.LEFT, self.TOP, self.width() - self.LEFT - self.RIGHT,
                      self.height() - self.TOP - self.BOTTOM)

    def _bar_at(self, x):
        plot = self._plot()
        if not self._bars or not (plot.left() <= x <= plot.right()):
            return None
        return min(len(self._bars) - 1, int((x - plot.left()) / (plot.width() / len(self._bars))))

    def mouseMoveEvent(self, event):
        index = self._bar_at(event.position().x())
        if index != self._hover:
            self._hover = index
            self.update()
        if index is not None and self._bars[index].get("tooltip"):
            QToolTip.showText(event.globalPosition().toPoint(), self._bars[index]["tooltip"], self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, _event):
        self._hover = None
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        plot = self._plot()
        if not self._bars:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(_font(self, 13))
            p.drawText(plot, Qt.AlignCenter, self._empty)
            return

        y_max = self._y_max or nice_max(max(b["value"] for b in self._bars) * 1.05)
        y_of = lambda v: plot.bottom() - (v / y_max) * plot.height()

        if self._band:
            lo, hi = self._band
            p.fillRect(QRectF(plot.left(), y_of(hi), plot.width(), y_of(lo) - y_of(hi)), _alpha(C["sage_light"], 0.35))
        p.setFont(_font(self, 10))
        for frac in (0, 0.5, 1):
            y = y_of(y_max * frac)
            p.setPen(QPen(_alpha(C["border"], 0.9), 1, Qt.DotLine if frac else Qt.SolidLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(C["text_muted"]))
            p.drawText(QRectF(0, y - 8, self.LEFT - 6, 16), Qt.AlignRight | Qt.AlignVCenter, f"{y_max * frac:g}")

        n = len(self._bars)
        slot = plot.width() / n
        bar_w = min(30.0, slot * 0.62)
        every = max(1, math.ceil(n / 12))
        for i, bar in enumerate(self._bars):
            x = plot.left() + slot * i + (slot - bar_w) / 2
            top = y_of(min(bar["value"], y_max))
            colour = QColor(bar.get("colour") or self._colour or C["primary"])
            if self._hover is not None and i != self._hover:
                colour = _alpha(colour, 0.55)
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, top, bar_w, max(plot.bottom() - top, 1)), 5, 5)
            p.fillPath(path, colour)
            if i % every == 0:
                p.setPen(QColor(C["primary"] if i == self._hover else C["text_muted"]))
                p.drawText(QRectF(x - 14, plot.bottom() + 6, bar_w + 28, 16), Qt.AlignCenter, bar["label"])


class LineChart(QWidget):
    """Smooth mood line between -1 (heavy) and +1 (positive), tinted green
    above the middle and red below. Points are {"x", "y", "label", "tooltip"}."""

    LEFT, RIGHT, TOP, BOTTOM = 66, 16, 10, 28

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points, self._hover = [], None
        self.setMouseTracking(True)
        self.setMinimumHeight(200)

    def set_points(self, points):
        self._points, self._hover = points, None
        self.update()

    def _plot(self):
        return QRectF(self.LEFT, self.TOP, self.width() - self.LEFT - self.RIGHT,
                      self.height() - self.TOP - self.BOTTOM)

    def _xy(self, point):
        plot = self._plot()
        xs = [pt["x"] for pt in self._points]
        lo, hi = min(xs), max(xs)
        fx = 0.5 if hi == lo else (point["x"] - lo) / (hi - lo)
        return QPointF(plot.left() + fx * plot.width(), plot.bottom() - (point["y"] + 1) / 2 * plot.height())

    def mouseMoveEvent(self, event):
        if not self._points:
            return
        nearest = min(range(len(self._points)),
                      key=lambda i: abs(self._xy(self._points[i]).x() - event.position().x()))
        if nearest != self._hover:
            self._hover = nearest
            self.update()
        QToolTip.showText(event.globalPosition().toPoint(), self._points[nearest]["tooltip"], self)

    def leaveEvent(self, _event):
        self._hover = None
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        plot = self._plot()
        if len(self._points) < 2:
            p.setPen(QColor(C["text_muted"]))
            p.setFont(_font(self, 13))
            p.drawText(plot, Qt.AlignCenter, "Check in on a couple of different days to see a trend")
            return

        zero_y = plot.center().y()
        p.setFont(_font(self, 10))
        for value, text in ((1, "positive"), (0, "mixed"), (-1, "heavy")):
            y = plot.bottom() - (value + 1) / 2 * plot.height()
            p.setPen(QPen(_alpha(C["border"], 0.9), 1, Qt.SolidLine if value == 0 else Qt.DotLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(C["text_muted"]))
            p.drawText(QRectF(0, y - 8, self.LEFT - 8, 16), Qt.AlignRight | Qt.AlignVCenter, text)

        pts = [self._xy(pt) for pt in self._points]
        # Catmull-Rom curve: smooth AND passes exactly through every data point
        # (a simpler smoothing cuts corners, so the markers would sit off the line).
        # The handles are clamped so the curve can't swing outside the plot.
        clamp_y = lambda pt: QPointF(pt.x(), min(plot.bottom(), max(plot.top(), pt.y())))
        curve = QPainterPath(pts[0])
        for i in range(len(pts) - 1):
            p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
            p3 = pts[min(i + 2, len(pts) - 1)]
            curve.cubicTo(clamp_y(p1 + (p2 - p0) / 6), clamp_y(p2 - (p3 - p1) / 6), p2)

        area = QPainterPath(curve)
        area.lineTo(pts[-1].x(), zero_y)
        area.lineTo(pts[0].x(), zero_y)
        area.closeSubpath()
        p.save()
        p.setClipRect(QRectF(plot.left(), plot.top(), plot.width(), zero_y - plot.top()))
        p.fillPath(area, _alpha(C["sage"], 0.32))
        p.restore()
        p.save()
        p.setClipRect(QRectF(plot.left(), zero_y, plot.width(), plot.bottom() - zero_y))
        p.fillPath(area, _alpha(HEAVY, 0.32))
        p.restore()

        line = QPen(QColor(C["primary"]), 2.5)
        line.setJoinStyle(Qt.RoundJoin)
        line.setCapStyle(Qt.RoundCap)
        p.setPen(line)
        p.setBrush(Qt.NoBrush)
        p.drawPath(curve)

        for i, pt in enumerate(pts):
            radius = 5.5 if i == self._hover else 3.5
            p.setPen(QPen(QColor(C["primary"]), 2))
            p.setBrush(QColor(C["surface"]))
            p.drawEllipse(pt, radius, radius)

        # x labels: at most ~6, always including the first and last
        p.setFont(_font(self, 10))
        p.setPen(QColor(C["text_muted"]))
        n = len(self._points)
        step = max(1, math.ceil((n - 1) / 5))
        shown = sorted(set(list(range(0, n, step)) + [n - 1]))
        for i in shown:
            if i != n - 1 and n - 1 - i < step * 0.6:
                continue                                    # too close to the last label
            p.drawText(QRectF(pts[i].x() - 30, plot.bottom() + 6, 60, 16), Qt.AlignCenter, self._points[i]["label"])


class MoodCalendar(QWidget):
    """A week-by-week grid (like a contribution graph) coloured by how each day's check-ins felt."""

    CELL, GAP, LEFT, TOP = 20, 4, 22, 18

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = []
        self.setMouseTracking(True)
        self.setMinimumHeight(self.TOP + 7 * (self.CELL + self.GAP) + 26)

    def set_grid(self, grid):
        self._grid = grid
        self.setMinimumWidth(self.LEFT + len(grid) * (self.CELL + self.GAP) + 4)
        self.update()

    @staticmethod
    def colour_for(day):
        if day is None or day["score"] is None:
            return QColor(C["border"])
        if day["score"] >= 0.34:
            return QColor(C["sage"])
        if day["score"] <= -0.34:
            return QColor(HEAVY)
        return QColor(MIXED)

    def _day_at(self, pos):
        step = self.CELL + self.GAP
        col, row = int((pos.x() - self.LEFT) // step), int((pos.y() - self.TOP) // step)
        if 0 <= col < len(self._grid) and 0 <= row < 7 and pos.x() >= self.LEFT and pos.y() >= self.TOP:
            return self._grid[col][row]
        return None

    def mouseMoveEvent(self, event):
        day = self._day_at(event.position())
        if day is None:
            QToolTip.hideText()
            return
        if day["count"]:
            feel = "positive" if day["score"] >= 0.34 else "heavy" if day["score"] <= -0.34 else "mixed"
            text = f"{day['date']:%a %d %b} - {day['count']} check-in{'s' if day['count'] != 1 else ''}, mostly {feel}"
        else:
            text = f"{day['date']:%a %d %b} - no check-in"
        QToolTip.showText(event.globalPosition().toPoint(), text, self)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        step = self.CELL + self.GAP
        p.setFont(_font(self, 10))
        p.setPen(QColor(C["text_muted"]))
        for row, name in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
            p.drawText(QRectF(0, self.TOP + row * step, self.LEFT - 2, self.CELL), Qt.AlignVCenter | Qt.AlignLeft, name[0])

        last_month = None
        for col, column in enumerate(self._grid):
            first = next((d for d in column if d), None)
            if first and first["date"].month != last_month:
                last_month = first["date"].month
                p.drawText(QRectF(self.LEFT + col * step, 0, 40, self.TOP - 2), Qt.AlignLeft | Qt.AlignVCenter,
                           f"{first['date']:%b}")
            for row, day in enumerate(column):
                if day is None:
                    continue
                rect = QRectF(self.LEFT + col * step, self.TOP + row * step, self.CELL, self.CELL)
                path = QPainterPath()
                path.addRoundedRect(rect, 5, 5)
                p.fillPath(path, self.colour_for(day))

        # legend
        y = self.TOP + 7 * step + 6
        x = self.LEFT
        for label, colour in (("no check-in", C["border"]), ("heavy", HEAVY), ("mixed", MIXED), ("positive", C["sage"])):
            p.setBrush(QColor(colour))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(x, y + 3, 11, 11), 3, 3)
            p.setPen(QColor(C["text_muted"]))
            p.drawText(QRectF(x + 15, y, 80, 18), Qt.AlignVCenter | Qt.AlignLeft, label)
            x += 26 + len(label) * 6.5
