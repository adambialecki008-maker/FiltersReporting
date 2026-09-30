from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from filters_reporting.collection.opc_ua_client import (
    disconnect_all_clients,
)
from filters_reporting.collection.sample_source import (
    get_current_samples,
)
from filters_reporting.config import (
    LOG_BACKUP_COUNT,
    LOG_FILE,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    LOGGER_NAME,
    SAMPLE_INTERVAL_SECONDS,
)
from filters_reporting.database.database_location import (
    load_database_path,
)
from filters_reporting.database.filters_repository import (
    FiltersRepository,
)
from filters_reporting.single_instance import (
    AlreadyRunningError,
    acquire_single_instance,
)


logger = logging.getLogger(
    LOGGER_NAME
)

_HANDLER_MARKER = (
    "_filters_reporting_collector_handler"
)

LOG_FILE_ENV = "FILTERSREPORTING_LOG_FILE"


def configure_logging() -> Path:
    """
    Configure the collector's file logger explicitly.

    The collector always records INFO diagnostics in v1.0.
    This avoids a global LOG_LEVEL accidentally filtering
    startup/cycle messages in the frozen executable.

    Returns the absolute log-file path used by this process.
    """

    if bool(
        getattr(
            sys,
            "frozen",
            False,
        )
    ):
        configured_log_file = (
            os.environ.get(
                LOG_FILE_ENV
            )
            or str(LOG_FILE)
        )
    else:
        configured_log_file = str(
            LOG_FILE
        )

    log_file = Path(
        configured_log_file
    ).expanduser()

    if not log_file.is_absolute():
        log_file = (
            log_file.resolve()
        )

    log_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Remove only handlers previously created by this
    # function. This makes repeated main() calls in tests
    # deterministic and avoids duplicate entries.
    for handler in list(
        logger.handlers
    ):
        if getattr(
            handler,
            _HANDLER_MARKER,
            False,
        ):
            logger.removeHandler(
                handler
            )

            try:
                handler.close()
            except Exception:
                pass

    logger.setLevel(
        logging.INFO
    )

    logger.propagate = False

    file_handler = (
        RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding="utf-8",
            delay=False,
        )
    )

    file_handler.setLevel(
        logging.INFO
    )

    formatter = (
        logging.Formatter(
            LOG_FORMAT
        )
    )

    file_handler.setFormatter(
        formatter
    )

    setattr(
        file_handler,
        _HANDLER_MARKER,
        True,
    )

    logger.addHandler(
        file_handler
    )

    logging.getLogger(
        "asyncua.client.client"
    ).setLevel(
        logging.ERROR
    )

    return log_file


def flush_logging() -> None:
    for handler in logger.handlers:
        try:
            handler.flush()
        except Exception:
            pass


def create_repository() -> FiltersRepository:
    database_path = Path(
        load_database_path()
    ).expanduser()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    repository = (
        FiltersRepository(
            database_path
        )
    )

    # GUI i collector muszą używać dokładnie
    # tej samej wybranej bazy SQLite.
    repository.database_name = (
        database_path
    )

    repository.create_table()

    return repository


def save_samples(
    repository,
    samples,
):
    for sample in samples:
        try:
            repository.save_filter_sample(
                sample
            )

        except Exception:
            logger.exception(
                "Błąd zapisu próbki "
                f"filter_id={sample.filter_id}"
            )

            flush_logging()


def start_stop_listener(
    loop,
    stop_event,
):
    def listen():
        if sys.stdin is None:
            return

        try:
            for line in sys.stdin:
                if line.strip() == "STOP":
                    loop.call_soon_threadsafe(
                        stop_event.set
                    )
                    break

        except (
            OSError,
            ValueError,
            TypeError,
        ):
            # W PyInstallerze lub podczas pytest stdin
            # może być niedostępny/przechwycony.
            #
            # Nie jest to błąd collectora. Zatrzymanie
            # nadal działa przez flagę w SQLite.
            return

    thread = threading.Thread(
        target=listen,
        daemon=True,
    )

    thread.start()


async def run_collector(
    sample_interval=(
        SAMPLE_INTERVAL_SECONDS
    ),
):
    repository = (
        create_repository()
    )

    repository.clear_collector_stop_request()

    repository.set_collector_heartbeat(
        datetime.now()
    )

    stop_event = asyncio.Event()

    start_stop_listener(
        asyncio.get_running_loop(),
        stop_event,
    )

    logger.info(
        "Data collector uruchomiony. "
        f"interval={sample_interval}s"
    )

    flush_logging()

    number_of_cycles = 0

    try:
        while True:
            now = datetime.now()

            seconds_from_epoch = (
                now.timestamp()
            )

            seconds_to_next_cycle = (
                sample_interval
                - seconds_from_epoch
                % sample_interval
            )

            stop_requested = (
                await (
                    wait_for_next_cycle_or_stop(
                        repository,
                        stop_event,
                        seconds_to_next_cycle,
                    )
                )
            )

            if stop_requested:
                break

            try:
                filters = (
                    repository
                    .get_active_filters()
                )

                samples = (
                    await get_current_samples(
                        filters
                    )
                )

                update_connection_statuses(
                    repository,
                    filters,
                    samples,
                )

                save_samples(
                    repository,
                    samples,
                )

                repository.set_collector_heartbeat(
                    datetime.now()
                )

                number_of_cycles += 1

                if (
                    len(samples)
                    == len(filters)
                ):
                    opc_status = "OPC_OK"
                else:
                    opc_status = (
                        "OPC_ERROR"
                    )

                logger.info(
                    f"Cykl {number_of_cycles}: "
                    f"zapisano {len(samples)}/"
                    f"{len(filters)} próbek. | "
                    f"{opc_status}"
                )

                flush_logging()

            except Exception:
                logger.exception(
                    "Błąd całego cyklu "
                    "collectora"
                )

                flush_logging()

    finally:
        await disconnect_all_clients()

        repository.clear_collector_stop_request()

        repository.clear_collector_heartbeat()

        logger.info(
            "Data collector zatrzymany przez "
            "użytkownika, wykonano "
            f"{number_of_cycles} cykli"
        )

        flush_logging()


def update_connection_statuses(
    repository,
    active_filters,
    samples,
):
    successful_filter_ids = {
        sample.filter_id
        for sample in samples
    }

    for filter_obj in (
        active_filters
    ):
        connected = (
            filter_obj.filter_id
            in successful_filter_ids
        )

        repository.set_filter_connection_status(
            filter_obj.filter_id,
            connected,
        )


async def wait_for_next_cycle_or_stop(
    repository,
    stop_event,
    seconds_to_next_cycle,
):
    check_interval = 1
    elapsed = 0

    while (
        elapsed
        < seconds_to_next_cycle
    ):
        if stop_event.is_set():
            return True

        if (
            repository
            .is_collector_stop_requested()
        ):
            return True

        sleep_time = min(
            check_interval,
            (
                seconds_to_next_cycle
                - elapsed
            ),
        )

        await asyncio.sleep(
            sleep_time
        )

        elapsed += sleep_time

    return False


def get_sample_interval(
    args,
):
    if len(args) < 2:
        return (
            SAMPLE_INTERVAL_SECONDS
        )

    try:
        sample_interval = int(
            args[1]
        )

    except (
        TypeError,
        ValueError,
    ):
        return (
            SAMPLE_INTERVAL_SECONDS
        )

    return max(
        5,
        min(
            sample_interval,
            300,
        ),
    )


def main(
    args=None,
):
    if args is None:
        args = sys.argv

    try:
        log_file = (
            configure_logging()
        )

    except Exception:
        # Jeśli nawet utworzenie loggera się nie uda,
        # nie ma sensu udawać, że collector działa.
        # Traceback pozostaje dostępny na stderr
        # w buildzie diagnostycznym / przy uruchomieniu
        # ręcznym.
        raise

    logger.info(
        "Collector bootstrap. "
        f"log={log_file} | "
        f"pid={os.getpid()} | "
        f"exe={sys.executable} | "
        f"cwd={Path.cwd()} | "
        "frozen="
        f"{bool(getattr(sys, 'frozen', False))}"
    )

    flush_logging()

    try:
        instance_lock = (
            acquire_single_instance(
                "Collector"
            )
        )

    except AlreadyRunningError:
        logger.warning(
            "FiltersReportingCollector "
            "jest już uruchomiony. "
            "Druga instancja nie zostanie "
            "uruchomiona."
        )

        flush_logging()

        return 0

    try:
        sample_interval = (
            get_sample_interval(
                args
            )
        )

        asyncio.run(
            run_collector(
                sample_interval
            )
        )

        return 0

    except Exception:
        logger.exception(
            "Krytyczny błąd collectora."
        )

        flush_logging()

        raise

    finally:
        instance_lock.release()

        flush_logging()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
