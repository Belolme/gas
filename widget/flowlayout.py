import sys
from typing import Optional
from PySide6.QtCore import Qt, QMargins, QPoint, QRect, QSize
from PySide6.QtWidgets import (
    QApplication,
    QLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
    QLayoutItem,
    QWidgetItem,
)


class FlowLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(QMargins(0, 0, 0, 0))

        self._item_list = []

    def addItem(self, item):
        self._item_list.append(item)
        self.invalidate()

    def insertWidget(self, index, widget):
        self.addChildWidget(widget)
        widget_item = QWidgetItem(widget)
        self._item_list.insert(index, widget_item)
        self.invalidate()

    def count(self):
        return len(self._item_list)

    def itemAt(self, index) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    def takeAt(self, index) -> Optional[QLayoutItem]:
        if 0 <= index < len(self._item_list):
            item = self._item_list.pop(index)
            self.invalidate()
            return item

        return None

    def expandingDirections(self):
        return Qt.Orientation.Vertical

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self._do_layout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())

        size += QSize(
            self.contentsMargins().left() + self.contentsMargins().right(),
            self.contentsMargins().top() + self.contentsMargins().bottom(),
        )
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x() + self.contentsMargins().left()
        y = rect.y() + self.contentsMargins().top()
        line_height = 0
        spacing = self.spacing()

        for item in self._item_list:
            space_x = spacing + spacing
            space_y = spacing + spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x() + self.contentsMargins().left()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()


class Window(QWidget):
    def __init__(self):
        super().__init__()

        flow_layout = FlowLayout(self)
        flow_layout.addWidget(QPushButton("Short"))
        flow_layout.addWidget(QPushButton("Longer"))
        flow_layout.addWidget(QPushButton("Different text"))
        flow_layout.addWidget(QPushButton("More text"))
        flow_layout.addWidget(QPushButton("Even longer button text"))

        self.setWindowTitle("Flow Layout")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = Window()
    main_win.show()
    sys.exit(app.exec())
