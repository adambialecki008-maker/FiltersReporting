from datetime import datetime


class FilterSample:
    def __init__(
        self,
        filter_id: int,
        delta_p: int,
        status: bool,
        alarm_active: bool,
        timestamp: datetime,
    ):
        self.filter_id = filter_id
        self.delta_p = delta_p
        self.status = status
        self.alarm_active = alarm_active
        self.timestamp = timestamp
