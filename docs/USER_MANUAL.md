# FiltersReporting v1.0 — User Manual

## Dashboard

The Dashboard provides:

- collector start/stop
- collection interval
- daily-report generation
- quick actions
- filters requiring attention
- recent events
- system status
- access to reports and logs

## Filters

Configure one independent machine per filter.

Each filter can define its own OPC UA endpoint, security, authentication and NodeIds.

## Signals

Expected signals:

```text
DeltaP
Status
AlarmActive
```

## Reports

Reports can be generated as:

```text
.xlsx
.txt
```

Manual generation and manual email sending are supported.

## Collector

Development:

```text
python -m filters_reporting.collection.data_collector
```

Installed build:

```text
FiltersReportingCollector.exe
```

## Logs

Use:

```text
Dashboard → Logi
```

The installed GUI and collector are configured to use the same resolved log file.

Typical entries include:

```text
Collector bootstrap...
Data collector uruchomiony...
Cykl 1: zapisano 5/5 próbek. | OPC_OK
```

## Database

Changing the configured database path does not automatically move the existing SQLite file. Close the GUI and collector before manually copying an existing database.

## Version

```text
FiltersReporting v1.0
```
