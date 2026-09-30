from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from filters_reporting.config import (
    LOG_FILE,
)
from filters_reporting.database.database_location import (
    load_database_path,
)
from filters_reporting.database.filters_repository import (
    FiltersRepository,
)
from filters_reporting.gui.main_window import (
    MainWindow,
)
from filters_reporting.opcua.server_runner import (
    OpcUaServerRunner,
)
from filters_reporting.single_instance import (
    AlreadyRunningError,
    acquire_single_instance,
)


def ensure_log_file() -> None:
    """
    Zapewnia istnienie katalogu i pliku logu.

    Dzięki temu plik logu istnieje już po uruchomieniu GUI,
    również przed pierwszym uruchomieniem collectora.
    """

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOG_FILE.touch(
        exist_ok=True,
    )


def create_repository() -> FiltersRepository:
    database_path = Path(load_database_path()).expanduser()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    repository = FiltersRepository(database_path)

    # Wymuszamy dokładnie ścieżkę wybraną
    # przez użytkownika.
    #
    # Dzięki temu GUI i osobny collector
    # korzystają z tego samego pliku SQLite.
    repository.database_name = database_path

    repository.create_table()

    return repository


def main():
    app = QApplication(sys.argv)

    try:
        instance_lock = acquire_single_instance("GUI")

    except AlreadyRunningError:
        QMessageBox.information(
            None,
            "FiltersReporting",
            ("FiltersReporting jest już " "uruchomiony."),
        )
        return

    try:
        # ==================================================
        # RUNTIME FILES
        # ==================================================

        ensure_log_file()

        # ==================================================
        # DATABASE
        # ==================================================

        repository = create_repository()

        # ==================================================
        # OPC UA SERVER
        # ==================================================

        server_runner = OpcUaServerRunner(repository)

        # ==================================================
        # GUI
        # ==================================================

        window = MainWindow(repository)

        app.aboutToQuit.connect(server_runner.stop)

        window.show()

        # ==================================================
        # OPTIONAL LOCAL OPC UA SERVER
        # ==================================================

        try:
            server_runner.start()

        except (
            RuntimeError,
            TimeoutError,
        ) as error:
            QMessageBox.warning(
                window,
                "OPC UA Server",
                (
                    "Nie udało się uruchomić "
                    "OPC UA Server.\n\n"
                    f"{error}\n\n"
                    "Aplikacja będzie działała "
                    "dalej bez lokalnego "
                    "serwera OPC UA."
                ),
            )

        sys.exit(app.exec())

    finally:
        instance_lock.release()


if __name__ == "__main__":
    main()
