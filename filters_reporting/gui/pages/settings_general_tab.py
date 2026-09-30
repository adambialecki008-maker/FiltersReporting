from __future__ import annotations

import smtplib
from dataclasses import replace
from email.message import EmailMessage
from pathlib import Path

from PySide6.QtCore import Qt, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from filters_reporting.database.database_location import (
    DEFAULT_DATABASE_PATH,
    load_database_path,
    normalise_database_path,
    save_database_path,
)
from filters_reporting.gui.pages.settings_widgets import (
    NoWheelSpinBox,
    NoWheelTimeEdit,
    SettingsTabBase,
)
from filters_reporting.reporting.email_reporting import (
    send_report_email,
)
from filters_reporting.settings_service import (
    AppSettings,
    SETTINGS_FILE,
    has_email_password,
    set_runtime_email_password,
)


class GeneralSettingsTab(SettingsTabBase):
    def __init__(
        self,
        settings: AppSettings,
    ):
        super().__init__()

        self.settings = settings

        self.build_ui()
        self.load_from_settings(settings)

    def build_ui(
        self,
    ) -> None:
        self._build_database_panel()
        self._build_reports_panel()
        self._build_smtp_panel()
        self._build_settings_file_panel()

        self.content_layout.addStretch()

    # ==============================================
    # DATABASE
    # ==============================================

    def _build_database_panel(
        self,
    ) -> None:
        panel = self.create_panel()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        layout.setSpacing(10)

        title = QLabel("Baza danych")

        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Plik SQLite używany przez aplikację i collector. "
            "Zmiana lokalizacji zostanie zastosowana po ponownym "
            "uruchomieniu FiltersReporting."
        )

        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.database_path_edit = QLineEdit()
        self.database_path_edit.setPlaceholderText(
            str(DEFAULT_DATABASE_PATH)
        )

        database_row = QHBoxLayout()
        database_row.setSpacing(7)
        database_row.addWidget(
            self.database_path_edit,
            1,
        )

        self.choose_database_button = QPushButton(
            "Wybierz bazę"
        )
        self.choose_database_button.setObjectName(
            "secondaryButton"
        )
        self.choose_database_button.clicked.connect(
            self.choose_database_file
        )
        database_row.addWidget(
            self.choose_database_button
        )

        self.default_database_button = QPushButton(
            "Domyślna"
        )
        self.default_database_button.setObjectName(
            "secondaryButton"
        )
        self.default_database_button.clicked.connect(
            self.restore_default_database_path
        )
        database_row.addWidget(
            self.default_database_button
        )

        form.addRow(
            "Plik SQLite",
            database_row,
        )

        layout.addLayout(form)

        self.database_default_label = QLabel(
            "Domyślna lokalizacja: "
            f"{DEFAULT_DATABASE_PATH}"
        )
        self.database_default_label.setObjectName(
            "pathLabel"
        )
        self.database_default_label.setWordWrap(True)
        self.database_default_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        layout.addWidget(
            self.database_default_label
        )

        self.database_migration_note = QLabel(
            "Zmiana lokalizacji bazy nie przenosi istniejących danych. "
            "Jeśli wskazany plik nie istnieje, po ponownym uruchomieniu "
            "FiltersReporting utworzy w tej lokalizacji nową, pustą "
            "bazę. Aby zachować dotychczasowe dane, zamknij aplikację "
            "i collector, a następnie ręcznie skopiuj obecny plik .db "
            "do wybranej lokalizacji przed ponownym uruchomieniem."
        )
        self.database_migration_note.setObjectName(
            "databaseMigrationNote"
        )
        self.database_migration_note.setWordWrap(True)
        layout.addWidget(self.database_migration_note)

        self.content_layout.addWidget(panel)

    def choose_database_file(
        self,
    ) -> None:
        current = self.database_path_edit.text().strip()

        start_path = (
            current
            if current
            else str(DEFAULT_DATABASE_PATH)
        )

        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Wybierz bazę danych",
            start_path,
            "Baza SQLite (*.db);;Wszystkie pliki (*)",
        )

        if selected:
            self.database_path_edit.setText(selected)

    def restore_default_database_path(
        self,
    ) -> None:
        self.database_path_edit.setText(
            str(DEFAULT_DATABASE_PATH)
        )

    def get_database_path_from_form(
        self,
    ) -> Path:
        raw_path = self.database_path_edit.text().strip()

        if not raw_path:
            raise ValueError(
                "Podaj ścieżkę pliku bazy danych."
            )

        database_path = normalise_database_path(
            raw_path
        )

        if database_path.exists() and database_path.is_dir():
            raise ValueError(
                "Ścieżka bazy danych wskazuje katalog, "
                "a nie plik."
            )

        return database_path

    def database_location_changed(
        self,
    ) -> bool:
        return (
            self.get_database_path_from_form()
            != load_database_path()
        )

    def save_database_location(
        self,
    ) -> Path:
        return save_database_path(
            self.get_database_path_from_form()
        )

    # ==============================================
    # REPORTS
    # ==============================================

    def _build_reports_panel(
        self,
    ) -> None:
        panel = self.create_panel()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        layout.setSpacing(10)

        title = QLabel("Raporty")

        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Folder raportów oraz " "automatyczne generowanie " "raportu dziennego."
        )

        hint.setObjectName("hint")

        hint.setWordWrap(True)

        layout.addWidget(title)

        layout.addWidget(hint)

        form = self.create_form()

        self.reports_dir_edit = QLineEdit()

        self.reports_dir_edit.setPlaceholderText("Folder raportów")

        self.auto_report_checkbox = QCheckBox("Włącz raport automatyczny")

        self.auto_report_checkbox.toggled.connect(self.update_auto_report_controls)

        self.auto_report_time_edit = NoWheelTimeEdit()

        self.auto_report_time_edit.setDisplayFormat("HH:mm")

        self.auto_report_send_checkbox = QCheckBox("Wyślij raport e-mailem")

        form.addRow(
            "Folder raportów",
            self.create_directory_row(self.reports_dir_edit),
        )

        form.addRow(
            "Automatyzacja",
            self.auto_report_checkbox,
        )

        form.addRow(
            "Godzina",
            self.auto_report_time_edit,
        )

        form.addRow(
            "Po wygenerowaniu",
            self.auto_report_send_checkbox,
        )

        layout.addLayout(form)

        note = QLabel(
            "Raport automatyczny dotyczy "
            "poprzedniego dnia i jest "
            "wykonywany maksymalnie raz dziennie."
        )

        note.setObjectName("hint")

        note.setWordWrap(True)

        layout.addWidget(note)

        self.content_layout.addWidget(panel)

    # ==============================================
    # SMTP
    # ==============================================

    def _build_smtp_panel(
        self,
    ) -> None:
        panel = self.create_panel()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        layout.setSpacing(10)

        title = QLabel("E-mail / SMTP")

        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Hasło SMTP nie jest zapisywane "
            "w settings.json. Po zapisaniu jest "
            "szyfrowane przez Windows DPAPI dla "
            "bieżącego użytkownika. Zmienna "
            "EMAIL_PASSWORD, jeśli jest ustawiona, "
            "ma pierwszeństwo."
        )

        hint.setObjectName("hint")

        hint.setWordWrap(True)

        layout.addWidget(title)

        layout.addWidget(hint)

        form = self.create_form()

        self.smtp_host_edit = QLineEdit()

        self.smtp_host_edit.setPlaceholderText("smtp.example.com")

        self.smtp_port_spinbox = NoWheelSpinBox()

        self.smtp_port_spinbox.setRange(
            1,
            65535,
        )

        self.smtp_username_edit = QLineEdit()

        self.smtp_username_edit.setPlaceholderText("login@example.com")

        self.smtp_sender_edit = QLineEdit()

        self.smtp_sender_edit.setPlaceholderText("sender@example.com")

        self.smtp_recipients_edit = QLineEdit()

        self.smtp_recipients_edit.setPlaceholderText("a@example.com; b@example.com")

        self.smtp_password_edit = QLineEdit()

        self.smtp_password_edit.setEchoMode(QLineEdit.Password)

        self.smtp_password_edit.setPlaceholderText(
            "Puste = zachowaj zapisane hasło"
        )

        self.password_state_label = QLabel("—")

        self.password_state_label.setObjectName("passwordState")

        password_layout = QVBoxLayout()

        password_layout.setSpacing(4)

        password_layout.addWidget(self.smtp_password_edit)

        password_layout.addWidget(self.password_state_label)

        form.addRow(
            "Serwer SMTP",
            self.smtp_host_edit,
        )

        form.addRow(
            "Port",
            self.smtp_port_spinbox,
        )

        form.addRow(
            "Login",
            self.smtp_username_edit,
        )

        form.addRow(
            "Nadawca",
            self.smtp_sender_edit,
        )

        form.addRow(
            "Odbiorcy",
            self.smtp_recipients_edit,
        )

        form.addRow(
            "Hasło",
            password_layout,
        )

        layout.addLayout(form)

        self.test_smtp_button = QPushButton("Test SMTP")

        self.test_smtp_button.setObjectName("secondaryButton")

        self.test_smtp_button.clicked.connect(self.test_smtp)

        layout.addWidget(self.test_smtp_button)

        self.content_layout.addWidget(panel)

    # ==============================================
    # SETTINGS FILE
    # ==============================================

    def _build_settings_file_panel(
        self,
    ) -> None:
        panel = self.create_panel()

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            18,
            14,
            18,
            14,
        )

        layout.setSpacing(6)

        title = QLabel("Plik ustawień")

        title.setObjectName("sectionTitle")

        self.settings_file_label = QLabel(str(SETTINGS_FILE))

        self.settings_file_label.setObjectName("pathLabel")

        layout.addWidget(title)

        layout.addWidget(self.settings_file_label)

        self.content_layout.addWidget(panel)

    # ==============================================
    # STATE
    # ==============================================

    def update_auto_report_controls(
        self,
    ) -> None:
        enabled = self.auto_report_checkbox.isChecked()

        self.auto_report_time_edit.setEnabled(enabled)

        self.auto_report_send_checkbox.setEnabled(enabled)

    def parse_recipients(
        self,
    ) -> list[str]:
        raw = (
            self.smtp_recipients_edit.text()
            .replace(
                ",",
                ";",
            )
            .replace(
                "\n",
                ";",
            )
        )

        return [value.strip() for value in raw.split(";") if value.strip()]

    # ==============================================
    # SETTINGS
    # ==============================================

    def apply_to_settings(
        self,
        settings: AppSettings,
    ) -> AppSettings:
        return replace(
            settings,
            reports_dir=Path(self.reports_dir_edit.text().strip()).expanduser(),
            smtp_host=(self.smtp_host_edit.text().strip()),
            smtp_port=(self.smtp_port_spinbox.value()),
            username=(self.smtp_username_edit.text().strip()),
            sender=(self.smtp_sender_edit.text().strip()),
            recipients=(self.parse_recipients()),
            auto_report_enabled=(self.auto_report_checkbox.isChecked()),
            auto_report_time=(self.auto_report_time_edit.time().toString("HH:mm")),
            auto_report_send_email=(self.auto_report_send_checkbox.isChecked()),
        )

    def validate(
        self,
        settings: AppSettings,
    ) -> tuple[bool, str]:
        if not str(settings.reports_dir).strip():
            return (
                False,
                "Podaj folder raportów.",
            )

        if not settings.smtp_host:
            return (
                False,
                "Podaj serwer SMTP.",
            )

        if not settings.username:
            return (
                False,
                "Podaj login SMTP.",
            )

        if not settings.sender:
            return (
                False,
                "Podaj adres nadawcy.",
            )

        if not settings.recipients:
            return (
                False,
                "Podaj co najmniej " "jednego odbiorcę.",
            )

        return (
            True,
            "",
        )

    def load_from_settings(
        self,
        settings: AppSettings,
    ) -> None:
        self.settings = settings

        self.database_path_edit.setText(
            str(load_database_path())
        )

        self.reports_dir_edit.setText(str(settings.reports_dir))

        self.auto_report_checkbox.setChecked(settings.auto_report_enabled)

        time_value = QTime.fromString(
            settings.auto_report_time,
            "HH:mm",
        )

        if not time_value.isValid():
            time_value = QTime(
                6,
                0,
            )

        self.auto_report_time_edit.setTime(time_value)

        self.auto_report_send_checkbox.setChecked(settings.auto_report_send_email)

        self.smtp_host_edit.setText(settings.smtp_host)

        self.smtp_port_spinbox.setValue(settings.smtp_port)

        self.smtp_username_edit.setText(settings.username)

        self.smtp_sender_edit.setText(settings.sender)

        self.smtp_recipients_edit.setText("; ".join(settings.recipients))

        self.smtp_password_edit.clear()

        self.password_state_label.setText(
            "Hasło SMTP: dostępne"
            if has_email_password()
            else "Hasło SMTP: brak"
        )

        self.update_auto_report_controls()

    def get_smtp_password(
        self,
    ) -> str:
        return self.smtp_password_edit.text()

    # ==============================================
    # SMTP TEST
    # ==============================================

    def test_smtp(
        self,
    ) -> None:
        settings = self.apply_to_settings(self.settings)

        valid, validation_message = self.validate(settings)

        if not valid:
            QMessageBox.warning(
                self,
                "SMTP",
                validation_message,
            )

            return

        password = self.smtp_password_edit.text()

        if password.strip():
            set_runtime_email_password(password)

        if not has_email_password():
            QMessageBox.warning(
                self,
                "SMTP",
                "Brak hasła SMTP.\n\n"
                "Wpisz hasło albo ustaw "
                "zmienną EMAIL_PASSWORD.",
            )

            return

        email_config = settings.to_email_config()

        message = EmailMessage()

        message["Subject"] = "FiltersReporting - test SMTP"

        message["From"] = email_config.sender

        message["To"] = ", ".join(email_config.recipients)

        message.set_content("Test połączenia SMTP " "z aplikacji FiltersReporting.")

        self.test_smtp_button.setEnabled(False)

        self.test_smtp_button.setText("Testowanie...")

        try:
            send_report_email(
                message,
                email_config,
            )

            QMessageBox.information(
                self,
                "SMTP",
                "Wiadomość testowa " "została wysłana.",
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

        except (
            ConnectionError,
            TimeoutError,
            OSError,
        ) as error:
            QMessageBox.critical(
                self,
                "SMTP",
                f"Błąd połączenia:\n{error}",
            )

        finally:
            self.test_smtp_button.setEnabled(True)

            self.test_smtp_button.setText("Test SMTP")
