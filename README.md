# FiltersReporting

Industrial OPC UA monitoring and reporting application written in Python.

FiltersReporting is a Windows desktop application for collecting, storing, monitoring and reporting filtration-system data from multiple independent OPC UA machines.

## Status

**v1.0 release candidate**

Automated test baseline:

```text
359 passed
```

The v1.0 feature set is frozen. Remaining release work is final installed-build smoke testing, screenshots, anonymised sample reports and repository cleanup.

## Main features

- multiple independent OPC UA machines
- one filter = one independent OPC UA endpoint
- per-machine Security Policy / Security Mode
- X.509 client certificates
- per-machine Username/Password authentication
- Windows DPAPI credential protection
- asynchronous data collection
- SQLite persistence
- filter-state monitoring
- Excel and TXT daily reports
- SMTP report delivery
- automatic daily reporting
- PySide6 desktop GUI
- Dashboard recent-events section
- OPC UA namespace browser
- optional local OPC UA Server
- GUI and collector single-instance protection
- dedicated frozen collector executable
- rotating collector log
- PyInstaller + Inno Setup packaging

## Collector runtime

Development:

```text
python -m filters_reporting.collection.data_collector
```

Installed build:

```text
FiltersReportingCollector.exe
```

The GUI and frozen collector explicitly share the same log-file path.

## OPC UA model

In v1.0:

> one configured filter = one independent machine / OPC UA server

Each machine can have its own:

- endpoint
- Security Policy
- Security Mode
- Application URI
- client certificate
- private key
- trusted certificate directory
- server certificate
- certificate validation setting
- authentication method
- username/password
- timeouts
- reconnect delay
- DeltaP NodeId
- Status NodeId
- AlarmActive NodeId

A communication problem with one machine does not stop acquisition from the others.

## Reports

Daily reports are generated as:

```text
.xlsx
.txt
```

They include statistics such as:

- sample count
- minimum Δp
- average Δp
- maximum Δp
- threshold
- alarm percentage
- operating percentage
- attention state

## Technology stack

- Python
- PySide6
- asyncua / OPC UA
- asyncio
- SQLite
- openpyxl
- Windows DPAPI
- pytest
- PyInstaller
- Inno Setup

## Screenshots

Add:

```text
docs/screenshots/dashboard.png
docs/screenshots/filters.png
docs/screenshots/reports.png
docs/screenshots/opc-ua-client.png
docs/screenshots/opc-ua-server.png
```

## Sample reports

Add anonymised examples:

```text
samples/sample_daily_report.xlsx
samples/sample_daily_report.txt
```

## Testing

Run:

```powershell
python -m pytest
```

Current baseline:

```text
359 passed
```

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/OPC_UA_SECURITY.md`
- `docs/TESTING.md`
- `docs/USER_MANUAL.md`
- `docs/RELEASE_CHECKLIST.md`
