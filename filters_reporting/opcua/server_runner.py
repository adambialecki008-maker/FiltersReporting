from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable

from filters_reporting.opcua.server import (
    FiltersReportingOpcUaServer,
)
from filters_reporting.settings_service import (
    load_settings,
)

logger = logging.getLogger(__name__)


class OpcUaServerRunner:
    def __init__(
        self,
        repository,
        *,
        settings_loader: Callable = load_settings,
        server_factory: Callable = (FiltersReportingOpcUaServer),
        start_timeout: float = 5.0,
        stop_timeout: float = 10.0,
    ):
        self.repository = repository

        self.settings_loader = settings_loader

        self.server_factory = server_factory

        self.start_timeout = float(start_timeout)

        self.stop_timeout = float(stop_timeout)

        if self.start_timeout <= 0:
            raise ValueError("start_timeout musi być " "większe od 0.")

        if self.stop_timeout <= 0:
            raise ValueError("stop_timeout musi być " "większe od 0.")

        self._thread: threading.Thread | None = None

        self._thread_lock = threading.Lock()

        self._started_event = threading.Event()

        self._loop: asyncio.AbstractEventLoop | None = None

        self._async_stop_event: asyncio.Event | None = None

        self._server = None

        self._running = False

        self._last_error: BaseException | None = None

    # ==================================================
    # STATE
    # ==================================================

    @property
    def running(
        self,
    ) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    @property
    def last_error(
        self,
    ):
        return self._last_error

    @property
    def server(
        self,
    ):
        return self._server

    # ==================================================
    # START
    # ==================================================

    def start(
        self,
    ) -> bool:
        with self._thread_lock:
            if self._thread is not None and self._thread.is_alive():
                return True

            settings = self.settings_loader()

            if not (settings.opc_server_enabled):
                logger.info("OPC UA Server wyłączony " "w ustawieniach.")

                return False

            self._started_event.clear()

            self._last_error = None

            self._running = False

            self._thread = threading.Thread(
                target=(self._thread_main),
                args=(settings,),
                name=("FiltersReporting-" "OPCUAServer"),
                daemon=True,
            )

            self._thread.start()

        started = self._started_event.wait(timeout=(self.start_timeout))

        if not started:
            self.stop()

            raise TimeoutError("Timeout podczas uruchamiania " "OPC UA Server.")

        if self._last_error is not None:
            error = self._last_error

            raise RuntimeError(
                "Nie udało się uruchomić " "OPC UA Server: " f"{error}"
            ) from error

        return self.running

    # ==================================================
    # THREAD
    # ==================================================

    def _thread_main(
        self,
        settings,
    ) -> None:
        try:
            asyncio.run(self._async_main(settings))

        except BaseException as error:
            self._last_error = error

            logger.exception(
                "Błąd OPC UA Server: %s",
                error,
            )

        finally:
            self._running = False

            self._started_event.set()

            self._loop = None

            self._async_stop_event = None

    # ==================================================
    # ASYNC LOOP
    # ==================================================

    async def _async_main(
        self,
        settings,
    ) -> None:
        self._loop = asyncio.get_running_loop()

        self._async_stop_event = asyncio.Event()

        server = self.server_factory(
            self.repository,
            settings,
        )

        self._server = server

        try:
            await server.start()

            self._running = True

            self._started_event.set()

            logger.info(
                "OPC UA Server uruchomiony: %s",
                settings.opc_server_endpoint,
            )

            while not (self._async_stop_event.is_set()):
                try:
                    await asyncio.wait_for(
                        self._async_stop_event.wait(),
                        timeout=(server.refresh_interval),
                    )

                except TimeoutError:
                    await server.refresh()

        finally:
            self._running = False

            try:
                await server.stop()

            except Exception as error:
                logger.exception(
                    "Błąd zatrzymywania " "OPC UA Server: %s",
                    error,
                )

            logger.info("OPC UA Server zatrzymany.")

    # ==================================================
    # STOP
    # ==================================================

    def stop(
        self,
    ) -> bool:
        thread = self._thread

        if thread is None:
            return True

        loop = self._loop

        async_stop_event = self._async_stop_event

        if loop is not None and async_stop_event is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(async_stop_event.set)

            except RuntimeError:
                pass

        if thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=(self.stop_timeout))

        stopped = not thread.is_alive()

        if not stopped:
            logger.error(
                "OPC UA Server nie zatrzymał " "się w czasie %.1f s.",
                self.stop_timeout,
            )

            return False

        self._thread = None

        return True
