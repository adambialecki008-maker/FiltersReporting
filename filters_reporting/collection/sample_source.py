from filters_reporting.collection.simulator import generate_current_samples
from filters_reporting.config import DATA_SOURCE
from filters_reporting.collection.opc_ua_client import read_opc_ua_samples


async def get_current_samples(filters=None):
    if DATA_SOURCE == "SIMULATOR":
        if filters is None:
            raise ValueError("Simulator wymaga listy filtrów")
        return generate_current_samples(filters)
    if DATA_SOURCE == "OPC_UA":
        if filters is None:
            raise ValueError("OPC_UA wymaga listy filtrów")
        return await read_opc_ua_samples(filters)
    raise ValueError(f"Nieznane źródło danych: {DATA_SOURCE}")
