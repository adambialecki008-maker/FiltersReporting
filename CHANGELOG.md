# Changelog

## v1.0.0 --- 2026-09-30

First frozen portfolio release.

### Added

-   multi-machine OPC UA collection
-   one independent OPC UA configuration per filter/machine
-   per-machine endpoint, NodeIds and security configuration
-   X.509 client certificate support
-   per-machine Anonymous or Username/Password client authentication
-   Windows DPAPI credential protection
-   SQLite persistence
-   filter-state monitoring
-   Excel and TXT daily reports
-   SMTP report delivery and automatic daily reporting
-   PySide6 desktop GUI
-   Dashboard recent-events section
-   OPC UA namespace browser
-   optional local read-only OPC UA Server
-   GUI and collector single-instance protection
-   rotating collector logs
-   PyInstaller packaging and Inno Setup installer
-   development OPC UA machine simulator

### Packaging/runtime fixes

-   separated installed runtime data from program files
-   added dedicated collector executable launching in frozen builds
-   preserved development `python -m` collector launching
-   hardened collector file logging for frozen builds
-   added collector bootstrap diagnostics
-   unified GUI/collector log path in frozen builds through explicit
    runtime handoff
-   added regression coverage for frozen log-path handoff
-   restored the Dashboard recent-events section to the visible layout

### Validation

``` text
359 automated tests passed
```

The final installed build also passed GUI, collector, OPC UA, logging,
persistence, reporting, SMTP and automatic-report smoke tests.
