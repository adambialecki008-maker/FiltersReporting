# FiltersReporting — Portfolio Notes

## One-sentence description

FiltersReporting is a Windows Python application that independently monitors multiple OPC UA machines, stores process data in SQLite and generates automated daily reports.

## CV version

**FiltersReporting — Python / OPC UA industrial monitoring application**

- developed a PySide6 desktop application for multi-machine OPC UA monitoring
- implemented independent per-machine endpoints, security policies, certificates and credentials
- implemented asynchronous collection and failure isolation
- implemented SQLite persistence and filter-state evaluation
- implemented daily Excel/TXT reporting and SMTP delivery
- protected persistent credentials with Windows DPAPI
- packaged GUI and collector as separate Windows executables using PyInstaller and Inno Setup
- implemented explicit development-vs-installed collector launching
- implemented explicit GUI → collector log-path handoff in frozen builds
- maintained an automated suite with **359 passing tests**
- restored and verified the Dashboard recent-events section after UI refactoring

## Interview discussion points

### Why independent OPC UA clients?

Industrial machines can differ in endpoint, certificate, Security Policy, credentials, NodeIds and availability. A global client configuration would couple unrelated machines.

### Why separate collector and GUI?

It keeps the GUI responsive, isolates acquisition from presentation, makes process lifecycle visible and improves diagnostics.

### Packaging issue solved

In development:

```text
sys.executable = python.exe
```

In a PyInstaller GUI:

```text
sys.executable = FiltersReporting.exe
```

Therefore the installed GUI must start the dedicated:

```text
FiltersReportingCollector.exe
```

instead of trying to run `FiltersReporting.exe -m ...`.

### Logging issue solved

The frozen GUI and collector explicitly share the same log path so Dashboard → Logi opens the file actually written by the collector.

## Test baseline

```text
359 passed
```
