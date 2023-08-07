from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QBoxLayout, QWidget, QTextEdit, QSizePolicy


class LogView(QWidget):
    def __init__(self):
        super().__init__()

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding,
        )

        l = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        l.addWidget(self.text_edit)
        l.setContentsMargins(0, 0, 0, 0)

        self.setLayout(l)

    def log(self, message):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(message + "\n")
        self.text_edit.setTextCursor(cursor)

    def clear(self):
        self.text_edit.clear()
