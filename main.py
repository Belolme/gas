import os
import sys


from PySide6 import QtGui
from PySide6.QtCore import QDir, Qt, QStandardPaths
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from typing_extensions import override

from arrange.arrange_ui import ArrangeUi
from export.export_ui import ExportUi
from tools.stringresources import load_string


def init_resource():
    mainpath = __file__
    projectpath = os.path.dirname(mainpath)

    QDir.addSearchPath("root", os.path.join(projectpath, "resources/"))
    QDir.addSearchPath("bm", os.path.join(projectpath, "resources/bitmap/"))
    QDir.addSearchPath("str", os.path.join(projectpath, "resources/strings/"))
    QDir.addSearchPath("model", os.path.join(projectpath, "resources/model/"))
    QDir.addSearchPath("config", os.path.join(projectpath, "resources/config/"))

    data_dir = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DocumentsLocation
    )
    data_dir = os.path.join(data_dir, "GenshinArtifactScanner")
    if os.path.isdir(data_dir) is False:
        os.makedirs(data_dir)
    QDir.addSearchPath("data", data_dir)


class MainUi(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent=parent)

        self.app = app

        self.init_layout()

        self.export_win = None
        self.arrage_win = None

    def init_layout(self):
        self.setWindowTitle(load_string("app_name"))
        self.setWindowIcon(QtGui.QIcon("bm:AppIcon.ico"))

        export_btn = QPushButton(load_string("export_btn"))
        export_btn.clicked.connect(self.open_export_win)

        arrange_btn = QPushButton(load_string("arrange_btn"))
        arrange_btn.clicked.connect(self.open_arrange_win)

        vertical_layout = QVBoxLayout(self)

        vertical_layout.addStretch()
        vertical_layout.addWidget(export_btn)
        vertical_layout.addWidget(arrange_btn)
        vertical_layout.addStretch()

        self.resize(280, vertical_layout.sizeHint().height())

    def open_export_win(self):
        if self.export_win and self.export_win.isVisible():
            if self.export_win.isMinimized():
                self.export_win.showNormal()
            self.export_win.activateWindow()
            return

        self.export_win = ExportUi()
        self.export_win.show()

    def open_arrange_win(self):
        if self.arrage_win and self.arrage_win.isVisible():
            if self.arrage_win.isMinimized():
                self.arrage_win.showNormal()
            self.arrage_win.activateWindow()
            return

        self.arrage_win = ArrangeUi()
        self.arrage_win.show()

    @override
    def closeEvent(self, event) -> None:
        self.app.quit()
        return super().closeEvent(event)


def run():
    init_resource()

    app = QApplication([])

    main = MainUi(app)
    main.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
