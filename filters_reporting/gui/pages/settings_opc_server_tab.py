from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from filters_reporting.gui.pages.settings_widgets import (
    NoWheelComboBox,
    SettingsTabBase,
)
from filters_reporting.opcua.auth import (
    hash_password,
)
from filters_reporting.opcua.certificate_service import (
    ApplicationCertificatePaths,
    generate_application_certificate,
    get_default_application_uri,
    load_certificate_info,
)
from filters_reporting.opcua.security import (
    OPC_UA_SECURITY_MODES,
    OPC_UA_SECURITY_POLICIES,
)
from filters_reporting.opcua.server import (
    validate_server_settings,
)
from filters_reporting.runtime_paths import (
    CERTIFICATES_DIR,
)
from filters_reporting.settings_service import (
    AppSettings,
)


class OpcServerSettingsTab(SettingsTabBase):
    def __init__(
        self,
        settings: AppSettings,
    ):
        super().__init__()

        self.settings = settings

        self.build_ui()
        self.load_from_settings(settings)

    # ==================================================
    # UI
    # ==================================================

    def build_ui(
        self,
    ) -> None:
        self._build_restart_notice()
        self._build_server_panel()
        self._build_security_panel()
        self._build_authentication_panel()

        self.content_layout.addStretch()

        self.enabled_checkbox.toggled.connect(
            self.update_controls
        )
        self.policy_combo.currentTextChanged.connect(
            self.update_controls
        )
        self.mode_combo.currentTextChanged.connect(
            self.update_controls
        )
        self.username_edit.textChanged.connect(
            self.update_controls
        )
        self.password_edit.textChanged.connect(
            self.update_controls
        )

    # ==================================================
    # RESTART NOTICE
    # ==================================================

    def _build_restart_notice(
        self,
    ) -> None:
        notice = QLabel(
            "ℹ  Zmiany konfiguracji OPC UA Server "
            "zostaną zastosowane po ponownym "
            "uruchomieniu aplikacji."
        )
        notice.setObjectName("restartNotice")
        notice.setWordWrap(True)
        notice.setStyleSheet("""
            QLabel#restartNotice {
                color: #93c5fd;
                background-color: #10243a;
                border: 1px solid #285780;
                border-radius: 6px;
                padding: 9px 12px;
                font-size: 10px;
            }
        """)
        self.content_layout.addWidget(notice)

    # ==================================================
    # SERVER
    # ==================================================

    def _build_server_panel(
        self,
    ) -> None:
        panel = self.create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("OPC UA Server")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Lokalny serwer FiltersReporting. "
            "Udostępniane zmienne są tylko do odczytu."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.enabled_checkbox = QCheckBox(
            "Uruchamiaj z aplikacją"
        )
        self.endpoint_edit = QLineEdit()
        self.endpoint_edit.setPlaceholderText(
            "opc.tcp://127.0.0.1:4850/filtersreporting/"
        )

        self.namespace_edit = QLineEdit()
        self.namespace_edit.setPlaceholderText(
            "urn:FiltersReporting:Server"
        )

        self.application_uri_edit = QLineEdit()
        self.application_uri_edit.setPlaceholderText(
            "urn:HOST:FiltersReporting:OPCServer"
        )

        form.addRow("Serwer", self.enabled_checkbox)
        form.addRow("Endpoint", self.endpoint_edit)
        form.addRow("Namespace", self.namespace_edit)
        form.addRow(
            "Application URI",
            self.application_uri_edit,
        )

        layout.addLayout(form)
        self.content_layout.addWidget(panel)

    # ==================================================
    # SECURITY
    # ==================================================

    def _build_security_panel(
        self,
    ) -> None:
        panel = self.create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("SecureChannel")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Transport OPC UA i własny certyfikat serwera "
            "FiltersReporting. Certyfikat serwera jest niezależny "
            "od certyfikatów klientów przypisanych do filtrów."
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

        self.allow_no_security_checkbox = QCheckBox(
            "Udostępnij dodatkowo endpoint NoSecurity"
        )

        self.no_security_state_label = QLabel("—")
        self.no_security_state_label.setObjectName(
            "hint"
        )
        self.no_security_state_label.setWordWrap(True)

        self.certificate_edit = QLineEdit()
        self.private_key_edit = QLineEdit()

        certificate_row = self.create_file_row(
            self.certificate_edit,
            (
                "Certyfikaty (*.der *.pem *.crt *.cer);;"
                "Wszystkie pliki (*)"
            ),
        )
        key_row = self.create_file_row(
            self.private_key_edit,
            (
                "Klucze (*.pem *.der *.key);;"
                "Wszystkie pliki (*)"
            ),
        )

        form.addRow(
            "Security Policy",
            self.policy_combo,
        )
        form.addRow(
            "Security Mode",
            self.mode_combo,
        )
        form.addRow(
            "NoSecurity",
            self.allow_no_security_checkbox,
        )
        form.addRow(
            "",
            self.no_security_state_label,
        )
        form.addRow(
            "Certyfikat serwera",
            certificate_row,
        )
        form.addRow(
            "Klucz prywatny",
            key_row,
        )

        layout.addLayout(form)

        self.generate_certificate_button = QPushButton(
            "Generuj certyfikat serwera"
        )
        self.generate_certificate_button.setObjectName(
            "primaryButton"
        )
        self.generate_certificate_button.clicked.connect(
            self.generate_server_certificate
        )

        self.refresh_certificate_button = QPushButton(
            "Odśwież informacje"
        )
        self.refresh_certificate_button.setObjectName(
            "secondaryButton"
        )
        self.refresh_certificate_button.clicked.connect(
            self.refresh_certificate_info
        )

        actions = QHBoxLayout()
        actions.setSpacing(7)
        actions.addWidget(
            self.generate_certificate_button
        )
        actions.addWidget(
            self.refresh_certificate_button
        )
        actions.addStretch()
        layout.addLayout(actions)

        self.certificate_info_label = QLabel(
            "Certyfikat serwera: brak"
        )
        self.certificate_info_label.setObjectName(
            "certificateInfo"
        )
        self.certificate_info_label.setWordWrap(True)
        self.certificate_info_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        layout.addWidget(
            self.certificate_info_label
        )

        self.content_layout.addWidget(panel)

    # ==================================================
    # AUTHENTICATION
    # ==================================================

    def _build_authentication_panel(
        self,
    ) -> None:
        panel = self.create_panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Uwierzytelnianie")
        title.setObjectName("sectionTitle")

        hint = QLabel(
            "Anonymous może działać samodzielnie albo równolegle "
            "z Username/Password. Hasło jest przechowywane "
            "wyłącznie jako salted PBKDF2 hash."
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(hint)

        form = self.create_form()

        self.allow_anonymous_checkbox = QCheckBox(
            "Zezwól na połączenia anonimowe"
        )

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText(
            "np. operator"
        )

        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(
            QLineEdit.Password
        )
        self.password_edit.setPlaceholderText(
            "Puste = zachowaj obecne hasło"
        )

        self.password_state_label = QLabel("—")
        self.password_state_label.setObjectName(
            "passwordState"
        )

        password_layout = QVBoxLayout()
        password_layout.setSpacing(4)
        password_layout.addWidget(
            self.password_edit
        )
        password_layout.addWidget(
            self.password_state_label
        )

        form.addRow(
            "Anonymous",
            self.allow_anonymous_checkbox,
        )
        form.addRow(
            "Username",
            self.username_edit,
        )
        form.addRow(
            "Password",
            password_layout,
        )

        layout.addLayout(form)

        note = QLabel(
            "Aby wyłączyć Username/Password, wyczyść Username i zapisz. "
            "Jeżeli zmienisz Username, podaj również nowe hasło."
        )
        note.setObjectName("hint")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.content_layout.addWidget(panel)

    # ==================================================
    # STATE
    # ==================================================

    def update_controls(
        self,
    ) -> None:
        enabled = self.enabled_checkbox.isChecked()
        policy = self.policy_combo.currentText()
        mode = self.mode_combo.currentText()

        if policy == "None":
            if mode != "None":
                self.mode_combo.setCurrentText(
                    "None"
                )
            secure = False
        else:
            secure = True
            if mode == "None":
                self.mode_combo.setCurrentText(
                    "SignAndEncrypt"
                )

        self.endpoint_edit.setEnabled(enabled)
        self.namespace_edit.setEnabled(enabled)
        self.application_uri_edit.setEnabled(enabled)
        self.policy_combo.setEnabled(enabled)
        self.mode_combo.setEnabled(enabled)

        self.certificate_edit.setEnabled(
            enabled and secure
        )
        self.private_key_edit.setEnabled(
            enabled and secure
        )
        self.generate_certificate_button.setEnabled(
            enabled and secure
        )
        self.refresh_certificate_button.setEnabled(
            enabled and secure
        )

        self.allow_anonymous_checkbox.setEnabled(
            enabled
        )
        self.username_edit.setEnabled(enabled)
        self.password_edit.setEnabled(enabled)

        username = self.username_edit.text().strip()
        password_entered = bool(
            self.password_edit.text()
        )
        same_username = (
            username
            == self.settings.opc_server_username.strip()
        )
        stored_hash_available = bool(
            self.settings.opc_server_password_hash
        )
        user_auth_configured = bool(
            username
            and (
                password_entered
                or (
                    same_username
                    and stored_hash_available
                )
            )
        )

        if not enabled:
            self.allow_no_security_checkbox.setEnabled(
                False
            )
            self.no_security_state_label.setText(
                "Serwer jest wyłączony."
            )
            return

        if not secure:
            # Policy=None/Mode=None oznacza, że główny endpoint
            # już jest NoSecurity. Checkbox "dodatkowo" nie ma
            # wtedy osobnego znaczenia.
            self.allow_no_security_checkbox.blockSignals(
                True
            )
            self.allow_no_security_checkbox.setChecked(
                True
            )
            self.allow_no_security_checkbox.blockSignals(
                False
            )
            self.allow_no_security_checkbox.setEnabled(
                False
            )
            self.no_security_state_label.setText(
                "Główny endpoint działa już jako NoSecurity. "
                "Opcja dodatkowego endpointu nie jest potrzebna."
            )
            return

        if user_auth_configured:
            self.allow_no_security_checkbox.blockSignals(
                True
            )
            self.allow_no_security_checkbox.setChecked(
                False
            )
            self.allow_no_security_checkbox.blockSignals(
                False
            )
            self.allow_no_security_checkbox.setEnabled(
                False
            )
            self.no_security_state_label.setText(
                "Dodatkowy NoSecurity jest wyłączony, gdy aktywne jest "
                "Username/Password. Hasła nie mogą być wystawiane po "
                "niezabezpieczonym SecureChannel."
            )
            return

        self.allow_no_security_checkbox.setEnabled(
            True
        )
        self.no_security_state_label.setText(
            "Dla zabezpieczonego głównego endpointu możesz opcjonalnie "
            "udostępnić dodatkowo NoSecurity (np. dla Anonymous)."
        )

    # ==================================================
    # CERTIFICATE
    # ==================================================

    @staticmethod
    def _server_certificate_paths(
    ) -> ApplicationCertificatePaths:
        base_dir = (
            Path(CERTIFICATES_DIR)
            / "opc_server"
        )
        return ApplicationCertificatePaths(
            certificate=(
                base_dir
                / "filters_reporting_opc_server.der"
            ),
            private_key=(
                base_dir
                / "private"
                / "filters_reporting_opc_server_key.pem"
            ),
            trusted=(base_dir / "trusted"),
            rejected=(base_dir / "rejected"),
        )

    def generate_server_certificate(
        self,
    ) -> None:
        application_uri = (
            self.application_uri_edit.text().strip()
        )
        if not application_uri:
            application_uri = (
                f"{get_default_application_uri()}:OPCServer"
            )
            self.application_uri_edit.setText(
                application_uri
            )

        paths = self._server_certificate_paths()

        if (
            paths.certificate.exists()
            or paths.private_key.exists()
        ):
            answer = QMessageBox.question(
                self,
                "Certyfikat OPC UA Server",
                "Certyfikat serwera lub klucz prywatny już istnieje.\n\n"
                "Wygenerowanie nowego certyfikatu nadpisze aktualne pliki.\n"
                "Kontynuować?",
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
                    "FiltersReporting OPC UA Server"
                ),
                overwrite=True,
            )
        except Exception as error:
            QMessageBox.critical(
                self,
                "Certyfikat OPC UA Server",
                "Nie udało się wygenerować certyfikatu serwera.\n\n"
                f"{type(error).__name__}: {error}",
            )
            return

        self.certificate_edit.setText(
            str(paths.certificate)
        )
        self.private_key_edit.setText(
            str(paths.private_key)
        )
        self.show_certificate_info(info)

        QMessageBox.information(
            self,
            "Certyfikat OPC UA Server",
            "Wygenerowano osobny certyfikat serwera FiltersReporting.\n\n"
            f"Certyfikat:\n{paths.certificate}\n\n"
            f"Klucz prywatny:\n{paths.private_key}",
        )

    def refresh_certificate_info(
        self,
    ) -> None:
        certificate_path = self.path_from_edit(
            self.certificate_edit
        )
        if (
            certificate_path is None
            or not certificate_path.is_file()
        ):
            self.certificate_info_label.setText(
                "Certyfikat serwera: brak"
            )
            return

        try:
            info = load_certificate_info(
                certificate_path
            )
        except Exception as error:
            self.certificate_info_label.setText(
                "Certyfikat serwera: błąd odczytu\n"
                f"{error}"
            )
            return

        self.show_certificate_info(info)

    def show_certificate_info(
        self,
        info,
    ) -> None:
        application_uris = (
            ", ".join(info.application_uris)
            if info.application_uris
            else "—"
        )
        dns_names = (
            ", ".join(info.dns_names)
            if info.dns_names
            else "—"
        )
        roles = []
        if info.server_auth:
            roles.append("Server")
        if info.client_auth:
            roles.append("Client")

        self.certificate_info_label.setText(
            "Certyfikat serwera\n"
            f"CN: {info.common_name or '—'}\n"
            f"Application URI: {application_uris}\n"
            f"DNS: {dns_names}\n"
            f"Role: {' + '.join(roles) if roles else '—'}\n"
            f"Ważny do: {info.valid_until.isoformat()}\n"
            f"SHA-256: {info.sha256_thumbprint}"
        )

    # ==================================================
    # PASSWORD
    # ==================================================

    def _password_hash_for_form(
        self,
        settings: AppSettings,
        username: str,
    ) -> str:
        if not username:
            return ""

        password = self.password_edit.text()
        if password:
            return hash_password(password)

        if (
            username
            == settings.opc_server_username.strip()
        ):
            return settings.opc_server_password_hash

        return ""

    # ==================================================
    # SETTINGS
    # ==================================================

    def apply_to_settings(
        self,
        settings: AppSettings,
    ) -> AppSettings:
        username = self.username_edit.text().strip()

        return replace(
            settings,
            opc_server_enabled=(
                self.enabled_checkbox.isChecked()
            ),
            opc_server_endpoint=(
                self.endpoint_edit.text().strip()
            ),
            opc_server_namespace=(
                self.namespace_edit.text().strip()
            ),
            opc_server_application_uri=(
                self.application_uri_edit.text().strip()
            ),
            opc_server_security_policy=(
                self.policy_combo.currentText()
            ),
            opc_server_security_mode=(
                self.mode_combo.currentText()
            ),
            opc_server_allow_no_security=(
                self.allow_no_security_checkbox.isChecked()
            ),
            opc_server_certificate_path=(
                self.path_from_edit(
                    self.certificate_edit
                )
            ),
            opc_server_private_key_path=(
                self.path_from_edit(
                    self.private_key_edit
                )
            ),
            opc_server_allow_anonymous=(
                self.allow_anonymous_checkbox.isChecked()
            ),
            opc_server_username=username,
            opc_server_password_hash=(
                self._password_hash_for_form(
                    settings,
                    username,
                )
            ),
        )

    # ==================================================
    # VALIDATION
    # ==================================================

    def validate(
        self,
        settings: AppSettings,
    ) -> tuple[bool, str]:
        if not settings.opc_server_enabled:
            return True, ""

        try:
            validate_server_settings(settings)
        except (
            ValueError,
            FileNotFoundError,
        ) as error:
            return (
                False,
                f"OPC UA Server:\n{error}",
            )

        authentication = (
            settings.to_opc_server_authentication_config()
        )
        if (
            authentication.username_enabled
            and settings.opc_server_allow_no_security
        ):
            return (
                False,
                (
                    "OPC UA Server:\n"
                    "Username/Password nie może być "
                    "udostępniane razem z endpointem NoSecurity."
                ),
            )

        return True, ""

    # ==================================================
    # LOAD
    # ==================================================

    def load_from_settings(
        self,
        settings: AppSettings,
    ) -> None:
        self.settings = settings

        self.enabled_checkbox.setChecked(
            settings.opc_server_enabled
        )
        self.endpoint_edit.setText(
            settings.opc_server_endpoint
        )
        self.namespace_edit.setText(
            settings.opc_server_namespace
        )
        self.application_uri_edit.setText(
            settings.opc_server_application_uri
        )
        self.policy_combo.setCurrentText(
            settings.opc_server_security_policy
        )
        self.mode_combo.setCurrentText(
            settings.opc_server_security_mode
        )
        self.allow_no_security_checkbox.setChecked(
            settings.opc_server_allow_no_security
        )
        self.certificate_edit.setText(
            str(settings.opc_server_certificate_path)
            if settings.opc_server_certificate_path
            else ""
        )
        self.private_key_edit.setText(
            str(settings.opc_server_private_key_path)
            if settings.opc_server_private_key_path
            else ""
        )
        self.allow_anonymous_checkbox.setChecked(
            settings.opc_server_allow_anonymous
        )
        self.username_edit.setText(
            settings.opc_server_username
        )
        self.password_edit.clear()

        if settings.opc_server_password_hash:
            self.password_state_label.setText(
                "Hasło ustawione"
            )
        else:
            self.password_state_label.setText(
                "Brak hasła"
            )

        self.update_controls()
        self.refresh_certificate_info()
