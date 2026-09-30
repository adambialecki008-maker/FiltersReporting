from filters_reporting.reporting.excel_report import create_excel_report
from filters_reporting.reporting.text_report import (
    build_filter_statistics_report,
    save_report_to_txt,
)
from filters_reporting.reporting.email_reporting import send_generated_report


def generate_reports_for_day(repository, chosen_day):
    stats = repository.get_daily_filter_stats(chosen_day)
    samples = repository.get_daily_samples_for_report(chosen_day)

    if not stats or not samples:
        return False

    report = build_filter_statistics_report(stats)

    txt_path = save_report_to_txt(report, chosen_day)
    excel_path = create_excel_report(stats, samples, chosen_day)
    if not txt_path or not excel_path:
        return False
    return excel_path, txt_path


def generate_and_send_reports_for_day(
    repository,
    chosen_day,
    email_config,
):
    result = generate_reports_for_day(
        repository,
        chosen_day,
    )
    if not result:
        return False
    excel_path, txt_path = result
    send_generated_report(
        excel_path=excel_path,
        txt_path=txt_path,
        chosen_day=chosen_day,
        email_config=email_config,
    )
    return True
