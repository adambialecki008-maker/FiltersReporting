from __future__ import annotations

import smtplib
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QDate,
    QTimer,
    Qt,
    QUrl,
)
from PySide6.QtGui import (
    QDesktopServices,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from filters_reporting.reporting.email_reporting import (
    send_generated_report,
)
from filters_reporting.reporting.report_service import (
    generate_reports_for_day,
)
from filters_reporting.settings_service import (
    apply_settings_runtime,
    load_settings,
    move_generated_report_files,
)


class ReportsPage(QWidget):
    def __init__(
        self,
        repository,
    ):
        super().__init__()

        self.setObjectName("reportsPage")

        self.repository = repository

        self.settings = None
        self.reports_dir = None
        self.current_stats = []

        self.build_ui()
        self.apply_style()

        # QDateEdit ustawia maximumDate tylko w momencie
        # tworzenia widgetu.
        # Jeżeli aplikacja działa przez północ, limit daty
        # musi zostać odświeżony bez restartu aplikacji.
        self._date_limit_timer = QTimer(self)
        self._date_limit_timer.setInterval(30_000)
        self._date_limit_timer.timeout.connect(self.refresh_report_date_limit)
        self._date_limit_timer.start()

        self.refresh_page()

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

        title = QLabel("Raporty")
        title.setObjectName("pageTitle")

        subtitle = QLabel("Generowanie, wysyłanie " "i przegląd raportów dziennych.")
        subtitle.setObjectName("subtitle")

        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)

        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        self.open_folder_button = QPushButton("Folder raportów")
        self.open_folder_button.setObjectName("secondaryButton")
        self.open_folder_button.clicked.connect(self.open_reports_folder)

        header_layout.addWidget(self.open_folder_button)

        main_layout.addLayout(header_layout)

        # ----------------------------------------------
        # STATUS CARDS
        # ----------------------------------------------

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.date_card = self.create_status_card(
            "WYBRANY DZIEŃ",
            "—",
            "Raport dzienny",
        )

        self.samples_card = self.create_status_card(
            "PRÓBKI",
            "—",
            "Brak danych",
        )

        self.filters_card = self.create_status_card(
            "FILTRY W RAPORCIE",
            "—",
            "Brak danych",
        )

        self.files_card = self.create_status_card(
            "PLIKI RAPORTU",
            "—",
            "Excel + TXT",
        )

        for card in (
            self.date_card,
            self.samples_card,
            self.filters_card,
            self.files_card,
        ):
            cards_layout.addWidget(card["frame"])

        main_layout.addLayout(cards_layout)

        # ----------------------------------------------
        # GENERATOR
        # ----------------------------------------------

        generator_panel = self.create_panel()

        generator_layout = QVBoxLayout(generator_panel)

        generator_layout.setContentsMargins(
            16,
            13,
            16,
            13,
        )

        generator_layout.setSpacing(10)

        generator_title = QLabel("Raport dzienny")
        generator_title.setObjectName("sectionTitle")

        generator_description = QLabel(
            "Wybierz datę, sprawdź dane " "i wygeneruj raport Excel + TXT."
        )
        generator_description.setObjectName("hint")

        generator_layout.addWidget(generator_title)
        generator_layout.addWidget(generator_description)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        date_label = QLabel("Data")
        date_label.setObjectName("formLabel")

        action_layout.addWidget(date_label)

        self.report_date = QDateEdit()

        self.report_date.setCalendarPopup(True)

        self.report_date.setDisplayFormat("yyyy-MM-dd")

        self.report_date.setDate(QDate.currentDate())

        self.report_date.setMaximumDate(QDate.currentDate())

        self.report_date.setMinimumWidth(145)

        self.report_date.dateChanged.connect(self.refresh_day_data)

        action_layout.addWidget(self.report_date)

        action_layout.addStretch()

        self.refresh_button = QPushButton("Odśwież")
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(self.refresh_page)

        self.generate_button = QPushButton("Generuj")
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(self.generate_report)

        self.generate_send_button = QPushButton("Generuj i wyślij")
        self.generate_send_button.setObjectName("outlinePrimaryButton")
        self.generate_send_button.clicked.connect(self.generate_and_send_report)

        action_layout.addWidget(self.refresh_button)
        action_layout.addWidget(self.generate_button)
        action_layout.addWidget(self.generate_send_button)

        generator_layout.addLayout(action_layout)

        self.operation_status_label = QLabel("Gotowe.")
        self.operation_status_label.setObjectName("operationStatus")

        self.path_label = QLabel("")
        self.path_label.setObjectName("pathLabel")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        generator_layout.addWidget(self.operation_status_label)

        generator_layout.addWidget(self.path_label)

        main_layout.addWidget(generator_panel)

        # ----------------------------------------------
        # PREVIEW
        # ----------------------------------------------

        preview_panel = self.create_panel()

        preview_layout = QVBoxLayout(preview_panel)

        preview_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        preview_layout.setSpacing(8)

        preview_header = QHBoxLayout()

        preview_title = QLabel("Podgląd danych dla raportu")
        preview_title.setObjectName("sectionTitle")

        self.preview_state_label = QLabel("—")
        self.preview_state_label.setObjectName("smallMuted")

        preview_header.addWidget(preview_title)
        preview_header.addStretch()
        preview_header.addWidget(self.preview_state_label)

        preview_layout.addLayout(preview_header)

        self.preview_table = QTableWidget(
            0,
            8,
        )

        self.preview_table.setHorizontalHeaderLabels(
            [
                "Filtr",
                "Próbki",
                "Min Δp",
                "Śr. Δp",
                "Max Δp",
                "Próg Δp",
                "Alarm %",
                "Praca %",
            ]
        )

        self.preview_table.verticalHeader().setVisible(False)

        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.preview_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.preview_table.setShowGrid(False)

        # Pionowy scroll zawsze widoczny.
        self.preview_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        # Płynne przewijanie kółkiem myszy.
        self.preview_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        # Nie chcemy poziomego scrolla.
        self.preview_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        preview_header_view = self.preview_table.horizontalHeader()

        preview_header_view.setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )

        for column in range(
            1,
            8,
        ):
            preview_header_view.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        # Celowo ograniczona wysokość.
        # Przy 5+ filtrach tabela ma mieć realny
        # zakres przewijania.
        self.preview_table.setFixedHeight(150)

        preview_layout.addWidget(self.preview_table)

        main_layout.addWidget(preview_panel)

        # ----------------------------------------------
        # FILES
        # ----------------------------------------------

        files_panel = self.create_panel()

        files_layout = QVBoxLayout(files_panel)

        files_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        files_layout.setSpacing(8)

        files_header = QHBoxLayout()

        files_title = QLabel("Wygenerowane raporty")
        files_title.setObjectName("sectionTitle")

        self.open_selected_button = QPushButton("Otwórz plik")
        self.open_selected_button.setObjectName("secondaryButton")
        self.open_selected_button.setEnabled(False)
        self.open_selected_button.clicked.connect(self.open_selected_report)

        files_header.addWidget(files_title)
        files_header.addStretch()
        files_header.addWidget(self.open_selected_button)

        files_layout.addLayout(files_header)

        self.files_table = QTableWidget(
            0,
            4,
        )

        self.files_table.setHorizontalHeaderLabels(
            [
                "Plik",
                "Format",
                "Rozmiar",
                "Zmodyfikowano",
            ]
        )

        self.files_table.verticalHeader().setVisible(False)

        self.files_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.files_table.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.files_table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.files_table.setShowGrid(False)

        files_header_view = self.files_table.horizontalHeader()

        files_header_view.setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )

        files_header_view.setSectionResizeMode(
            1,
            QHeaderView.ResizeToContents,
        )

        files_header_view.setSectionResizeMode(
            2,
            QHeaderView.ResizeToContents,
        )

        files_header_view.setSectionResizeMode(
            3,
            QHeaderView.ResizeToContents,
        )

        self.files_table.itemSelectionChanged.connect(self.on_report_file_selected)

        self.files_table.cellDoubleClicked.connect(self.open_report_from_row)

        self.files_table.setMinimumHeight(145)

        files_layout.addWidget(self.files_table)

        main_layout.addWidget(
            files_panel,
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
        title_text,
        value_text,
        detail_text,
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

    # ==================================================
    # SETTINGS
    # ==================================================

    def reload_settings(self):
        self.settings = load_settings()

        apply_settings_runtime(self.settings)

        self.reports_dir = Path(self.settings.reports_dir)

        self.reports_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path_label.setText(("Folder raportów: " f"{self.reports_dir}"))

    # ==================================================
    # DATE / REFRESH
    # ==================================================

    def refresh_report_date_limit(
        self,
    ) -> None:
        today = QDate.currentDate()

        if self.report_date.maximumDate() != today:
            self.report_date.setMaximumDate(today)

    def showEvent(
        self,
        event,
    ) -> None:
        self.refresh_report_date_limit()

        super().showEvent(event)

    def get_chosen_day(self):
        self.refresh_report_date_limit()

        return self.report_date.date().toString("yyyy-MM-dd")

    def refresh_page(self):
        self.refresh_report_date_limit()

        self.reload_settings()

        self.refresh_day_data()

        self.refresh_report_files()

    def refresh_day_data(self):
        chosen_day = self.get_chosen_day()

        self.date_card["value"].setText(chosen_day)

        try:
            stats = self.repository.get_daily_filter_stats(chosen_day)

        except Exception as error:
            stats = []

            self.operation_status_label.setText(("Błąd odczytu danych: " f"{error}"))

        if stats is None:
            stats = []

        self.current_stats = stats

        self.populate_preview_table(stats)

        sample_count = sum(stat.sample_count for stat in stats)

        filter_count = len(stats)

        self.samples_card["value"].setText(str(sample_count))

        self.filters_card["value"].setText(str(filter_count))

        has_data = sample_count > 0

        self.generate_button.setEnabled(has_data)

        self.generate_send_button.setEnabled(has_data)

        if has_data:
            self.samples_card["detail"].setText("Dane dostępne")

            self.filters_card["detail"].setText((f"{filter_count} " "filtrów z danymi"))

            self.preview_state_label.setText(
                (f"{sample_count} próbek | " f"{filter_count} filtrów")
            )

        else:
            self.samples_card["detail"].setText("Brak danych")

            self.filters_card["detail"].setText("Brak danych")

            self.preview_state_label.setText(("Brak danych dla " "wybranej daty"))

        self.refresh_files_card()

    def populate_preview_table(
        self,
        stats,
    ):
        self.preview_table.setRowCount(len(stats))

        for row, stat in enumerate(stats):
            sample_count = stat.sample_count or 0

            alarm_count = stat.alarm_count or 0

            status_count = stat.status_count or 0

            if sample_count:
                alarm_percent = alarm_count / sample_count * 100

                work_percent = status_count / sample_count * 100

            else:
                alarm_percent = 0
                work_percent = 0

            values = [
                stat.filter_name,
                sample_count,
                self.format_delta_p(stat.min_delta_p),
                self.format_delta_p(stat.avg_delta_p),
                self.format_delta_p(stat.max_delta_p),
                self.format_delta_p(stat.delta_p_threshold),
                f"{alarm_percent:.1f}%",
                f"{work_percent:.1f}%",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column != 0:
                    item.setTextAlignment(Qt.AlignCenter)

                self.preview_table.setItem(
                    row,
                    column,
                    item,
                )

            self.preview_table.setRowHeight(
                row,
                29,
            )

    # ==================================================
    # FILES
    # ==================================================

    def get_report_files(self):
        if not self.reports_dir:
            return []

        if not self.reports_dir.exists():
            return []

        files = [
            path
            for path in self.reports_dir.iterdir()
            if (
                path.is_file()
                and path.suffix.lower()
                in {
                    ".xlsx",
                    ".txt",
                }
            )
        ]

        return sorted(
            files,
            key=lambda path: (path.stat().st_mtime),
            reverse=True,
        )

    def get_files_for_chosen_day(
        self,
    ):
        chosen_day = self.get_chosen_day()

        return [path for path in self.get_report_files() if chosen_day in path.name]

    def refresh_report_files(self):
        files = self.get_report_files()

        self.files_table.setRowCount(len(files))

        self.open_selected_button.setEnabled(False)

        for row, path in enumerate(files):
            file_stat = path.stat()

            modified = datetime.fromtimestamp(file_stat.st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            values = [
                path.name,
                path.suffix.upper().lstrip("."),
                self.format_file_size(file_stat.st_size),
                modified,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setData(
                        Qt.UserRole,
                        str(path),
                    )

                if column in (
                    1,
                    2,
                    3,
                ):
                    item.setTextAlignment(Qt.AlignCenter)

                self.files_table.setItem(
                    row,
                    column,
                    item,
                )

            self.files_table.setRowHeight(
                row,
                29,
            )

        self.refresh_files_card()

    def refresh_files_card(self):
        if not self.reports_dir:
            return

        files = self.get_files_for_chosen_day()

        self.files_card["value"].setText(str(len(files)))

        suffixes = {path.suffix.lower() for path in files}

        if ".xlsx" in suffixes and ".txt" in suffixes:
            detail = "Excel + TXT gotowe"

        elif files:
            detail = "Niepełny zestaw plików"

        else:
            detail = "Brak raportu dla dnia"

        self.files_card["detail"].setText(detail)

    def on_report_file_selected(
        self,
    ):
        selected_rows = self.files_table.selectionModel().selectedRows()

        self.open_selected_button.setEnabled(bool(selected_rows))

    def get_selected_report_path(
        self,
    ):
        selected_rows = self.files_table.selectionModel().selectedRows()

        if not selected_rows:
            return None

        row = selected_rows[0].row()

        item = self.files_table.item(
            row,
            0,
        )

        if item is None:
            return None

        value = item.data(Qt.UserRole)

        if not value:
            return None

        return Path(value)

    def open_selected_report(
        self,
    ):
        path = self.get_selected_report_path()

        if path is not None:
            self.open_path(path)

    def open_report_from_row(
        self,
        row,
        column,
    ):
        item = self.files_table.item(
            row,
            0,
        )

        if item is None:
            return

        path_text = item.data(Qt.UserRole)

        if path_text:
            self.open_path(Path(path_text))

    def open_reports_folder(self):
        self.reload_settings()

        self.open_path(self.reports_dir)

    def open_path(
        self,
        path: Path,
    ):
        if not path.exists():
            QMessageBox.warning(
                self,
                "Raporty",
                ("Plik lub folder " "nie istnieje."),
            )

            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

        if not opened:
            QMessageBox.warning(
                self,
                "Raporty",
                ("Nie udało się " "otworzyć lokalizacji."),
            )

    # ==================================================
    # GENERATION
    # ==================================================

    def generate_report(self):
        self.reload_settings()

        chosen_day = self.get_chosen_day()

        self.set_busy(
            True,
            "Generowanie raportu...",
        )

        try:
            result = generate_reports_for_day(
                self.repository,
                chosen_day,
            )

            if not result:
                self.show_no_data(chosen_day)
                return

            (
                excel_path,
                txt_path,
            ) = result

            (
                excel_path,
                txt_path,
            ) = move_generated_report_files(
                excel_path,
                txt_path,
                self.reports_dir,
            )

            self.repository.add_event(
                "report_generated",
                ("Wygenerowano raport " f"za {chosen_day}"),
            )

            self.operation_status_label.setText(
                ("Raport wygenerowany: " f"{chosen_day}")
            )

            self.refresh_report_files()

            QMessageBox.information(
                self,
                "Raport",
                ("Raport został " "wygenerowany."),
            )

        except PermissionError:
            QMessageBox.critical(
                self,
                "Błąd zapisu",
                ("Nie można zapisać raportu.\n" "Plik jest prawdopodobnie " "otwarty."),
            )

        except OSError as error:
            QMessageBox.critical(
                self,
                "Błąd zapisu",
                (f"{type(error).__name__}:\n" f"{error}"),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Nieoczekiwany błąd",
                str(error),
            )

        finally:
            self.set_busy(False)

    def generate_and_send_report(
        self,
    ):
        self.reload_settings()

        chosen_day = self.get_chosen_day()

        self.set_busy(
            True,
            ("Generowanie i wysyłanie " "raportu..."),
        )

        try:
            result = generate_reports_for_day(
                self.repository,
                chosen_day,
            )

            if not result:
                self.show_no_data(chosen_day)
                return

            (
                excel_path,
                txt_path,
            ) = result

            (
                excel_path,
                txt_path,
            ) = move_generated_report_files(
                excel_path,
                txt_path,
                self.reports_dir,
            )

            email_config = self.settings.to_email_config()

            send_generated_report(
                excel_path=excel_path,
                txt_path=txt_path,
                chosen_day=chosen_day,
                email_config=email_config,
            )

            self.repository.add_event(
                "report_sent",
                ("Wysłano raport " f"za {chosen_day}"),
            )

            self.operation_status_label.setText(
                ("Raport wygenerowany " "i wysłany: " f"{chosen_day}")
            )

            self.refresh_report_files()

            QMessageBox.information(
                self,
                "Raport",
                ("Raport został " "wygenerowany i wysłany."),
            )

        except PermissionError:
            QMessageBox.warning(
                self,
                "Błąd zapisu",
                ("Nie można zapisać raportu.\n" "Plik może być otwarty."),
            )

        except smtplib.SMTPAuthenticationError:
            QMessageBox.critical(
                self,
                "Błąd poczty",
                ("Nie udało się zalogować " "do serwera SMTP."),
            )

        except (
            ConnectionError,
            TimeoutError,
        ):
            QMessageBox.warning(
                self,
                "Brak połączenia",
                ("Nie można połączyć się " "z serwerem pocztowym."),
            )

        except smtplib.SMTPException as error:
            QMessageBox.warning(
                self,
                "Błąd wysyłania",
                ("Nie udało się wysłać " "raportu.\n\n" f"{error}"),
            )

        except (
            OSError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "Błąd",
                (f"{type(error).__name__}:\n" f"{error}"),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "Nieoczekiwany błąd",
                str(error),
            )

        finally:
            self.set_busy(False)

    def show_no_data(
        self,
        chosen_day,
    ):
        QMessageBox.warning(
            self,
            "Raport",
            ("Brak danych dla " "wybranej daty."),
        )

        self.operation_status_label.setText(("Brak danych dla " f"{chosen_day}."))

    # ==================================================
    # BUSY
    # ==================================================

    def set_busy(
        self,
        busy,
        message=None,
    ):
        has_data = bool(self.current_stats)

        self.generate_button.setEnabled(not busy and has_data)

        self.generate_send_button.setEnabled(not busy and has_data)

        self.refresh_button.setEnabled(not busy)

        self.report_date.setEnabled(not busy)

        if message:
            self.operation_status_label.setText(message)

        QApplication.processEvents()

    # ==================================================
    # FORMATTERS
    # ==================================================

    @staticmethod
    def format_delta_p(
        value,
    ):
        if value is None:
            return "—"

        try:
            return f"{float(value):.0f} Pa"

        except (
            TypeError,
            ValueError,
        ):
            return str(value)

    @staticmethod
    def format_file_size(
        size_bytes,
    ):
        if size_bytes < 1024:
            return f"{size_bytes} B"

        size_kb = size_bytes / 1024

        if size_kb < 1024:
            return f"{size_kb:.1f} KB"

        size_mb = size_kb / 1024

        return f"{size_mb:.1f} MB"

    # ==================================================
    # STYLE
    # ==================================================

    def apply_style(self):
        self.setStyleSheet("""
            QWidget#reportsPage {
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
            QLabel#smallMuted,
            QLabel#operationStatus,
            QLabel#pathLabel {
                color: #8296aa;
                font-size: 10px;
            }

            QLabel#pathLabel {
                font-family: Consolas;
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

            QDateEdit,
            QTableWidget {
                background-color: #0d1724;
                color: #dbe5ef;
                border: 1px solid #2a3d52;
                border-radius: 5px;
                selection-background-color: #1f4f7a;
                selection-color: #ffffff;
            }

            QDateEdit {
                min-height: 31px;
                padding: 0 8px;
            }

            QDateEdit:focus {
                border: 1px solid #468ac4;
            }

            QDateEdit::drop-down {
                border: none;
                width: 24px;
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

            QPushButton#outlinePrimaryButton {
                background-color: transparent;
                color: #8fc5ff;
                border: 1px solid #377dbd;
            }

            QPushButton#outlinePrimaryButton:hover {
                background-color: #12283c;
                color: #b7d9ff;
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
                background: transparent;
                width: 10px;
                margin: 2px 2px 2px 1px;
            }

                QScrollBar::handle:vertical {
                background-color: #5f7892;
                min-height: 24px;
                border-radius: 3px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #7893ad;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                background: transparent;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
                        """)
