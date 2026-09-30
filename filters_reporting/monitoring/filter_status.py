from filters_reporting.config import SAMPLE_INTERVAL_SECONDS


def get_filter_status(
    sample_data,
    now,
    collector_running,
    sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
):
    if collector_running is False:
        return "monitoring-stopped"
    if sample_data["timestamp"] is None:
        return "offline"
    sample_age = now - sample_data["timestamp"]
    if sample_age.total_seconds() >= 2 * sample_interval_seconds:
        return "offline"
    if sample_data["alarm_active"] is True:
        return "error"
    if sample_data["status"] is True:
        if sample_data["delta_p"] < sample_data["delta_p_threshold"]:
            return "clean-working"
        return "dirty-working"
    if sample_data["last_working_delta_p"] is None:
        return "clean-stopped"
    if sample_data["last_working_delta_p"] < sample_data["delta_p_threshold"]:
        return "clean-stopped"
    return "dirty-stopped"
