from PySide6.QtCore import QDate, Qt, QTimer, QProcess, QUrl
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QDateEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QApplication,
    QMessageBox,
)

from PySide6.QtGui import QColor, QDesktopServices
from datetime import datetime
import sys, os, smtplib
from filters_reporting.collector_launcher import (
    get_collector_command,
)
from filters_reporting.monitoring.filter_monitor import (
    get_current_filter_statuses,
    count_attention_filters,
    get_attention_state,
    get_attention_summary,
    build_attention_rows,
    get_attention_filters,
    get_filter_status_state,
    get_system_status_counts,
    is_collector_running,
    build_filter_rows,
    get_filters_for_attention_table,
)
from filters_reporting.reporting.report_service import (
    generate_reports_for_day,
    generate_and_send_reports_for_day,
)
from filters_reporting.config import (
    EMAIL_CONFIG,
    REPORTS_DIR,
    LOG_DIR,
    LOG_FILE,
)
from email.message import EmailMessage
from filters_reporting.reporting.email_reporting import (
    send_report_email,
)


class DashboardPage(QWidget):
    def __init__(self, repository):
        super().__init__()

        self.setObjectName("dashboardPage")
        self.repository = repository
        self.collector_running = False
        self.collector_process = QProcess(self)
        self.build_ui()
        self.apply_style()
        self.refresh_database_status()
        self.refresh_attention_status()
        self.refresh_events()
        self.refresh_collector_controls()
        self.refresh_collector_status()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_dashboard)
        self.refresh_timer.start(5000)
        self.collector_process.started.connect(self.on_collector_started)
        self.collector_process.finished.connect(self.on_collector_finished)
        QApplication.instance().aboutToQuit.connect(self.shutdown_collector)
        self.show_all_filters = False

    # ======================================================
    # UI
    # ======================================================

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            20,
            14,
            20,
            14,
        )

        main_layout.setSpacing(10)

        # ==================================================
        # HEADER
        # ==================================================

        header_layout = QHBoxLayout()

        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(0)

        title = QLabel("Przegląd")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Monitoring zbierania danych, komunikacji i stanu filtrów.")
        subtitle.setObjectName("subtitle")

        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)

        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # ==================================================
        # STATUS CARDS
        # ==================================================

        status_layout = QHBoxLayout()
        status_layout.setSpacing(10)

        self.collector_card = self.create_status_card(
            "ZBIERANIE DANYCH",
            "Zatrzymane",
            "Interwał: 60 s",
        )

        self.database_card = self.create_status_card(
            "BAZA DANYCH",
            "Nie sprawdzono",
            "Brak danych",
        )

        self.filters_card = self.create_status_card(
            "FILTRY AKTYWNE",
            "—",
            "Łącznie: —",
        )

        self.attention_card = self.create_status_card(
            "WYMAGA UWAGI",
            "—",
            "Brak danych",
        )

        status_layout.addWidget(self.collector_card["frame"])

        status_layout.addWidget(self.database_card["frame"])

        status_layout.addWidget(self.filters_card["frame"])

        status_layout.addWidget(self.attention_card["frame"])

        main_layout.addLayout(status_layout)

        # ==================================================
        # ACTION ROW
        # ==================================================

        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)

        # --------------------------------------------------
        # COLLECTOR
        # --------------------------------------------------

        collector_panel = self.create_panel()

        collector_layout = QVBoxLayout(collector_panel)

        collector_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )

        collector_layout.setSpacing(6)

        collector_title = QLabel("Zbieranie danych")
        collector_title.setObjectName("sectionTitle")

        collector_description = QLabel("Odczyt danych z aktywnych filtrów.")
        collector_description.setObjectName("description")

        interval_layout = QHBoxLayout()

        interval_label = QLabel("Interwał")
        interval_label.setObjectName("fieldLabel")

        self.interval_spinbox = QSpinBox()

        self.interval_spinbox.setRange(
            5,
            300,
        )

        self.interval_spinbox.setValue(60)

        self.interval_spinbox.setSuffix(" s")

        self.interval_spinbox.setFixedWidth(90)

        interval_layout.addWidget(interval_label)

        interval_layout.addStretch()

        interval_layout.addWidget(self.interval_spinbox)

        self.collector_button = QPushButton("Uruchom")

        self.collector_button.setObjectName("primaryButton")

        self.collector_button.clicked.connect(self.toggle_collector)

        collector_layout.addWidget(collector_title)

        collector_layout.addWidget(collector_description)

        collector_layout.addStretch()

        collector_layout.addLayout(interval_layout)

        collector_layout.addWidget(self.collector_button)

        # --------------------------------------------------
        # REPORT
        # --------------------------------------------------

        report_panel = self.create_panel()

        report_layout = QVBoxLayout(report_panel)

        report_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )

        report_layout.setSpacing(6)

        report_title = QLabel("Raport dzienny")
        report_title.setObjectName("sectionTitle")

        report_description = QLabel("Excel i TXT dla wybranego dnia.")
        report_description.setObjectName("description")

        date_layout = QHBoxLayout()

        date_label = QLabel("Data")
        date_label.setObjectName("fieldLabel")

        self.report_date = QDateEdit()

        self.report_date.setDate(QDate.currentDate())

        self.report_date.setCalendarPopup(True)

        self.report_date.setDisplayFormat("yyyy-MM-dd")

        date_layout.addWidget(date_label)

        date_layout.addStretch()

        date_layout.addWidget(self.report_date)

        report_buttons = QHBoxLayout()

        self.generate_report_button = QPushButton("Generuj")

        self.generate_report_button.setObjectName("primaryButton")
        self.generate_report_button.clicked.connect(self.generate_report)

        self.generate_send_button = QPushButton("Generuj i wyślij")

        self.generate_send_button.setObjectName("secondaryButton")
        self.generate_send_button.clicked.connect(self.generate_and_send_report)

        report_buttons.addWidget(self.generate_report_button)

        report_buttons.addWidget(self.generate_send_button)

        report_layout.addWidget(report_title)

        report_layout.addWidget(report_description)

        report_layout.addStretch()

        report_layout.addLayout(date_layout)

        report_layout.addLayout(report_buttons)

        # --------------------------------------------------
        # QUICK ACTIONS
        # --------------------------------------------------

        quick_panel = self.create_panel()

        quick_layout = QVBoxLayout(quick_panel)

        quick_layout.setContentsMargins(
            14,
            11,
            14,
            11,
        )

        quick_layout.setSpacing(4)

        quick_title = QLabel("Szybkie akcje")

        quick_title.setObjectName("sectionTitle")

        quick_layout.addWidget(quick_title)

        self.open_reports_button = QPushButton("Folder raportów")
        self.open_reports_button.clicked.connect(self.open_reports_folder)
        self.show_logs_button = QPushButton("Logi")
        self.show_logs_button.clicked.connect(self.open_logs)
        self.test_smtp_button = QPushButton("Test SMTP")
        self.test_smtp_button.clicked.connect(self.test_smtp_connection)
        self.check_database_button = QPushButton("Sprawdź bazę")
        self.check_database_button.clicked.connect(self.check_database)
        for button in (
            self.open_reports_button,
            self.show_logs_button,
            self.test_smtp_button,
            self.check_database_button,
        ):
            button.setObjectName("quickButton")

            quick_layout.addWidget(button)

        action_layout.addWidget(
            collector_panel,
            1,
        )

        action_layout.addWidget(
            report_panel,
            1,
        )

        action_layout.addWidget(
            quick_panel,
            1,
        )

        main_layout.addLayout(action_layout)

        # ==================================================
        # ATTENTION
        # ==================================================

        attention_panel = self.create_panel()

        attention_layout = QVBoxLayout(attention_panel)

        attention_layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        attention_layout.setSpacing(6)

        attention_header = QHBoxLayout()

        attention_title = QLabel("Wymaga uwagi")

        attention_title.setObjectName("sectionTitle")

        self.show_all_attention_button = QPushButton("Pokaż wszystkie")

        self.show_all_attention_button.setObjectName("linkButton")
        self.show_all_attention_button.clicked.connect(self.toggle_attention_filters)
        attention_header.addWidget(attention_title)

        attention_header.addStretch()

        attention_header.addWidget(self.show_all_attention_button)

        self.attention_table = QTableWidget()

        self.attention_table.setColumnCount(4)

        self.attention_table.setHorizontalHeaderLabels(
            [
                "Filtr",
                "Ostatnia Δp",
                "Stan",
                "Ostatnia próbka",
            ]
        )

        self.attention_table.verticalHeader().setVisible(False)

        self.attention_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.attention_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.attention_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        header = self.attention_table.horizontalHeader()

        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.attention_table.setFixedHeight(128)
        filters_statuses = get_current_filter_statuses(self.repository, datetime.now())
        filter_attention_rows = build_attention_rows(filters_statuses)
        attention_filters = get_attention_filters(filters_statuses)
        self.attention_table.setRowCount(len(filter_attention_rows))

        for row, values in enumerate(filter_attention_rows):
            self.attention_table.setRowHeight(
                row,
                27,
            )

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 2:
                    filter_status = attention_filters[row]["filter_status"]
                    state = get_filter_status_state(filter_status)
                    if state == "error":
                        item.setForeground(QColor("#ef4444"))
                    elif state == "warning":
                        item.setForeground(QColor("#f59e0b"))
                if column in (
                    1,
                    4,
                ):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.attention_table.setItem(
                    row,
                    column,
                    item,
                )

        attention_layout.addLayout(attention_header)

        attention_layout.addWidget(self.attention_table)

        main_layout.addWidget(attention_panel)

        # ==================================================
        # BOTTOM
        # ==================================================

        lower_layout = QGridLayout()

        lower_layout.setHorizontalSpacing(10)

        # --------------------------------------------------
        # EVENTS
        # --------------------------------------------------

        events_panel = self.create_panel()

        events_layout = QVBoxLayout(events_panel)

        events_layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        events_layout.setSpacing(6)

        events_title = QLabel("Ostatnie zdarzenia")

        events_title.setObjectName("sectionTitle")

        self.events_table = QTableWidget()

        self.events_table.setColumnCount(2)

        self.events_table.setHorizontalHeaderLabels(
            [
                "Czas",
                "Zdarzenie",
            ]
        )

        self.events_table.verticalHeader().setVisible(False)

        self.events_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.events_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        event_header = self.events_table.horizontalHeader()

        event_header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents,
        )

        event_header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        self.events_table.setFixedHeight(128)
        self.events_table.setRowCount(0)

        events_layout.addWidget(events_title)

        events_layout.addWidget(self.events_table)

        # --------------------------------------------------
        # SYSTEM STATE
        # --------------------------------------------------

        stats_panel = self.create_panel()

        stats_layout = QVBoxLayout(stats_panel)

        stats_layout.setContentsMargins(
            14,
            10,
            14,
            10,
        )

        stats_layout.setSpacing(4)

        stats_title = QLabel("Stan systemu")

        stats_title.setObjectName("sectionTitle")

        stats_layout.addWidget(stats_title)

        self.total_filters_stat = self.create_stat_row(
            "Filtry",
            "30",
        )

        self.ok_filters_stat = self.create_stat_row(
            "OK",
            "27",
        )

        self.attention_filters_stat = self.create_stat_row(
            "Uwaga",
            "2",
        )

        self.offline_filters_stat = self.create_stat_row(
            "Offline",
            "1",
        )

        for stat in (
            self.total_filters_stat,
            self.ok_filters_stat,
            self.attention_filters_stat,
            self.offline_filters_stat,
        ):
            stats_layout.addWidget(stat["frame"])

        lower_layout.addWidget(
            events_panel,
            0,
            0,
        )

        lower_layout.addWidget(
            stats_panel,
            0,
            1,
        )

        lower_layout.setColumnStretch(
            0,
            3,
        )

        lower_layout.setColumnStretch(
            1,
            1,
        )

        main_layout.addLayout(lower_layout)

    # ======================================================
    # HELPERS
    # ======================================================

    def create_panel(self):
        panel = QFrame()

        panel.setObjectName("panel")

        return panel

    def create_status_card(
        self,
        title,
        value,
        detail,
    ):
        frame = QFrame()

        frame.setObjectName("statusCard")

        frame.setFixedHeight(82)

        layout = QVBoxLayout(frame)

        layout.setContentsMargins(
            14,
            9,
            14,
            9,
        )

        layout.setSpacing(1)

        title_label = QLabel(title)

        title_label.setObjectName("statusTitle")

        value_label = QLabel(value)

        value_label.setObjectName("statusValue")

        detail_label = QLabel(detail)

        detail_label.setObjectName("statusDetail")

        layout.addWidget(title_label)

        layout.addWidget(value_label)

        layout.addWidget(detail_label)

        return {
            "frame": frame,
            "title": title_label,
            "value": value_label,
            "detail": detail_label,
        }

    def create_stat_row(
        self,
        name,
        value,
    ):
        frame = QFrame()

        frame.setObjectName("statRow")

        frame.setFixedHeight(24)

        layout = QHBoxLayout(frame)

        layout.setContentsMargins(
            9,
            2,
            9,
            2,
        )

        name_label = QLabel(name)

        name_label.setObjectName("statName")

        value_label = QLabel(value)

        value_label.setObjectName("statValue")

        layout.addWidget(name_label)

        layout.addStretch()

        layout.addWidget(value_label)

        return {
            "frame": frame,
            "name": name_label,
            "value": value_label,
        }

    # ======================================================
    # STATUS
    # ======================================================

    def set_status_card_state(
        self,
        card,
        state,
    ):
        colors = {
            "ok": "#22c55e",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "neutral": "#f5f8fc",
        }

        color = colors.get(
            state,
            colors["neutral"],
        )

        card["value"].setStyleSheet(f"""
            color: {color};
            font-size: 17px;
            font-weight: 700;
            """)

    # ======================================================
    # REFRESH
    # ======================================================
    def refresh_dashboard(self):
        self.refresh_database_status()
        self.refresh_attention_status()
        self.refresh_collector_status()
        self.refresh_attention_table()
        self.refresh_collector_controls()
        self.refresh_events()

    def refresh_database_status(self):
        try:
            total, active = self.repository.get_filter_counts()
            self.database_card["value"].setText("OK")
            self.database_card["detail"].setText(f"{total} filtrów w bazie")
            self.set_status_card_state(
                self.database_card,
                "ok",
            )
            self.filters_card["value"].setText(str(active))
            self.filters_card["detail"].setText(f"Łącznie: {total}")
            self.set_status_card_state(
                self.filters_card,
                "ok",
            )
            self.total_filters_stat["value"].setText(str(total))
        except Exception as error:
            self.database_card["value"].setText("Błąd")
            self.database_card["detail"].setText(str(error))
            self.set_status_card_state(
                self.database_card,
                "error",
            )

    def refresh_attention_status(self):
        filter_statuses = get_current_filter_statuses(
            self.repository,
            datetime.now(),
        )
        attention_count = count_attention_filters(filter_statuses)
        attention_state = get_attention_state(filter_statuses)
        attention_summary = get_attention_summary(filter_statuses)
        self.attention_card["value"].setText(str(attention_count))
        self.attention_card["detail"].setText(attention_summary)
        self.set_status_card_state(
            self.attention_card,
            attention_state,
        )
        system_counts = get_system_status_counts(filter_statuses)
        self.total_filters_stat["value"].setText(str(system_counts["total"]))
        self.ok_filters_stat["value"].setText(str(system_counts["ok"]))
        self.attention_filters_stat["value"].setText(str(system_counts["attention"]))
        self.offline_filters_stat["value"].setText(str(system_counts["offline"]))

    def refresh_collector_status(self):
        now = datetime.now()
        heartbeat = self.repository.get_collector_heartbeat()
        collector_running = is_collector_running(
            heartbeat,
            now,
        )
        if not collector_running:
            self.collector_card["value"].setText("Zatrzymane")
            self.collector_card["detail"].setText("Collector nie pracuje")
            self.set_status_card_state(
                self.collector_card,
                "neutral",
            )
            return
        active_count, connected_count = self.repository.get_connection_counts()
        self.collector_card["value"].setText("Uruchomione")
        self.collector_card["detail"].setText(
            f"OPC UA: {connected_count} / " f"{active_count} połączonych"
        )
        if active_count == 0:
            state = "neutral"
        elif connected_count == active_count:
            state = "ok"
        elif connected_count == 0:
            state = "error"
        else:
            state = "warning"
        self.set_status_card_state(
            self.collector_card,
            state,
        )

    def refresh_attention_table(self):
        filter_statuses = get_current_filter_statuses(
            self.repository,
            datetime.now(),
        )
        visible_filters = get_filters_for_attention_table(
            filter_statuses,
            self.show_all_filters,
        )
        status_labels = {
            "clean-working": "Czysty – praca",
            "dirty-working": "Brudny – praca",
            "clean-stopped": "Czysty – postój",
            "dirty-stopped": "Brudny – postój",
            "error": "Awaria",
            "offline": "Offline",
            "monitoring-stopped": ("Monitoring zatrzymany"),
        }
        self.attention_table.setRowCount(len(visible_filters))
        for row, filter_data in enumerate(visible_filters):
            self.attention_table.setRowHeight(
                row,
                27,
            )
            delta_p = filter_data["delta_p"]
            if delta_p is None:
                delta_p_text = "—"
            else:
                delta_p_text = f"{delta_p} Pa"
            timestamp = filter_data["timestamp"]
            if timestamp is None:
                timestamp_text = "—"
            else:
                timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            filter_status = filter_data["filter_status"]
            status_text = status_labels.get(
                filter_status,
                filter_status,
            )
            values = [
                filter_data["filter_name"],
                delta_p_text,
                status_text,
                timestamp_text,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column in (
                    1,
                    3,
                ):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.attention_table.setItem(
                    row,
                    column,
                    item,
                )

    def refresh_collector_controls(self):
        now = datetime.now()
        heartbeat = self.repository.get_collector_heartbeat()
        collector_running = is_collector_running(heartbeat, now)
        if collector_running:
            self.collector_button.setText("Zatrzymaj")
            self.collector_button.setEnabled(True)
            self.interval_spinbox.setEnabled(False)
        else:
            self.collector_button.setText("Uruchom")
            self.collector_button.setEnabled(True)
            self.interval_spinbox.setEnabled(True)

    def refresh_events(self):
        events = self.repository.get_recent_events(limit=10)
        self.events_table.setRowCount(len(events))
        for row, event in enumerate(events):
            timestamp, event_type, message = event
            self.events_table.setRowHeight(
                row,
                27,
            )
            time_text = timestamp.strftime("%H:%M:%S")
            self.events_table.setItem(
                row,
                0,
                QTableWidgetItem(time_text),
            )
            self.events_table.setItem(
                row,
                1,
                QTableWidgetItem(message),
            )

    # ======================================================
    # ACTIONS
    # ======================================================
    # Collector_Start_Stop
    # ======================================================
    def toggle_collector(self):
        now = datetime.now()
        heartbeat = self.repository.get_collector_heartbeat()
        collector_running = is_collector_running(
            heartbeat,
            now,
        )
        if collector_running:
            self.collector_button.setEnabled(False)
            self.collector_card["value"].setText("Zatrzymywanie...")
            self.repository.request_collector_stop()
            QTimer.singleShot(
                2000,
                self.force_kill_collector,
            )
            return
        self.collector_button.setEnabled(False)
        self.collector_card["value"].setText("Uruchamianie...")
        try:
            program, arguments = get_collector_command(self.interval_spinbox.value())

        except FileNotFoundError as error:
            self.collector_button.setEnabled(True)

            self.collector_card["value"].setText("Błąd uruchomienia")

            self.set_status_card_state(
                self.collector_card,
                "error",
            )

            QMessageBox.critical(
                self,
                "Collector",
                str(error),
            )

            return

        self.collector_process.start(
            program,
            arguments,
        )

    def on_collector_started(self):
        self.collector_button.setEnabled(True)
        self.collector_button.setText("Zatrzymaj")
        self.collector_card["value"].setText("Uruchomione")

        self.set_status_card_state(
            self.collector_card,
            "ok",
        )
        self.refresh_collector_status()
        self.repository.add_event(
            "collector_started",
            "Uruchomiono zbieranie danych",
        )
        self.refresh_events()

    def on_collector_finished(
        self,
        exit_code,
        exit_status,
    ):
        self.collector_button.setEnabled(True)
        self.collector_button.setText("Uruchom")
        self.collector_card["value"].setText("Zatrzymane")
        self.set_status_card_state(
            self.collector_card,
            "neutral",
        )
        self.repository.add_event(
            "collector_stopped",
            "Zatrzymano zbieranie danych",
        )
        self.refresh_events()

    def force_kill_collector(self):
        if self.collector_process.state() != QProcess.ProcessState.NotRunning:
            self.collector_process.kill()

    def shutdown_collector(self):
        if self.collector_process.state() == QProcess.ProcessState.NotRunning:
            return
        self.collector_process.terminate()
        if not self.collector_process.waitForFinished(1000):
            self.collector_process.kill()
            self.collector_process.waitForFinished(1000)

    # ======================================================
    # REPORT GENERATOR
    # =============================================
    def generate_report(self):
        chosen_day = self.report_date.date().toString("yyyy-MM-dd")
        try:
            result = generate_reports_for_day(
                self.repository,
                chosen_day,
            )
            if not result:
                QMessageBox.warning(
                    self,
                    "Raport",
                    "Brak danych dla wybranej daty.",
                )
                return
            QMessageBox.information(
                self,
                "Raport",
                "Raport został wygenerowany.",
            )
            self.repository.add_event(
                "report_generated",
                f"Wygenerowano raport za {chosen_day}",
            )
        except PermissionError:
            QMessageBox.critical(
                self,
                "Błąd zapisu",
                "Nie można zapisać raportu.\n" "Plik jest prawdopodobnie otwarty.",
            )

    def generate_and_send_report(self):
        chosen_day = self.report_date.date().toString("yyyy-MM-dd")
        try:
            result = generate_and_send_reports_for_day(
                self.repository,
                chosen_day,
                EMAIL_CONFIG,
            )
            if not result:
                QMessageBox.warning(
                    self,
                    "Brak danych",
                    "Brak danych dla wybranej daty.",
                )
                return
            QMessageBox.information(
                self,
                "Raport",
                "Raport został wygenerowany i wysłany.",
            )
            self.repository.add_event(
                "report_sent",
                f"Wysłano raport za {chosen_day}",
            )
        except PermissionError:
            QMessageBox.warning(
                self,
                "Błąd zapisu",
                "Nie można zapisać raportu.\n" "Plik może być otwarty.",
            )
        except smtplib.SMTPAuthenticationError:
            QMessageBox.critical(
                self,
                "Błąd poczty",
                "Nie udało się zalogować " "do serwera SMTP.",
            )
        except (
            ConnectionError,
            TimeoutError,
        ):
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można połączyć się " "z serwerem pocztowym.",
            )
        except smtplib.SMTPException:
            QMessageBox.warning(
                self,
                "Błąd wysyłania",
                "Nie udało się wysłać raportu.",
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Błąd",
                f"{type(error).__name__}:\n{error}",
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Nieoczekiwany błąd",
                str(error),
            )

    # ======================================================
    # QUICK ACTIONS
    # ======================================================

    def toggle_attention_filters(self):
        self.show_all_filters = not self.show_all_filters
        if self.show_all_filters:
            self.show_all_attention_button.setText("Pokaż wymagające uwagi")
        else:
            self.show_all_attention_button.setText("Pokaż wszystkie")
        self.refresh_attention_table()

    def open_reports_folder(self):
        REPORTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(REPORTS_DIR.resolve())))

    def open_logs(self):
        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        if not LOG_FILE.exists():
            QMessageBox.warning(
                self,
                "Logi",
                "Plik logów jeszcze nie istnieje.",
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(LOG_FILE.resolve())))

    def test_smtp_connection(self):
        msg = EmailMessage()
        msg["Subject"] = "FiltersReporting - test SMTP"
        msg["From"] = EMAIL_CONFIG.sender
        msg["To"] = ", ".join(EMAIL_CONFIG.recipients)
        msg.set_content("Test połączenia SMTP " "z aplikacji FiltersReporting.")
        try:
            send_report_email(
                msg,
                EMAIL_CONFIG,
            )
            QMessageBox.information(
                self,
                "SMTP",
                "Wiadomość testowa została wysłana.",
            )
        except smtplib.SMTPAuthenticationError:
            QMessageBox.critical(
                self,
                "SMTP",
                "Błąd uwierzytelnienia SMTP.",
            )
        except smtplib.SMTPException as error:
            QMessageBox.critical(
                self,
                "SMTP",
                f"Błąd SMTP:\n{error}",
            )
        except OSError as error:
            QMessageBox.critical(
                self,
                "SMTP",
                f"Błąd połączenia:\n{error}",
            )

    def check_database(self):
        try:
            total, active = self.repository.get_filter_counts()
            QMessageBox.information(
                self,
                "Baza danych",
                (
                    "Połączenie z bazą działa.\n\n"
                    f"Filtry: {total}\n"
                    f"Aktywne: {active}"
                ),
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Baza danych",
                f"Błąd bazy danych:\n{error}",
            )

    # ======================================================
    # STYLE
    # ======================================================

    def apply_style(self):
        self.setStyleSheet("""
            QWidget#dashboardPage {
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

            QLabel#subtitle {
                color: #8296aa;
                font-size: 11px;
            }

            QFrame#panel,
            QFrame#statusCard {
                background-color: #111b28;
                border: 1px solid #26384c;
                border-radius: 8px;
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

            QLabel#statusDetail {
                color: #8295a8;
                font-size: 9px;
            }

            QLabel#sectionTitle {
                color: #f5f8fc;
                font-size: 14px;
                font-weight: 700;
            }

            QLabel#description {
                color: #8295a8;
                font-size: 10px;
            }

            QLabel#fieldLabel,
            QLabel#statName {
                color: #94a5b5;
                font-size: 10px;
            }

            QFrame#statRow {
                background-color: #0d1723;
                border: 1px solid #203246;
                border-radius: 5px;
            }

            QLabel#statValue {
                color: #f8fafc;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton {
                min-height: 29px;
                border-radius: 5px;
                padding-left: 10px;
                padding-right: 10px;
                font-size: 10px;
            }

            QPushButton#primaryButton {
                background-color: #1f6feb;
                border: 1px solid #1f6feb;
                color: white;
                font-weight: 600;
            }

            QPushButton#primaryButton:hover {
                background-color: #2d7cf0;
            }

            QPushButton#secondaryButton {
                background-color: transparent;
                border: 1px solid #3b82f6;
                color: #67adff;
                font-weight: 600;
            }

            QPushButton#secondaryButton:hover {
                background-color: #15263b;
            }

            QPushButton#quickButton {
                min-height: 23px;
                background-color: #162231;
                border: 1px solid #293d52;
                color: #d7e1eb;
                text-align: left;
                padding-left: 10px;
            }

            QPushButton#quickButton:hover {
                background-color: #1d2e40;
            }

            QPushButton#linkButton {
                min-height: 18px;
                background: transparent;
                border: none;
                color: #60a5fa;
                padding: 0 4px;
                font-size: 10px;
                font-weight: 600;
            }

            QSpinBox,
            QDateEdit {
                background-color: #0d1723;
                border: 1px solid #32495f;
                border-radius: 5px;
                min-height: 27px;
                padding-left: 6px;
                padding-right: 6px;
                color: #edf4fa;
                font-size: 10px;
            }

            QTableWidget {
                background-color: #0d1723;
                border: 1px solid #24394d;
                border-radius: 5px;
                gridline-color: #213345;
                color: #d7e2ec;
                selection-background-color: #1c4f83;
                font-size: 10px;
            }

            QTableWidget::item {
                background: transparent;
                padding-left: 5px;
                padding-right: 5px;
            }

            QHeaderView::section {
                background-color: #172536;
                color: #9fb2c4;
                border: none;
                border-bottom: 1px solid #31495e;
                padding: 5px;
                font-size: 10px;
                font-weight: 600;
            }

            QTableCornerButton::section {
                background-color: #172536;
                border: none;
            }

            QScrollBar:vertical {
                background-color: #0d1723;
                width: 6px;
            }

            QScrollBar::handle:vertical {
                background-color: #354a5d;
                min-height: 20px;
                border-radius: 3px;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            """)
