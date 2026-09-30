from dataclasses import dataclass
from datetime import datetime


@dataclass
class DailyFilterStats:
    filter_name: str
    min_delta_p: int
    max_delta_p: int
    avg_delta_p: float
    sample_count: int
    alarm_count: int
    status_count: int
    delta_p_threshold: int = 2000


@dataclass
class DailyFilterReportSample:
    sample_id: int
    filter_name: str
    filter_id: int
    delta_p: int
    alarm_active: bool
    status: bool
    timestamp: datetime
