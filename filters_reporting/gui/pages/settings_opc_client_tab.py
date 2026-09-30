from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from filters_reporting.collection.opc_ua_client import (
    OpcUaFilterClient,
)
from filters_reporting.runtime_paths import CERTIFICATES_DIR
from filters_reporting.gui.pages.settings_widgets import (
    NoWheelComboBox,
    SettingsTabBase,
)
from filters_reporting.models.filter import Filter
from filters_reporting.opcua.certificate_service import (
    ApplicationCertificatePaths,
    create_default_certificate_paths,
    generate_application_certificate,
    get_default_application_uri,
    load_certificate_info,
)
from filters_reporting.opcua.client_credentials import (
    delete_filter_password,
    has_filter_password,
    set_filter_password,
)
from filters_reporting.opcua.security import (
    OPC_UA_SECURITY_MODES,
    OPC_UA_SECURITY_POLICIES,
    OpcUaSecurityConfig,
)
from filters_reporting.settings_service import AppSettings


AUTHENTICATION_TYPES = (
    "Anonymous",
    "UsernamePassword",
)


class OpcClientConnectionTestWorker(QThread):
    success = Signal()
    failed = Signal(str)

    def __init__(
        self,
        filter_obj: Filter,
        parent=None,
    ):
        super().__init__(parent)
        self.filter_obj = filter_obj

    def run(self) -> None:
        async def _test_connection() -> None:
            client = OpcUaFilterClient(
                self.filter_obj
            )

            try:
                await client.connect()
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

        try:
            asyncio.run(_test_connection())
        except Exception as error:
            self.failed.emit(
                f"{type(error).__name__}: {error}"
            )
            return

        self.success.emit()


class OpcClientSettingsTab(SettingsTabBase):
    # Zostawione dla kompatybilności z istniejącym SettingsPage.
    # W v1.0 certyfikat klienta jest per maszyna i nie powinien być
    # automatycznie przepisywany do globalnego OPC UA Server.
    certificate_generated = Signal(
        str,
        str,
        str,
    )

    def __init__(
        self,
        settings: AppSettings,
        repository=None,
    ):
        super().__init__()

        self.settings = settings
        self.repository = repository

        self._filters_by_id: dict[int, Filter] = {}
        self._loading_form = False
        self._clear_password_requested = False
        self._connection_worker: (
            OpcClientConnectionTestWorker | None
        ) = None

        self.build_ui()
        self.load_from_settings(settings)

    # ==================================================
    # UI
    # ==================================================

    def build_ui(self) -> None:
        self._build_machine_panel()
        self._build_security_panel()
        self._build_authentication_panel()
        self._build_certificate_panel()
        self._build_connection_panel()

        self.content_layout.addStretch()

        self.machine_combo.currentIndexChanged.connect(
            self._machine_changed
        )

        self.policy_combo.currentTextChanged.connect(
            self.update_security_controls
        )
        self.mode_combo.currentTextChanged.connect(
            self.update_security_controls
        )
        self.validate_checkbox.toggled.connect(
            self.update_security_controls
        )
        self.auth_combo.currentTextChanged.connect(
            self.update_authentication_controls
        )

    # ==================================================
    # MACHINE
    # ==================================================

    def _build_machine_panel(self) -> None:
        self.machine_panel = self.create_panel()
        layout = QVBoxLayout(self.machine_panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Maszyna / filtr OPC UA")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "W FiltersReporting v1.0 każdy filtr jest traktowany "
            "jako niezależna maszyna OPC UA. Endpoint, zabezpieczenia, "
            "certyfikaty i dane logowania są zapisywane osobno dla "
            "każdego filtra."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        machine_row = QHBoxLayout()
        machine_row.setSpacing(7)

        self.machine_combo = NoWheelComboBox()

        self.refresh_machines_button = QPushButton(
            "Odśwież listę"
        )
        self.refresh_machines_button.setObjectName(
            "secondaryButton"
        )
        self.refresh_machines_button.clicked.connect(
            lambda _checked=False: self.refresh_filters()
        )

        machine_row.addWidget(self.machine_combo, 1)
        machine_row.addWidget(self.refresh_machines_button)
        layout.addLayout(machine_row)

        form = self.create_form()

        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText(
            "opc.tcp://192.168.1.10:4840"
        )

        self.machine_state_label = QLabel("—")
        self.machine_state_label.setObjectName("hint")

        form.addRow("Endpoint", self.endpoint_edit)
        form.addRow("Stan filtra", self.machine_state_label)

        layout.addLayout(form)
        self.content_layout.addWidget(self.machine_panel)

    # ==================================================
    # SECURITY
    # ==================================================

    def _build_security_panel(self) -> None:
        self.security_panel = self.create_panel()
        layout = QVBoxLayout(self.security_panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("SecureChannel tej maszyny")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Security Policy i Security Mode dotyczą wyłącznie "
            "aktualnie wybranego filtra / serwera OPC UA."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.policy_combo = NoWheelComboBox()
        self.policy_combo.addItems(
            OPC_UA_SECURITY_POLICIES
        )

        self.mode_combo = NoWheelComboBox()
        self.mode_combo.addItems(
            OPC_UA_SECURITY_MODES
        )

        self.application_uri_edit = QLineEdit()
        self.application_uri_edit.setPlaceholderText(
            get_default_application_uri()
        )

        self.validate_checkbox = QCheckBox(
            "Weryfikuj zaufanie certyfikatu serwera"
        )

        form.addRow("Security Policy", self.policy_combo)
        form.addRow("Security Mode", self.mode_combo)
        form.addRow("Application URI", self.application_uri_edit)
        form.addRow("Walidacja", self.validate_checkbox)

        layout.addLayout(form)
        self.content_layout.addWidget(self.security_panel)

    # ==================================================
    # AUTHENTICATION
    # ==================================================

    def _build_authentication_panel(self) -> None:
        self.authentication_panel = self.create_panel()
        layout = QVBoxLayout(
            self.authentication_panel
        )
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Uwierzytelnianie tej maszyny")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Hasło nie jest zapisywane w SQLite ani settings.json. "
            "Jest przechowywane osobno i szyfrowane przez Windows DPAPI "
            "dla bieżącego użytkownika."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.auth_combo = NoWheelComboBox()
        self.auth_combo.addItems(AUTHENTICATION_TYPES)

        self.username_edit = QLineEdit()

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(
            QLineEdit.Password
        )
        self.password_edit.setPlaceholderText(
            "Pozostaw puste, aby zachować zapisane hasło"
        )

        password_row = QHBoxLayout()
        password_row.setSpacing(7)
        password_row.addWidget(self.password_edit, 1)

        self.clear_password_button = QPushButton(
            "Usuń zapisane"
        )
        self.clear_password_button.setObjectName(
            "secondaryButton"
        )
        self.clear_password_button.clicked.connect(
            self.request_password_clear
        )
        password_row.addWidget(
            self.clear_password_button
        )

        self.password_state_label = QLabel(
            "Hasło: brak informacji"
        )
        self.password_state_label.setObjectName(
            "passwordState"
        )

        form.addRow("Logowanie", self.auth_combo)
        form.addRow("Użytkownik", self.username_edit)
        form.addRow("Hasło", password_row)
        form.addRow("Stan", self.password_state_label)

        layout.addLayout(form)
        self.content_layout.addWidget(
            self.authentication_panel
        )

    # ==================================================
    # CERTIFICATES
    # ==================================================

    def _build_certificate_panel(self) -> None:
        self.certificate_panel = self.create_panel()
        layout = QVBoxLayout(self.certificate_panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Certyfikaty tej maszyny")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Każdy filtr może mieć własny certyfikat klienta, "
            "klucz prywatny, katalog trusted i certyfikat serwera."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.certificate_edit = QLineEdit()
        self.private_key_edit = QLineEdit()
        self.trusted_dir_edit = QLineEdit()
        self.server_certificate_edit = QLineEdit()

        certificate_row = self.create_file_row(
            self.certificate_edit,
            "Certyfikaty (*.der *.pem *.crt *.cer);;"
            "Wszystkie pliki (*)",
        )

        key_row = self.create_file_row(
            self.private_key_edit,
            "Klucze (*.pem *.der *.key);;"
            "Wszystkie pliki (*)",
        )

        trusted_row = self.create_directory_row(
            self.trusted_dir_edit
        )

        server_certificate_row = self.create_file_row(
            self.server_certificate_edit,
            "Certyfikaty (*.der *.pem *.crt *.cer);;"
            "Wszystkie pliki (*)",
        )

        form.addRow(
            "Certyfikat klienta",
            certificate_row,
        )
        form.addRow("Klucz prywatny", key_row)
        form.addRow("Trusted certificates", trusted_row)
        form.addRow(
            "Certyfikat serwera",
            server_certificate_row,
        )

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.generate_button = QPushButton(
            "Generuj certyfikat dla tej maszyny"
        )
        self.generate_button.setObjectName("primaryButton")
        self.generate_button.clicked.connect(
            self.generate_certificate
        )

        self.refresh_button = QPushButton(
            "Odśwież informacje"
        )
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.clicked.connect(
            self.refresh_certificate_info
        )

        buttons.addWidget(self.generate_button)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.certificate_info_label = QLabel(
            "Certyfikat: brak informacji"
        )
        self.certificate_info_label.setObjectName(
            "certificateInfo"
        )
        self.certificate_info_label.setWordWrap(True)
        self.certificate_info_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        layout.addWidget(self.certificate_info_label)
        self.content_layout.addWidget(
            self.certificate_panel
        )

    # ==================================================
    # CONNECTION
    # ==================================================

    def _build_connection_panel(self) -> None:
        self.connection_panel = self.create_panel()
        layout = QVBoxLayout(self.connection_panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Połączenie")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Timeouty i reconnect są niezależne dla każdej maszyny."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.connect_timeout_edit = QLineEdit()
        self.request_timeout_edit = QLineEdit()
        self.reconnect_delay_edit = QLineEdit()

        self.connect_timeout_edit.setPlaceholderText("5.0")
        self.request_timeout_edit.setPlaceholderText("5.0")
        self.reconnect_delay_edit.setPlaceholderText("5.0")

        form.addRow(
            "Connect timeout [s]",
            self.connect_timeout_edit,
        )
        form.addRow(
            "Request timeout [s]",
            self.request_timeout_edit,
        )
        form.addRow(
            "Reconnect delay [s]",
            self.reconnect_delay_edit,
        )

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.setSpacing(7)

        self.save_machine_button = QPushButton(
            "Zapisz konfigurację maszyny"
        )
        self.save_machine_button.setObjectName(
            "primaryButton"
        )
        self.save_machine_button.clicked.connect(
            self.save_current_machine
        )

        self.test_connection_button = QPushButton(
            "Test connection"
        )
        self.test_connection_button.setObjectName(
            "secondaryButton"
        )
        self.test_connection_button.clicked.connect(
            self.test_connection
        )

        buttons.addWidget(self.save_machine_button)
        buttons.addWidget(self.test_connection_button)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.connection_status_label = QLabel("—")
        self.connection_status_label.setObjectName("hint")
        self.connection_status_label.setWordWrap(True)
        layout.addWidget(self.connection_status_label)

        self.content_layout.addWidget(
            self.connection_panel
        )

    # ==================================================
    # FILTER LIST / FORM
    # ==================================================

    def set_repository(self, repository) -> None:
        self.repository = repository
        self.refresh_filters()

    def refresh_filters(
        self,
        select_filter_id: int | None = None,
    ) -> None:
        if select_filter_id is None:
            select_filter_id = self.current_filter_id()

        self._filters_by_id = {}

        self.machine_combo.blockSignals(True)
        self.machine_combo.clear()

        if self.repository is None:
            self.machine_combo.addItem(
                "Brak repozytorium filtrów"
            )
            self.machine_combo.setEnabled(False)
            self.machine_combo.blockSignals(False)
            self._set_machine_controls_enabled(False)
            return

        try:
            filters = self.repository.get_all_filters()
        except Exception as error:
            self.machine_combo.addItem(
                "Błąd odczytu filtrów"
            )
            self.machine_combo.setEnabled(False)
            self.machine_combo.blockSignals(False)
            self._set_machine_controls_enabled(False)
            self.connection_status_label.setText(
                f"Nie udało się odczytać filtrów: {error}"
            )
            return

        for filter_obj in filters:
            if filter_obj.filter_id is None:
                continue

            filter_id = int(filter_obj.filter_id)
            self._filters_by_id[filter_id] = filter_obj

            label = filter_obj.name
            if not filter_obj.active:
                label += " [nieaktywny]"

            self.machine_combo.addItem(
                label,
                filter_id,
            )

        has_filters = bool(self._filters_by_id)
        self.machine_combo.setEnabled(has_filters)
        self.machine_combo.blockSignals(False)
        self._set_machine_controls_enabled(has_filters)

        if not has_filters:
            self.machine_combo.addItem("Brak filtrów")
            self.clear_machine_form()
            return

        selected_index = 0

        if select_filter_id is not None:
            candidate_index = self.machine_combo.findData(
                int(select_filter_id)
            )
            if candidate_index >= 0:
                selected_index = candidate_index

        self.machine_combo.setCurrentIndex(selected_index)
        self.load_selected_filter()

    def _machine_changed(self) -> None:
        if self._loading_form:
            return

        self.load_selected_filter()

    def current_filter_id(self) -> int | None:
        value = self.machine_combo.currentData()

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def current_filter(self) -> Filter | None:
        filter_id = self.current_filter_id()

        if filter_id is None:
            return None

        return self._filters_by_id.get(filter_id)

    def load_selected_filter(self) -> None:
        filter_obj = self.current_filter()

        if filter_obj is None:
            self.clear_machine_form()
            self._set_machine_controls_enabled(False)
            return

        self._set_machine_controls_enabled(True)
        self._loading_form = True

        try:
            self.endpoint_edit.setText(
                filter_obj.opc_url or ""
            )

            self.machine_state_label.setText(
                "aktywny"
                if filter_obj.active
                else "nieaktywny"
            )

            self.policy_combo.setCurrentText(
                filter_obj.opc_security_policy or "None"
            )
            self.mode_combo.setCurrentText(
                filter_obj.opc_security_mode or "None"
            )
            self.application_uri_edit.setText(
                filter_obj.opc_application_uri or ""
            )
            self.validate_checkbox.setChecked(
                bool(
                    filter_obj.opc_validate_server_certificate
                )
            )

            self.certificate_edit.setText(
                filter_obj.opc_client_certificate_path
                or ""
            )
            self.private_key_edit.setText(
                filter_obj.opc_client_private_key_path
                or ""
            )
            self.trusted_dir_edit.setText(
                filter_obj.opc_trusted_certificates_dir
                or ""
            )
            self.server_certificate_edit.setText(
                filter_obj.opc_server_certificate_path
                or ""
            )

            auth_type = (
                filter_obj.opc_auth_type
                or "Anonymous"
            )
            if auth_type not in AUTHENTICATION_TYPES:
                auth_type = "Anonymous"

            self.auth_combo.setCurrentText(auth_type)
            self.username_edit.setText(
                filter_obj.opc_username or ""
            )

            self.password_edit.clear()
            self._clear_password_requested = False
            self.refresh_password_state()

            self.connect_timeout_edit.setText(
                str(
                    filter_obj.opc_connect_timeout_seconds
                )
            )
            self.request_timeout_edit.setText(
                str(
                    filter_obj.opc_request_timeout_seconds
                )
            )
            self.reconnect_delay_edit.setText(
                str(
                    filter_obj.opc_reconnect_delay_seconds
                )
            )
        finally:
            self._loading_form = False

        self.update_security_controls()
        self.update_authentication_controls()
        self.refresh_certificate_info()
        self.connection_status_label.setText("—")

    def clear_machine_form(self) -> None:
        self._loading_form = True

        try:
            for line_edit in (
                self.endpoint_edit,
                self.application_uri_edit,
                self.certificate_edit,
                self.private_key_edit,
                self.trusted_dir_edit,
                self.server_certificate_edit,
                self.username_edit,
                self.password_edit,
                self.connect_timeout_edit,
                self.request_timeout_edit,
                self.reconnect_delay_edit,
            ):
                line_edit.clear()

            self.policy_combo.setCurrentText("None")
            self.mode_combo.setCurrentText("None")
            self.auth_combo.setCurrentText("Anonymous")
            self.validate_checkbox.setChecked(True)
            self.machine_state_label.setText("—")
            self.password_state_label.setText("Hasło: —")
            self.certificate_info_label.setText("Certyfikat: brak")
            self.connection_status_label.setText("—")
            self._clear_password_requested = False
        finally:
            self._loading_form = False

    def _set_machine_controls_enabled(
        self,
        enabled: bool,
    ) -> None:
        for panel in (
            self.security_panel,
            self.authentication_panel,
            self.certificate_panel,
            self.connection_panel,
        ):
            panel.setEnabled(enabled)

        self.endpoint_edit.setEnabled(enabled)

    # ==================================================
    # STATE
    # ==================================================

    def update_security_controls(self) -> None:
        policy = self.policy_combo.currentText()
        mode = self.mode_combo.currentText()

        if policy == "None":
            if mode != "None":
                self.mode_combo.setCurrentText("None")
            secure = False
        else:
            secure = True
            if mode == "None":
                self.mode_combo.setCurrentText(
                    "SignAndEncrypt"
                )

        self.application_uri_edit.setEnabled(secure)
        self.certificate_edit.setEnabled(secure)
        self.private_key_edit.setEnabled(secure)
        self.validate_checkbox.setEnabled(secure)
        self.trusted_dir_edit.setEnabled(
            secure
            and self.validate_checkbox.isChecked()
        )
        self.server_certificate_edit.setEnabled(secure)
        self.generate_button.setEnabled(secure)
        self.refresh_button.setEnabled(secure)

    def update_authentication_controls(self) -> None:
        username_password = (
            self.auth_combo.currentText()
            == "UsernamePassword"
        )

        self.username_edit.setEnabled(username_password)
        self.password_edit.setEnabled(username_password)
        self.clear_password_button.setEnabled(
            username_password
        )

    # ==================================================
    # SETTINGS PAGE COMPATIBILITY
    # ==================================================

    def apply_to_settings(
        self,
        settings: AppSettings,
    ) -> AppSettings:
        # OPC UA Client jest teraz konfiguracją per filtr / maszyna,
        # więc nie zapisujemy security klienta do globalnego settings.json.
        return settings

    def validate(
        self,
        settings: AppSettings,
    ) -> tuple[bool, str]:
        if self.repository is None:
            return True, ""

        if self.current_filter() is None:
            return True, ""

        try:
            self.build_filter_from_form(
                require_saved_password=False
            )
        except (
            ValueError,
            FileNotFoundError,
        ) as error:
            return False, f"OPC UA Client:\n{error}"

        return True, ""

    def load_from_settings(
        self,
        settings: AppSettings,
    ) -> None:
        self.settings = settings
        self.refresh_filters()

    # ==================================================
    # FORM -> FILTER
    # ==================================================

    @staticmethod
    def _positive_float(
        text: str,
        field_name: str,
    ) -> float:
        try:
            value = float(text.strip())
        except ValueError as error:
            raise ValueError(
                f"{field_name}: wpisz poprawną liczbę."
            ) from error

        if value <= 0:
            raise ValueError(
                f"{field_name}: wartość musi być większa od 0."
            )

        return value

    def _security_config_from_filter(
        self,
        filter_obj: Filter,
    ) -> OpcUaSecurityConfig:
        return OpcUaSecurityConfig(
            policy=filter_obj.opc_security_policy,
            mode=filter_obj.opc_security_mode,
            application_uri=filter_obj.opc_application_uri,
            certificate_path=(
                Path(filter_obj.opc_client_certificate_path)
                if filter_obj.opc_client_certificate_path
                else None
            ),
            private_key_path=(
                Path(filter_obj.opc_client_private_key_path)
                if filter_obj.opc_client_private_key_path
                else None
            ),
            trusted_certificates_dir=(
                Path(filter_obj.opc_trusted_certificates_dir)
                if filter_obj.opc_trusted_certificates_dir
                else None
            ),
            server_certificate_path=(
                Path(filter_obj.opc_server_certificate_path)
                if filter_obj.opc_server_certificate_path
                else None
            ),
            validate_server_certificate=(
                filter_obj.opc_validate_server_certificate
            ),
        )

    def build_filter_from_form(
        self,
        *,
        require_saved_password: bool,
    ) -> Filter:
        original = self.current_filter()

        if original is None:
            raise ValueError(
                "Nie wybrano filtra / maszyny OPC UA."
            )

        endpoint = self.endpoint_edit.text().strip()

        if not endpoint:
            raise ValueError("Brak endpointu OPC UA.")

        if not endpoint.lower().startswith("opc.tcp://"):
            raise ValueError(
                "Endpoint OPC UA musi zaczynać się od opc.tcp://"
            )

        auth_type = self.auth_combo.currentText()
        username = self.username_edit.text().strip()

        if auth_type == "UsernamePassword":
            if not username:
                raise ValueError(
                    "Dla UsernamePassword podaj nazwę użytkownika."
                )

            filter_id = original.filter_id
            pending_password = bool(
                self.password_edit.text()
            )
            existing_password = (
                filter_id is not None
                and has_filter_password(int(filter_id))
                and not self._clear_password_requested
            )

            if (
                require_saved_password
                and not pending_password
                and not existing_password
            ):
                raise ValueError(
                    "Dla UsernamePassword podaj hasło."
                )

        connect_timeout = self._positive_float(
            self.connect_timeout_edit.text(),
            "Connect timeout",
        )
        request_timeout = self._positive_float(
            self.request_timeout_edit.text(),
            "Request timeout",
        )
        reconnect_delay = self._positive_float(
            self.reconnect_delay_edit.text(),
            "Reconnect delay",
        )

        updated = replace(
            original,
            opc_url=endpoint,
            opc_security_policy=(
                self.policy_combo.currentText()
            ),
            opc_security_mode=(
                self.mode_combo.currentText()
            ),
            opc_application_uri=(
                self.application_uri_edit.text().strip()
            ),
            opc_client_certificate_path=(
                self.certificate_edit.text().strip()
                or None
            ),
            opc_client_private_key_path=(
                self.private_key_edit.text().strip()
                or None
            ),
            opc_trusted_certificates_dir=(
                self.trusted_dir_edit.text().strip()
                or None
            ),
            opc_server_certificate_path=(
                self.server_certificate_edit.text().strip()
                or None
            ),
            opc_validate_server_certificate=(
                self.validate_checkbox.isChecked()
            ),
            opc_auth_type=auth_type,
            opc_username=username,
            opc_connect_timeout_seconds=(connect_timeout),
            opc_request_timeout_seconds=(request_timeout),
            opc_reconnect_delay_seconds=(reconnect_delay),
        )

        security_config = self._security_config_from_filter(
            updated
        )
        security_config.validate()

        return updated

    # ==================================================
    # SAVE / PASSWORD
    # ==================================================

    def save_current_machine(
        self,
        checked: bool = False,
        *,
        show_message: bool = True,
    ) -> bool:
        del checked

        if self.repository is None:
            if show_message:
                QMessageBox.warning(
                    self,
                    "OPC UA Client",
                    "Brak repozytorium filtrów.",
                )
            return False

        try:
            filter_obj = self.build_filter_from_form(
                require_saved_password=True
            )

            if filter_obj.filter_id is None:
                raise ValueError(
                    "Filtr nie ma filter_id."
                )

            filter_id = int(filter_obj.filter_id)

            # Endpoint ma osobną metodę repozytorium, dzięki czemu zapis
            # security nie dotyka nazwy, progów ani NodeId filtra.
            self.repository.update_filter_opc_url(
                filter_obj.name,
                filter_obj.opc_url,
            )
            self.repository.update_filter_opc_settings(
                filter_obj
            )

            if filter_obj.opc_auth_type == "UsernamePassword":
                password = self.password_edit.text()

                if password:
                    set_filter_password(
                        filter_id,
                        password,
                    )
                elif self._clear_password_requested:
                    delete_filter_password(filter_id)
            else:
                # Nie zostawiamy nieużywanego sekretu po przełączeniu
                # maszyny z UsernamePassword na Anonymous.
                delete_filter_password(filter_id)

        except (
            ValueError,
            FileNotFoundError,
            OSError,
        ) as error:
            if show_message:
                QMessageBox.warning(
                    self,
                    "OPC UA Client",
                    str(error),
                )
            return False
        except Exception as error:
            if show_message:
                QMessageBox.critical(
                    self,
                    "OPC UA Client",
                    "Nie udało się zapisać konfiguracji maszyny.\n\n"
                    f"{type(error).__name__}: {error}",
                )
            return False

        self.password_edit.clear()
        self._clear_password_requested = False
        self.refresh_filters(
            select_filter_id=filter_id
        )

        if show_message:
            QMessageBox.information(
                self,
                "OPC UA Client",
                f"Zapisano konfigurację:\n{filter_obj.name}",
            )

        return True

    def request_password_clear(self) -> None:
        filter_obj = self.current_filter()

        if filter_obj is None or filter_obj.filter_id is None:
            return

        self.password_edit.clear()
        self._clear_password_requested = True
        self.password_state_label.setText(
            "Hasło: zostanie usunięte po zapisie"
        )

    def refresh_password_state(self) -> None:
        filter_obj = self.current_filter()

        if filter_obj is None or filter_obj.filter_id is None:
            self.password_state_label.setText("Hasło: —")
            return

        try:
            stored = has_filter_password(
                int(filter_obj.filter_id)
            )
        except Exception:
            stored = False

        self.password_state_label.setText(
            "Hasło: zapisane (DPAPI)"
            if stored
            else "Hasło: brak"
        )

    # ==================================================
    # TEST CONNECTION
    # ==================================================

    def test_connection(self) -> None:
        if self._connection_worker is not None:
            if self._connection_worker.isRunning():
                return

        # Testujemy dokładnie tę konfigurację, która ma być używana przez
        # collector. Najpierw zapisujemy zmiany i credential dla maszyny.
        if not self.save_current_machine(
            show_message=False
        ):
            QMessageBox.warning(
                self,
                "OPC UA Client",
                "Najpierw popraw i zapisz konfigurację tej maszyny.",
            )
            return

        filter_obj = self.current_filter()

        if filter_obj is None:
            return

        self.test_connection_button.setEnabled(False)
        self.connection_status_label.setText(
            "Łączenie..."
        )

        self._connection_worker = (
            OpcClientConnectionTestWorker(
                filter_obj,
                self,
            )
        )
        self._connection_worker.success.connect(
            self._test_connection_succeeded
        )
        self._connection_worker.failed.connect(
            self._test_connection_failed
        )
        self._connection_worker.finished.connect(
            self._test_connection_finished
        )
        self._connection_worker.start()

    def _test_connection_succeeded(self) -> None:
        self.connection_status_label.setText(
            "Połączenie OPC UA: OK"
        )
        QMessageBox.information(
            self,
            "OPC UA Client",
            "Połączenie z wybraną maszyną zakończone powodzeniem.",
        )

    def _test_connection_failed(
        self,
        message: str,
    ) -> None:
        self.connection_status_label.setText(
            f"Połączenie OPC UA: BŁĄD — {message}"
        )
        QMessageBox.warning(
            self,
            "OPC UA Client",
            "Nie udało się połączyć z wybraną maszyną.\n\n"
            f"{message}",
        )

    def _test_connection_finished(self) -> None:
        self.test_connection_button.setEnabled(True)
        self._connection_worker = None

    # ==================================================
    # CERTIFICATE
    # ==================================================

    def _default_machine_certificate_paths(
        self,
    ) -> ApplicationCertificatePaths:
        filter_obj = self.current_filter()

        if filter_obj is None or filter_obj.filter_id is None:
            return create_default_certificate_paths()

        base_dir = (
            Path(CERTIFICATES_DIR)
            / f"filter_{int(filter_obj.filter_id)}"
        )

        return create_default_certificate_paths(
            base_dir=base_dir
        )

    def _default_machine_application_uri(self) -> str:
        filter_obj = self.current_filter()

        if filter_obj is None or filter_obj.filter_id is None:
            return get_default_application_uri()

        return (
            f"{get_default_application_uri()}:"
            f"filter:{int(filter_obj.filter_id)}"
        )

    def generate_certificate(self) -> None:
        filter_obj = self.current_filter()

        if filter_obj is None:
            QMessageBox.warning(
                self,
                "Certyfikat OPC UA",
                "Najpierw wybierz filtr / maszynę.",
            )
            return

        default_paths = (
            self._default_machine_certificate_paths()
        )

        certificate_path = (
            self.path_from_edit(self.certificate_edit)
            or default_paths.certificate
        )
        private_key_path = (
            self.path_from_edit(self.private_key_edit)
            or default_paths.private_key
        )
        trusted_dir = (
            self.path_from_edit(self.trusted_dir_edit)
            or default_paths.trusted
        )
        rejected_dir = trusted_dir.parent / "rejected"

        application_uri = (
            self.application_uri_edit.text().strip()
        )

        if not application_uri:
            application_uri = (
                self._default_machine_application_uri()
            )
            self.application_uri_edit.setText(
                application_uri
            )

        paths = ApplicationCertificatePaths(
            certificate=certificate_path,
            private_key=private_key_path,
            trusted=trusted_dir,
            rejected=rejected_dir,
        )

        if (
            certificate_path.exists()
            or private_key_path.exists()
        ):
            answer = QMessageBox.question(
                self,
                "Certyfikat OPC UA",
                "Certyfikat lub klucz tej maszyny już istnieje.\n\n"
                "Wygenerowanie nowego certyfikatu nadpisze aktualne "
                "pliki.\nKontynuować?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )

            if answer != QMessageBox.Yes:
                return

        try:
            info = generate_application_certificate(
                paths=paths,
                application_uri=application_uri,
                common_name=(
                    f"FiltersReporting Client - {filter_obj.name}"
                ),
                overwrite=True,
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Certyfikat OPC UA",
                "Nie udało się wygenerować certyfikatu.\n\n"
                f"{type(error).__name__}: {error}",
            )
            return

        self.certificate_edit.setText(
            str(paths.certificate)
        )
        self.private_key_edit.setText(
            str(paths.private_key)
        )
        self.trusted_dir_edit.setText(
            str(paths.trusted)
        )

        self.show_certificate_info(info)

        # Celowo NIE emitujemy certificate_generated. Ten certyfikat należy
        # do konkretnej maszyny-klienta, a nie do globalnego OPC UA Server.

        QMessageBox.information(
            self,
            "Certyfikat OPC UA",
            "Wygenerowano certyfikat klienta dla maszyny:\n"
            f"{filter_obj.name}\n\n"
            f"Certyfikat:\n{paths.certificate}\n\n"
            f"Klucz prywatny:\n{paths.private_key}",
        )

    def refresh_certificate_info(self) -> None:
        certificate_path = self.path_from_edit(
            self.certificate_edit
        )

        if (
            certificate_path is None
            or not certificate_path.is_file()
        ):
            self.certificate_info_label.setText(
                "Certyfikat: brak"
            )
            return

        try:
            info = load_certificate_info(
                certificate_path
            )
        except Exception as error:
            self.certificate_info_label.setText(
                "Certyfikat: błąd odczytu\n"
                f"{error}"
            )
            return

        self.show_certificate_info(info)

    def show_certificate_info(self, info) -> None:
        uris = ", ".join(info.application_uris) or "—"
        dns_names = ", ".join(info.dns_names) or "—"

        roles = []
        if info.client_auth:
            roles.append("Client")
        if info.server_auth:
            roles.append("Server")

        role_text = " + ".join(roles) or "—"

        self.certificate_info_label.setText(
            "Certyfikat klienta\n"
            f"CN: {info.common_name}\n"
            f"Application URI: {uris}\n"
            f"DNS: {dns_names}\n"
            f"Role: {role_text}\n"
            f"Ważny od: {info.valid_from:%Y-%m-%d %H:%M:%S %Z}\n"
            f"Ważny do: {info.valid_until:%Y-%m-%d %H:%M:%S %Z}\n"
            f"SHA-256: {info.sha256_thumbprint}"
        )
