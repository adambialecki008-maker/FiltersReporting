from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

WORKING_SAMPLE_COUNT = 10


@dataclass(frozen=True)
class FilterAttention:
    filter_name: str
    average_delta_p: float
    dirty_percent: float


def build_filter_attention(
    stats: Iterable,
    samples: Iterable,
    *,
    sample_count: int = WORKING_SAMPLE_COUNT,
) -> list[FilterAttention]:
    if sample_count <= 0:
        raise ValueError("sample_count musi być większe od 0")

    threshold_by_filter = {stat.filter_name: stat.delta_p_threshold for stat in stats}

    working_values: dict[str, list[float]] = {}

    for sample in samples:
        if not sample.status:
            continue

        working_values.setdefault(
            sample.filter_name,
            [],
        ).append(sample.delta_p)

    attention: list[FilterAttention] = []

    for filter_name, threshold in threshold_by_filter.items():
        values = working_values.get(
            filter_name,
            [],
        )

        if len(values) < sample_count:
            continue

        last_values = values[-sample_count:]

        average_delta_p = sum(last_values) / sample_count

        if threshold <= 0:
            continue

        raw_dirty_percent = average_delta_p / threshold * 100

        if raw_dirty_percent < 100:
            continue

        dirty_percent = min(
            raw_dirty_percent,
            100.0,
        )

        attention.append(
            FilterAttention(
                filter_name=filter_name,
                average_delta_p=average_delta_p,
                dirty_percent=dirty_percent,
            )
        )

    return attention
