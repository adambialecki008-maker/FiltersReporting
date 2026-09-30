# Changelog

## v1.0.0 — release candidate

### Added

- multi-machine OPC UA collection
- per-machine OPC UA endpoint and NodeIds
- per-machine security configuration
- X.509 client certificate support
- per-machine Username/Password authentication
- Windows DPAPI credential protection
- SQLite persistence
- filter-state monitoring
- Excel and TXT reports
- SMTP report delivery
- automatic report scheduling
- PySide6 desktop GUI
- Dashboard recent-events section
- OPC UA namespace browser
- optional local read-only OPC UA Server
- GUI and collector single-instance protection
- rotating collector logs
- PyInstaller packaging
- Inno Setup installer
- development OPC UA machine simulator

### Packaging/runtime fixes

- separated installed runtime data from program files
- added dedicated collector executable launching in frozen builds
- preserved development `python -m` collector launching
- ensured runtime log file exists when GUI starts
- removed import-time Qt URL opening
- hardened collector file logging for frozen builds
- added collector bootstrap diagnostics
- unified GUI/collector log path in frozen builds through explicit runtime handoff
- added regression coverage for frozen log-path handoff
- restored the Dashboard recent-events section to the visible layout

### Test status

```text
359 passed
```
