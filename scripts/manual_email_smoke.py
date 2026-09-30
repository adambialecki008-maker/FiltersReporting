from filters_reporting.reporting.email_reporting import (
    EmailConfig,
    create_report_email,
    create_smtp_client,
    login_smtp,
    send_email,
    get_email_password,
    send_generated_report,
)
from filters_reporting.config import (
    SMTP_HOST,
    SMTP_PORT,
    EMAIL_USERNAME,
    EMAIL_SENDER,
    EMAIL_RECIPIENTS,
    DATABASE_NAME,
)
from filters_reporting.database.filters_repository import FiltersRepository
from datetime import date
from main import generate_reports_for_day

email_config = EmailConfig(
    smtp_host=SMTP_HOST,
    smtp_port=SMTP_PORT,
    username=EMAIL_USERNAME,
    sender=EMAIL_SENDER,
    recipients=EMAIL_RECIPIENTS,
)
chosen_day = "2026-08-28"
repository = FiltersRepository(DATABASE_NAME)
paths = generate_reports_for_day(
    repository,
    chosen_day,
)
if paths is None:
    print("Brak danych")
else:
    excel_path, txt_path = paths
send_generated_report(
    chosen_day,
    excel_path,
    txt_path,
    email_config,
)
