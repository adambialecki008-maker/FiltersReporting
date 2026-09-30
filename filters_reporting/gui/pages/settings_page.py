from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from filters_reporting.gui.pages.settings_general_tab import (
    GeneralSettingsTab,
)
from filters_reporting.gui.pages.settings_opc_client_tab import (
    OpcClientSettingsTab,
)
from filters_reporting.gui.pages.settings_opc_server_tab import (
    OpcServerSettingsTab,
)
from filters_reporting.gui.pages.settings_widgets import (
    NoWheelTabWidget,
)
from filters_reporting.settings_service import (
    load_settings,
    save_email_password,
    save_settings,
)


class SettingsPage(QWidget):
    def __init__(
        self,
        repository=None,
    ):
        super().__init__()

        self.setObjectName("settingsPage")
        self.repository = repository
        self.settings = load_settings()

        self.build_ui()
        self.apply_style()

    # ==============================================
    # UI
    # ==============================================

    def build_ui(
        self,
    ) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            20,
            14,
            20,
            14,
        )
        main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_text_layout = QVBoxLayout()
        header_text_layout.setSpacing(0)

        title = QLabel("Ustawienia")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Konfiguracja aplikacji, raportów, " "SMTP i komunikacji OPC UA."
        )
        subtitle.setObjectName("subtitle")

        header_text_layout.addWidget(title)
        header_text_layout.addWidget(subtitle)
        header_layout.addLayout(header_text_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        self.tabs = NoWheelTabWidget()
        self.tabs.setObjectName("settingsTabs")

        self.general_tab = GeneralSettingsTab(self.settings)
        self.opc_client_tab = OpcClientSettingsTab(
            self.settings,
            repository=self.repository,
        )
        self.opc_server_tab = OpcServerSettingsTab(self.settings)

        self.tabs.addTab(
            self.general_tab,
            "Ogólne",
        )
        self.tabs.addTab(
            self.opc_client_tab,
            "OPC UA Client",
        )
        self.tabs.addTab(
            self.opc_server_tab,
            "OPC UA Server",
        )

        # OPC UA Client ma już własny przycisk:
        # "Zapisz konfigurację maszyny".
        # Dodajemy analogiczne, niezależne zapisy dla
        # Ogólne i OPC UA Server.
        self.general_save_button = self._insert_tab_save_button(
            self.general_tab,
            "Zapisz Ogólne",
            self.save_general_settings,
        )
        self.server_save_button = self._insert_tab_save_button(
            self.opc_server_tab,
            "Zapisz OPC UA Server",
            self.save_opc_server_settings,
        )

        main_layout.addWidget(self.tabs, 1)

    def _insert_tab_save_button(
        self,
        tab,
        text: str,
        slot,
    ) -> QPushButton:
        row = QHBoxLayout()
        row.addStretch()

        button = QPushButton(text)
        button.setObjectName("primaryButton")
        button.clicked.connect(slot)
        row.addWidget(button)

        # Każdy SettingsTabBase kończy się stretch'em.
        # Wstawiamy przycisk przed nim, więc jest na dole
        # treści konkretnej zakładki, a nie globalnie w headerze.
        insert_index = max(
            0,
            tab.content_layout.count() - 1,
        )
        tab.content_layout.insertLayout(
            insert_index,
            row,
        )

        return button

    # ==============================================
    # SEPARATE SAVE: GENERAL
    # ==============================================

    def save_general_settings(
        self,
        checked: bool = False,
    ) -> bool:
        del checked

        try:
            database_changed = self.general_tab.database_location_changed()
            database_path = self.general_tab.get_database_path_from_form()
        except ValueError as error:
            self.tabs.setCurrentWidget(self.general_tab)
            QMessageBox.warning(
                self,
                "Baza danych",
                str(error),
            )
            return False

        settings = self.general_tab.apply_to_settings(self.settings)
        valid, validation_message = self.general_tab.validate(settings)

        if not valid:
            self.tabs.setCurrentWidget(self.general_tab)
            QMessageBox.warning(
                self,
                "Ogólne",
                validation_message,
            )
            return False

        smtp_password = self.general_tab.get_smtp_password()

        try:
            save_settings(settings)
            self.general_tab.save_database_location()

            if smtp_password.strip():
                save_email_password(smtp_password)
        except (
            OSError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self,
                "Ogólne",
                "Nie udało się zapisać ustawień.\n\n" f"{error}",
            )
            return False

        self.settings = settings
        self.general_tab.load_from_settings(settings)

        if database_changed:
            QMessageBox.information(
                self,
                "Ogólne",
                "Ustawienia zostały zapisane.\n\n"
                "Nowa lokalizacja bazy danych:\n"
                f"{database_path}\n\n"
                "Zmiana bazy zacznie obowiązywać "
                "po ponownym uruchomieniu "
                "FiltersReporting.\n\n"
                "Jeśli wskazany plik nie istnieje, "
                "aplikacja utworzy nową, pustą bazę. "
                "Istniejąca baza NIE jest przenoszona "
                "automatycznie.\n\n"
                "Aby zachować dane, zamknij aplikację "
                "i collector, a następnie ręcznie "
                "skopiuj obecny plik .db do nowej "
                "lokalizacji przed ponownym "
                "uruchomieniem.",
            )
        else:
            QMessageBox.information(
                self,
                "Ogólne",
                "Ustawienia ogólne zostały zapisane.",
            )

        return True

    # ==============================================
    # SEPARATE SAVE: OPC UA SERVER
    # ==============================================

    def save_opc_server_settings(
        self,
        checked: bool = False,
    ) -> bool:
        del checked

        settings = self.opc_server_tab.apply_to_settings(self.settings)
        valid, validation_message = self.opc_server_tab.validate(settings)

        if not valid:
            self.tabs.setCurrentWidget(self.opc_server_tab)
            QMessageBox.warning(
                self,
                "OPC UA Server",
                validation_message,
            )
            return False

        try:
            save_settings(settings)
        except (
            OSError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self,
                "OPC UA Server",
                "Nie udało się zapisać konfiguracji " "OPC UA Server.\n\n" f"{error}",
            )
            return False

        self.settings = settings
        self.opc_server_tab.load_from_settings(settings)

        QMessageBox.information(
            self,
            "OPC UA Server",
            "Konfiguracja OPC UA Server została "
            "zapisana. Zmiany zaczną obowiązywać "
            "po ponownym uruchomieniu aplikacji.",
        )
        return True

    # ==============================================
    # LEGACY / TEST COMPATIBILITY
    # ==============================================

    def build_settings_from_tabs(
        self,
    ):
        settings = self.settings
        settings = self.general_tab.apply_to_settings(settings)
        settings = self.opc_client_tab.apply_to_settings(settings)
        settings = self.opc_server_tab.apply_to_settings(settings)
        return settings

    def validate_tabs(
        self,
        settings,
    ) -> tuple[bool, str]:
        for tab in (
            self.general_tab,
            self.opc_client_tab,
            self.opc_server_tab,
        ):
            valid, message = tab.validate(settings)
            if not valid:
                return False, message

        return True, ""

    def save_settings_from_tabs(
        self,
    ) -> None:
        """Legacy helper retained for existing tests/callers.

        UI nie używa już globalnego zapisu. Normalnie zapisujemy
        każdą zakładkę osobno.
        """
        try:
            database_changed = self.general_tab.database_location_changed()
            database_path = self.general_tab.get_database_path_from_form()
        except ValueError as error:
            self.tabs.setCurrentWidget(self.general_tab)
            QMessageBox.warning(
                self,
                "Baza danych",
                str(error),
            )
            return

        settings = self.build_settings_from_tabs()
        valid, validation_message = self.validate_tabs(settings)
        if not valid:
            QMessageBox.warning(
                self,
                "Ustawienia",
                validation_message,
            )
            return

        smtp_password = self.general_tab.get_smtp_password()

        try:
            save_settings(settings)
            self.general_tab.save_database_location()
            if smtp_password.strip():
                save_email_password(smtp_password)
        except (
            OSError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self,
                "Ustawienia",
                "Nie udało się zapisać " "ustawień.\n\n" f"{error}",
            )
            return

        self.settings = settings
        self.load_tabs_from_settings()

        if database_changed:
            QMessageBox.information(
                self,
                "Ustawienia",
                "Ustawienia zostały zapisane.\n\n"
                "Nowa lokalizacja bazy danych:\n"
                f"{database_path}\n\n"
                "Zmiana bazy zacznie obowiązywać "
                "po ponownym uruchomieniu "
                "FiltersReporting.\n\n"
                "Jeśli wskazany plik nie istnieje, "
                "aplikacja utworzy nową, pustą bazę. "
                "Istniejąca baza NIE jest przenoszona "
                "automatycznie.\n\n"
                "Aby zachować dane, zamknij aplikację "
                "i collector, a następnie ręcznie "
                "skopiuj obecny plik .db do nowej "
                "lokalizacji przed ponownym "
                "uruchomieniem.",
            )
        else:
            QMessageBox.information(
                self,
                "Ustawienia",
                "Ustawienia zostały zapisane.",
            )

    # ==============================================
    # LOAD
    # ==============================================

    def load_tabs_from_settings(
        self,
    ) -> None:
        self.general_tab.load_from_settings(self.settings)
        self.opc_client_tab.load_from_settings(self.settings)
        self.opc_server_tab.load_from_settings(self.settings)

    def reload_settings(
        self,
    ) -> None:
        self.settings = load_settings()
        self.load_tabs_from_settings()

    # ==============================================
    # STYLE
    # ==============================================

    def apply_style(
        self,
    ) -> None:
        self.setStyleSheet("""
            QWidget#settingsPage,
            QWidget#settingsTab,
            QWidget#settingsTabContent {
                background-color: #0b1220;
            }

            QScrollArea#settingsTabScroll {
                background-color: #0b1220;
                border: none;
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
            QLabel#hint,
            QLabel#pathLabel,
            QLabel#passwordState {
                color: #8296aa;
                font-size: 10px;
            }

            QLabel#pathLabel,
            QLabel#certificateInfo {
                font-family: Consolas;
            }

            QLabel#sectionTitle {
                color: #f5f8fc;
                font-size: 13px;
                font-weight: 700;
            }

            QLabel#certificateInfo {
                color: #a9bacb;
                background-color: #0d1724;
                border: 1px solid #26384c;
                border-radius: 5px;
                padding: 9px;
                font-size: 10px;
            }

            QFrame#panel {
                background-color: #111b28;
                border: 1px solid #26384c;
                border-radius: 8px;
            }

            QTabWidget#settingsTabs::pane {
                border: 1px solid #26384c;
                border-radius: 7px;
                background-color: #0b1220;
                top: -1px;
            }

            QTabBar::tab {
                background-color: #111b28;
                color: #9fb0c2;
                border: 1px solid #26384c;
                border-bottom: none;
                min-width: 135px;
                min-height: 34px;
                padding: 0 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
            }

            QTabBar::tab:selected {
                background-color: #1a2a3d;
                color: #ffffff;
                border-color: #3a5875;
            }

            QTabBar::tab:hover:!selected {
                background-color: #162334;
            }

            QLineEdit,
            QSpinBox,
            QDoubleSpinBox,
            QTimeEdit,
            QComboBox {
                background-color: #0d1724;
                color: #e7edf4;
                border: 1px solid #2b4056;
                border-radius: 5px;
                padding: 6px 9px;
                min-height: 28px;
                selection-background-color: #2563eb;
            }

            QLineEdit:focus,
            QSpinBox:focus,
            QDoubleSpinBox:focus,
            QTimeEdit:focus,
            QComboBox:focus {
                border: 1px solid #3b82f6;
            }

            QLineEdit:disabled,
            QSpinBox:disabled,
            QDoubleSpinBox:disabled,
            QTimeEdit:disabled,
            QComboBox:disabled {
                color: #617386;
                background-color: #101925;
                border-color: #243546;
            }

            QCheckBox {
                color: #dbe5ef;
                spacing: 7px;
            }

            QPushButton {
                background-color: #162334;
                color: #e3ebf4;
                border: 1px solid #30475f;
                border-radius: 5px;
                min-height: 30px;
                padding: 3px 13px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #1c2c40;
                border-color: #426281;
            }

            QPushButton#primaryButton {
                background-color: #2563eb;
                border: 1px solid #3478f6;
                color: #ffffff;
            }

            QPushButton#primaryButton:hover {
                background-color: #2f6ff0;
            }

            QPushButton#secondaryButton {
                background-color: #142132;
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
