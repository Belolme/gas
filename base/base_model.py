from typing import Optional
from PySide6.QtCore import QObject


class BaseModel(QObject):
    def __init__(self, parent: Optional["BaseModel"] = None) -> None:
        super().__init__(parent)

        self.is_close = False


    def on_close(self):
        pass

    def close(self):
        if not self.is_close:
            self.on_close()
            self.is_close = True
