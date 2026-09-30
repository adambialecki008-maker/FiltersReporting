import random
from datetime import datetime
from filters_reporting.models.filter import Filter
from filters_reporting.models.filter_sample import FilterSample

last_delta_p = {}


def generate_current_samples(filters: list[Filter]):
    sample_time = datetime.now().replace(microsecond=0)
    filter_samples = []

    for filter_obj in filters:
        filtersample_obj = FilterSample(
            filter_id=filter_obj.filter_id,
            delta_p=generate_delta_p(filter_obj.filter_id),
            status=random.choice([True, False]),
            alarm_active=random.choice([True, False]),
            timestamp=sample_time,
        )

        filter_samples.append(filtersample_obj)

    return filter_samples


def generate_delta_p(filter_id):
    if filter_id not in last_delta_p:
        last_delta_p[filter_id] = random.randint(0, 200)

    change = random.randint(-80, 80)
    new_delta_p = last_delta_p[filter_id] + change

    new_delta_p = max(0, min(2500, new_delta_p))

    last_delta_p[filter_id] = new_delta_p

    return new_delta_p
