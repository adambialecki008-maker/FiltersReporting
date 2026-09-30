import asyncio
import random
from filters_reporting.config import DATABASE_NAME
from filters_reporting.database.filters_repository import FiltersRepository
from asyncua import Server
from filters_reporting.collection.simulator import generate_delta_p


async def main():
    repository = FiltersRepository(DATABASE_NAME)
    active_filters = repository.get_active_filters()

    await asyncio.gather(
        *(run_filter_server(filter_obj) for filter_obj in active_filters)
    )


async def run_filter_server(filter_obj):
    server = Server()
    await server.init()
    server.set_endpoint(filter_obj.opc_url)
    namespace_uri = "FiltersReporting"
    namespace_index = await server.register_namespace(namespace_uri)

    filter_node = await server.nodes.objects.add_object(
        namespace_index,
        "Filter",
    )
    opc_node = await filter_node.add_object(
        namespace_index,
        filter_obj.name,
    )
    delta_p = await opc_node.add_variable(
        filter_obj.delta_p_node_id,
        "DeltaP",
        0,
    )
    status = await opc_node.add_variable(
        filter_obj.status_node_id,
        "Status",
        False,
    )
    alarm_active = await opc_node.add_variable(
        filter_obj.alarm_node_id,
        "AlarmActive",
        False,
    )
    print(f"{filter_obj.name}: " f"namespace={namespace_index}")
    print(f"  Δp:     {delta_p.nodeid}")
    print(f"  status: {status.nodeid}")
    print(f"  alarm:  {alarm_active.nodeid}")
    async with server:
        print(f"OPC UA server {filter_obj.name} działa: " f"{filter_obj.opc_url}")
        while True:
            await delta_p.write_value(generate_delta_p(filter_obj.name))
            await status.write_value(random.choice([True, False]))
            await alarm_active.write_value(random.choice([True, False]))
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
