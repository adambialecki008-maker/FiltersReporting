from PySide6.QtCore import (
    Qt,
    QProcess,
    QTimer,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from filters_reporting.gui.pages.dashboard_page import (
    DashboardPage,
)
from filters_reporting.gui.pages.filters_page import (
    FiltersPage,
)
from filters_reporting.gui.pages.reports_page import (
    ReportsPage,
)
from filters_reporting.gui.pages.settings_page import (
    SettingsPage,
)
from filters_reporting.scheduling.report_scheduler import (
    ReportScheduler,
)


class MainWindow(QMainWindow):
    def __init__(
        self,
        repository,
    ):
        super().__init__()

        self.setWindowTitle("Filters Reporting")

        self.resize(
            1180,
            720,
        )

        self.setMinimumSize(
            1000,
            650,
        )

        self.repository = repository

        central_widget = QWidget()

        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(0)

        # ==================================================
        # NAVIGATION
        # ==================================================

        self.navigation = QListWidget()

        self.navigation.setObjectName("navigation")

        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.navigation.setFixedWidth(190)

        dashboard_item = QListWidgetItem("Przegląd")

        dashboard_item.setToolTip(
            "Podgląd stanu systemu, " "filtrów i sterowanie " "collectorem."
        )

        filters_item = QListWidgetItem("Filtry")

        filters_item.setToolTip("Konfiguracja filtrów, " "endpointów OPC UA i NodeId.")

        reports_item = QListWidgetItem("Raporty")

        reports_item.setToolTip("Generowanie, wysyłanie " "i przegląd raportów.")

        settings_item = QListWidgetItem("Ustawienia")

        settings_item.setToolTip("Konfiguracja folderu " "raportów i serwera SMTP.")

        self.navigation.addItem(dashboard_item)

        self.navigation.addItem(filters_item)

        self.navigation.addItem(reports_item)

        self.navigation.addItem(settings_item)

        # ==================================================
        # PAGES
        # ==================================================

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage(self.repository)

        self.filters_page = FiltersPage(self.repository)

        self.reports_page = ReportsPage(self.repository)

        self.settings_page = SettingsPage(self.repository)

        self.report_scheduler = ReportScheduler(self.repository)

        self.scheduler_timer = QTimer(self)

        self.scheduler_timer.timeout.connect(self.run_scheduled_tasks)

        self.scheduler_timer.start(30_000)

        QTimer.singleShot(
            1_000,
            self.run_scheduled_tasks,
        )

        self.pages.addWidget(self.dashboard_page)

        self.pages.addWidget(self.filters_page)

        self.pages.addWidget(self.reports_page)

        self.pages.addWidget(self.settings_page)

        main_layout.addWidget(self.navigation)

        main_layout.addWidget(self.pages)

        self.navigation.currentRowChanged.connect(self.change_page)

        self.navigation.setCurrentRow(0)

        # ==================================================
        # STATUS BAR
        # ==================================================

        author_label = QLabel("made by AB")

        author_label.setStyleSheet("""
            color: #718399;
            font-size: 9px;
            padding-right: 6px;
            background: transparent;
        """)

        self.statusBar().addPermanentWidget(author_label)

        # ==================================================
        # STYLE
        # ==================================================

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b1220;
            }

            QWidget {
                background-color: #0b1220;
                color: #dce6ef;
                font-family: Segoe UI;
            }

            QStackedWidget {
                background-color: #0b1220;
                border: none;
            }

            QListWidget#navigation {
                background-color: #101827;
                color: #d7e0ea;
                border: none;
                font-size: 14px;
                padding-top: 12px;
            }

            QListWidget#navigation::item {
                padding: 12px 14px;
                margin: 3px 8px;
                border-radius: 7px;
            }

            QListWidget#navigation::item:selected {
                background-color: #1e293b;
                color: white;
            }

            QListWidget#navigation::item:hover {
                background-color: #182438;
            }

            QToolTip {
                background-color: #172536;
                color: #dce6ef;
                border: 1px solid #32475d;
                padding: 6px;
            }

            QStatusBar {
                background-color: #101827;
                border: none;
                color: #7f91a5;
                min-height: 20px;
                max-height: 20px;
            }

            QStatusBar QLabel {
                background: transparent;
            }
        """)

    # ==================================================
    # PAGE NAVIGATION
    # ==================================================

    def change_page(
        self,
        index,
    ):
        if index < 0:
            return

        self.pages.setCurrentIndex(index)

        current_page = self.pages.currentWidget()

        if current_page is self.reports_page:
            self.reports_page.refresh_page()

        elif current_page is self.settings_page:
            self.settings_page.reload_settings()

        elif current_page is self.filters_page:
            self.filters_page.refresh_filters()

        elif current_page is self.dashboard_page:
            self.dashboard_page.refresh_dashboard()

    # ==================================================
    # SCHEDULED TASKS
    # ==================================================

    def run_scheduled_tasks(
        self,
    ):
        result = self.report_scheduler.check()

        if result is None:
            return

        self.dashboard_page.refresh_events()

        if self.pages.currentWidget() is self.reports_page:
            self.reports_page.refresh_page()

    # ==================================================
    # CLOSE
    # ==================================================

    def closeEvent(
        self,
        event,
    ):
        self.scheduler_timer.stop()

        self.repository.request_collector_stop()

        collector_process = self.dashboard_page.collector_process

        if collector_process.state() != QProcess.ProcessState.NotRunning:
            collector_process.waitForFinished(5000)

        super().closeEvent(event)
