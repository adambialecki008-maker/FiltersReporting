from __future__ import annotations

import sqlite3

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
)

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filters_reporting.collection.opc_ua_browser import (
    OpcUaBrowseResult,
    OpcUaNodeInfo,
    browse_opc_ua_server,
)

from filters_reporting.models.filter import Filter


class OpcUaBrowseWorker(QThread):
    success = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        endpoint: str,
        filter_obj: Filter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.endpoint = endpoint
        self.filter_obj = filter_obj

    def run(self):
        try:
            result = browse_opc_ua_server(
                self.endpoint,
                timeout_seconds=5.0,
                max_depth=10,
                max_nodes=3000,
                filter_obj=self.filter_obj,
            )

            self.success.emit(result)

        except Exception as error:
            self.failed.emit(f"{type(error).__name__}: {error}")


class OpcUaBrowserDialog(QDialog):
    def __init__(
        self,
        endpoint: str,
        delta_p_node_id: str = "",
        status_node_id: str = "",
        alarm_node_id: str = "",
        filter_obj: Filter | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.endpoint = endpoint.strip()
        self.filter_obj = filter_obj

        self.worker: OpcUaBrowseWorker | None = None

        self.selected_node: OpcUaNodeInfo | None = None

        self.node_ids = {
            "delta_p": delta_p_node_id.strip(),
            "status": status_node_id.strip(),
            "alarm": alarm_node_id.strip(),
        }

        self.setWindowTitle("Przeglądarka OPC UA")

        self.resize(
            1050,
            720,
        )

        self.setMinimumSize(
            850,
            560,
        )

        self.build_ui()
        self.apply_style()

        self.refresh_assignment_fields()

        self.start_browse()

    # ==================================================
    # UI
    # ==================================================

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        main_layout.setSpacing(12)

        # ----------------------------------------------
        # HEADER
        # ----------------------------------------------

        header_layout = QHBoxLayout()

        header_text_layout = QVBoxLayout()

        header_text_layout.setSpacing(2)

        title = QLabel("Przeglądarka OPC UA")

        title.setObjectName("dialogTitle")

        endpoint_label = QLabel(self.endpoint)

        endpoint_label.setObjectName("endpointLabel")

        endpoint_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        header_text_layout.addWidget(title)

        header_text_layout.addWidget(endpoint_label)

        header_layout.addLayout(header_text_layout)

        header_layout.addStretch()

        self.refresh_button = QPushButton("Połącz ponownie")

        self.refresh_button.setObjectName("secondaryButton")

        self.refresh_button.clicked.connect(self.start_browse)

        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        # ----------------------------------------------
        # CONNECTION STATUS
        # ----------------------------------------------

        self.status_label = QLabel("Łączenie z serwerem OPC UA...")

        self.status_label.setObjectName("statusLabel")

        main_layout.addWidget(self.status_label)

        # ----------------------------------------------
        # NAMESPACE + ADDRESS SPACE
        # ----------------------------------------------

        splitter = QSplitter(Qt.Horizontal)

        splitter.setChildrenCollapsible(False)

        namespace_panel = QFrame()

        namespace_panel.setObjectName("panel")

        namespace_layout = QVBoxLayout(namespace_panel)

        namespace_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        namespace_layout.setSpacing(8)

        namespace_title = QLabel("Namespaces")

        namespace_title.setObjectName("sectionTitle")

        namespace_layout.addWidget(namespace_title)

        self.namespace_table = QTableWidget(
            0,
            2,
        )

        self.namespace_table.setHorizontalHeaderLabels(
            [
                "ns",
                "URI",
            ]
        )

        self.namespace_table.verticalHeader().setVisible(False)

        self.namespace_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.namespace_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        namespace_header = self.namespace_table.horizontalHeader()

        namespace_header.setSectionResizeMode(
            0,
            QHeaderView.ResizeToContents,
        )

        namespace_header.setSectionResizeMode(
            1,
            QHeaderView.Stretch,
        )

        namespace_layout.addWidget(self.namespace_table)

        tree_panel = QFrame()

        tree_panel.setObjectName("panel")

        tree_layout = QVBoxLayout(tree_panel)

        tree_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        tree_layout.setSpacing(8)

        tree_title = QLabel("Address space")

        tree_title.setObjectName("sectionTitle")

        tree_layout.addWidget(tree_title)

        self.tree = QTreeWidget()

        self.tree.setColumnCount(3)

        self.tree.setHeaderLabels(
            [
                "Nazwa",
                "Klasa",
                "NodeId",
            ]
        )

        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)

        self.tree.setUniformRowHeights(True)

        tree_header = self.tree.header()

        tree_header.setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )

        tree_header.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )

        tree_header.setSectionResizeMode(
            2,
            QHeaderView.Stretch,
        )

        self.tree.itemSelectionChanged.connect(self.on_tree_selection_changed)

        tree_layout.addWidget(self.tree)

        splitter.addWidget(namespace_panel)

        splitter.addWidget(tree_panel)

        splitter.setStretchFactor(
            0,
            1,
        )

        splitter.setStretchFactor(
            1,
            4,
        )

        main_layout.addWidget(
            splitter,
            1,
        )

        # ----------------------------------------------
        # CURRENT SELECTION
        # ----------------------------------------------

        selected_panel = QFrame()

        selected_panel.setObjectName("panel")

        selected_layout = QVBoxLayout(selected_panel)

        selected_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        selected_layout.setSpacing(8)

        selected_header_layout = QHBoxLayout()

        selected_title = QLabel("Wybrany node")

        selected_title.setObjectName("sectionTitle")

        selected_header_layout.addWidget(selected_title)

        selected_header_layout.addStretch()

        self.selected_class_label = QLabel("—")

        self.selected_class_label.setObjectName("smallMuted")

        selected_header_layout.addWidget(self.selected_class_label)

        selected_layout.addLayout(selected_header_layout)

        self.selected_node_id = QLineEdit()

        self.selected_node_id.setReadOnly(True)

        self.selected_node_id.setPlaceholderText("Zaznacz zmienną w drzewie")

        selected_layout.addWidget(self.selected_node_id)

        assign_layout = QHBoxLayout()

        assign_layout.setSpacing(8)

        self.assign_delta_p_button = QPushButton("Ustaw jako Δp")

        self.assign_status_button = QPushButton("Ustaw jako Status")

        self.assign_alarm_button = QPushButton("Ustaw jako Alarm")

        for button in (
            self.assign_delta_p_button,
            self.assign_status_button,
            self.assign_alarm_button,
        ):
            button.setObjectName("secondaryButton")

            button.setEnabled(False)

            assign_layout.addWidget(button)

        self.assign_delta_p_button.clicked.connect(
            lambda: self.assign_selected_node("delta_p")
        )

        self.assign_status_button.clicked.connect(
            lambda: self.assign_selected_node("status")
        )

        self.assign_alarm_button.clicked.connect(
            lambda: self.assign_selected_node("alarm")
        )

        selected_layout.addLayout(assign_layout)

        main_layout.addWidget(selected_panel)

        # ----------------------------------------------
        # ASSIGNED NODES
        # ----------------------------------------------

        assignments_panel = QFrame()

        assignments_panel.setObjectName("panel")

        assignments_layout = QGridLayout(assignments_panel)

        assignments_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        assignments_layout.setHorizontalSpacing(10)

        assignments_layout.setVerticalSpacing(7)

        assignments_layout.addWidget(
            QLabel("Δp"),
            0,
            0,
        )

        self.delta_p_assignment = QLineEdit()

        self.delta_p_assignment.setReadOnly(True)

        assignments_layout.addWidget(
            self.delta_p_assignment,
            0,
            1,
        )

        assignments_layout.addWidget(
            QLabel("Status"),
            1,
            0,
        )

        self.status_assignment = QLineEdit()

        self.status_assignment.setReadOnly(True)

        assignments_layout.addWidget(
            self.status_assignment,
            1,
            1,
        )

        assignments_layout.addWidget(
            QLabel("Alarm"),
            2,
            0,
        )

        self.alarm_assignment = QLineEdit()

        self.alarm_assignment.setReadOnly(True)

        assignments_layout.addWidget(
            self.alarm_assignment,
            2,
            1,
        )

        main_layout.addWidget(assignments_panel)

        # ----------------------------------------------
        # FOOTER
        # ----------------------------------------------

        footer_layout = QHBoxLayout()

        footer_layout.addStretch()

        self.cancel_button = QPushButton("Anuluj")

        self.cancel_button.setObjectName("secondaryButton")

        self.cancel_button.clicked.connect(self.reject)

        self.apply_button = QPushButton("Zastosuj NodeId")

        self.apply_button.setObjectName("primaryButton")

        self.apply_button.clicked.connect(self.accept)

        footer_layout.addWidget(self.cancel_button)

        footer_layout.addWidget(self.apply_button)

        main_layout.addLayout(footer_layout)

    # ==================================================
    # OPC UA BROWSE
    # ==================================================

    def start_browse(self):
        if self.worker and self.worker.isRunning():
            return

        self.tree.clear()

        self.namespace_table.setRowCount(0)

        self.selected_node = None

        self.selected_node_id.clear()

        self.selected_class_label.setText("—")

        self.set_assignment_buttons_enabled(False)

        self.status_label.setText("Łączenie i pobieranie " "address space...")

        self.refresh_button.setEnabled(False)

        self.cancel_button.setEnabled(False)

        self.apply_button.setEnabled(False)

        self.worker = OpcUaBrowseWorker(
            self.endpoint,
            filter_obj=self.filter_obj,
            parent=self,
        )

        self.worker.success.connect(self.on_browse_success)

        self.worker.failed.connect(self.on_browse_failed)

        self.worker.finished.connect(self.on_browse_finished)

        self.worker.start()

    def on_browse_success(
        self,
        result: OpcUaBrowseResult,
    ):
        self.populate_namespaces(result.namespaces)

        self.populate_tree(result.root)

        status = f"Połączono. Odczytano " f"{result.node_count} nodów."

        if result.truncated:
            status += (
                " Widok został ograniczony "
                "przez limit głębokości "
                "lub liczby nodów."
            )

        self.status_label.setText(status)

        self.apply_button.setEnabled(True)

    def on_browse_failed(
        self,
        message: str,
    ):
        self.status_label.setText("Nie udało się pobrać " "address space.")

        QMessageBox.critical(
            self,
            "OPC UA",
            ("Nie udało się połączyć " "lub przeglądać serwera." "\n\n" f"{message}"),
        )

    def on_browse_finished(self):
        self.refresh_button.setEnabled(True)

        self.cancel_button.setEnabled(True)

        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    # ==================================================
    # NAMESPACES
    # ==================================================

    def populate_namespaces(
        self,
        namespaces: list[str],
    ):
        self.namespace_table.setRowCount(len(namespaces))

        for index, uri in enumerate(namespaces):
            index_item = QTableWidgetItem(str(index))

            uri_item = QTableWidgetItem(uri)

            index_item.setTextAlignment(Qt.AlignCenter)

            self.namespace_table.setItem(
                index,
                0,
                index_item,
            )

            self.namespace_table.setItem(
                index,
                1,
                uri_item,
            )

    # ==================================================
    # TREE
    # ==================================================

    def populate_tree(
        self,
        root: OpcUaNodeInfo,
    ):
        self.tree.clear()

        root_item = self.create_tree_item(root)

        self.tree.addTopLevelItem(root_item)

        root_item.setExpanded(True)

    def create_tree_item(
        self,
        node: OpcUaNodeInfo,
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem(
            [
                node.name,
                node.node_class,
                node.node_id,
            ]
        )

        item.setData(
            0,
            Qt.UserRole,
            node,
        )

        if node.selectable:
            item.setToolTip(
                0,
                ("Zmienna — można " "przypisać do " "konfiguracji filtra."),
            )
        else:
            item.setToolTip(
                0,
                "Ten node nie jest zmienną.",
            )

        for child in node.children:
            item.addChild(self.create_tree_item(child))

        return item

    def on_tree_selection_changed(
        self,
    ):
        selected_items = self.tree.selectedItems()

        if not selected_items:
            self.selected_node = None

            self.selected_node_id.clear()

            self.selected_class_label.setText("—")

            self.set_assignment_buttons_enabled(False)

            return

        node = selected_items[0].data(
            0,
            Qt.UserRole,
        )

        self.selected_node = node

        self.selected_node_id.setText(node.node_id)

        self.selected_class_label.setText(
            (f"{node.node_class} | " f"ns={node.namespace_index}")
        )

        self.set_assignment_buttons_enabled(node.selectable)

    # ==================================================
    # NODE ASSIGNMENT
    # ==================================================

    def set_assignment_buttons_enabled(
        self,
        enabled: bool,
    ):
        self.assign_delta_p_button.setEnabled(enabled)

        self.assign_status_button.setEnabled(enabled)

        self.assign_alarm_button.setEnabled(enabled)

    def assign_selected_node(
        self,
        target: str,
    ):
        if not self.selected_node:
            return

        if not self.selected_node.selectable:
            return

        self.node_ids[target] = self.selected_node.node_id

        self.refresh_assignment_fields()

    def refresh_assignment_fields(
        self,
    ):
        self.delta_p_assignment.setText(self.node_ids["delta_p"])

        self.status_assignment.setText(self.node_ids["status"])

        self.alarm_assignment.setText(self.node_ids["alarm"])

    def get_node_ids(
        self,
    ) -> dict[str, str]:
        return dict(self.node_ids)

    # ==================================================
    # SAFE CLOSE
    # ==================================================

    def reject(self):
        if self.worker and self.worker.isRunning():
            return

        super().reject()

    def closeEvent(
        self,
        event,
    ):
        if self.worker and self.worker.isRunning():
            event.ignore()
            return

        super().closeEvent(event)

    # ==================================================
    # STYLE
    # ==================================================

    def apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1220;
                color: #dbe5ef;
            }

            QLabel {
                color: #dbe5ef;
                background: transparent;
            }

            QLabel#dialogTitle {
                color: #f8fafc;
                font-size: 20px;
                font-weight: 700;
            }

            QLabel#endpointLabel,
            QLabel#statusLabel,
            QLabel#smallMuted {
                color: #8296aa;
                font-size: 10px;
            }

            QLabel#sectionTitle {
                color: #f5f8fc;
                font-size: 12px;
                font-weight: 700;
            }

            QFrame#panel {
                background-color: #111b28;
                border: 1px solid #26384c;
                border-radius: 8px;
            }

            QLineEdit,
            QTableWidget,
            QTreeWidget {
                background-color: #0d1724;
                color: #dbe5ef;
                border: 1px solid #2a3d52;
                border-radius: 5px;
                selection-background-color: #1f4f7a;
                selection-color: #ffffff;
            }

            QLineEdit {
                padding: 7px;
            }

            QHeaderView::section {
                background-color: #152233;
                color: #a9bacb;
                border: none;
                border-bottom: 1px solid #2a3d52;
                padding: 7px;
                font-weight: 600;
            }

            QPushButton {
                min-height: 30px;
                padding: 0 14px;
                border-radius: 5px;
                font-weight: 600;
            }

            QPushButton#primaryButton {
                background-color: #2563a6;
                color: white;
                border: 1px solid #3377bd;
            }

            QPushButton#primaryButton:hover {
                background-color: #2d72b8;
            }

            QPushButton#secondaryButton {
                background-color: #172536;
                color: #dbe5ef;
                border: 1px solid #32475d;
            }

            QPushButton#secondaryButton:hover {
                background-color: #1c3045;
            }

            QPushButton:disabled {
                color: #5f7183;
                background-color: #101923;
                border-color: #243342;
            }

            QScrollBar:vertical {
                background-color: #0d1723;
                width: 8px;
                margin: 2px 2px 2px 1px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #354a5d;
                min-height: 20px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #4a647b;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                border: none;
                background: transparent;
            }

            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QSplitter::handle {
                background-color: #0b1220;
                width: 6px;
            }
            """)


class FiltersPage(QWidget):
    def __init__(
        self,
        repository,
    ):
        super().__init__()

        self.setObjectName("filtersPage")

        self.repository = repository

        self.selected_filter_id: int | None = None

        self.filters: list[Filter] = []

        self.build_ui()
        self.apply_style()

        self.refresh_filters()

    # ==================================================
    # UI
    # ==================================================

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            20,
            14,
            20,
            14,
        )

        main_layout.setSpacing(10)

        # ----------------------------------------------
        # HEADER
        # ----------------------------------------------

        header_layout = QHBoxLayout()

        header_text_layout = QVBoxLayout()

        header_text_layout.setSpacing(0)

        title = QLabel("Filtry")

        title.setObjectName("pageTitle")

        subtitle = QLabel("Konfiguracja filtrów, " "endpointów OPC UA i NodeId.")

        subtitle.setObjectName("subtitle")

        header_text_layout.addWidget(title)

        header_text_layout.addWidget(subtitle)

        header_layout.addLayout(header_text_layout)

        header_layout.addStretch()

        self.new_button = QPushButton("+ Nowy filtr")

        self.new_button.setObjectName("primaryButton")

        self.new_button.clicked.connect(self.start_new_filter)

        header_layout.addWidget(self.new_button)

        main_layout.addLayout(header_layout)

        # ----------------------------------------------
        # SUMMARY CARDS
        # ----------------------------------------------

        cards_layout = QHBoxLayout()

        cards_layout.setSpacing(10)

        self.total_card = self.create_status_card(
            "FILTRY RAZEM",
            "—",
            "Wszystkie konfiguracje",
        )

        self.active_card = self.create_status_card(
            "AKTYWNE",
            "—",
            "Używane przez collector",
        )

        self.configured_card = self.create_status_card(
            "SKONFIGUROWANE OPC UA",
            "—",
            "Endpoint + 3 NodeId",
        )

        cards_layout.addWidget(self.total_card["frame"])

        cards_layout.addWidget(self.active_card["frame"])

        cards_layout.addWidget(self.configured_card["frame"])

        main_layout.addLayout(cards_layout)

        # ----------------------------------------------
        # CONTENT
        # ----------------------------------------------

        splitter = QSplitter(Qt.Horizontal)

        splitter.setChildrenCollapsible(False)

        # ==============================================
        # FILTER LIST
        # ==============================================

        list_panel = self.create_panel()

        list_layout = QVBoxLayout(list_panel)

        list_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        list_layout.setSpacing(8)

        list_header_layout = QHBoxLayout()

        list_title = QLabel("Lista filtrów")

        list_title.setObjectName("sectionTitle")

        list_header_layout.addWidget(list_title)

        list_header_layout.addStretch()

        self.refresh_button = QPushButton("Odśwież")

        self.refresh_button.setObjectName("secondaryButton")

        self.refresh_button.clicked.connect(self.refresh_filters)

        list_header_layout.addWidget(self.refresh_button)

        list_layout.addLayout(list_header_layout)

        self.filters_table = QTableWidget(
            0,
            5,
        )

        self.filters_table.setHorizontalHeaderLabels(
            [
                "Nazwa",
                "Aktywny",
                "OPC UA",
                "Próg Δp",
                "Konfiguracja",
            ]
        )

        self.filters_table.verticalHeader().setVisible(False)

        self.filters_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.filters_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.filters_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.filters_table.setShowGrid(False)

        # ----------------------------------------------
        # SCROLL
        # ----------------------------------------------

        self.filters_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.filters_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.filters_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        table_header = self.filters_table.horizontalHeader()

        table_header.setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )

        table_header.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )

        table_header.setSectionResizeMode(
            2,
            QHeaderView.Stretch,
        )

        table_header.setSectionResizeMode(
            3,
            QHeaderView.ResizeToContents,
        )

        table_header.setSectionResizeMode(
            4,
            QHeaderView.ResizeToContents,
        )

        self.filters_table.itemSelectionChanged.connect(self.on_filter_selected)

        list_layout.addWidget(self.filters_table)

        # ==============================================
        # EDITOR
        # ==============================================

        editor_panel = self.create_panel()

        editor_layout = QVBoxLayout(editor_panel)

        editor_layout.setContentsMargins(
            16,
            12,
            16,
            12,
        )

        editor_layout.setSpacing(10)

        editor_header_layout = QHBoxLayout()

        self.editor_title = QLabel("Konfiguracja filtra")

        self.editor_title.setObjectName("sectionTitle")

        editor_header_layout.addWidget(self.editor_title)

        editor_header_layout.addStretch()

        self.editor_state_label = QLabel("Wybierz filtr")

        self.editor_state_label.setObjectName("editorState")

        editor_header_layout.addWidget(self.editor_state_label)

        editor_layout.addLayout(editor_header_layout)

        # ----------------------------------------------
        # FORM
        # ----------------------------------------------

        form_layout = QGridLayout()

        form_layout.setHorizontalSpacing(12)

        form_layout.setVerticalSpacing(8)

        form_layout.setColumnStretch(
            1,
            1,
        )

        row = 0

        form_layout.addWidget(
            self.create_form_label("Nazwa filtra"),
            row,
            0,
        )

        self.name_edit = QLineEdit()

        self.name_edit.setPlaceholderText("np. Esta_01")

        form_layout.addWidget(
            self.name_edit,
            row,
            1,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Aktywny"),
            row,
            0,
        )

        self.active_checkbox = QCheckBox("Collector ma odczytywać " "ten filtr")

        self.active_checkbox.setChecked(True)

        form_layout.addWidget(
            self.active_checkbox,
            row,
            1,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Próg Δp [Pa]"),
            row,
            0,
        )

        self.threshold_spinbox = QSpinBox()

        self.threshold_spinbox.setRange(
            1,
            1_000_000,
        )

        self.threshold_spinbox.setValue(2000)

        self.threshold_spinbox.setSuffix(" Pa")

        form_layout.addWidget(
            self.threshold_spinbox,
            row,
            1,
        )

        row += 1

        opc_section = QLabel("OPC UA")

        opc_section.setObjectName("formSection")

        form_layout.addWidget(
            opc_section,
            row,
            0,
            1,
            2,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Endpoint"),
            row,
            0,
        )

        endpoint_layout = QHBoxLayout()

        endpoint_layout.setSpacing(7)

        self.opc_url_edit = QLineEdit()

        self.opc_url_edit.setPlaceholderText("opc.tcp://192.168.0.10:4840/")

        endpoint_layout.addWidget(
            self.opc_url_edit,
            1,
        )

        self.browse_opc_button = QPushButton("Przeglądaj OPC UA")

        self.browse_opc_button.setObjectName("secondaryButton")

        self.browse_opc_button.clicked.connect(self.open_opc_browser)

        endpoint_layout.addWidget(self.browse_opc_button)

        form_layout.addLayout(
            endpoint_layout,
            row,
            1,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Node Δp"),
            row,
            0,
        )

        self.delta_p_node_edit = QLineEdit()

        self.delta_p_node_edit.setPlaceholderText("np. ns=3;s=Filter.DeltaP")

        form_layout.addWidget(
            self.delta_p_node_edit,
            row,
            1,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Node status"),
            row,
            0,
        )

        self.status_node_edit = QLineEdit()

        self.status_node_edit.setPlaceholderText("np. ns=3;s=Filter.Status")

        form_layout.addWidget(
            self.status_node_edit,
            row,
            1,
        )

        row += 1

        form_layout.addWidget(
            self.create_form_label("Node alarm"),
            row,
            0,
        )

        self.alarm_node_edit = QLineEdit()

        self.alarm_node_edit.setPlaceholderText("np. ns=3;s=Filter.Alarm")

        form_layout.addWidget(
            self.alarm_node_edit,
            row,
            1,
        )

        editor_layout.addLayout(form_layout)

        hint = QLabel(
            "Możesz wpisać NodeId ręcznie "
            "albo pobrać je bezpośrednio "
            "z address space serwera OPC UA."
        )

        hint.setWordWrap(True)

        hint.setObjectName("hint")

        editor_layout.addWidget(hint)

        editor_layout.addStretch()

        # ----------------------------------------------
        # EDITOR BUTTONS
        # ----------------------------------------------

        editor_buttons_layout = QHBoxLayout()

        editor_buttons_layout.setSpacing(8)

        self.delete_button = QPushButton("Usuń filtr")

        self.delete_button.setObjectName("dangerButton")

        self.delete_button.setEnabled(False)

        self.delete_button.clicked.connect(self.delete_selected_filter)

        self.cancel_edit_button = QPushButton("Anuluj")

        self.cancel_edit_button.setObjectName("secondaryButton")

        self.cancel_edit_button.clicked.connect(self.cancel_edit)

        self.save_button = QPushButton("Zapisz")

        self.save_button.setObjectName("primaryButton")

        self.save_button.clicked.connect(self.save_filter)

        editor_buttons_layout.addWidget(self.delete_button)

        editor_buttons_layout.addStretch()

        editor_buttons_layout.addWidget(self.cancel_edit_button)

        editor_buttons_layout.addWidget(self.save_button)

        editor_layout.addLayout(editor_buttons_layout)

        splitter.addWidget(list_panel)

        splitter.addWidget(editor_panel)

        splitter.setStretchFactor(
            0,
            3,
        )

        splitter.setStretchFactor(
            1,
            2,
        )

        main_layout.addWidget(
            splitter,
            1,
        )

    # ==================================================
    # UI HELPERS
    # ==================================================

    def create_panel(self):
        panel = QFrame()

        panel.setObjectName("panel")

        return panel

    def create_status_card(
        self,
        title_text: str,
        value_text: str,
        detail_text: str,
    ):
        frame = QFrame()

        frame.setObjectName("statusCard")

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        layout.setSpacing(2)

        title = QLabel(title_text)

        title.setObjectName("statusTitle")

        value = QLabel(value_text)

        value.setObjectName("statusValue")

        detail = QLabel(detail_text)

        detail.setObjectName("statusDetail")

        layout.addWidget(title)

        layout.addWidget(value)

        layout.addWidget(detail)

        return {
            "frame": frame,
            "title": title,
            "value": value,
            "detail": detail,
        }

    def create_form_label(
        self,
        text: str,
    ):
        label = QLabel(text)

        label.setObjectName("formLabel")

        return label

    # ==================================================
    # LOAD / REFRESH
    # ==================================================

    def refresh_filters(
        self,
        select_filter_id: int | None = None,
    ):
        if select_filter_id is None:
            select_filter_id = self.selected_filter_id

        self.filters = self.repository.get_all_filters()

        self.filters_table.blockSignals(True)

        self.filters_table.setRowCount(len(self.filters))

        row_to_select = None

        for row, filter_obj in enumerate(self.filters):
            configured = self.is_filter_configured(filter_obj)

            values = [
                filter_obj.name,
                ("Tak" if filter_obj.active else "Nie"),
                (filter_obj.opc_url or "—"),
                (f"{filter_obj.delta_p_threshold} " "Pa"),
                ("Gotowa" if configured else "Niepełna"),
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column in (
                    1,
                    3,
                    4,
                ):
                    item.setTextAlignment(Qt.AlignCenter)

                self.filters_table.setItem(
                    row,
                    column,
                    item,
                )

            self.filters_table.setRowHeight(
                row,
                31,
            )

            if (
                select_filter_id is not None
                and filter_obj.filter_id == select_filter_id
            ):
                row_to_select = row

        self.filters_table.blockSignals(False)

        self.refresh_summary_cards()

        if row_to_select is not None:
            self.filters_table.selectRow(row_to_select)

            self.load_filter(self.filters[row_to_select])

        elif self.filters:
            self.filters_table.selectRow(0)

            self.load_filter(self.filters[0])

        else:
            self.start_new_filter()

    def refresh_summary_cards(self):
        total = len(self.filters)

        active = sum(1 for filter_obj in self.filters if filter_obj.active)

        configured = sum(
            1 for filter_obj in self.filters if self.is_filter_configured(filter_obj)
        )

        self.total_card["value"].setText(str(total))

        self.active_card["value"].setText(str(active))

        self.configured_card["value"].setText(str(configured))

        self.active_card["detail"].setText(f"Nieaktywne: {total - active}")

        self.configured_card["detail"].setText(f"Niepełne: {total - configured}")

    @staticmethod
    def is_filter_configured(
        filter_obj: Filter,
    ):
        return bool(
            filter_obj.opc_url
            and filter_obj.delta_p_node_id
            and filter_obj.status_node_id
            and filter_obj.alarm_node_id
        )

    # ==================================================
    # SELECTION
    # ==================================================

    def on_filter_selected(self):
        selected_rows = self.filters_table.selectionModel().selectedRows()

        if not selected_rows:
            return

        row = selected_rows[0].row()

        if not (0 <= row < len(self.filters)):
            return

        self.load_filter(self.filters[row])

    def load_filter(
        self,
        filter_obj: Filter,
    ):
        self.selected_filter_id = filter_obj.filter_id

        self.editor_title.setText(("Konfiguracja: " f"{filter_obj.name}"))

        self.editor_state_label.setText(f"ID: {filter_obj.filter_id}")

        self.name_edit.setText(filter_obj.name)

        self.active_checkbox.setChecked(filter_obj.active)

        self.threshold_spinbox.setValue(filter_obj.delta_p_threshold)

        self.opc_url_edit.setText(filter_obj.opc_url or "")

        self.delta_p_node_edit.setText(filter_obj.delta_p_node_id or "")

        self.status_node_edit.setText(filter_obj.status_node_id or "")

        self.alarm_node_edit.setText(filter_obj.alarm_node_id or "")

        self.delete_button.setEnabled(True)

    # ==================================================
    # NEW / CANCEL
    # ==================================================

    def start_new_filter(self):
        self.filters_table.clearSelection()

        self.selected_filter_id = None

        self.editor_title.setText("Nowy filtr")

        self.editor_state_label.setText("Nowa konfiguracja")

        self.name_edit.clear()

        self.active_checkbox.setChecked(True)

        self.threshold_spinbox.setValue(2000)

        self.opc_url_edit.clear()

        self.delta_p_node_edit.clear()

        self.status_node_edit.clear()

        self.alarm_node_edit.clear()

        self.delete_button.setEnabled(False)

        self.name_edit.setFocus()

    def cancel_edit(self):
        if self.selected_filter_id is None:
            if self.filters:
                self.filters_table.selectRow(0)

                self.load_filter(self.filters[0])

            else:
                self.start_new_filter()

            return

        filter_obj = self.find_filter_by_id(self.selected_filter_id)

        if filter_obj:
            self.load_filter(filter_obj)

    # ==================================================
    # DELETE
    # ==================================================

    def delete_selected_filter(self):
        if self.selected_filter_id is None:
            return

        filter_obj = self.find_filter_by_id(self.selected_filter_id)

        if filter_obj is None:
            QMessageBox.warning(
                self,
                "Usuń filtr",
                ("Nie udało się odnaleźć " "wybranego filtra."),
            )

            return

        answer = QMessageBox.question(
            self,
            "Usuń filtr",
            (
                "Czy na pewno usunąć filtr "
                f"„{filter_obj.name}”?\n\n"
                "Tej operacji nie można cofnąć."
            ),
            (QMessageBox.Yes | QMessageBox.No),
            QMessageBox.No,
        )

        if answer != QMessageBox.Yes:
            return

        if not hasattr(
            self.repository,
            "delete_filter",
        ):
            QMessageBox.critical(
                self,
                "Usuń filtr",
                ("Repozytorium nie posiada " "metody delete_filter(filter_id)."),
            )

            return

        try:
            self.repository.delete_filter(self.selected_filter_id)

        except sqlite3.IntegrityError as error:
            QMessageBox.critical(
                self,
                "Błąd usuwania",
                ("Baza danych nie pozwoliła " "usunąć filtra." "\n\n" f"{error}"),
            )

            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "Błąd usuwania",
                (f"{type(error).__name__}: " f"{error}"),
            )

            return

        deleted_name = filter_obj.name

        self.selected_filter_id = None

        self.refresh_filters()

        QMessageBox.information(
            self,
            "Usuń filtr",
            (f"Filtr „{deleted_name}” " "został usunięty."),
        )

    # ==================================================
    # OPC UA BROWSER
    # ==================================================

    def open_opc_browser(self):
        endpoint = self.opc_url_edit.text().strip()

        if not endpoint:
            QMessageBox.warning(
                self,
                "OPC UA",
                ("Najpierw podaj " "endpoint OPC UA."),
            )

            self.opc_url_edit.setFocus()

            return

        filter_obj = None

        if self.selected_filter_id is not None:
            filter_obj = self.find_filter_by_id(self.selected_filter_id)

        dialog = OpcUaBrowserDialog(
            endpoint=endpoint,
            delta_p_node_id=(self.delta_p_node_edit.text()),
            status_node_id=(self.status_node_edit.text()),
            alarm_node_id=(self.alarm_node_edit.text()),
            filter_obj=filter_obj,
            parent=self,
        )

        if dialog.exec() != QDialog.Accepted:
            return

        node_ids = dialog.get_node_ids()

        self.delta_p_node_edit.setText(node_ids["delta_p"])

        self.status_node_edit.setText(node_ids["status"])

        self.alarm_node_edit.setText(node_ids["alarm"])

    # ==================================================
    # FORM
    # ==================================================

    def get_form_values(self):
        return {
            "name": (self.name_edit.text().strip()),
            "active": (self.active_checkbox.isChecked()),
            "delta_p_threshold": (self.threshold_spinbox.value()),
            "opc_url": (self.opc_url_edit.text().strip()),
            "delta_p_node_id": (self.delta_p_node_edit.text().strip()),
            "status_node_id": (self.status_node_edit.text().strip()),
            "alarm_node_id": (self.alarm_node_edit.text().strip()),
        }

    def validate_form(
        self,
        values,
    ):
        if not values["name"]:
            return (
                False,
                "Podaj nazwę filtra.",
            )

        for filter_obj in self.filters:
            if filter_obj.filter_id == self.selected_filter_id:
                continue

            if filter_obj.name.casefold() == values["name"].casefold():
                return (
                    False,
                    ("Filtr o tej nazwie " "już istnieje."),
                )

        if values["active"]:
            missing = []

            if not values["opc_url"]:
                missing.append("endpoint OPC UA")

            if not values["delta_p_node_id"]:
                missing.append("Node Δp")

            if not values["status_node_id"]:
                missing.append("Node status")

            if not values["alarm_node_id"]:
                missing.append("Node alarm")

            if missing:
                return (
                    False,
                    (
                        "Aktywny filtr musi "
                        "mieć pełną "
                        "konfigurację OPC UA:"
                        "\n\n- " + "\n- ".join(missing)
                    ),
                )

        return (
            True,
            "",
        )

    # ==================================================
    # SAVE
    # ==================================================

    def save_filter(self):
        values = self.get_form_values()

        valid, message = self.validate_form(values)

        if not valid:
            QMessageBox.warning(
                self,
                "Konfiguracja filtra",
                message,
            )

            return

        filter_obj = Filter(
            name=values["name"],
            filter_id=(self.selected_filter_id),
            active=values["active"],
            opc_url=(values["opc_url"] or None),
            delta_p_threshold=(values["delta_p_threshold"]),
            delta_p_node_id=(values["delta_p_node_id"] or None),
            status_node_id=(values["status_node_id"] or None),
            alarm_node_id=(values["alarm_node_id"] or None),
        )

        try:
            if self.selected_filter_id is None:
                self.repository.save_filter(filter_obj)

            else:
                self.repository.update_filter(filter_obj)

        except sqlite3.IntegrityError as error:
            QMessageBox.critical(
                self,
                "Błąd zapisu",
                ("Baza danych odrzuciła " "konfigurację." "\n\n" f"{error}"),
            )

            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "Błąd zapisu",
                (f"{type(error).__name__}: " f"{error}"),
            )

            return

        self.selected_filter_id = filter_obj.filter_id

        self.refresh_filters(select_filter_id=(filter_obj.filter_id))

        QMessageBox.information(
            self,
            "Konfiguracja filtra",
            ("Konfiguracja została " "zapisana."),
        )

    # ==================================================
    # HELPERS
    # ==================================================

    def find_filter_by_id(
        self,
        filter_id: int,
    ) -> Filter | None:
        for filter_obj in self.filters:
            if filter_obj.filter_id == filter_id:
                return filter_obj

        return None

    # ==================================================
    # STYLE
    # ==================================================

    def apply_style(self):
        self.setStyleSheet("""
            QWidget#filtersPage {
                background-color: #0b1220;
            }

            QLabel {
                background: transparent;
                border: none;
                color: #dbe5ef;
            }

            QLabel#pageTitle {
                color: #f8fafc;
                font-size: 24px;
                font-weight: 700;
            }

            QLabel#subtitle,
            QLabel#statusDetail,
            QLabel#hint,
            QLabel#editorState {
                color: #8296aa;
                font-size: 10px;
            }

            QLabel#statusTitle {
                color: #7e97ae;
                font-size: 9px;
                font-weight: 600;
            }

            QLabel#statusValue {
                color: #f5f8fc;
                font-size: 17px;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #f5f8fc;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#formSection {
                color: #8cb7df;
                font-size: 11px;
                font-weight: 700;
                padding-top: 8px;
            }

            QLabel#formLabel {
                color: #9eb0c2;
                font-size: 10px;
                font-weight: 600;
            }

            QFrame#panel,
            QFrame#statusCard {
                background-color: #111b28;
                border: 1px solid #26384c;
                border-radius: 8px;
            }

            QLineEdit,
            QSpinBox,
            QTableWidget {
                background-color: #0d1724;
                color: #dbe5ef;
                border: 1px solid #2a3d52;
                border-radius: 5px;
                selection-background-color: #1f4f7a;
                selection-color: #ffffff;
            }

            QLineEdit,
            QSpinBox {
                min-height: 31px;
                padding: 0 8px;
            }

            QLineEdit:focus,
            QSpinBox:focus {
                border: 1px solid #468ac4;
            }

            QCheckBox {
                color: #dbe5ef;
                spacing: 7px;
            }

            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }

            QHeaderView::section {
                background-color: #152233;
                color: #a9bacb;
                border: none;
                border-bottom: 1px solid #2a3d52;
                padding: 7px;
                font-weight: 600;
            }

            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #19283a;
            }

            QPushButton {
                min-height: 31px;
                padding: 0 14px;
                border-radius: 5px;
                font-weight: 600;
            }

            QPushButton#primaryButton {
                background-color: #2563a6;
                color: white;
                border: 1px solid #3377bd;
            }

            QPushButton#primaryButton:hover {
                background-color: #2d72b8;
            }

            QPushButton#secondaryButton {
                background-color: #172536;
                color: #dbe5ef;
                border: 1px solid #32475d;
            }

            QPushButton#secondaryButton:hover {
                background-color: #1c3045;
            }

            QPushButton#dangerButton {
                background-color: #3a1820;
                color: #ffb4bd;
                border: 1px solid #73313d;
            }

            QPushButton#dangerButton:hover {
                background-color: #51202b;
                color: #ffd0d5;
                border: 1px solid #954252;
            }

            QPushButton:disabled {
                color: #5f7183;
                background-color: #101923;
                border-color: #243342;
            }

            QScrollBar:vertical {
                background-color: #0d1723;
                width: 8px;
                margin: 2px 2px 2px 1px;
                border: none;
            }

            QScrollBar::handle:vertical {
                background-color: #354a5d;
                min-height: 20px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #4a647b;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                border: none;
                background: transparent;
            }

            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                width: 0px;
                height: 0px;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }

            QSplitter::handle {
                background-color: #0b1220;
                width: 6px;
            }
            """)
