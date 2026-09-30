from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from filters_reporting.reporting.email_reporting import (
    EmailConfig,
)

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

REPORTS_DIR = BASE_DIR / "reports"

DATABASE_NAME = DATA_DIR / "filters.db"

SAMPLE_INTERVAL_SECONDS = 60

DATA_SOURCE = "OPC_UA"

LOG_MAX_BYTES = 5_000_000
LOG_BACKUP_COUNT = 5


# ======================================================
# SMTP
# ======================================================

SMTP_HOST = os.getenv(
    "SMTP_HOST",
    "",
).strip()

SMTP_PORT = int(
    os.getenv(
        "SMTP_PORT",
        "465",
    )
)

EMAIL_USERNAME = os.getenv(
    "EMAIL_USERNAME",
    "",
).strip()

EMAIL_SENDER = os.getenv(
    "EMAIL_SENDER",
    "",
).strip()

EMAIL_RECIPIENTS = [
    recipient.strip()
    for recipient in os.getenv(
        "EMAIL_RECIPIENTS",
        "",
    ).split(";")
    if recipient.strip()
]


# ======================================================
# LOGGING
# ======================================================

LOG_DIR = BASE_DIR / "logs"

LOG_FILE = LOG_DIR / "collector.log"

LOGGER_NAME = "data_collector"

LOG_FORMAT = "%(asctime)s " "%(levelname)s " "%(message)s"

LOG_LEVEL = "INFO"


# ======================================================
# EMAIL CONFIG
# ======================================================

EMAIL_CONFIG = EmailConfig(
    smtp_host=SMTP_HOST,
    smtp_port=SMTP_PORT,
    username=EMAIL_USERNAME,
    sender=EMAIL_SENDER,
    recipients=EMAIL_RECIPIENTS,
)
