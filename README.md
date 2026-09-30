# FiltersReporting

**Industrial OPC UA monitoring and reporting for independent machines.**

FiltersReporting is a Windows desktop application written in Python for
collecting, storing, monitoring and reporting filtration-system data
from multiple independent OPC UA machines.

> **Release:** v1.0.0\
> **Automated tests:** 359 passed\
> **Installed-build smoke test:** passed\
> **License:** proprietary --- source available for portfolio/review
> purposes only

![FiltersReporting Dashboard](docs/screenshots/dashboard.png)

## What it does

FiltersReporting treats every configured filter as an independent OPC UA
machine. Each machine can use its own endpoint, NodeIds, security
policy, security mode, certificates and authentication settings.

The application provides:

-   asynchronous OPC UA data acquisition from multiple machines
-   per-machine connection and security configuration
-   X.509 client certificate support
-   Username/Password or Anonymous client authentication
-   Windows DPAPI protection for stored credentials
-   SQLite persistence
-   live monitoring and attention-state evaluation
-   daily Excel and TXT reports
-   manual and automatic SMTP report delivery
-   automatic daily reporting
-   OPC UA namespace browsing
-   optional local read-only OPC UA server
-   separate GUI and collector processes
-   rotating collector logs
-   single-instance protection
-   Windows packaging with PyInstaller and Inno Setup

## Why the architecture is per-machine

Industrial installations are rarely uniform. Different machines can
expose different endpoints, certificates, credentials, NodeIds and
security requirements.

FiltersReporting therefore uses the model:

``` text
one filter = one independent OPC UA machine
```

A communication failure on one machine does not stop data acquisition
from the others.

``` text
 OPC UA Machine #1 ─┐
 OPC UA Machine #2 ─┼──> async collector ──> SQLite
 OPC UA Machine #N ─┘                         │
                                              ├──> monitoring
                                              ├──> Excel / TXT reports
                                              └──> SMTP
                                                       │
                                                       ▼
                                                   PySide6 GUI
```

## Application views

### Monitoring dashboard

The dashboard shows collector state, database status, connected OPC UA
machines, filters requiring attention, recent events and quick actions.

![Dashboard](docs/screenshots/dashboard.png)

### Filter configuration

Each filter has its own endpoint and signal NodeIds (`DeltaP`, `Status`,
`AlarmActive`).

![Filters](docs/screenshots/filter-configuration.png)

### Daily reports

Daily reports aggregate collected samples and expose sample count,
minimum/average/maximum Δp, configured threshold, alarm percentage and
operating percentage.

![Reports](docs/screenshots/daily-reports.png)

### OPC UA security

Client configuration is independent for every machine and supports
security policy/mode selection, client certificates, server-certificate
trust and per-machine credentials.

See the visual walkthrough in [SHOWCASE.md](docs/SHOWCASE.md).

## Collector runtime

The collector is a separate process from the GUI.

Development:

``` powershell
python -m filters_reporting.collection.data_collector
```

Installed build:

``` text
FiltersReportingCollector.exe
```

The installed GUI launches the dedicated collector executable and
explicitly hands off the resolved collector log path so both processes
refer to the same physical log file.

## Reports

A daily report is generated in two formats:

``` text
.xlsx
.txt
```

The Excel workbook contains summary statistics and raw samples. Reports
can be generated manually, generated and sent by e-mail, or scheduled
automatically for the previous day.

## Technology stack

  Area                       Technology
  -------------------------- ------------------
  Language                   Python
  Desktop GUI                PySide6
  Industrial communication   OPC UA / asyncua
  Concurrency                asyncio
  Persistence                SQLite
  Excel reporting            openpyxl
  Credential protection      Windows DPAPI
  Tests                      pytest
  Packaging                  PyInstaller
  Installer                  Inno Setup

## Validation

The frozen v1.0.0 build was validated after installation.

-   **359 automated tests passed**
-   GUI startup passed
-   collector start / stop / restart passed
-   5/5 simulated OPC UA machines connected
-   sustained collection passed
-   collector logging passed
-   settings persistence passed
-   Excel report generation passed
-   TXT report generation passed
-   SMTP delivery passed
-   automatic daily report passed

See [TESTING.md](docs/TESTING.md) for the automated test scope.

## Documentation

-   [Showcase](docs/SHOWCASE.md)
-   [User manual](docs/USER_MANUAL.md)
-   [Architecture](docs/ARCHITECTURE.md)
-   [OPC UA security](docs/OPC_UA_SECURITY.md)
-   [Testing](docs/TESTING.md)
-   [Changelog](CHANGELOG.md)

## Repository note

This repository is published as a **portfolio/source-review project**.
Publication of the source code does not grant permission to use, copy,
modify, distribute, sublicense or commercialize it.

See [LICENSE](LICENSE).

------------------------------------------------------------------------

**FiltersReporting v1.0.0**
