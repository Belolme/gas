from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QLabel, QLineEdit, QSizePolicy, QWidget, QHBoxLayout


class Ranger(QWidget):
    min_text_edited = Signal(str)
    max_text_edited = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._ranage_title = QLabel()
        self._ranage_title.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )

        self._min_level = QLineEdit()
        self._min_level.textEdited.connect(self._notify_min_range_changed)
        self._min_level.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )

        self._level_connection = QLabel("~")
        self._level_connection.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Minimum,
        )
        self._level_connection.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )

        self._max_level = QLineEdit()
        self._max_level.textEdited.connect(self._notify_max_range_changed)
        self._max_level.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )

        layout = QHBoxLayout()
        layout.addWidget(self._ranage_title)
        layout.addWidget(self._min_level)
        layout.addWidget(self._level_connection)
        layout.addWidget(self._max_level)
        layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(layout)

    def set_title(self, title: str):
        self._ranage_title.setText(title)

    def set_validator(self, validator: QValidator):
        self._min_level.setValidator(validator)
        self._max_level.setValidator(validator)

    def set_input_width(self, width: int):
        width = self._min_level.fontMetrics().averageCharWidth() * width
        self._min_level.setFixedWidth(width)
        self._max_level.setFixedWidth(width)

    def set_range(self, min=None, max=None):
        if min is not None:
            self._min_level.setText(str(min))
        if max is not None:
            self._max_level.setText(str(max))

    def set_placeholder(self, min=None, max=None):
        if min is not None:
            self._min_level.setPlaceholderText(str(min))
        if max is not None:
            self._max_level.setPlaceholderText(str(max))

    def min_text(self):
        return self._min_level.text()

    def max_text(self):
        return self._max_level.text()

    @Slot(str)
    def _notify_min_range_changed(self, text: str):
        self.min_text_edited.emit(text)

    @Slot(str)
    def _notify_max_range_changed(self, text: str):
        self.max_text_edited.emit(text)
