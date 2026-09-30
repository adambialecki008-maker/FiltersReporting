from filters_reporting.config import REPORTS_DIR


def build_filter_statistics_report(stats):
    report = []

    for stat in stats:
        lines = [
            f"Filtr: {stat.filter_name}",
            f"Minimum ΔP: {stat.min_delta_p} Pa",
            f"Maximum ΔP: {stat.max_delta_p} Pa",
            f"Średnia ΔP: {stat.avg_delta_p:.0f} Pa",
            f"Próg ΔP: {stat.delta_p_threshold} Pa",
            f"Liczba próbek: {stat.sample_count}",
            f"Liczba alarmów: {stat.alarm_count}",
        ]

        if stat.sample_count != 0:
            alarm_percentage = stat.alarm_count / stat.sample_count * 100

            working_percentage = stat.status_count / stat.sample_count * 100

            lines.append(f"Alarm był aktywny w " f"{alarm_percentage:.1f}% próbek")

            lines.append(f"Liczba próbek podczas pracy filtra: " f"{stat.status_count}")

            lines.append(f"Filtr pracował w " f"{working_percentage:.1f}% próbek")

            if stat.max_delta_p >= stat.delta_p_threshold:
                lines.append("Próg ΔP został przekroczony: TAK")
            else:
                lines.append("Próg ΔP został przekroczony: NIE")

        else:
            lines.append("Brak próbek")

        report.append("\n".join(lines))

    return "\n\n".join(report)


def save_report_to_txt(
    report,
    chosen_day,
):
    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = f"Raport_filtry_{chosen_day}.txt"

    file_path = REPORTS_DIR / filename

    with open(
        file_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(report)

    return file_path
