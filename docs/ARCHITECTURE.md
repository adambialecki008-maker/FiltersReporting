# Architecture

## Overview

```text
 OPC UA Machine #1 ─┐
 OPC UA Machine #2 ─┼─> independent OPC UA clients
 OPC UA Machine #N ─┘
                           │
                           ▼
                    Data Collector
                           │
                           ▼
                        SQLite
                    ┌──────┴──────┐
                    ▼             ▼
                Monitoring     Reporting
                    │             │
                    └──────┬──────┘
                           ▼
                       PySide6 GUI
```

## Collector

The collector runs as a separate process.

Development:

```text
python -m filters_reporting.collection.data_collector
```

Installed:

```text
FiltersReportingCollector.exe
```

## Frozen log-path handoff

The GUI and collector are separate executables after packaging. The GUI passes the exact resolved log-file path to the frozen collector through the runtime environment so both processes use one physical `collector.log`.

This avoids divergent log paths caused by different executables or working directories.

## Persistence

SQLite stores application configuration, filter samples, collector heartbeat and runtime state.

## Monitoring

Monitoring converts samples/runtime state into application states such as:

```text
clean-working
clean-stopped
dirty-working
dirty-stopped
error
offline
monitoring-stopped
```

## GUI

The PySide6 GUI contains:

- Dashboard
- Filters
- Reports
- Settings

Dashboard includes:

- collector controls
- report actions
- quick actions
- filters requiring attention
- recent events
- system status

## Test baseline

```text
359 passed
```
