from typing import Optional
import time
from PySide6.QtCore import QDir
import yaml
import os


class RuleListItem(object):
    yaml_tag = "!rule_list_item"

    def __init__(self) -> None:
        self.id: int = time.time_ns() // 1000_000
        self.name: str = ""

    @staticmethod
    def _constructor(loader, node):
        data = loader.construct_mapping(node)
        item = RuleListItem()
        item.id = int(data["id"])
        item.name = data["name"]
        return item

    @staticmethod
    def _representer(dumper, item: "RuleListItem"):
        data = {"id": item.id, "name": item.name}
        return dumper.represent_mapping(RuleListItem.yaml_tag, data)


yaml.add_representer(RuleListItem, RuleListItem._representer, yaml.SafeDumper)
yaml.add_constructor(RuleListItem.yaml_tag, RuleListItem._constructor, yaml.SafeLoader)


class RuleDataHandler(object):
    _instance: Optional["RuleDataHandler"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        self._cfg_dir = QDir("data:")
        if not self._cfg_dir.exists("./arrange"):
            self._cfg_dir.mkdir("arrange")
        self._cfg_dir.cd("arrange")

        self._cache_rule_list = None

    def _rule_list_path(self):
        return self._cfg_dir.absoluteFilePath("rule_list.yaml")

    def get_rule_list(self):
        if self._cache_rule_list is not None:
            return self._cache_rule_list

        path = self._rule_list_path()
        if not os.path.isfile(path):
            self._cache_rule_list = []
            return self._cache_rule_list.copy()

        with open(path, "r", encoding="utf8") as f:
            self._cache_rule_list = yaml.safe_load(f)

            if self._cache_rule_list is None:
                self._cache_rule_list = []

            return self._cache_rule_list.copy()

    def save_rule_list(self, rule_list: list[RuleListItem]):
        path = self._rule_list_path()
        with open(path, "w", encoding="utf8") as f:
            yaml.safe_dump(
                rule_list,
                f,
                encoding="utf8",
                allow_unicode=True,
            )
        self._cache_rule_list = rule_list.copy()

    def update_rule_name(self, id: int, name: str):
        if self._cache_rule_list is not None:
            rule_list = self._cache_rule_list
        else:
            rule_list = self.get_rule_list()

        for rule in rule_list:
            if rule.id == id:
                rule.name = name
                break

        path = self._rule_list_path()
        with open(path, "w", encoding="utf8") as f:
            yaml.safe_dump(
                rule_list,
                f,
                encoding="utf8",
                allow_unicode=True,
            )

    def _rule_content_path(self, id: int):
        return self._cfg_dir.absoluteFilePath(f"rule_{id}.yaml")

    def get_rule_content(self, id: int) -> Optional[dict]:
        path = self._rule_content_path(id)
        if not os.path.isfile(path):
            return None

        with open(path, "r", encoding="utf8") as f:
            return yaml.safe_load(f)

    def update_rule_content(self, id: int, content: dict):
        path = self._rule_content_path(id)

        with open(path, "w", encoding="utf8") as f:
            yaml.safe_dump(
                content,
                f,
                encoding="utf8",
                allow_unicode=True,
            )

    def delete_rule_content(self, id: int):
        path = self._rule_content_path(id)

        if os.path.isfile(path):
            os.remove(path)
