import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from filters_reporting.runtime_paths import (
    DATABASE_PATH,
    ensure_runtime_directories,
)

from filters_reporting.models.filter_sample import FilterSample
from filters_reporting.models.filter import Filter
from filters_reporting.models.filter_report_models import (
    DailyFilterStats,
    DailyFilterReportSample,
)


class FiltersRepository:
    def __init__(
        self,
        database_name: str | Path,
    ):
        requested_path = Path(database_name)

        if (
            getattr(sys, "frozen", False)
            and requested_path.name.lower() == "filters.db"
        ):
            ensure_runtime_directories()
            self.database_name = DATABASE_PATH
        else:
            self.database_name = requested_path

    def connect(self):
        self.database_name.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        return sqlite3.connect(self.database_name)

    @staticmethod
    def _migrate_filters_table(cursor):
        cursor.execute("PRAGMA table_info(filters)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        migrations = {
            "opc_security_policy": "TEXT NOT NULL DEFAULT 'None'",
            "opc_security_mode": "TEXT NOT NULL DEFAULT 'None'",
            "opc_application_uri": "TEXT NOT NULL DEFAULT ''",
            "opc_client_certificate_path": "TEXT",
            "opc_client_private_key_path": "TEXT",
            "opc_trusted_certificates_dir": "TEXT",
            "opc_server_certificate_path": "TEXT",
            "opc_validate_server_certificate": "INTEGER NOT NULL DEFAULT 1",
            "opc_auth_type": "TEXT NOT NULL DEFAULT 'Anonymous'",
            "opc_username": "TEXT NOT NULL DEFAULT ''",
            "opc_connect_timeout_seconds": "REAL NOT NULL DEFAULT 5.0",
            "opc_request_timeout_seconds": "REAL NOT NULL DEFAULT 5.0",
            "opc_reconnect_delay_seconds": "REAL NOT NULL DEFAULT 5.0",
        }

        for column_name, definition in migrations.items():
            if column_name in existing_columns:
                continue

            cursor.execute(
                f"ALTER TABLE filters ADD COLUMN " f"{column_name} {definition}"
            )

    @staticmethod
    def _filter_from_row(row):
        return Filter(
            filter_id=row[0],
            name=row[1],
            active=bool(row[2]),
            opc_url=row[3],
            delta_p_threshold=row[4],
            delta_p_node_id=row[5],
            status_node_id=row[6],
            alarm_node_id=row[7],
            opc_security_policy=row[8],
            opc_security_mode=row[9],
            opc_application_uri=row[10],
            opc_client_certificate_path=row[11],
            opc_client_private_key_path=row[12],
            opc_trusted_certificates_dir=row[13],
            opc_server_certificate_path=row[14],
            opc_validate_server_certificate=bool(row[15]),
            opc_auth_type=row[16],
            opc_username=row[17],
            opc_connect_timeout_seconds=row[18],
            opc_request_timeout_seconds=row[19],
            opc_reconnect_delay_seconds=row[20],
        )

    def create_table(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            current_table = "filter_samples"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS filter_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_id INTEGER NOT NULL,
                    delta_p INTEGER NOT NULL,
                    status INTEGER NOT NULL,
                    alarm_active INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            current_table = "filters"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    opc_url TEXT UNIQUE NOT NULL,
                    delta_p_threshold INTEGER NOT NULL DEFAULT 2000,
                    delta_p_node_id TEXT,
                    status_node_id TEXT,
                    alarm_node_id TEXT,
                    opc_security_policy TEXT NOT NULL DEFAULT 'None',
                    opc_security_mode TEXT NOT NULL DEFAULT 'None',
                    opc_application_uri TEXT NOT NULL DEFAULT '',
                    opc_client_certificate_path TEXT,
                    opc_client_private_key_path TEXT,
                    opc_trusted_certificates_dir TEXT,
                    opc_server_certificate_path TEXT,
                    opc_validate_server_certificate INTEGER NOT NULL DEFAULT 1,
                    opc_auth_type TEXT NOT NULL DEFAULT 'Anonymous',
                    opc_username TEXT NOT NULL DEFAULT '',
                    opc_connect_timeout_seconds REAL NOT NULL DEFAULT 5.0,
                    opc_request_timeout_seconds REAL NOT NULL DEFAULT 5.0,
                    opc_reconnect_delay_seconds REAL NOT NULL DEFAULT 5.0
                )
            """)

            self._migrate_filters_table(cursor)

            current_table = "filter_connection_status"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS filter_connection_status (
                    filter_id INTEGER PRIMARY KEY,
                    connected INTEGER NOT NULL DEFAULT 0,
                    last_change TEXT NOT NULL,
                    last_error TEXT,
                    FOREIGN KEY (filter_id) REFERENCES filters(id)
                )
            """)

            current_table = "collector_status"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collector_status (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    last_heartbeat TEXT NOT NULL
                )
            """)

            current_table = "collector_control"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collector_control (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    stop_requested INTEGER NOT NULL DEFAULT 0
                )
            """)

            current_table = "system_events"

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL
                )
            """)

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print(f"Błąd tworzenia tabeli " f"{current_table}: {error}")

        finally:
            if connection:
                connection.close()

    def save_filter_sample(
        self,
        filtersample_obj: FilterSample,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO filter_samples (
                    filter_id,
                    delta_p,
                    status,
                    alarm_active,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    filtersample_obj.filter_id,
                    filtersample_obj.delta_p,
                    int(filtersample_obj.status),
                    int(filtersample_obj.alarm_active),
                    filtersample_obj.timestamp.isoformat(),
                ),
            )

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print(f"Błąd zapisu próbki: " f"{error}")

        finally:
            if connection:
                connection.close()

    def save_filter(
        self,
        filter_obj: Filter,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO filters (
                    name,
                    active,
                    opc_url,
                    delta_p_threshold,
                    delta_p_node_id,
                    status_node_id,
                    alarm_node_id,
                    opc_security_policy,
                    opc_security_mode,
                    opc_application_uri,
                    opc_client_certificate_path,
                    opc_client_private_key_path,
                    opc_trusted_certificates_dir,
                    opc_server_certificate_path,
                    opc_validate_server_certificate,
                    opc_auth_type,
                    opc_username,
                    opc_connect_timeout_seconds,
                    opc_request_timeout_seconds,
                    opc_reconnect_delay_seconds
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    filter_obj.name,
                    int(filter_obj.active),
                    filter_obj.opc_url,
                    filter_obj.delta_p_threshold,
                    filter_obj.delta_p_node_id,
                    filter_obj.status_node_id,
                    filter_obj.alarm_node_id,
                    filter_obj.opc_security_policy,
                    filter_obj.opc_security_mode,
                    filter_obj.opc_application_uri,
                    filter_obj.opc_client_certificate_path,
                    filter_obj.opc_client_private_key_path,
                    filter_obj.opc_trusted_certificates_dir,
                    filter_obj.opc_server_certificate_path,
                    int(filter_obj.opc_validate_server_certificate),
                    filter_obj.opc_auth_type,
                    filter_obj.opc_username,
                    filter_obj.opc_connect_timeout_seconds,
                    filter_obj.opc_request_timeout_seconds,
                    filter_obj.opc_reconnect_delay_seconds,
                ),
            )

            connection.commit()

            filter_obj.filter_id = cursor.lastrowid

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print(f"Błąd zapisu filtra: " f"{error}")

        finally:
            if connection:
                connection.close()

    def get_all_filters(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    name,
                    active,
                    opc_url,
                    delta_p_threshold,
                    delta_p_node_id,
                    status_node_id,
                    alarm_node_id,
                    opc_security_policy,
                    opc_security_mode,
                    opc_application_uri,
                    opc_client_certificate_path,
                    opc_client_private_key_path,
                    opc_trusted_certificates_dir,
                    opc_server_certificate_path,
                    opc_validate_server_certificate,
                    opc_auth_type,
                    opc_username,
                    opc_connect_timeout_seconds,
                    opc_request_timeout_seconds,
                    opc_reconnect_delay_seconds
                FROM filters
                ORDER BY id
            """)

            rows = cursor.fetchall()

            filters = []

            for row in rows:
                filters.append(self._filter_from_row(row))

            return filters

        except sqlite3.Error as error:
            print("Błąd pobierania wszystkich " f"filtrów: {error}")

            return []

        finally:
            if connection:
                connection.close()

    def get_filter_by_name(
        self,
        name,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    active,
                    opc_url,
                    delta_p_threshold,
                    delta_p_node_id,
                    status_node_id,
                    alarm_node_id,
                    opc_security_policy,
                    opc_security_mode,
                    opc_application_uri,
                    opc_client_certificate_path,
                    opc_client_private_key_path,
                    opc_trusted_certificates_dir,
                    opc_server_certificate_path,
                    opc_validate_server_certificate,
                    opc_auth_type,
                    opc_username,
                    opc_connect_timeout_seconds,
                    opc_request_timeout_seconds,
                    opc_reconnect_delay_seconds
                FROM filters
                WHERE name = ?
                """,
                (name,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return self._filter_from_row(row)

        finally:
            if connection:
                connection.close()

    def get_filter_by_opc_url(
        self,
        opc_url,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    active,
                    opc_url,
                    delta_p_threshold,
                    delta_p_node_id,
                    status_node_id,
                    alarm_node_id,
                    opc_security_policy,
                    opc_security_mode,
                    opc_application_uri,
                    opc_client_certificate_path,
                    opc_client_private_key_path,
                    opc_trusted_certificates_dir,
                    opc_server_certificate_path,
                    opc_validate_server_certificate,
                    opc_auth_type,
                    opc_username,
                    opc_connect_timeout_seconds,
                    opc_request_timeout_seconds,
                    opc_reconnect_delay_seconds
                FROM filters
                WHERE opc_url = ?
                """,
                (opc_url,),
            )

            row = cursor.fetchone()

            if row is None:
                return None

            return self._filter_from_row(row)

        except sqlite3.Error as error:
            print("Błąd pobierania filtra " f"po opc_url: {error}")

            return None

        finally:
            if connection:
                connection.close()

    def update_filter_activity(
        self,
        name,
        if_activate: bool,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE filters
                SET active = ?
                WHERE name = ?
                """,
                (
                    int(if_activate),
                    name,
                ),
            )

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print("Błąd zmiany aktywności " f"filtra {name}: {error}")

        finally:
            if connection:
                connection.close()

    def get_active_filters(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    id,
                    name,
                    active,
                    opc_url,
                    delta_p_threshold,
                    delta_p_node_id,
                    status_node_id,
                    alarm_node_id,
                    opc_security_policy,
                    opc_security_mode,
                    opc_application_uri,
                    opc_client_certificate_path,
                    opc_client_private_key_path,
                    opc_trusted_certificates_dir,
                    opc_server_certificate_path,
                    opc_validate_server_certificate,
                    opc_auth_type,
                    opc_username,
                    opc_connect_timeout_seconds,
                    opc_request_timeout_seconds,
                    opc_reconnect_delay_seconds
                FROM filters
                WHERE active = 1
                ORDER BY id
            """)

            rows = cursor.fetchall()

            filters = []

            for row in rows:
                filters.append(self._filter_from_row(row))

            return filters

        except sqlite3.Error as error:
            print("Błąd pobierania aktywnych " f"filtrów: {error}")

            return []

        finally:
            if connection:
                connection.close()

    def get_filter_samples_by_filter_id(
        self,
        filter_id: int,
        chosen_day: str,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    filters.name,
                    filter_samples.delta_p,
                    filter_samples.timestamp
                FROM filter_samples
                JOIN filters
                    ON filter_samples.filter_id
                    = filters.id
                WHERE filter_samples.filter_id = ?
                AND filter_samples.timestamp LIKE ?
                ORDER BY
                    filter_samples.timestamp,
                    filter_samples.id
                """,
                (
                    filter_id,
                    f"{chosen_day}%",
                ),
            )

            return cursor.fetchall()

        except sqlite3.Error as error:
            print("Błąd pobierania próbek " f"po ID filtra: {error}")

            return []

        finally:
            if connection:
                connection.close()

    def get_delta_p_stats_by_filter_id(
        self,
        filter_id,
        timestamp,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    MIN(delta_p),
                    MAX(delta_p),
                    AVG(delta_p),
                    COUNT(*),
                    SUM(alarm_active),
                    SUM(status)
                FROM filter_samples
                WHERE filter_id = ?
                AND timestamp LIKE ?
                """,
                (
                    filter_id,
                    f"{timestamp}%",
                ),
            )

            result = cursor.fetchone()

            if result[0] is not None:
                return result

            return None

        except sqlite3.Error as error:
            print("Błąd liczenia statystyk: " f"{error}")

            return None

        finally:
            if connection:
                connection.close()

    def get_daily_filter_stats(
        self,
        chosen_day,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    filters.name,
                    MIN(
                        filter_samples.delta_p
                    ),
                    MAX(
                        filter_samples.delta_p
                    ),
                    AVG(
                        filter_samples.delta_p
                    ),
                    COUNT(*),
                    SUM(
                        filter_samples.alarm_active
                    ),
                    SUM(
                        filter_samples.status
                    ),
                    filters.delta_p_threshold
                FROM filter_samples
                JOIN filters
                    ON filter_samples.filter_id
                    = filters.id
                WHERE filter_samples.timestamp LIKE ?
                GROUP BY
                    filters.id,
                    filters.name,
                    filters.delta_p_threshold
                ORDER BY filters.id
                """,
                (f"{chosen_day}%",),
            )

            rows = cursor.fetchall()

            stats = []

            for row in rows:
                stat = DailyFilterStats(
                    filter_name=row[0],
                    min_delta_p=row[1],
                    max_delta_p=row[2],
                    avg_delta_p=row[3],
                    sample_count=row[4],
                    alarm_count=row[5],
                    status_count=row[6],
                    delta_p_threshold=row[7],
                )

                stats.append(stat)

            return stats

        except sqlite3.Error as error:
            print("Błąd liczenia próbek " f"po filtrze: {error}")

            return None

        finally:
            if connection:
                connection.close()

    def get_daily_samples_for_report(
        self,
        chosen_day,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    filter_samples.id,
                    filters.name,
                    filter_samples.filter_id,
                    filter_samples.delta_p,
                    filter_samples.alarm_active,
                    filter_samples.status,
                    filter_samples.timestamp
                FROM filter_samples
                JOIN filters
                    ON filter_samples.filter_id
                    = filters.id
                WHERE filter_samples.timestamp LIKE ?
                ORDER BY
                    filter_samples.filter_id,
                    filter_samples.timestamp,
                    filter_samples.id
                """,
                (f"{chosen_day}%",),
            )

            samples = []

            rows = cursor.fetchall()

            for row in rows:
                sample = DailyFilterReportSample(
                    sample_id=row[0],
                    filter_name=row[1],
                    filter_id=row[2],
                    delta_p=row[3],
                    alarm_active=bool(row[4]),
                    status=bool(row[5]),
                    timestamp=datetime.fromisoformat(row[6]),
                )

                samples.append(sample)

            return samples

        except sqlite3.Error as error:
            print("Błąd pobierania dziennych " f"próbek: {error}")

            return None

        finally:
            if connection:
                connection.close()

    def delete_samples_for_day(
        self,
        chosen_day,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                DELETE FROM filter_samples
                WHERE timestamp LIKE ?
                """,
                (f"{chosen_day}%",),
            )

            connection.commit()

            return cursor.rowcount

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print("Błąd usuwania próbek " f"z dnia {chosen_day}: " f"{error}")

            return 0

        finally:
            if connection:
                connection.close()

    def update_filter_opc_url(
        self,
        name,
        opc_url,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE filters
                SET opc_url = ?
                WHERE name = ?
                """,
                (
                    opc_url,
                    name,
                ),
            )

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print("Błąd aktualizacji opc_url: " f"{error}")

        finally:
            if connection:
                connection.close()

    def get_filter_counts(self):
        with self.connect() as connection:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*),
                    SUM(
                        CASE
                            WHEN active = 1
                            THEN 1
                            ELSE 0
                        END
                    )
                FROM filters
            """)

            (
                total,
                active,
            ) = cursor.fetchone()

            return (
                total,
                active or 0,
            )

    def get_latest_active_filter_samples(
        self,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    filters.name,
                    filters.id,
                    latest_sample.delta_p,
                    latest_sample.alarm_active,
                    latest_sample.status,
                    latest_sample.timestamp,
                    filters.delta_p_threshold,
                    last_working_sample.delta_p,
                    last_working_sample.timestamp
                FROM filters

                LEFT JOIN filter_samples
                    AS latest_sample
                    ON latest_sample.id = (
                        SELECT id
                        FROM filter_samples
                        WHERE filter_id
                            = filters.id
                        ORDER BY
                            timestamp DESC,
                            id DESC
                        LIMIT 1
                    )

                LEFT JOIN filter_samples
                    AS last_working_sample
                    ON last_working_sample.id = (
                        SELECT id
                        FROM filter_samples
                        WHERE filter_id
                            = filters.id
                        AND status = 1
                        ORDER BY
                            timestamp DESC,
                            id DESC
                        LIMIT 1
                    )

                WHERE filters.active = 1
                ORDER BY filters.id
            """)

            rows = cursor.fetchall()

            result = []

            for row in rows:
                result.append(
                    {
                        "filter_name": row[0],
                        "filter_id": row[1],
                        "delta_p": row[2],
                        "alarm_active": (bool(row[3]) if row[3] is not None else None),
                        "status": (bool(row[4]) if row[4] is not None else None),
                        "timestamp": (
                            datetime.fromisoformat(row[5])
                            if row[5] is not None
                            else None
                        ),
                        "delta_p_threshold": (row[6]),
                        "last_working_delta_p": (row[7]),
                        "last_working_timestamp": (
                            datetime.fromisoformat(row[8])
                            if row[8] is not None
                            else None
                        ),
                    }
                )

            return result

        except sqlite3.Error as error:
            print("Błąd pobierania ostatnich " "próbek aktywnych filtrów: " f"{error}")

            return []

        finally:
            if connection:
                connection.close()

    def set_filter_connection_status(
        self,
        filter_id,
        connected,
        last_error=None,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            timestamp = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO filter_connection_status (
                    filter_id,
                    connected,
                    last_change,
                    last_error
                )
                VALUES (?, ?, ?, ?)

                ON CONFLICT(filter_id)
                DO UPDATE SET
                    connected
                        = excluded.connected,

                    last_change = CASE
                        WHEN
                            filter_connection_status.connected
                            != excluded.connected
                        THEN
                            excluded.last_change
                        ELSE
                            filter_connection_status.last_change
                    END,

                    last_error
                        = excluded.last_error
                """,
                (
                    filter_id,
                    int(connected),
                    timestamp,
                    last_error,
                ),
            )

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print(
                "Błąd aktualizacji statusu "
                f"połączenia filtra {filter_id}: "
                f"{error}"
            )

        finally:
            if connection:
                connection.close()

    def get_connection_counts(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    COUNT(
                        filters.id
                    ),

                    SUM(
                        CASE
                            WHEN
                                filter_connection_status.connected
                                = 1
                            THEN 1
                            ELSE 0
                        END
                    )

                FROM filters

                LEFT JOIN
                    filter_connection_status
                    ON
                        filter_connection_status.filter_id
                        = filters.id

                WHERE filters.active = 1
            """)

            (
                active_count,
                connected_count,
            ) = cursor.fetchone()

            return (
                active_count or 0,
                connected_count or 0,
            )

        except sqlite3.Error as error:
            print("Błąd pobierania statusów " f"połączeń: {error}")

            return (
                0,
                0,
            )

        finally:
            if connection:
                connection.close()

    def set_collector_heartbeat(
        self,
        timestamp,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO collector_status (
                    id,
                    last_heartbeat
                )
                VALUES (1, ?)

                ON CONFLICT(id)
                DO UPDATE SET
                    last_heartbeat
                        = excluded.last_heartbeat
                """,
                (timestamp.isoformat(),),
            )

            connection.commit()

        except sqlite3.Error as error:
            if connection:
                connection.rollback()

            print("Błąd zapisu heartbeat " f"collectora: {error}")

        finally:
            if connection:
                connection.close()

    def get_collector_heartbeat(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT last_heartbeat
                FROM collector_status
                WHERE id = 1
            """)

            row = cursor.fetchone()

            if row is None:
                return None

            return datetime.fromisoformat(row[0])

        except sqlite3.Error as error:
            print("Błąd odczytu heartbeat " f"collectora: {error}")

            return None

        finally:
            if connection:
                connection.close()

    def clear_collector_heartbeat(
        self,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                DELETE FROM collector_status
                WHERE id = 1
            """)

            connection.commit()

        finally:
            if connection:
                connection.close()

    def request_collector_stop(self):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO collector_control (
                    id,
                    stop_requested
                )
                VALUES (1, 1)

                ON CONFLICT(id)
                DO UPDATE SET
                    stop_requested = 1
            """)

            connection.commit()

        finally:
            if connection:
                connection.close()

    def is_collector_stop_requested(
        self,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                SELECT stop_requested
                FROM collector_control
                WHERE id = 1
            """)

            row = cursor.fetchone()

            if row is None:
                return False

            return bool(row[0])

        finally:
            if connection:
                connection.close()

    def clear_collector_stop_request(
        self,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute("""
                INSERT INTO collector_control (
                    id,
                    stop_requested
                )
                VALUES (1, 0)

                ON CONFLICT(id)
                DO UPDATE SET
                    stop_requested = 0
            """)

            connection.commit()

        finally:
            if connection:
                connection.close()

    def add_event(
        self,
        event_type,
        message,
        timestamp=None,
    ):
        if timestamp is None:
            timestamp = datetime.now()

        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                INSERT INTO system_events (
                    timestamp,
                    event_type,
                    message
                )
                VALUES (?, ?, ?)
                """,
                (
                    timestamp.isoformat(),
                    event_type,
                    message,
                ),
            )

            connection.commit()

        except sqlite3.Error:
            if connection:
                connection.rollback()

            raise

        finally:
            if connection:
                connection.close()

    def get_recent_events(
        self,
        limit=10,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    timestamp,
                    event_type,
                    message
                FROM system_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

            return [
                (
                    datetime.fromisoformat(row[0]),
                    row[1],
                    row[2],
                )
                for row in rows
            ]

        finally:
            if connection:
                connection.close()

    def delete_filter(
        self,
        filter_id: int,
    ) -> bool:
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT id
                FROM filters
                WHERE id = ?
                """,
                (filter_id,),
            )

            if cursor.fetchone() is None:
                return False

            cursor.execute(
                """
                DELETE FROM filter_samples
                WHERE filter_id = ?
                """,
                (filter_id,),
            )

            cursor.execute(
                """
                DELETE FROM filter_connection_status
                WHERE filter_id = ?
                """,
                (filter_id,),
            )

            cursor.execute(
                """
                DELETE FROM filters
                WHERE id = ?
                """,
                (filter_id,),
            )

            connection.commit()

            return True

        except sqlite3.Error:
            if connection:
                connection.rollback()

            raise

        finally:
            if connection:
                connection.close()

    def update_filter_opc_settings(
        self,
        filter_obj: Filter,
    ):
        if filter_obj.filter_id is None:
            raise ValueError(
                "Nie można zapisać ustawień OPC UA " "dla filtra bez filter_id."
            )

        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE filters
                SET
                    opc_security_policy = ?,
                    opc_security_mode = ?,
                    opc_application_uri = ?,
                    opc_client_certificate_path = ?,
                    opc_client_private_key_path = ?,
                    opc_trusted_certificates_dir = ?,
                    opc_server_certificate_path = ?,
                    opc_validate_server_certificate = ?,
                    opc_auth_type = ?,
                    opc_username = ?,
                    opc_connect_timeout_seconds = ?,
                    opc_request_timeout_seconds = ?,
                    opc_reconnect_delay_seconds = ?
                WHERE id = ?
                """,
                (
                    filter_obj.opc_security_policy,
                    filter_obj.opc_security_mode,
                    filter_obj.opc_application_uri,
                    filter_obj.opc_client_certificate_path,
                    filter_obj.opc_client_private_key_path,
                    filter_obj.opc_trusted_certificates_dir,
                    filter_obj.opc_server_certificate_path,
                    int(filter_obj.opc_validate_server_certificate),
                    filter_obj.opc_auth_type,
                    filter_obj.opc_username,
                    filter_obj.opc_connect_timeout_seconds,
                    filter_obj.opc_request_timeout_seconds,
                    filter_obj.opc_reconnect_delay_seconds,
                    filter_obj.filter_id,
                ),
            )

            connection.commit()

        except sqlite3.Error:
            if connection:
                connection.rollback()

            raise

        finally:
            if connection:
                connection.close()

    def update_filter(
        self,
        filter_obj: Filter,
    ):
        connection = None

        try:
            connection = self.connect()
            cursor = connection.cursor()

            cursor.execute(
                """
                UPDATE filters
                SET
                    name = ?,
                    active = ?,
                    opc_url = ?,
                    delta_p_threshold = ?,
                    delta_p_node_id = ?,
                    status_node_id = ?,
                    alarm_node_id = ?
                WHERE id = ?
                """,
                (
                    filter_obj.name,
                    int(filter_obj.active),
                    filter_obj.opc_url,
                    filter_obj.delta_p_threshold,
                    filter_obj.delta_p_node_id,
                    filter_obj.status_node_id,
                    filter_obj.alarm_node_id,
                    filter_obj.filter_id,
                ),
            )

            connection.commit()

        except sqlite3.Error:
            if connection:
                connection.rollback()

            raise

        finally:
            if connection:
                connection.close()
