from filters_reporting.monitoring.filter_status import get_filter_status
from filters_reporting.config import SAMPLE_INTERVAL_SECONDS

no_attention_statuses = {
    "clean-working",
    "clean-stopped",
    "monitoring-stopped",
}


def build_filter_statuses(
    samples, now, collector_running, sample_interval_seconds=SAMPLE_INTERVAL_SECONDS
):
    result = []
    for sample in samples:
        filter_data = sample.copy()
        filter_data["filter_status"] = get_filter_status(
            sample, now, collector_running, sample_interval_seconds
        )
        result.append(filter_data)
    return result


def get_current_filter_statuses(
    repository,
    now,
    sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
):
    samples = repository.get_latest_active_filter_samples()
    heartbeat = repository.get_collector_heartbeat()
    collector_running = is_collector_running(
        heartbeat,
        now,
        sample_interval_seconds,
    )
    return build_filter_statuses(
        samples,
        now,
        collector_running,
        sample_interval_seconds,
    )


def count_attention_filters(filters):
    counter = 0
    for filter_data in filters:
        if filter_data["filter_status"] not in no_attention_statuses:
            counter += 1
    return counter


def get_attention_state(filters):
    orange_statuses = {
        "dirty-working",
        "dirty-stopped",
    }
    red_statuses = {
        "error",
        "offline",
    }
    if not filters:
        return "neutral"
    if all(
        filter_data["filter_status"] == "monitoring-stopped" for filter_data in filters
    ):
        return "neutral"
    for filter_data in filters:
        if filter_data["filter_status"] in red_statuses:
            return "error"
    for filter_data in filters:
        if filter_data["filter_status"] in orange_statuses:
            return "warning"
    return "ok"


def get_attention_summary(filters):
    error_count = 0
    offline_count = 0
    dirty_count = 0
    if filters and all(
        filter_data["filter_status"] == "monitoring-stopped" for filter_data in filters
    ):
        return "Monitoring zatrzymany"
    for filter_data in filters:
        status = filter_data["filter_status"]
        if status == "error":
            error_count += 1
        elif status == "offline":
            offline_count += 1

        elif status in {"dirty-working", "dirty-stopped"}:
            dirty_count += 1
    summary_parts = []
    if error_count > 0:
        summary_parts.append(f"Awaria: {error_count}")
    if offline_count > 0:
        summary_parts.append(f"Offline: {offline_count}")
    if dirty_count > 0:
        summary_parts.append(f"Zabrudzone: {dirty_count}")
    if not summary_parts:
        return "Brak problemów"
    return " · ".join(summary_parts)


def get_attention_filters(filters):
    result = []
    for filter_obj in filters:
        if filter_obj["filter_status"] not in no_attention_statuses:
            result.append(filter_obj)
    return result


def build_attention_rows(filters):
    attention_filters = get_attention_filters(filters)
    rows = []
    for filter_data in attention_filters:
        timestamp = filter_data["timestamp"]
        if timestamp is None:
            timestamp_text = "—"
        else:
            timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        if filter_data["filter_status"] == "offline":
            communication = "Offline"
        else:
            communication = "OK"
        delta_p = filter_data["delta_p"]
        if delta_p is None:
            delta_p_text = "—"
        else:
            delta_p_text = f"{delta_p} Pa"
        rows.append(
            [
                filter_data["filter_name"],
                delta_p_text,
                filter_data["filter_status"],
                communication,
                timestamp_text,
            ]
        )
    return rows


def get_filter_status_label(status):
    status_labels = {
        "clean-working": "Pracuje",
        "clean-stopped": "Postój",
        "dirty-working": "Zabrudzony / pracuje",
        "dirty-stopped": "Zabrudzony / postój",
        "error": "Awaria",
        "offline": "Offline",
        "monitoring-stopped": "Monitoring zatrzymany",
    }
    return status_labels.get(status, status)


def get_filter_status_state(status):
    if status in {"error", "offline"}:
        return "error"

    if status in {"dirty-working", "dirty-stopped"}:
        return "warning"
    if status == "monitoring-stopped":
        return "neutral"
    return "ok"


def get_system_status_counts(filters):
    ok_state = {"clean-working", "clean-stopped"}
    attention_state = {
        "dirty-working",
        "dirty-stopped",
        "error",
    }
    total_count = len(filters)
    ok_count = 0
    attention_count = 0
    offline_count = 0
    for filter_data in filters:
        if filter_data["filter_status"] in ok_state:
            ok_count += 1
        elif filter_data["filter_status"] in attention_state:
            attention_count += 1
        elif filter_data["filter_status"] == "offline":
            offline_count += 1

    counts = {
        "total": total_count,
        "ok": ok_count,
        "attention": attention_count,
        "offline": offline_count,
    }
    return counts


def is_collector_running(
    heartbeat,
    now,
    sample_interval_seconds=SAMPLE_INTERVAL_SECONDS,
):
    if heartbeat is None:
        return False

    heartbeat_age = now - heartbeat

    return heartbeat_age.total_seconds() < 2 * sample_interval_seconds


def build_filter_rows(filters):
    rows = []
    for filter_data in filters:
        timestamp = filter_data["timestamp"]
        if timestamp is None:
            timestamp_text = "—"
        else:
            timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        filter_status = filter_data["filter_status"]
        if filter_status == "offline":
            communication = "Offline"
        elif filter_status == "monitoring-stopped":
            communication = "—"
        else:
            communication = "OK"
        delta_p = filter_data["delta_p"]
        if delta_p is None:
            delta_p_text = "—"
        else:
            delta_p_text = f"{delta_p} Pa"
        rows.append(
            [
                filter_data["filter_name"],
                delta_p_text,
                get_filter_status_label(filter_status),
                communication,
                timestamp_text,
            ]
        )
    return rows


ATTENTION_STATUSES = {
    "offline",
    "error",
    "dirty-working",
    "dirty-stopped",
}


def get_filters_for_attention_table(
    filter_statuses,
    show_all,
):
    if show_all:
        return filter_statuses

    return get_attention_filters(filter_statuses)
