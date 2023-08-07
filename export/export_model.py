import json
import os
import platform
import threading
import time
import traceback
from enum import Enum

import yaml
from PySide6.QtCore import QDir, QObject, Signal, Slot

# import bin.InferPybinder as infer
from infer.artifact_warehouse_handler import ArtifactWarehouseHandler
from tools.stringresources import load_string


class ScanState(Enum):
    Idle = 0
    Running = 1
    Finished = 2
    Error = 3


class LogOp(Enum):
    Append = 0
    Clear = 1


class ExportModel(QObject):
    scan_state = Signal(ScanState)
    progress = Signal(int)
    dialog_save_output = Signal(str)

    log = Signal(LogOp, str)

    Export_Format_Mona = "mona"
    Export_Format_YuanMo = "yuanmo"

    def __init__(self):
        super().__init__()

        self._five_star = True
        self._four_star = True
        self._level_range = [0, 20]
        self._scan_state = ScanState.Idle
        self._progress = 0

        self._export_format = self.Export_Format_Mona
        self._available_export_formats = [
            self.Export_Format_Mona,
            self.Export_Format_YuanMo,
        ]

        self._close = False

        self._cfg_dir = QDir("data:")
        if not self._cfg_dir.exists("./export"):
            self._cfg_dir.mkdir("export")
        self._cfg_dir.cd("export")
        self._cfg = self._cfg_dir.absoluteFilePath("export.yaml")
        self._load_persist()

    def _persist(self):
        with open(self._cfg, "w", encoding="utf8") as f:
            data = {
                "version": 1,
                "five_star": self._five_star,
                "four_star": self._four_star,
                "level_range": self._level_range,
                "export_format": self._export_format,
            }

            yaml.safe_dump(data, f)

    def _load_persist(self):
        if not os.path.exists(self._cfg):
            return

        with open(self._cfg, "r", encoding="utf8") as f:
            data: dict = yaml.safe_load(f)
            self._five_star = data.get("five_star", self._five_star)
            self._four_star = data.get("four_star", self._four_star)
            self._level_range = data.get("level_range", self._level_range)
            self._export_format = data.get("export_format", self._export_format)

    def get_five_star(self):
        return self._five_star

    def set_five_star(self, value):
        self._five_star = value
        self._persist()

    def get_four_star(self):
        return self._four_star

    def set_four_star(self, value):
        self._four_star = value
        self._persist()

    def get_level_range(self):
        return self._level_range

    def set_level_range(self, min=None, max=None):
        if min is not None:
            self._level_range[0] = min
        if max is not None:
            self._level_range[1] = max
        self._persist()

    def get_export_format(self):
        return self._export_format

    def set_export_format(self, value):
        self._export_format = value
        self._persist()

    def get_available_export_formats(self):
        return self._available_export_formats

    def get_scan_state(self):
        return self._scan_state

    def get_progress(self):
        return self._progress

    def _scan_callback(self, code: int, **argws):
        if code == ArtifactWarehouseHandler.CB_INFO_PROGRAM:
            self._progress = argws["program"]
            self.progress.emit(self._progress)
        if code == ArtifactWarehouseHandler.CB_INFO_ARTIFACTS_COUNT:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("artifacts_count").format(argws["count"]),
            )
        elif code == ArtifactWarehouseHandler.CB_WARN_RECGNIZE_FAILED:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_recognize_failed")
                + f"\n{argws['artifact']}",
            )
        elif code == ArtifactWarehouseHandler.CB_INFO_FINISH:
            output_path = self._cfg_dir.absoluteFilePath("output.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    argws["artifacts"],
                    f,
                    ensure_ascii=False,
                    indent=2,
                    separators=(",", ": "),
                )
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("scan_finished"),
            )
            self._progress = 100
            self.progress.emit(self._progress)
            self._scan_state = ScanState.Finished
            self.scan_state.emit(self._scan_state)
            self.dialog_save_output.emit(output_path)
        elif code == ArtifactWarehouseHandler.CB_ERR_INTERRUPT_BY_USER:
            output_path = self._cfg_dir.absoluteFilePath("output.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    argws["artifacts"],
                    f,
                    ensure_ascii=False,
                    indent=2,
                    separators=(",", ": "),
                )
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_scan_interrupt_by_user"),
            )
            self._scan_state = ScanState.Error
            self.scan_state.emit(self._scan_state)
            self.dialog_save_output.emit(output_path)
        elif code == ArtifactWarehouseHandler.CB_ERR_SWITCH_FAILED:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ") + load_string("error_switch_genshin_failed"),
            )
            self._scan_state = ScanState.Error
            self.scan_state.emit(self._scan_state)
        elif code == ArtifactWarehouseHandler.CB_ERR_FIND_ARTIFACT_COUNT_FAILED:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_surface_not_artifacts_warehouse"),
            )
            self._scan_state = ScanState.Error
            self.scan_state.emit(self._scan_state)
        elif code == ArtifactWarehouseHandler.CB_ERR_CANNOT_FIND_DET_CONFIG:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_cannot_find_det_config"),
            )
            self._scan_state = ScanState.Error
            self.scan_state.emit(self._scan_state)

    def _scan(self, min_star, max_star, min_level, max_level):
        try:
            res_root = QDir("root:").absolutePath()
            if platform.system() == "Windows":
                res_root = res_root.replace("/", os.path.sep)
            else:
                res_root = res_root.replace("\\", os.path.sep)
            res_root += os.path.sep

            awh = ArtifactWarehouseHandler()
            format = "none"
            if self._export_format == self.Export_Format_Mona:
                format = "mona"
            elif self._export_format == self.Export_Format_YuanMo:
                format = "yuanmo"

            self._progress = 0
            self.progress.emit(self._progress)
            awh.scan_artifacts(
                min_star=min_star,
                max_star=max_star,
                min_level=min_level,
                max_level=max_level,
                format=format,
                callback=self._scan_callback,
            )
        except Exception as e:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_log_prefix").format(str(e)),
            )
            traceback.print_exc()
            self._scan_state = ScanState.Error
            self.scan_state.emit(self._scan_state)

    def start_scan(self):
        if self._scan_state is ScanState.Running:
            return

        self._progress = 0
        self.scan_state.emit(self._scan_state)
        self.progress.emit(self._progress)
        self.log.emit(LogOp.Clear, "")

        if self._four_star and self._five_star:
            star_range = (4, 5)
        elif self._four_star and not self._five_star:
            star_range = (4, 4)
        elif not self._four_star and self._five_star:
            star_range = (5, 5)
        else:
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_tip_none_selected_star"),
            )
            return

        if (
            self._level_range[0] > self._level_range[1]
            or self._level_range[0] < 0
            or self._level_range[0] > 20
            or self._level_range[1] < 0
            or self._level_range[1] > 20
        ):
            self.log.emit(
                LogOp.Append,
                time.strftime("%H:%M:%S ")
                + load_string("error_tip_level_range_invalid"),
            )
            return
        else:
            level_range = (self._level_range[0], self._level_range[1])

        self._scan_state = ScanState.Running

        self.t = threading.Thread(
            target=self._scan,
            kwargs={
                "min_star": star_range[0],
                "max_star": star_range[1],
                "min_level": level_range[0],
                "max_level": level_range[1],
            },
        )
        self.t.start()

    def close(self):
        self._close = True

    def __del__(self):
        self._close = True
