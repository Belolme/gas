import os
import re
import time
from typing import Callable, Final, Literal, Optional

import cv2
import numpy as np
import pyautogui
import yaml
from PySide6.QtCore import QDir

from infer import wm
from infer.rec import TextRecInfer


def _encode_artifacts_yuanmo(artifacts: list):
    mapper_fold = QDir("config:mapper").path()
    artifact_name_mapper: dict = {}
    artifact_attr_mapper: dict = {}
    artifact_pos_mapper: dict = {}
    with open(
        os.path.join(mapper_fold, "artifact_attr_yuanmo.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_attr_mapper = yaml.safe_load(f)
    with open(
        os.path.join(mapper_fold, "artifact_name_yuanmo.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_name_mapper = yaml.safe_load(f)

    with open(
        os.path.join(mapper_fold, "artifact_pos_yuanmo.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_pos_mapper = yaml.safe_load(f)

    output = []
    for artifact in artifacts:
        name = artifact["name"].strip()
        name = artifact_name_mapper.get(name, None)
        if name is None:
            continue

        pos = artifact_pos_mapper.get(artifact["pos"], None)
        if pos is None:
            continue

        main_attr = artifact_attr_mapper.get(artifact["main_attr"], None)
        if main_attr is None:
            continue

        main_value = artifact["main_value"]
        if main_value == 0:
            continue

        star = artifact["star"]
        if star < 4:
            continue

        level = artifact["level"]
        if level < 0 or level > 20:
            continue

        sub_attrs = [
            artifact_attr_mapper[sub_attr] for sub_attr in artifact["sub_attrs"]
        ]
        sub_values = artifact.sub_values

        o = {
            "asKey": name,
            "rarity": star,
            "slot": pos,
            "level": level,
            "mainStat": main_attr,
            "subStat1Type": "critRate",
            "mark": "none",
        }
        for i in range(1, 5):
            if i < len(sub_attrs):
                o[f"subStat{i}Type"] = sub_attrs[i - 1]
                o[f"subStat{i}Value"] = sub_values[i - 1]
            else:
                o[f"subStat{i}Type"] = "critDamage"
                o[f"subStat{i}Value"] = 0

        output.append(o)

    return output


def _encode_artifacts_mona(artifacts: list):
    mapper_fold = QDir("config:mapper").path()

    artifact_name_mapper: dict = {}
    artifact_attr_mapper: dict = {}
    artifact_pos_mapper: dict = {}
    with open(
        os.path.join(mapper_fold, "artifact_attr_mona.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_attr_mapper = yaml.safe_load(f)
    with open(
        os.path.join(mapper_fold, "artifact_name_mona.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_name_mapper = yaml.safe_load(f)

    with open(
        os.path.join(mapper_fold, "artifact_pos_mona.yaml"),
        "r",
        encoding="utf8",
    ) as f:
        artifact_pos_mapper = yaml.safe_load(f)

    output = {
        "version": 1,
        "flower": [],
        "feather": [],
        "sand": [],
        "cup": [],
        "head": [],
    }
    for artifact in artifacts:
        name = artifact["name"].strip()
        name = artifact_name_mapper.get(name, None)
        if name is None:
            continue

        pos = artifact_pos_mapper.get(artifact["pos"], None)
        if pos is None:
            continue

        main_attr = artifact_attr_mapper.get(artifact["main_attr"], None)
        if main_attr is None:
            continue

        main_value = artifact["main_value"]
        if main_value == 0:
            continue

        star = artifact["star"]
        if star < 4:
            continue

        level = artifact["level"]
        if level < 0 or level > 20:
            continue

        sub_attrs = [
            artifact_attr_mapper[sub_attr] for sub_attr in artifact["sub_attrs"]
        ]
        sub_values = artifact["sub_values"]

        new_artifact = {
            "setName": name,
            "position": pos,
            "mainTag": {"name": main_attr, "value": main_value},
            "normalTags": [
                {"name": sub_attr, "value": sub_value}
                for sub_attr, sub_value in zip(sub_attrs, sub_values)
            ],
            "omit": False,
            "level": level,
            "star": star,
            "equip": artifact["equipper"],
        }
        output[pos].append(new_artifact)
    return output


class ArtifactWarehouseHandler(object):
    CB_ERR_INTERRUPT_BY_USER: Final[int] = -6
    CB_ERR_CANNOT_FIND_DET_CONFIG: Final[int] = -5
    CB_ERR_PARAM_INVALID: Final[int] = -4
    CB_ERR_FIND_ARTIFACT_COUNT_FAILED: Final[int] = -3
    CB_ERR_SWITCH_FAILED: Final[int] = -2
    CB_WARN_RECGNIZE_FAILED: Final[int] = -1
    CB_INFO_FINISH: Final[int] = 0
    CB_INFO_PROGRAM: Final[int] = 1
    CB_INFO_ARTIFACTS_COUNT: Final[int] = 2

    def __init__(self) -> None:
        self._detconfig_path = QDir("config:det/artifact_warehouse").path()

        map_fold = QDir("config:mapper")
        map_pos_zh_path = map_fold.filePath("artifact_pos_zh.yaml")
        with open(map_pos_zh_path, "r", encoding="utf-8") as f:
            self._map_pos_zh = yaml.safe_load(f)
        map_name_zh_path = map_fold.filePath("artifact_name_zh.yaml")
        with open(map_name_zh_path, "r", encoding="utf-8") as f:
            self._map_name_zh = yaml.safe_load(f)
        map_attr_zh_path = map_fold.filePath("artifact_attr_zh.yaml")
        with open(map_attr_zh_path, "r", encoding="utf-8") as f:
            self._map_attr_zh = yaml.safe_load(f)

        self._infer = TextRecInfer()

    def _to_star(self, star_str: str):
        count = star_str.count("★")
        if count > 5 or count <= 0:
            return -1
        return count

    def _to_level(self, level_str: str):
        level = self._to_int(level_str)
        if level < 0 or level > 20:
            return -1
        return level

    def _to_float(self, value: str):
        value = re.sub("[,，]", "", value)
        m = re.search(r"\d+\.?\d+%?", value)
        if m is None:
            return -1.0

        num_str = m.group()
        if num_str.find("%") >= 0:
            num_str = num_str.replace("%", "")
            return float(num_str) / 100
        else:
            return float(num_str)

    def _to_int(self, value: str):
        value = re.sub("[,，.]", "", value)
        m = re.search(r"\d+", value)
        if m is None:
            return -1
        return int(m.group())

    def _find_in_map(self, key: str, map: dict[str, str]):
        for k, v in map.items():
            if key.find(v) >= 0:
                return k

        return ""

    def _detect_det_config(self, win_width, win_height):
        sch_ratio = win_width / win_height
        for det_name in os.listdir(self._detconfig_path):
            det_path = os.path.join(self._detconfig_path, det_name)
            with open(det_path, "r", encoding="utf8") as f:
                det_config = yaml.safe_load(f)

            det_width = det_config["resolution"]["width"]
            det_height = det_config["resolution"]["height"]
            if det_width == win_width and det_height == win_height:
                break

            det_ratio = det_width / det_height
            if abs((det_ratio - sch_ratio) / sch_ratio) < 0.01:
                break
        else:
            return False

        scale = win_width / det_width
        count_bound = np.array(det_config["count"], dtype=np.float64)
        count_bound *= scale
        count_bound = np.round(count_bound).astype(np.int32)
        count_bound = np.expand_dims(count_bound, axis=0)
        self._count_bound = count_bound

        info_bounds = []
        info_bounds.append(np.array(det_config["pos"], dtype=np.float64))  # 0
        info_bounds.append(np.array(det_config["level"], dtype=np.float64))  # 1
        info_bounds.append(np.array(det_config["main_attr"], dtype=np.float64))  # 2
        info_bounds.append(np.array(det_config["main_value"], dtype=np.float64))  # 3
        info_bounds.append(np.array(det_config["star"], dtype=np.float64))  # 4
        info_bounds.append(np.array(det_config["lock"], dtype=np.float64))  # 5
        info_bounds.append(np.array(det_config["equipper"], dtype=np.float64))  # 6
        txt_row = det_config["txt"]["row"]
        txt_height = det_config["txt"]["txt_height"]
        txt_bound = det_config["txt"]["bound"]
        txt_intervalh = (txt_bound[3] - txt_bound[1] - txt_height * txt_row) / (
            txt_row - 1
        )
        for i in range(txt_row):
            l = txt_bound[0]
            t = txt_bound[1] + i * (txt_height + txt_intervalh)
            r = txt_bound[2]
            b = t + txt_height
            info_bounds.append(
                np.array(
                    (l, t, r, b),
                    dtype=np.float64,
                )
            )
        info_bounds = np.array(info_bounds, dtype=np.float64)
        info_bounds *= scale
        info_bounds = np.round(info_bounds).astype(np.int32)
        self._info_bounds = info_bounds

        list_row = det_config["list"]["row"]
        list_col = det_config["list"]["col"]
        list_bound = np.array(det_config["list"]["bound"], dtype="float")
        list_bound *= scale
        list_bound = np.round(list_bound).astype(np.int32)
        list_width = list_bound[2] - list_bound[0]
        list_height = list_bound[3] - list_bound[1]
        card_width = det_config["list"]["card"]["width"]
        card_width *= scale
        card_width = int(round(card_width))
        card_height = det_config["list"]["card"]["height"]
        card_height *= scale
        card_height = int(round(card_height))
        card_intervalx = int((list_width - card_width * list_col) / (list_col - 1))
        card_intervaly = int((list_height - card_height * list_row) / (list_row - 1))
        self._list_row = list_row
        self._list_col = list_col
        self._list_bound = list_bound
        self._list_width = list_width
        self._list_height = list_height
        self._card_width = card_width
        self._card_height = card_height
        self._card_intervalx = card_intervalx
        self._card_intervaly = card_intervaly

        return True

    def scan_artifacts(
        self,
        min_star: int,
        max_star: int,
        min_level: int,
        max_level: int,
        format: Literal["none", "mona", "yuanmo"],
        callback: Callable[..., None],
    ):
        if (
            min_star > max_star
            or min_level > max_level
            or min_star < 0
            or min_star > 5
            or max_star < 0
            or max_star > 5
            or min_level < 0
            or min_level > 20
            or max_level < 0
            or max_level > 20
        ):
            callback(code=ArtifactWarehouseHandler.CB_ERR_PARAM_INVALID)
            return

        hwnd = wm.switch_to_genshin()
        if hwnd == 0:
            callback(code=ArtifactWarehouseHandler.CB_ERR_SWITCH_FAILED)
            return

        sch = wm.ScreenshootHandler(hwnd)
        sch_height = sch.height
        sch_width = sch.width

        if self._detect_det_config(sch_width, sch_height) is False:
            callback(code=ArtifactWarehouseHandler.CB_ERR_CANNOT_FIND_DET_CONFIG)
            return

        img = sch.take()
        (count,) = self._infer.predict(img, self._count_bound)
        count = self._to_int(count)
        if count == -1:
            callback(code=ArtifactWarehouseHandler.CB_ERR_FIND_ARTIFACT_COUNT_FAILED)
            return
        else:
            callback(code=ArtifactWarehouseHandler.CB_INFO_ARTIFACTS_COUNT, count=count)

        winx, winy, _, _ = wm.get_client_frame(hwnd)

        # start scan
        # state diagram
        # begin_capture -> capturing -> scroll_next_page -> capturing -> end_capture
        action_begin = 100

        action_check_page_skippable = 200

        action_itr_start = 300
        action_itr_click_next = 301
        action_itr_rec = 302
        action_itr_capture_screenshoot = 303

        action_scroll_cards = 400
        action_scroll_next_page = 401

        action_end_by_ending = 600
        action_end_by_user = 601

        action = action_begin

        itr_rowi = 0
        itr_coli = 0
        artifacts = []

        mouse_x = 0
        mouse_y = 0

        scroll_to_end = False
        scroll_distances_of_list = 0
        scroll_card_num = 0
        scroll_anchor_l = self._list_bound[0]
        scroll_anchor_t = self._list_bound[1] - self._card_intervaly
        scroll_anchor_r = int(scroll_anchor_l + self._card_width * 0.3)
        scroll_anchor_b = int(scroll_anchor_t + self._card_intervaly * 0.5)
        scroll_anchor_img = img[
            scroll_anchor_t:scroll_anchor_b,
            scroll_anchor_l:scroll_anchor_r,
            :,
        ]

        while True:
            if action == action_begin:
                posx = self._info_bounds[0, 0] + winx
                posy = self._info_bounds[0, 1] + winy
                pyautogui.moveTo(posx, posy)

                for _ in range(3):
                    pyautogui.scroll(clicks=1)

                action = action_check_page_skippable

            elif action == action_check_page_skippable:
                first_x = self._list_bound[0] + winx + self._card_width // 2
                first_y = self._list_bound[1] + winy + self._card_height // 2

                pyautogui.click(first_x, first_y)
                time.sleep(0.05)
                img = sch.take()
                first_info = self._fetch_artifact_info(img)[0]

                if first_info["star"] <= 0 or first_info["level"] < 0:
                    action = action_itr_start
                    continue

                first_star_level = first_info["star"] * 100 + first_info["level"]

                if not scroll_to_end:
                    last_x = self._list_bound[2] + winx - self._card_width // 2
                    last_y = self._list_bound[3] + winy - self._card_height // 2

                    pyautogui.click(last_x, last_y)
                    time.sleep(0.05)
                    img = sch.take()
                    last_info = self._fetch_artifact_info(img)[0]

                    if last_info["star"] <= 0 or last_info["level"] < 0:
                        action = action_itr_start
                        continue

                    last_star_info = last_info["star"] * 100 + last_info["level"]
                else:
                    last_star_info = 0

                skip = True
                for star in range(min_star, max_star + 1):
                    for level in range(min_level, max_level + 1):
                        star_level = star * 100 + level
                        # print(
                        #     "awh.scanartifact check star_level: ",
                        #     star_level,
                        #     first_star_level,
                        #     last_star_info,
                        # )
                        if (
                            star_level <= first_star_level
                            and star_level >= last_star_info
                        ):
                            skip = False
                            break
                    if not skip:
                        break
                # print("awh.scanartifact check skip: ", skip)
                if skip:
                    end = min_star * 100 + min_level > first_star_level
                    if end:
                        action = action_end_by_ending
                    elif scroll_to_end:
                        action = action_end_by_ending
                    else:
                        action = action_scroll_next_page
                else:
                    action = action_itr_start

            elif action == action_scroll_cards:
                if abs(scroll_card_num) > 1 and scroll_distances_of_list > 0:
                    scroll_distances = (
                        scroll_distances_of_list
                        * (abs(scroll_card_num) - 0.5)
                        / self._list_row
                    )
                    scroll_distances = int(scroll_distances)

                    for _ in range(scroll_distances):
                        pyautogui.scroll(1 if scroll_card_num > 0 else -1, _pause=False)
                        time.sleep(0.01)
                    scroll_card_num = 1 if scroll_card_num > 0 else -1

                is_interval = True
                scroll_distances = 0
                update_scroll_distances_of_list = abs(scroll_card_num) == self._list_row
                before_img = None
                confidence_threshold = 0.8
                mouse_moved = False
                scroll_is_end = False

                while True:
                    mouse_x, mouse_y = pyautogui.position()

                    img = sch.take()
                    if before_img is not None:
                        confidence = cv2.matchTemplate(
                            img,
                            before_img,
                            cv2.TM_CCOEFF_NORMED,
                        )[0, 0]
                        if confidence > 0.95:
                            scroll_is_end = True
                            break

                    before_img = img
                    anchor_img = img[
                        scroll_anchor_t:scroll_anchor_b,
                        scroll_anchor_l:scroll_anchor_r,
                        :,
                    ]
                    confidence = cv2.matchTemplate(
                        anchor_img,
                        scroll_anchor_img,
                        cv2.TM_CCOEFF_NORMED,
                    )[0, 0]
                    # print("awh.scanartifact scroll confidence: ", confidence)

                    if confidence > confidence_threshold:
                        if not is_interval:
                            if scroll_card_num > 0:
                                scroll_card_num -= 1
                            else:
                                scroll_card_num += 1
                            is_interval = True
                    else:
                        if is_interval:
                            is_interval = False

                    if scroll_card_num == 0:
                        break

                    cur_mouse_x, cur_mouse_y = pyautogui.position()
                    if (
                        abs(cur_mouse_x - mouse_x) > 10
                        or abs(cur_mouse_y - mouse_y) > 10
                    ):
                        mouse_moved = True
                        break
                    # print("awh.scanartifact scroll: ", scroll_card_num)
                    pyautogui.scroll(1 if scroll_card_num > 0 else -1, _pause=False)
                    time.sleep(0.05)
                    scroll_distances += 1

                if update_scroll_distances_of_list and not scroll_is_end:
                    scroll_distances_of_list = scroll_distances

                if mouse_moved:
                    action = action_end_by_user
                elif scroll_is_end:
                    scroll_card_num = 1
                    scroll_to_end = True
                    action = action_scroll_cards
                else:
                    action = action_check_page_skippable
            elif action == action_scroll_next_page:
                scroll_card_num = -self._list_row
                action = action_scroll_cards

            elif action == action_itr_start:
                itr_rowi = 0
                itr_coli = -1
                action = action_itr_click_next
            elif action == action_itr_click_next:
                itr_coli += 1
                if itr_coli >= self._list_col:
                    itr_coli = 0
                    itr_rowi += 1
                if itr_rowi >= self._list_row:
                    action = action_scroll_next_page
                    continue

                x = (
                    self._list_bound[0]
                    + itr_coli * (self._card_intervalx + self._card_width)
                    + winx
                    + self._card_width // 2
                )
                y = (
                    self._list_bound[1]
                    + itr_rowi * (self._card_intervaly + self._card_height)
                    + winy
                    + self._card_height // 2
                )

                pyautogui.click(x, y, _pause=False)
                mouse_x = x
                mouse_y = y

                if itr_coli == 0 and itr_rowi == 0:
                    time.sleep(0.1)
                    action = action_itr_capture_screenshoot
                else:
                    action = action_itr_rec
            elif action == action_itr_capture_screenshoot:
                img = sch.take()
                if itr_coli == self._list_col - 1 and itr_rowi == self._list_row - 1:
                    action = action_itr_rec
                else:
                    action = action_itr_click_next
            elif action == action_itr_rec:
                artifact, raw_info = self._fetch_artifact_info(img)

                end = False
                if (
                    artifact["name"] == ""
                    or artifact["level"] < 0
                    or artifact["star"] < 0
                    or artifact["pos"] == ""
                    or artifact["main_attr"] == ""
                    or artifact["main_value"] < 0
                ):
                    callback(
                        code=ArtifactWarehouseHandler.CB_WARN_RECGNIZE_FAILED,
                        artifact=raw_info,
                    )
                else:
                    level = artifact["level"]
                    star = artifact["star"]
                    if (
                        star >= min_star
                        and star <= max_star
                        and level >= min_level
                        and level <= max_level
                    ):
                        artifacts.append(artifact)
                    if star <= min_star and level < min_level or star < min_star:
                        end = True

                if end:
                    action = action_end_by_ending
                    continue

                cur_mouse_x, cur_mouse_y = pyautogui.position()
                if abs(cur_mouse_y - mouse_y) > 10 or abs(cur_mouse_x - mouse_x) > 10:
                    action = action_end_by_user
                    continue

                if itr_coli == self._list_col - 1 and itr_rowi == self._list_row - 1:
                    action = action_scroll_next_page
                else:
                    action = action_itr_capture_screenshoot

            elif action == action_end_by_ending:
                artifacts = self._encode_artifacts(artifacts, format)
                callback(
                    code=ArtifactWarehouseHandler.CB_INFO_FINISH, artifacts=artifacts
                )
                break
            elif action == action_end_by_user:
                artifacts = self._encode_artifacts(artifacts, format)
                callback(
                    code=ArtifactWarehouseHandler.CB_ERR_INTERRUPT_BY_USER,
                    artifacts=artifacts,
                )
                break

    def _encode_artifacts(
        self, artifacts: list, format: Literal["mona", "yuanmo", "none"]
    ):
        match format:
            case "mona":
                return _encode_artifacts_mona(artifacts)
            case "yuanmo":
                return _encode_artifacts_yuanmo(artifacts)
            case "none":
                return artifacts

    def _fetch_artifact_info(self, img):
        info_list = self._infer.predict(img, self._info_bounds)
        pos = self._find_in_map(info_list[0], self._map_pos_zh)
        level = self._to_int(info_list[1])
        if level < 0 or level > 20:
            level = -1
        main_attr = self._find_in_map(info_list[2], self._map_attr_zh)
        main_value = self._to_float(info_list[3])
        if main_value < 1.0:
            if main_attr == "hp":
                main_attr = "hprate"
            elif main_attr == "atk":
                main_attr = "atkrate"
            elif main_attr == "def":
                main_attr = "defrate"
        star = self._to_star(info_list[4])

        if info_list[5].find("开的锁") >= 0:
            lock = 0
        elif info_list[5].find("关的锁") >= 0:
            lock = 1
        else:
            lock = -1

        equipper_match = re.search(r"(.*)已装备", info_list[6])
        if equipper_match:
            equipper = equipper_match.group(1)
        else:
            equipper = ""

        name = ""
        sub_attrs = []
        sub_values = []
        for i in range(7, len(info_list)):
            txt = info_list[i]
            if not name:
                name = self._find_in_map(txt, self._map_name_zh)
                if name:
                    continue

            sub_attr = self._find_in_map(txt, self._map_attr_zh)
            if sub_attr:
                sub_value = self._to_float(txt)
                if sub_value > 0.0:
                    if sub_value < 1.0:
                        if sub_attr == "hp":
                            sub_attr = "hprate"
                        elif sub_attr == "atk":
                            sub_attr = "atkrate"
                        elif sub_attr == "def":
                            sub_attr = "defrate"

                    sub_attrs.append(sub_attr)
                    sub_values.append(sub_value)

        artifact = {
            "name": name,
            "pos": pos,
            "star": star,
            "level": level,
            "lock": lock,
            "main_attr": main_attr,
            "main_value": main_value,
            "sub_attrs": sub_attrs,
            "sub_values": sub_values,
            "equipper": equipper,
        }
        return artifact, info_list
