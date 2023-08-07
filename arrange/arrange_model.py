import os
import sys
import time
from enum import Enum
from typing import Optional

from PySide6.QtCore import QDir, QMetaMethod, QObject, Signal, Slot
from typing_extensions import override

from base.base_model import BaseModel
from widget import ranger

from base import artifact
from tools.stringresources import load_string
from .arrange_data import *


class RuleListModel(BaseModel):
    name_list = Signal(list)
    name_list_item_update = Signal(int, str)
    selected_index = Signal(int)

    def __init__(self, parent: BaseModel | None = None):
        super().__init__(parent)

        self._rule_data_handler = RuleDataHandler()
        self._is_dirty = False

        self._name_list: list[RuleListItem] = self._rule_data_handler.get_rule_list()
        self._selected_index = -1

    def get_name_list(self) -> list[RuleListItem]:
        return self._name_list

    def get_selected_index(self) -> int:
        return self._selected_index

    def select_item(self, index: int):
        if self._selected_index == index:
            return

        self._selected_index = index
        self.selected_index.emit(self._selected_index)

    def add_new_rule(self):
        new_item = RuleListItem()
        new_item.name = load_string("new_rule")
        self._name_list.insert(0, new_item)
        self._selected_index = 0

        self._is_dirty = True

        self.name_list.emit(self._name_list)
        self.selected_index.emit(self._selected_index)

    def delete_selected_rule(self):
        if self._selected_index < 0:
            return

        if self._selected_index >= len(self._name_list):
            return

        item = self._name_list.pop(self._selected_index)
        self._selected_index = -1

        self._is_dirty = True
        RuleDataHandler().delete_rule_content(item.id)

        self.selected_index.emit(self._selected_index)
        self.name_list.emit(self._name_list)

    def update_name(self, index: int, name: str):
        if len(self._name_list) < index or index < 0:
            return

        item = self._name_list[index]
        item.name = name

        self._is_dirty = True

        self.name_list_item_update.emit(index, name)

    def update_selected_name(self, name: str):
        self.update_name(self._selected_index, name)

    @override
    def on_close(self):
        if self._is_dirty:
            self._rule_data_handler.save_rule_list(self._name_list)
            self._is_dirty = False

        self.name_list.disconnect()
        self.name_list_item_update.disconnect()
        self.selected_index.disconnect()


class Statement(BaseModel):
    def init_data(self, represent: dict):
        pass

    def represent(self) -> Optional[dict]:
        pass


class FilterStatement(Statement):
    statement_deleted = Signal(Statement)

    def delete_statement(self):
        self.statement_deleted.emit(self)

    def on_close(self):
        super().on_close()
        self.statement_deleted.disconnect()


class ArtifactStarStatement(FilterStatement):
    five_star = Signal(bool)
    four_star = Signal(bool)

    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._four_star = True
        self._five_star = True

    @override
    def represent(self):
        return {
            "type": ArtifactStarStatement.__name__,
            "five_star": self._five_star,
            "four_star": self._four_star,
        }

    @override
    def init_data(self, represent: dict):
        five_star = represent.get("five_star", None)
        if five_star is not None:
            self.set_five_star(five_star)

        four_star = represent.get("four_star", None)
        if four_star is not None:
            self.set_four_star(four_star)

    def get_four_star(self) -> bool:
        return self._four_star

    def set_four_star(self, value: bool):
        if self._four_star == value:
            return

        self._four_star = value
        self.four_star.emit(value)

    def get_five_star(self) -> bool:
        return self._five_star

    def set_five_star(self, value: bool):
        if self._five_star == value:
            return

        self._five_star = value
        self.five_star.emit(value)

    @override
    def on_close(self):
        super().on_close()

        self.five_star.disconnect()
        self.four_star.disconnect()


class ArtifactLevelStatement(FilterStatement):
    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._min_level = 0
        self._max_level = 20

    @override
    def init_data(self, represent: dict):
        self._min_level = represent["min_level"]
        self._max_level = represent["max_level"]

    @override
    def represent(self) -> dict:
        return {
            "type": "ArtifactLevelStatement",
            "min_level": self._min_level,
            "max_level": self._max_level,
        }

    def get_min_level(self):
        return self._min_level

    def set_min_level(self, value: int):
        if self._min_level == value:
            return

        self._min_level = value

    def get_max_level(self):
        return self._max_level

    def set_max_level(self, value: int):
        if self._max_level == value:
            return

        self._max_level = value


class ArtifactLockStatement(FilterStatement):
    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._lock = True
        self._unclok = True

    @override
    def init_data(self, represent: dict):
        self._lock = represent["lock"]
        self._unclok = represent["unlock"]

    @override
    def represent(self) -> dict:
        return {
            "type": "ArtifactLockStatement",
            "lock": self._lock,
            "unlock": self._unclok,
        }

    def get_lock(self):
        return self._lock

    def set_lock(self, value: bool):
        if self._lock == value:
            return

        self._lock = value

    def get_unlock(self):
        return self._unclok

    def set_unlock(self, value: bool):
        if self._unclok == value:
            return

        self._unclok = value


class ArtifactNameStatement(FilterStatement):
    filter_ids = Signal(list)

    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._avaliable_ids: list[str] = artifact.Aritifacts_Id.copy()
        self._filter_ids: list[str] = list()

    @override
    def init_data(self, represent: dict):
        represent_filter_ids = represent["filter_ids"]
        for represent_filter_id in represent_filter_ids:
            self.add_filter_id(represent_filter_id)

    @override
    def represent(self) -> dict:
        return {
            "type": "ArtifactNameStatement",
            "filter_ids": self._filter_ids,
        }

    def get_avaliable_ids(self):
        return self._avaliable_ids

    def get_filter_ids(self):
        return self._filter_ids

    def add_filter_id(self, id: str):
        if id in self._filter_ids:
            return

        self._filter_ids.append(id)
        self.filter_ids.emit(self._filter_ids)

    def remove_filter_id(self, id: str):
        if id not in self._filter_ids:
            return

        self._filter_ids.remove(id)
        self.filter_ids.emit(self._filter_ids)

    def on_close(self):
        super().on_close()
        self.filter_ids.disconnect()


class AttributeItem(Statement):
    item_deleted = Signal(str)

    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self.id: str = ""

        self._min = 0.0
        self._max = 0.0

        self._default_min = 0.0
        self._default_max = 100.0

    @override
    def init_data(self, represent: dict):
        self.id = represent["id"]
        self._min = represent["min"]
        self._max = represent["max"]

    @override
    def represent(self) -> dict:
        return {
            "type": "AttributeItem",
            "id": self.id,
            "min": self._min,
            "max": self._max,
        }

    def set_min(self, value: float):
        if self._min == self._round(value):
            return
        self._min = self._round(value)

    def get_min(self):
        return self._min

    def set_max(self, value: float):
        if self._max == self._round(value):
            return
        self._max = self._round(value)

    def get_max(self):
        return self._max

    def set_default_min(self, value: float):
        self._default_min = self._round(value)

    def get_default_min(self):
        return self._default_min

    def set_default_max(self, value: float):
        self._default_max = self._round(value)

    def get_default_max(self):
        return self._default_max

    def _round(self, value):
        return round(value, 5)

    def delete(self):
        self.item_deleted.emit(self.id)

    def on_close(self):
        super().on_close()
        self.item_deleted.disconnect()


class AttributeStatement(FilterStatement):
    attr_items = Signal(list)

    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._avaliable_ids = []
        self._attributes_value_range = {}
        self._attr_items: list[AttributeItem] = []

    @override
    def init_data(self, represent: dict):
        represent_attr_items = represent["attr_items"]
        for represent_attr_item in represent_attr_items:
            self.add_attr_id(represent_attr_item["id"])
            attr_item = self._attr_items[-1]
            attr_item.init_data(represent_attr_item)

    @override
    def represent(self) -> dict:
        represent_attr_items = []
        for attr_item in self._attr_items:
            represent_attr_item = attr_item.represent()
            represent_attr_items.append(represent_attr_item)

        return {
            "type": type(self).__name__,
            "attr_items": represent_attr_items,
        }

    def get_avaliable_ids(self):
        return self._avaliable_ids

    def get_attr_items(self):
        return self._attr_items

    def add_attr_id(self, id: str):
        for item in self._attr_items:
            if item.id == id:
                return

        item = AttributeItem(self)
        item.id = id
        min, max = self._attributes_value_range[id]
        item.set_default_min(min)
        item.set_default_max(max)
        item.set_min(min)
        item.set_max(max)

        item.item_deleted.connect(self.remove_attr_id)

        self._attr_items.append(item)
        self.attr_items.emit(self._attr_items)

    def remove_attr_id(self, id: str):
        for idx, item in enumerate(self._attr_items):
            if item.id == id:
                index = idx
                break
        else:
            return

        item = self._attr_items.pop(index)
        item.close()
        item.deleteLater()

        self._avaliable_ids.append(id)
        self.attr_items.emit(self._attr_items)

    def on_close(self):
        super().on_close()
        self.attr_items.disconnect()


class MainAttributeStatement(AttributeStatement):
    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)
        self._avaliable_ids = artifact.Main_Attributes_Id
        self._attributes_value_range = artifact.Main_Attributes_Value_Range


class SubAttributeStatement(AttributeStatement):
    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)
        self._avaliable_ids = artifact.Subattributes_Id
        self._attributes_value_range = artifact.SubAttributes_Value_Range


_filter_statement_types: list[type[FilterStatement]] = [
    ArtifactNameStatement,
    ArtifactStarStatement,
    ArtifactLevelStatement,
    MainAttributeStatement,
    SubAttributeStatement,
    ArtifactLockStatement,
]


class AddStatement(Statement):
    statement_types: list[type[FilterStatement]] = _filter_statement_types

    statement_added = Signal(Statement, type)

    def add_statement(self, statement_type: type[FilterStatement]):
        self.statement_added.emit(self, statement_type)

    @override
    def represent(self) -> Optional[dict]:
        return {"type": "AddStatement"}


class OptStatement(Statement):
    Opt_None = 0
    Opt_And = 1
    Opt_Or = 2

    statement_types: list[type[FilterStatement]] = _filter_statement_types

    statement_added = Signal(Statement, int, type)
    opt = Signal(int)

    def __init__(self, parent: BaseModel | None = None) -> None:
        super().__init__(parent)

        self._opt = self.Opt_None

    def add_statement(self, opt: int, type: type[FilterStatement]):
        self.statement_added.emit(self, opt, type)

    def get_opt(self) -> int:
        return self._opt

    def set_opt(self, opt: int):
        if self._opt == opt:
            return

        self._opt = opt
        self.opt.emit(opt)

    @override
    def on_close(self):
        self.statement_added.disconnect()
        if self._opt != self.Opt_None:
            self.opt.disconnect()

    @override
    def init_data(self, represent: dict):
        self._opt = represent["opt"]

    @override
    def represent(self) -> dict:
        return {
            "type": "OptStatement",
            "opt": self._opt,
        }


class RuleDetailModel(BaseModel):
    name = Signal(str)
    delete_rule_clicked = Signal()

    statements_reset = Signal(list)
    statement_added = Signal(int, Statement)
    statement_deled = Signal(int)

    def __init__(self, id, parent: BaseModel | None = None):
        super().__init__(parent)
        self.id = id

        self._name = ""

        self._statements: list[Statement] = []
        self._should_save = True
        self._init_data()

    def _save_represent(self):
        statement_presenters = []
        for statement in self._statements:
            statement_represent = statement.represent()
            if statement_represent:
                statement_presenters.append(statement_represent)

        represent_data = {
            "statements": statement_presenters,
        }
        RuleDataHandler().update_rule_content(self.id, represent_data)

    def _init_data(self):
        data = RuleDataHandler().get_rule_content(self.id)
        if data and "statements" in data and len(data["statements"]):
            statement_representers = data["statements"]

            module_obj = sys.modules[__name__]
            for statement_representer in statement_representers:
                statemnt_type = statement_representer["type"]
                statement_class = getattr(module_obj, statemnt_type)

                if statement_class is AddStatement:
                    statement = self._build_add_statement()
                elif statement_class is OptStatement:
                    statement = self._build_opt_statement(statement_representer["opt"])
                elif issubclass(statement_class, FilterStatement):
                    statement = self._build_filter_statement(statement_class)
                    statement.init_data(statement_representer)
                else:
                    raise NotImplementedError(f"Unknown type {statemnt_type}")
                self._statements.append(statement)
        else:
            add_statement = self._build_add_statement()
            self._statements.append(add_statement)

    def get_name(self):
        return self._name

    def set_name(self, name: str):
        if name == self._name:
            return

        self._name = name
        self.name.emit(self._name)

    def delete_rule(self):
        self._should_save = False
        self.delete_rule_clicked.emit()

    def get_statements(self):
        return self._statements

    @Slot()
    def _add_statement(
        self,
        sender: Statement,
        opt: int,
        statement_type: type[FilterStatement],
    ):
        index = -1
        for i, statement in enumerate(self._statements):
            if statement is sender:
                index = i
                break

        assert index >= 0

        if (
            index == 0
            and len(self._statements) == 1
            and isinstance(sender, AddStatement)
        ):
            # only have 1 statement and the statement is AddStatement,
            statement = self._statements.pop(0)
            statement.close()
            statement.deleteLater()

            statement = self._build_filter_statement(statement_type)
            self._statements.append(statement)

            statement = self._build_opt_statement(opt)
            self._statements.append(statement)

            self.statements_reset.emit(self._statements)
        elif isinstance(sender, OptStatement) and opt != OptStatement.Opt_None:
            statement = self._build_filter_statement(statement_type)
            self._statements.insert(index, statement)
            self.statement_added.emit(index, statement)

            statement = self._build_opt_statement(opt)
            self._statements.insert(index, statement)
            self.statement_added.emit(index, statement)
        else:
            raise NotImplementedError()

    @Slot()
    def _del_statement(self, sender: Statement):
        assert not isinstance(
            sender,
            AddStatement,
        ) and not isinstance(
            sender,
            OptStatement,
        )

        index = -1
        for i, statement in enumerate(self._statements):
            if statement is sender:
                index = i
                break

        assert index >= 0

        if index == 0:
            if len(self._statements) == 2:
                statement = self._statements.pop(0)
                statement.close()
                statement.deleteLater()
                statement = self._statements.pop(0)
                statement.close()
                statement.deleteLater()

                self._statements.append(self._build_add_statement())
                self.statements_reset.emit(self._statements)
            else:
                statement = self._statements.pop(0)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(0)

                statement = self._statements.pop(0)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(0)
        elif index == len(self._statements) - 2:
            statement = self._statements.pop(index)
            statement.close()
            statement.deleteLater()
            self.statement_deled.emit(index)

            statement = self._statements.pop(index - 1)
            statement.close()
            statement.deleteLater()
            self.statement_deled.emit(index - 1)
        elif (
            index != 0
            and index < len(self._statements) - 2
            and isinstance(self._statements[index - 1], OptStatement)
            and isinstance(self._statements[index + 1], OptStatement)
        ):
            pre_opt = self._statements[index - 1]
            assert isinstance(pre_opt, OptStatement)
            next_opt = self._statements[index + 1]
            assert isinstance(next_opt, OptStatement)

            if (
                pre_opt.get_opt() is OptStatement.Opt_And
                and next_opt.get_opt() is OptStatement.Opt_Or
            ):
                statement = self._statements.pop(index)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(index)

                statement = self._statements.pop(index - 1)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(index - 1)
            else:
                statement = self._statements.pop(index)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(index)

                statement = self._statements.pop(index)
                statement.close()
                statement.deleteLater()
                self.statement_deled.emit(index)
        else:
            raise NotImplementedError(
                f"cannot delete statement {type(sender).__name__}"
            )

    def _build_add_statement(self):
        add_statement = AddStatement(self)
        add_statement.statement_added.connect(
            lambda sender, type: self._add_statement(
                sender, OptStatement.Opt_None, type
            )
        )
        return add_statement

    def _build_opt_statement(self, opt):
        opt_statement = OptStatement(self)
        opt_statement.set_opt(opt)
        opt_statement.statement_added.connect(self._add_statement)
        return opt_statement

    def _build_filter_statement(self, statement_type: type[FilterStatement]):
        statement = statement_type(self)
        statement.statement_deleted.connect(self._del_statement)
        return statement

    @override
    def on_close(self):
        # if self.isSignalConnected(QMetaMethod.fromSignal(self.name)):
        if self._should_save:
            self._save_represent()
        self.name.disconnect()
        self.delete_rule_clicked.disconnect()

        self.statements_reset.disconnect()
        self.statement_added.disconnect()
        self.statement_deled.disconnect()


class ArrangeModel(BaseModel):
    detail_model = Signal(RuleDetailModel)

    def __init__(self, parent: BaseModel | None = None):
        super().__init__(parent)

        self._list_model = RuleListModel(self)
        self._detail_model = None

        self._bind_detail_and_list_model()

    def get_list_model(self) -> RuleListModel:
        return self._list_model

    def get_detail_model(self) -> Optional[RuleDetailModel]:
        return self._detail_model

    def _bind_detail_and_list_model(self):
        name_list = self._list_model.get_name_list()
        if name_list and len(name_list) > 0:
            self._list_model.select_item(0)
            self._event_selected_index_changed(0)
        self._list_model.selected_index.connect(self._event_selected_index_changed)

    def _del_detail_model(self):
        if self._detail_model is None:
            return

        self._detail_model.close()
        self._detail_model.deleteLater()
        self._detail_model = None

    def _new_detail_model(self, id, name):
        self._del_detail_model()

        self._detail_model = RuleDetailModel(id, self)
        self._detail_model.set_name(name)

        self._detail_model.delete_rule_clicked.connect(
            lambda: self._list_model.delete_selected_rule()
        )
        self._detail_model.name.connect(
            lambda name: self._list_model.update_selected_name(name)
        )
        self._list_model.name_list_item_update.connect(
            lambda index, name: self._list_model.get_selected_index() == index
            and self._detail_model
            and self._detail_model.set_name(name)
        )

    @Slot(int)
    def _event_selected_index_changed(self, index: int):
        if len(self._list_model.get_name_list()) < index or index < 0:
            if self._detail_model is not None:
                self._del_detail_model()
                self.detail_model.emit(self._detail_model)
        else:
            rule_list_item = self._list_model.get_name_list()[index]
            if self._detail_model is None or self._detail_model.id != rule_list_item.id:
                self._new_detail_model(rule_list_item.id, rule_list_item.name)
                self.detail_model.emit(self._detail_model)
