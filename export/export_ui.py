import shutil

from PySide6.QtCore import QDir, QEvent, QFile, Qt, QTextStream, Slot
from PySide6.QtGui import (
    QCloseEvent,
    QDoubleValidator,
    QFontMetrics,
    QIcon,
    QIntValidator,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from typing_extensions import override

from tools.stringresources import load_string
from widget import LogView, Ranger

from .export_model import ExportModel, LogOp, ScanState


class ExportUi(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = ExportModel()

        self._init_layout()

    def _init_layout(self):
        self.setWindowTitle(load_string("export_win_title"))
        self.setWindowIcon(QIcon("bm:AppIcon.ico"))

        self._scan_setting_title = QLabel(load_string("scan_setting"))
        self._scan_setting_title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._scan_setting_title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self._star_level_subtitle = QLabel(load_string("star_level"))

        self._five_star = QCheckBox()
        self._five_star.setText(load_string("five_star"))
        self._five_star.setChecked(self._model.get_five_star())
        self._five_star.stateChanged.connect(self._notify_five_star_level_changed)

        self._four_star = QCheckBox()
        self._four_star.setText(load_string("four_star"))
        self._four_star.setChecked(self._model.get_four_star())
        self._four_star.stateChanged.connect(self._notify_four_star_level_changed)

        self._star_level_layout = QHBoxLayout()
        self._star_level_layout.addWidget(self._star_level_subtitle)
        self._star_level_layout.addWidget(self._five_star)
        self._star_level_layout.addWidget(self._four_star)
        self._star_level_layout.addStretch()

        self._level_range = Ranger()
        self._level_range.set_title(load_string("level_range"))
        self._level_range.set_range(*self._model.get_level_range())
        self._level_range.set_placeholder(0, 20)
        self._level_range.set_input_width(6)
        self._level_range.set_validator(QIntValidator())
        self._level_range.min_text_edited.connect(self._notify_level_range_changed)
        self._level_range.max_text_edited.connect(self._notify_level_range_changed)
        ranger_layout = self._level_range.layout()
        assert isinstance(
            ranger_layout, QHBoxLayout
        ), f"layout is {type(ranger_layout)}"
        ranger_layout.addStretch()

        self._export_format_title = QLabel(load_string("export_format"))

        self._export_layout = QHBoxLayout()
        self._export_layout.addWidget(self._export_format_title)

        self._export_group_radio = QButtonGroup()
        export_format_id = self._model.get_export_format()
        for format_id in self._model.get_available_export_formats():
            format_btn = QRadioButton(load_string(format_id))
            format_btn.setObjectName(format_id)

            if format_id == export_format_id:
                format_btn.setChecked(True)

            self._export_group_radio.addButton(format_btn)
            self._export_layout.addWidget(format_btn)

        self._export_group_radio.buttonToggled.connect(
            self._notify_export_format_changed
        )

        self._export_layout.addStretch()

        self._scan_btn = QPushButton(load_string("start_scan"))
        self._scan_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self._scan_btn.clicked.connect(self._notify_start_scan)
        self._model.scan_state.connect(self._event_scan_state_changed)
        self._model.progress.connect(self._event_scan_progress_changed)

        self._log_view = LogView()
        self._model.log.connect(self._event_log)

        self._root_layout = QVBoxLayout()
        self._root_layout.addWidget(self._scan_setting_title)
        self._root_layout.addLayout(self._star_level_layout)
        self._root_layout.addWidget(self._level_range)
        self._root_layout.addLayout(self._export_layout)
        self._root_layout.addWidget(self._scan_btn)
        self._root_layout.addWidget(self._log_view, stretch=1)

        self.setLayout(self._root_layout)
        self.setMinimumWidth(300)

        self._model.dialog_save_output.connect(self._event_save_output)

    @Slot(str)
    def _event_save_output(self, path: str):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            load_string("save_artifact_export"),
            self._model.get_export_format(),
            load_string("export_artifact_fitler"),
        )
        if file_path:
            print("export ui save output: ", path, file_path)
            shutil.copyfile(path, file_path)

    @Slot()
    def _notify_five_star_level_changed(self):
        self._model.set_five_star(self._five_star.isChecked())

    @Slot(bool)
    def _event_five_star_changed(self, enable: bool):
        if enable == self._five_star.isChecked():
            return

        self._five_star.setChecked(enable)

    @Slot()
    def _notify_four_star_level_changed(self):
        self._model.set_four_star(self._four_star.isChecked())

    @Slot(bool)
    def _event_four_star_changed(self, enable: bool):
        if enable == self._four_star.isChecked():
            return

        self._four_star.setChecked(enable)

    @Slot()
    def _notify_level_range_changed(self):
        min = self._level_range.min_text().replace(",", "")
        max = self._level_range.max_text().replace(",", "")

        min = int(min) if min else 0
        max = int(max) if max else 20
        self._model.set_level_range(min, max)

    @Slot(int, int)
    def _event_level_range_changed(self, min_level: int, max_level: int):
        if str(min_level) != self._level_range.min_text():
            self._level_range.set_range(min=str(min_level))

        if str(max_level) != self._level_range.max_text():
            self._level_range.set_range(max=str(max_level))

    def _notify_export_format_changed(self, button: QAbstractButton, toggled):
        if toggled == True:
            self._model.set_export_format(button.objectName())

    @Slot()
    def _notify_start_scan(self):
        self._model.start_scan()

    @Slot(ScanState)
    def _event_scan_state_changed(self, state: ScanState):
        if state is ScanState.Idle:
            self._scan_btn.setText(load_string("start_scan"))
            return

        if state is ScanState.Running:
            progress = self._model.get_progress()
            self._scan_btn.setText(load_string("scan_progress").format(progress))
            return

        if state is ScanState.Error:
            self._scan_btn.setText(load_string("scan_error"))
            return

        if state is ScanState.Finished:
            self._scan_btn.setText(load_string("finish_scan"))
            return

    @Slot(int)
    def _event_scan_progress_changed(self, progress: int):
        scan_state = self._model.get_scan_state()
        if scan_state is not ScanState.Running:
            return

        self._scan_btn.setText(load_string("scan_progress").format(progress))

    @Slot(LogOp, str)
    def _event_log(self, op: LogOp, message: str):
        if op is LogOp.Append:
            self._log_view.log(message)
        elif op is LogOp.Clear:
            self._log_view.clear()

    @override
    def closeEvent(self, event: QCloseEvent):
        self._model.close()
        event.accept()
