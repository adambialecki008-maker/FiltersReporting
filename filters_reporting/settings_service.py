from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filters_reporting.config import (
    DATA_DIR,
    EMAIL_CONFIG,
    REPORTS_DIR,
)
from filters_reporting.opcua.auth import (
    OpcUaAuthenticationConfig,
)
from filters_reporting.opcua.security import (
    OpcUaSecurityConfig,
)
from filters_reporting.reporting.email_reporting import (
    EmailConfig,
)
from filters_reporting.smtp_credentials import (
    has_smtp_password,
    set_smtp_password,
)

SETTINGS_FILE = DATA_DIR / "settings.json"


OPC_UA_SECURITY_POLICIES = (
    "None",
    "Basic256Sha256",
    "Aes128Sha256RsaOaep",
    "Aes256Sha256RsaPss",
)

OPC_UA_SECURITY_MODES = (
    "None",
    "Sign",
    "SignAndEncrypt",
)


@dataclass(slots=True)
class AppSettings:
    # ==================================================
    # REPORTS / SMTP
    # ==================================================

    reports_dir: Path
    smtp_host: str
    smtp_port: int
    username: str
    sender: str
    recipients: list[str]

    # ==================================================
    # AUTOMATIC REPORT
    # ==================================================

    auto_report_enabled: bool = False
    auto_report_time: str = "06:00"
    auto_report_send_email: bool = False

    # ==================================================
    # OPC UA CLIENT
    # ==================================================

    opc_client_security_policy: str = "None"
    opc_client_security_mode: str = "None"
    opc_client_application_uri: str = ""

    opc_client_certificate_path: Path | None = None
    opc_client_private_key_path: Path | None = None
    opc_client_trusted_dir: Path | None = None
    opc_client_server_certificate_path: Path | None = None

    opc_client_validate_server_certificate: bool = True

    # ==================================================
    # OPC UA SERVER
    # ==================================================

    opc_server_enabled: bool = False

    opc_server_endpoint: str = "opc.tcp://0.0.0.0:4840/" "filtersreporting/"

    opc_server_namespace: str = "urn:FiltersReporting:Server"

    opc_server_application_uri: str = ""

    opc_server_security_policy: str = "Aes256Sha256RsaPss"

    opc_server_security_mode: str = "SignAndEncrypt"

    opc_server_allow_no_security: bool = False

    opc_server_certificate_path: Path | None = None
    opc_server_private_key_path: Path | None = None

    # ==================================================
    # OPC UA SERVER AUTHENTICATION
    # ==================================================

    opc_server_allow_anonymous: bool = True
    opc_server_username: str = ""
    opc_server_password_hash: str = ""

    # ==================================================
    # CONVERSIONS
    # ==================================================

    def to_email_config(
        self,
    ) -> EmailConfig:
        return EmailConfig(
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            username=self.username,
            sender=self.sender,
            recipients=list(self.recipients),
        )

    def to_opc_client_security_config(
        self,
    ) -> OpcUaSecurityConfig:
        return OpcUaSecurityConfig(
            policy=(self.opc_client_security_policy),
            mode=(self.opc_client_security_mode),
            application_uri=(self.opc_client_application_uri),
            certificate_path=(self.opc_client_certificate_path),
            private_key_path=(self.opc_client_private_key_path),
            trusted_certificates_dir=(self.opc_client_trusted_dir),
            server_certificate_path=(self.opc_client_server_certificate_path),
            validate_server_certificate=(self.opc_client_validate_server_certificate),
        )

    def to_opc_server_authentication_config(
        self,
    ) -> OpcUaAuthenticationConfig:
        return OpcUaAuthenticationConfig(
            allow_anonymous=(self.opc_server_allow_anonymous),
            username=(self.opc_server_username),
            password_hash=(self.opc_server_password_hash),
        )


# ======================================================
# HELPERS
# ======================================================


def _optional_path(
    value,
) -> Path | None:
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return Path(value).expanduser()


def _read_bool(
    data: dict,
    key: str,
    default: bool,
) -> bool:
    value = data.get(
        key,
        default,
    )

    if isinstance(
        value,
        bool,
    ):
        return value

    return default


def _read_choice(
    data: dict,
    key: str,
    allowed_values,
    default: str,
) -> str:
    value = str(
        data.get(
            key,
            default,
        )
    ).strip()

    if value not in allowed_values:
        return default

    return value


def _normalise_time(
    value,
    default: str,
) -> str:
    value = str(value).strip()

    try:
        parsed = datetime.strptime(
            value,
            "%H:%M",
        )

    except ValueError:
        return default

    return parsed.strftime("%H:%M")


def _normalise_security(
    policy: str,
    mode: str,
) -> tuple[str, str]:
    if policy == "None" or mode == "None":
        return (
            "None",
            "None",
        )

    return (
        policy,
        mode,
    )


# ======================================================
# DEFAULT SETTINGS
# ======================================================


def get_default_settings() -> AppSettings:
    return AppSettings(
        reports_dir=Path(REPORTS_DIR),
        smtp_host=(EMAIL_CONFIG.smtp_host),
        smtp_port=(EMAIL_CONFIG.smtp_port),
        username=(EMAIL_CONFIG.username),
        sender=(EMAIL_CONFIG.sender),
        recipients=list(EMAIL_CONFIG.recipients),
    )


# ======================================================
# LOAD
# ======================================================


def load_settings() -> AppSettings:
    defaults = get_default_settings()

    if not SETTINGS_FILE.exists():
        apply_settings_runtime(defaults)

        return defaults

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        apply_settings_runtime(defaults)

        return defaults

    if not isinstance(
        data,
        dict,
    ):
        apply_settings_runtime(defaults)

        return defaults

    smtp_data = data.get(
        "smtp",
        {},
    )

    auto_report_data = data.get(
        "auto_report",
        {},
    )

    opc_client_data = data.get(
        "opc_ua_client",
        {},
    )

    opc_server_data = data.get(
        "opc_ua_server",
        {},
    )

    if not isinstance(
        smtp_data,
        dict,
    ):
        smtp_data = {}

    if not isinstance(
        auto_report_data,
        dict,
    ):
        auto_report_data = {}

    if not isinstance(
        opc_client_data,
        dict,
    ):
        opc_client_data = {}

    if not isinstance(
        opc_server_data,
        dict,
    ):
        opc_server_data = {}

    reports_dir_raw = data.get(
        "reports_dir",
        str(defaults.reports_dir),
    )

    recipients_raw = smtp_data.get(
        "recipients",
        defaults.recipients,
    )

    if not isinstance(
        recipients_raw,
        list,
    ):
        recipients_raw = defaults.recipients

    try:
        smtp_port = int(
            smtp_data.get(
                "port",
                defaults.smtp_port,
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        smtp_port = defaults.smtp_port

    # ==================================================
    # OPC UA CLIENT SECURITY
    # ==================================================

    client_policy = _read_choice(
        opc_client_data,
        "security_policy",
        OPC_UA_SECURITY_POLICIES,
        defaults.opc_client_security_policy,
    )

    client_mode = _read_choice(
        opc_client_data,
        "security_mode",
        OPC_UA_SECURITY_MODES,
        defaults.opc_client_security_mode,
    )

    (
        client_policy,
        client_mode,
    ) = _normalise_security(
        client_policy,
        client_mode,
    )

    # ==================================================
    # OPC UA SERVER SECURITY
    # ==================================================

    server_policy = _read_choice(
        opc_server_data,
        "security_policy",
        OPC_UA_SECURITY_POLICIES,
        defaults.opc_server_security_policy,
    )

    server_mode = _read_choice(
        opc_server_data,
        "security_mode",
        OPC_UA_SECURITY_MODES,
        defaults.opc_server_security_mode,
    )

    (
        server_policy,
        server_mode,
    ) = _normalise_security(
        server_policy,
        server_mode,
    )

    settings = AppSettings(
        # ----------------------------------------------
        # REPORTS / SMTP
        # ----------------------------------------------
        reports_dir=Path(reports_dir_raw).expanduser(),
        smtp_host=str(
            smtp_data.get(
                "host",
                defaults.smtp_host,
            )
        ).strip(),
        smtp_port=(smtp_port),
        username=str(
            smtp_data.get(
                "username",
                defaults.username,
            )
        ).strip(),
        sender=str(
            smtp_data.get(
                "sender",
                defaults.sender,
            )
        ).strip(),
        recipients=[
            str(recipient).strip()
            for recipient in recipients_raw
            if str(recipient).strip()
        ],
        # ----------------------------------------------
        # AUTOMATIC REPORT
        # ----------------------------------------------
        auto_report_enabled=(
            _read_bool(
                auto_report_data,
                "enabled",
                defaults.auto_report_enabled,
            )
        ),
        auto_report_time=(
            _normalise_time(
                auto_report_data.get(
                    "time",
                    defaults.auto_report_time,
                ),
                defaults.auto_report_time,
            )
        ),
        auto_report_send_email=(
            _read_bool(
                auto_report_data,
                "send_email",
                defaults.auto_report_send_email,
            )
        ),
        # ----------------------------------------------
        # OPC UA CLIENT
        # ----------------------------------------------
        opc_client_security_policy=(client_policy),
        opc_client_security_mode=(client_mode),
        opc_client_application_uri=str(
            opc_client_data.get(
                "application_uri",
                defaults.opc_client_application_uri,
            )
        ).strip(),
        opc_client_certificate_path=(
            _optional_path(
                opc_client_data.get(
                    "certificate_path",
                    defaults.opc_client_certificate_path,
                )
            )
        ),
        opc_client_private_key_path=(
            _optional_path(
                opc_client_data.get(
                    "private_key_path",
                    defaults.opc_client_private_key_path,
                )
            )
        ),
        opc_client_trusted_dir=(
            _optional_path(
                opc_client_data.get(
                    "trusted_dir",
                    defaults.opc_client_trusted_dir,
                )
            )
        ),
        opc_client_server_certificate_path=(
            _optional_path(
                opc_client_data.get(
                    "server_certificate_path",
                    defaults.opc_client_server_certificate_path,
                )
            )
        ),
        opc_client_validate_server_certificate=(
            _read_bool(
                opc_client_data,
                "validate_server_certificate",
                defaults.opc_client_validate_server_certificate,
            )
        ),
        # ----------------------------------------------
        # OPC UA SERVER
        # ----------------------------------------------
        opc_server_enabled=(
            _read_bool(
                opc_server_data,
                "enabled",
                defaults.opc_server_enabled,
            )
        ),
        opc_server_endpoint=str(
            opc_server_data.get(
                "endpoint",
                defaults.opc_server_endpoint,
            )
        ).strip(),
        opc_server_namespace=str(
            opc_server_data.get(
                "namespace",
                defaults.opc_server_namespace,
            )
        ).strip(),
        opc_server_application_uri=str(
            opc_server_data.get(
                "application_uri",
                defaults.opc_server_application_uri,
            )
        ).strip(),
        opc_server_security_policy=(server_policy),
        opc_server_security_mode=(server_mode),
        opc_server_allow_no_security=(
            _read_bool(
                opc_server_data,
                "allow_no_security",
                defaults.opc_server_allow_no_security,
            )
        ),
        opc_server_certificate_path=(
            _optional_path(
                opc_server_data.get(
                    "certificate_path",
                    defaults.opc_server_certificate_path,
                )
            )
        ),
        opc_server_private_key_path=(
            _optional_path(
                opc_server_data.get(
                    "private_key_path",
                    defaults.opc_server_private_key_path,
                )
            )
        ),
        # ----------------------------------------------
        # OPC UA SERVER AUTHENTICATION
        # ----------------------------------------------
        opc_server_allow_anonymous=(
            _read_bool(
                opc_server_data,
                "allow_anonymous",
                defaults.opc_server_allow_anonymous,
            )
        ),
        opc_server_username=str(
            opc_server_data.get(
                "username",
                defaults.opc_server_username,
            )
        ).strip(),
        opc_server_password_hash=str(
            opc_server_data.get(
                "password_hash",
                defaults.opc_server_password_hash,
            )
        ).strip(),
    )

    apply_settings_runtime(settings)

    return settings


# ======================================================
# SAVE
# ======================================================


def save_settings(
    settings: AppSettings,
) -> None:
    settings.reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    SETTINGS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "reports_dir": str(settings.reports_dir),
        "smtp": {
            "host": (settings.smtp_host),
            "port": (settings.smtp_port),
            "username": (settings.username),
            "sender": (settings.sender),
            "recipients": list(settings.recipients),
        },
        "auto_report": {
            "enabled": (settings.auto_report_enabled),
            "time": (settings.auto_report_time),
            "send_email": (settings.auto_report_send_email),
        },
        "opc_ua_client": {
            "security_policy": (settings.opc_client_security_policy),
            "security_mode": (settings.opc_client_security_mode),
            "application_uri": (settings.opc_client_application_uri),
            "certificate_path": (
                str(settings.opc_client_certificate_path)
                if settings.opc_client_certificate_path
                else ""
            ),
            "private_key_path": (
                str(settings.opc_client_private_key_path)
                if settings.opc_client_private_key_path
                else ""
            ),
            "trusted_dir": (
                str(settings.opc_client_trusted_dir)
                if settings.opc_client_trusted_dir
                else ""
            ),
            "server_certificate_path": (
                str(settings.opc_client_server_certificate_path)
                if settings.opc_client_server_certificate_path
                else ""
            ),
            "validate_server_certificate": (
                settings.opc_client_validate_server_certificate
            ),
        },
        "opc_ua_server": {
            "enabled": (settings.opc_server_enabled),
            "endpoint": (settings.opc_server_endpoint),
            "namespace": (settings.opc_server_namespace),
            "application_uri": (settings.opc_server_application_uri),
            "security_policy": (settings.opc_server_security_policy),
            "security_mode": (settings.opc_server_security_mode),
            "allow_no_security": (settings.opc_server_allow_no_security),
            "certificate_path": (
                str(settings.opc_server_certificate_path)
                if settings.opc_server_certificate_path
                else ""
            ),
            "private_key_path": (
                str(settings.opc_server_private_key_path)
                if settings.opc_server_private_key_path
                else ""
            ),
            "allow_anonymous": (settings.opc_server_allow_anonymous),
            "username": (settings.opc_server_username),
            "password_hash": (settings.opc_server_password_hash),
        },
    }

    SETTINGS_FILE.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    apply_settings_runtime(settings)


# ======================================================
# RUNTIME SETTINGS
# ======================================================


def apply_settings_runtime(
    settings: AppSettings,
) -> None:
    EMAIL_CONFIG.smtp_host = settings.smtp_host

    EMAIL_CONFIG.smtp_port = settings.smtp_port

    EMAIL_CONFIG.username = settings.username

    EMAIL_CONFIG.sender = settings.sender

    EMAIL_CONFIG.recipients = list(settings.recipients)


# ======================================================
# SMTP PASSWORD
# ======================================================


def set_runtime_email_password(
    password: str,
) -> None:
    password = password.strip()

    if password:
        os.environ["EMAIL_PASSWORD"] = password


def has_runtime_email_password() -> bool:
    return bool(os.getenv("EMAIL_PASSWORD"))


def save_email_password(
    password: str,
) -> None:
    """Persist an SMTP password for the current Windows user.

    The password is protected with Windows DPAPI and is never written to
    settings.json. A non-empty value also becomes immediately available to
    the current process through EMAIL_PASSWORD.
    """

    password = str(
        password or ""
    ).strip()

    if not password:
        return

    set_smtp_password(
        password
    )

    set_runtime_email_password(
        password
    )


def has_email_password() -> bool:
    """Return True when SMTP credentials are available now or persistently."""

    if has_runtime_email_password():
        return True

    return has_smtp_password()


# ======================================================
# REPORT FILES
# ======================================================


def move_generated_report_files(
    excel_path,
    txt_path,
    target_dir,
):
    target_dir = Path(target_dir).expanduser()

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    moved_paths = []

    for source_path in (
        excel_path,
        txt_path,
    ):
        source = Path(source_path)

        target = target_dir / source.name

        try:
            same_file = source.resolve() == target.resolve()

        except OSError:
            same_file = False

        if same_file:
            moved_paths.append(source)

            continue

        if target.exists():
            target.unlink()

        shutil.move(
            str(source),
            str(target),
        )

        moved_paths.append(target)

    return tuple(moved_paths)
