from typing import Optional

from PySide6.QtCore import (
    QDir,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    QRect,
    QSize,
    QStringListModel,
    Qt,
    QTimer,
    Slot,
)
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QDoubleValidator,
    QFontMetrics,
    QIcon,
    QIntValidator,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QLineEdit,
    QListView,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from typing_extensions import override

from tools.stringresources import load_string
from widget import FlowLayout, LogView, Ranger
from .arrange_data import RuleListItem
from .arrange_model import *

_style = """
QWidget#statement_box {
    border-radius: 3px; 
    border-color: gray;
    border-width: 0px; 
    border-style: solid;
    background-color: #ffffff;
    background-clip: content-box;
}

QMenu::item:!enabled {
    opacity: 0.5;
    color: #808080;
}
"""


class RuleListView(QWidget):
    def __init__(
        self,
        model: RuleListModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._init_layout()

    def _init_layout(self):
        self._add_btn = QPushButton(load_string("create_new_rule"))
        self._add_btn.clicked.connect(self._model.add_new_rule)

        self._list_view = QListView()
        self._list_view.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._list_view_model = QStringListModel()
        self._event_list_changed(self._model.get_name_list())
        self._list_view.setModel(self._list_view_model)
        self._list_view_model.dataChanged.connect(self._notify_list_changed)
        self._event_index_selected(self._model.get_selected_index())
        self._list_view.selectionModel().selectionChanged.connect(
            self._notify_index_selected
        )
        self._model.name_list_item_update.connect(self._event_list_item_update)
        self._model.name_list.connect(self._event_list_changed)
        self._model.selected_index.connect(self._event_index_selected)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self._add_btn)
        layout.addWidget(self._list_view, stretch=1)

        self.setLayout(layout)

    @Slot(QModelIndex, QModelIndex)
    def _notify_list_changed(self, top: QModelIndex, bottom: QModelIndex):
        for i in range(top.row(), bottom.row() + 1):
            new_name = self._list_view_model.index(i, 0).data()
            self._model.update_name(i, new_name)

    @Slot(list)
    def _event_list_changed(self, data: list[RuleListItem]):
        names = [item.name for item in data]
        self._list_view_model.setStringList(names)

    @Slot(int, str)
    def _event_list_item_update(self, index: int, name: str):
        i = self._list_view_model.index(index, 0)
        if i.data() == name:
            return

        self._list_view_model.setData(i, name)

    @Slot(QItemSelection, QItemSelection)
    def _notify_index_selected(
        self,
        selected: QItemSelection,
        deselected: QItemSelection,
    ):
        indexes = selected.indexes()
        assert len(indexes) == 1
        index = indexes[0].row()

        if self._model.get_selected_index() == index:
            return

        self._model.select_item(index)

    @Slot()
    def _event_index_selected(self, index: int):
        selection_model = self._list_view.selectionModel()

        if index < 0:
            selection_model.clearCurrentIndex()
            return

        selection = selection_model.selection()
        if selection and len(selection.indexes()):
            cur_select_index = selection.indexes()[0].row()
            if cur_select_index == index:
                return

        selection_model.setCurrentIndex(
            self._list_view_model.index(index, 0),
            QItemSelectionModel.SelectionFlag.ClearAndSelect,
        )


class RuleDetialView(QWidget):
    def __init__(
        self,
        model: RuleDetailModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model
        self._init_layout()

    def _init_layout(self):
        self._title = QLineEdit()
        self._title.setText(self._model.get_name())
        self._title.textChanged.connect(self._model.set_name)
        self._model.name.connect(self._event_set_title)

        trash_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_MessageBoxCritical
        )
        self._trash_btn = QPushButton()
        self._trash_btn.setIcon(trash_icon)
        self._trash_btn.setText(load_string("delete_rule"))
        self._trash_btn.clicked.connect(self._model.delete_rule)

        title_layout = QHBoxLayout()
        title_layout.addWidget(self._title, stretch=1)
        title_layout.addSpacing(8)
        title_layout.addWidget(self._trash_btn)

        self._content_layout = QVBoxLayout()
        self._event_reset_layout(self._model.get_statements())
        self._model.statements_reset.connect(self._event_reset_layout)
        self._model.statement_added.connect(self._event_add_statement)
        self._model.statement_deled.connect(self._event_del_statement)

        content = QWidget()
        content.setLayout(self._content_layout)
        scroll_area = QScrollArea()
        scroll_area.setWidget(content)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_layout = QVBoxLayout()
        scroll_layout.setSpacing(0)
        scroll_layout.addWidget(scroll_area)

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addLayout(title_layout)
        layout.addLayout(scroll_layout, stretch=1)

        self.setLayout(layout)

    def _delete_item_recursively(
        self, layout_item: Optional[QLayoutItem], delete_self=True
    ):
        if not isinstance(layout_item, QLayoutItem):
            return

        if layout_item.widget():
            if delete_self:
                widget = layout_item.widget()
                widget.deleteLater()
                del widget
        elif layout_item.layout():
            layout = layout_item.layout()
            item = layout.takeAt(0)
            while item:
                self._delete_item_recursively(item, True)
                item = layout.takeAt(0)
            if delete_self:
                layout.deleteLater()
                del layout

    @Slot(str)
    def _event_set_title(self, name):
        if name != self._title.text():
            self._title.setText(name)

    @Slot()
    def _event_reset_layout(self, statements: list[Statement]):
        self._delete_item_recursively(self._content_layout, False)

        for statement in statements:
            container = self._statement_container(statement)
            if isinstance(container, QLayout):
                self._content_layout.addLayout(container, stretch=0)
            else:
                self._content_layout.addWidget(container, stretch=0)

        strech = QWidget()
        self._content_layout.addWidget(strech, stretch=1)

    @Slot()
    def _event_add_statement(self, idx: int, statement: Statement):
        container = self._statement_container(statement)
        if isinstance(container, QLayout):
            self._content_layout.insertLayout(idx, container, stretch=0)
        else:
            self._content_layout.insertWidget(idx, container, stretch=0)

    @Slot()
    def _event_del_statement(self, idx: int):
        item = self._content_layout.takeAt(idx)
        self._delete_item_recursively(item, True)

    def _statement_container(self, statement: Statement):
        if isinstance(statement, AddStatement):
            return self._add_statement_layout(statement)
        elif isinstance(statement, OptStatement):
            return self._opt_statement_layout(statement)
        elif isinstance(statement, ArtifactStarStatement):
            return self._artifact_star_layout(statement)
        elif isinstance(statement, ArtifactLockStatement):
            return self._artifact_lock_layout(statement)
        elif isinstance(statement, ArtifactLevelStatement):
            return self._artifact_level_layout(statement)
        elif isinstance(statement, ArtifactNameStatement):
            return self._artifact_name_layout(statement)
        elif isinstance(statement, AttributeStatement):
            return self._attribute_layout(statement)
        else:
            raise NotImplementedError(f"cannot build container for {statement}")

    def _add_statement_layout(self, statement: AddStatement):
        menu = QMenu(self)
        for statement_type in statement.statement_types:
            item_name = load_string(statement_type.__name__)
            action = QAction(item_name, menu)
            menu.addAction(action)
            action.triggered.connect(
                (lambda st: lambda: statement.add_statement(st))(statement_type)
            )

        btn = QToolButton()
        btn.setText(load_string("new_statement"))
        btn.setMenu(menu)
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        layout = QHBoxLayout()
        layout.addWidget(btn)
        layout.addStretch(1)

        return layout

    def _opt_statement_layout(self, statement: OptStatement):
        and_menu = QMenu(self)
        and_menu.setTitle(load_string("new_and_statement"))
        for statement_type in statement.statement_types:
            item_name = load_string(statement_type.__name__)
            action = QAction(item_name, self)
            and_menu.addAction(action)
            action.triggered.connect(
                (
                    lambda st: lambda: statement.add_statement(
                        OptStatement.Opt_And,
                        st,
                    )
                )(statement_type)
            )

        or_menu = QMenu(self)
        or_menu.setTitle(load_string("new_or_statement"))
        for statement_type in statement.statement_types:
            item_name = load_string(statement_type.__name__)
            action = QAction(item_name, self)
            or_menu.addAction(action)
            action.triggered.connect(
                (
                    lambda st: lambda: statement.add_statement(
                        OptStatement.Opt_Or,
                        st,
                    )
                )(statement_type)
            )

        add_menu = QMenu(self)
        add_menu.addMenu(and_menu)
        add_menu.addMenu(or_menu)

        add_btn = QToolButton()
        add_btn.setText(load_string("new_statement"))
        add_btn.setMenu(add_menu)
        add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        if statement.get_opt():
            opt_box = QComboBox()
            opt_box.addItem(load_string("opt_and"))
            opt_box.addItem(load_string("opt_or"))

            opt_index = statement.get_opt() - 1
            opt_box.setCurrentIndex(opt_index)
            opt_box.currentIndexChanged.connect(
                lambda index: statement.set_opt(index + 1)
            )
            statement.opt.connect(lambda opt: opt_box.setCurrentIndex(opt - 1))

            layout = QHBoxLayout()
            layout.addWidget(opt_box)
            layout.addWidget(add_btn)
            layout.addStretch()

        else:
            layout = QHBoxLayout()
            layout.addWidget(add_btn)
            layout.addStretch()

        return layout

    def _artifact_star_layout(self, statement: ArtifactStarStatement):
        title = QLabel(load_string("star_level"))

        five_star = QCheckBox()
        five_star.setText(load_string("five_star"))
        five_star.setChecked(statement.get_five_star())
        five_star.stateChanged.connect(lambda state: statement.set_five_star(state > 0))
        statement.five_star.connect(five_star.setChecked)

        four_star = QCheckBox()
        four_star.setText(load_string("four_star"))
        four_star.setChecked(statement.get_four_star())
        four_star.stateChanged.connect(lambda state: statement.set_four_star(state > 0))
        statement.four_star.connect(four_star.setChecked)

        delete_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton
        )
        delete = QPushButton()
        delete.setIcon(delete_icon)
        delete.clicked.connect(statement.delete_statement)

        layout = QHBoxLayout()
        layout.addWidget(title)
        layout.addWidget(five_star)
        layout.addWidget(four_star)
        layout.addStretch(1)
        layout.addWidget(delete)

        frame = QWidget()
        frame.setObjectName("statement_box")
        frame.setLayout(layout)

        return frame

    def _artifact_lock_layout(self, statement: ArtifactLockStatement):
        title = QLabel(load_string("lock_state"))

        lock = QCheckBox()
        lock.setText(load_string("lock"))
        lock.setChecked(statement.get_lock())
        lock.stateChanged.connect(lambda state: statement.set_lock(state > 0))

        unlock = QCheckBox()
        unlock.setText(load_string("unlock"))
        unlock.setChecked(statement.get_unlock())
        unlock.stateChanged.connect(lambda state: statement.set_unlock(state > 0))

        delete_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton
        )
        delete = QPushButton()
        delete.setIcon(delete_icon)
        delete.clicked.connect(statement.delete_statement)

        layout = QHBoxLayout()
        layout.addWidget(title)
        layout.addWidget(lock)
        layout.addWidget(unlock)
        layout.addStretch(1)
        layout.addWidget(delete)

        frame = QWidget()
        frame.setObjectName("statement_box")
        frame.setLayout(layout)

        return frame

    def _artifact_level_layout(self, statement: ArtifactLevelStatement):
        title = QLabel(load_string("level_range"))

        ranger = Ranger()
        ranger.set_title(load_string("level_range"))
        ranger.set_range(statement.get_min_level(), statement.get_max_level())
        ranger.set_placeholder(0, 20)
        ranger.set_input_width(6)
        ranger.set_validator(QIntValidator())

        def level_change(setter, defaul_value):
            @Slot()
            def inner(new_value):
                new_value = new_value.replace(",", "")
                new_value = int(new_value) if new_value else defaul_value
                setter(new_value)

            return inner

        ranger.min_text_edited.connect(level_change(statement.set_min_level, 0))
        ranger.max_text_edited.connect(level_change(statement.set_max_level, 20))

        delete_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton
        )
        delete = QPushButton()
        delete.setIcon(delete_icon)
        delete.clicked.connect(statement.delete_statement)

        layout = QHBoxLayout()
        layout.addWidget(title)
        layout.addWidget(ranger)
        layout.addStretch(1)
        layout.addWidget(delete)

        frame = QWidget()
        frame.setObjectName("statement_box")
        frame.setLayout(layout)

        return frame

    def _artifact_name_layout(self, statement: ArtifactNameStatement):
        title = QLabel(load_string("title_artifact_name"))

        avaliable_ids_menu = QMenu(self)
        for id in statement.get_avaliable_ids():
            action = QAction(load_string(id), self)
            action.setObjectName(id)
            action.triggered.connect(
                (lambda id: lambda: statement.add_filter_id(id))(id)
            )
            avaliable_ids_menu.addAction(action)

        add_btn = QToolButton()
        add_btn.setText(load_string("add_filter_artifact"))
        add_btn.setMenu(avaliable_ids_menu)
        add_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        flowlayout = FlowLayout()
        flowlayout.addWidget(add_btn)

        def event_filter_ids_update(filter_ids):
            idx = 0

            def notifiy_remove_filter_id(item_label: QLabel):
                def inner():
                    statement.remove_filter_id(item_label.objectName())

                return inner

            while idx < len(filter_ids):
                filter_id = filter_ids[idx]
                if idx < flowlayout.count() - 1:
                    item = flowlayout.itemAt(idx)
                    assert item
                    item_frame = item.widget()
                    item_label = item_frame.findChildren(QLabel)[0]
                    assert isinstance(item_label, QLabel)
                    item_label.setObjectName(filter_id)
                    item_label.setText(load_string(filter_id))
                else:
                    item_label = QLabel()
                    item_label.setObjectName(filter_id)
                    item_label.setText(load_string(filter_id))
                    item_remove_icon = self.style().standardIcon(
                        QStyle.StandardPixmap.SP_TitleBarCloseButton
                    )
                    item_remove_btn = QPushButton()
                    item_remove_btn.setIcon(item_remove_icon)
                    item_remove_btn.clicked.connect(
                        notifiy_remove_filter_id(item_label)
                    )
                    item_remove_btn.setFixedSize(12, 12)
                    item_remove_btn.setIconSize(
                        item_remove_btn.rect().size() - QSize(3, 3)
                    )

                    item_layout = QHBoxLayout()
                    item_layout.setContentsMargins(8, 2, 8, 2)
                    item_layout.addWidget(item_label)
                    item_layout.addWidget(item_remove_btn)

                    item_frame = QFrame()
                    item_frame.setFrameShape(QFrame.Shape.Box)
                    item_frame.setFrameShadow(QFrame.Shadow.Plain)
                    item_frame.setLineWidth(1)
                    item_frame.setMidLineWidth(0)
                    item_frame.setLayout(item_layout)
                    item_frame.setContentsMargins(1, 1, 1, 1)

                    flowlayout.insertWidget(flowlayout.count() - 1, item_frame)

                idx += 1

            while idx < flowlayout.count() - 1:
                item = flowlayout.takeAt(idx)
                self._delete_item_recursively(item, True)

            # update avaliable menu
            actions = avaliable_ids_menu.actions()
            for action in actions:
                action_id = action.objectName()
                if action_id in filter_ids:
                    action.setEnabled(False)
                else:
                    action.setEnabled(True)

        event_filter_ids_update(statement.get_filter_ids())
        statement.filter_ids.connect(event_filter_ids_update)

        delete_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton
        )
        delete = QPushButton()
        delete.setIcon(delete_icon)
        delete.clicked.connect(statement.delete_statement)

        hlayout = QHBoxLayout()
        hlayout.addWidget(title, alignment=Qt.AlignmentFlag.AlignTop)
        hlayout.addLayout(flowlayout, stretch=1)
        hlayout.addWidget(delete, alignment=Qt.AlignmentFlag.AlignTop)

        frame = QWidget()
        frame.setObjectName("statement_box")
        frame.setLayout(hlayout)
        return frame

    def _attribute_layout(self, statement: AttributeStatement):
        title = QLabel(load_string(type(statement).__name__))

        add_menu = QMenu(self)
        for id in statement.get_avaliable_ids():
            action = QAction(load_string(id), self)
            action.triggered.connect((lambda id: lambda: statement.add_attr_id(id))(id))
            action.setObjectName(id)
            add_menu.addAction(action)

        add_item = QToolButton()
        add_item.setText(load_string("add_attribute"))
        add_item.setMenu(add_menu)
        add_item.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        attrs_layout = QVBoxLayout()
        attrs_layout.addWidget(add_item)
        attrs_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        def event_filter_items_updated(attr_items: list[AttributeItem]):
            idx = 0

            attr_item_size = len(attr_items)
            layout_item_size = attrs_layout.count() - 1
            while idx < min(attr_item_size, layout_item_size):
                item = attr_items[idx]
                layout_item = attrs_layout.itemAt(idx)

                if layout_item.layout().objectName() != item.id:
                    break

                idx += 1

            # delete all layout item after idx
            del_count = layout_item_size - idx
            for _ in range(del_count):
                layout_item = attrs_layout.takeAt(idx)
                self._delete_item_recursively(layout_item, True)

            # build new layout item for remaining item
            while idx < attr_item_size:
                item: AttributeItem = attr_items[idx]

                attr_ranger = Ranger()
                attr_ranger.set_title(load_string(item.id))
                attr_ranger.set_range(item.get_min(), item.get_max())
                attr_ranger.set_placeholder(
                    item.get_default_min(), item.get_default_max()
                )
                attr_ranger.set_input_width(8)
                attr_ranger.set_validator(QDoubleValidator())

                def attr_ranger_change(item: AttributeItem, set_min):
                    @Slot()
                    def inner(new_value):
                        new_value = new_value.replace(",", "").strip()
                        if new_value == "":
                            if set_min:
                                new_value = item.get_default_min()
                            else:
                                new_value = item.get_default_max()
                        else:
                            new_value = float(new_value)
                        if set_min:
                            item.set_min(new_value)
                        else:
                            item.set_max(new_value)

                    return inner

                attr_ranger.min_text_edited.connect(attr_ranger_change(item, True))
                attr_ranger.max_text_edited.connect(attr_ranger_change(item, False))

                del_attr_btn = QPushButton()
                del_attr_btn.setIcon(
                    self.style().standardIcon(
                        QStyle.StandardPixmap.SP_TitleBarCloseButton
                    )
                )
                del_attr_btn.setFixedSize(12, 12)
                del_attr_btn.setIconSize(del_attr_btn.rect().size() - QSize(3, 3))
                del_attr_btn.clicked.connect(item.delete)

                attr_layout = QHBoxLayout()
                attr_layout.addWidget(attr_ranger)
                attr_layout.addWidget(del_attr_btn)
                attr_layout.addStretch()

                attrs_layout.insertLayout(attrs_layout.count() - 1, attr_layout)

                idx += 1

            # update availabel attr menu
            attr_item_ids = [item.id for item in attr_items]
            actions = add_menu.actions()
            for action in actions:
                if action.objectName() in attr_item_ids:
                    action.setEnabled(False)
                else:
                    action.setEnabled(True)

        event_filter_items_updated(statement.get_attr_items())
        statement.attr_items.connect(event_filter_items_updated)

        delete_icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_DialogCloseButton
        )
        delete = QPushButton()
        delete.setIcon(delete_icon)
        delete.clicked.connect(statement.delete_statement)

        hlayout = QHBoxLayout()
        hlayout.addWidget(title, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)
        hlayout.addLayout(attrs_layout, stretch=1)
        hlayout.addWidget(delete, stretch=0, alignment=Qt.AlignmentFlag.AlignTop)

        frame = QWidget()
        frame.setObjectName("statement_box")
        frame.setLayout(hlayout)
        return frame


class OptStatementLayout(QLayout):
    def __init__(self, parent=None):
        super().__init__(parent)

        if parent is not None:
            self.setContentsMargins(0, 0, 0, 0)

        self._opt = OptStatement.Opt_None

        self._item_list: list[QLayoutItem] = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    @override
    def addItem(self, item):
        self._item_list.append(item)

    @override
    def count(self):
        return len(self._item_list)

    @override
    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]

        return None

    @override
    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)

        return None

    @override
    def sizeHint(self):
        return self.minimumSize()

    @override
    def minimumSize(self):
        size = QSize()

        for item in self._item_list:
            item_size_hint = item.sizeHint()
            size.setWidth(size.width() + item_size_hint.width())
            size.setHeight(max(size.height(), item_size_hint.height()))

        spacing_horizontal = max((len(self._item_list) - 1), 0) * self.spacing()
        size.setWidth(size.width() + spacing_horizontal)

        margin = self.contentsMargins()
        margin_vertical = margin.top() + margin.bottom()
        margin_horizontal = margin.left() + margin.right()

        size += QSize(margin_horizontal, margin_vertical)
        return size

    @override
    def setGeometry(self, rect: QRect):
        super(OptStatementLayout, self).setGeometry(rect)
        assert len(self._item_list) > 0

        margin = self.contentsMargins()

        content_width = rect.width() - margin.left() - margin.right()
        middlex = rect.left() + margin.left() + content_width // 2

        first_item = self._item_list[0]
        first_item_size = first_item.sizeHint()

        first_item_rect = QRect(
            QPoint(middlex - first_item_size.width() // 2, rect.top() + margin.top()),
            first_item_size,
        )
        first_item.setGeometry(first_item_rect)

        pre_item_rect = first_item_rect
        for i in range(1, len(self._item_list)):
            item = self._item_list[i]
            item_size = item.sizeHint()
            item_rect = QRect(
                QPoint(
                    pre_item_rect.right() + self.spacing(),
                    pre_item_rect.top(),
                ),
                item_size,
            )
            item.setGeometry(item_rect)
            pre_item_rect = item_rect


class ArrangeUi(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._model = ArrangeModel()
        self._init_layout()

    def _init_layout(self) -> None:
        self.setWindowTitle(load_string("arrange_win_title"))
        self.setWindowIcon(QIcon("bm:AppIcon.ico"))
        self.setStyleSheet(_style)

        list_model = self._model.get_list_model()
        self._rule_list_view = RuleListView(list_model)

        detail_model = self._model.get_detail_model()
        detail = None
        if detail_model:
            detail = RuleDetialView(model=detail_model)
        self._model.detail_model.connect(self._event_detail_model)

        self._layout = QHBoxLayout()
        self._layout.setSpacing(0)
        self._layout.addWidget(self._rule_list_view, stretch=1)
        if isinstance(detail, RuleDetialView):
            self._layout.addWidget(detail, stretch=2)
        else:
            self._layout.addStretch(stretch=2)

        self.setLayout(self._layout)
        self.resize(800, 495)

    def _close_model(self, model):
        for m in model.children():
            self._close_model(m)
        if hasattr(model, "close"):
            model.close()

    @override
    def closeEvent(self, event: QCloseEvent):
        self._close_model(self._model)
        event.accept()

    @Slot()
    def _event_detail_model(self, model: Optional[RuleDetailModel]):
        if model is None:
            detail = self._layout.takeAt(1)
            widget = detail.widget()
            if widget:
                widget.deleteLater()
            self._layout.addStretch(stretch=2)
            self._layout.update()
        else:
            detail = self._layout.takeAt(1)
            widget = detail.widget()
            if widget:
                widget.deleteLater()
            detail = RuleDetialView(model=model)
            self._layout.addWidget(detail, stretch=2)
