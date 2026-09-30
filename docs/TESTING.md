# Testing

## Current baseline

```text
359 passed
```

Run:

```powershell
python -m pytest
```

## Covered areas

The suite covers, among other areas:

- collector behaviour
- collector single-instance protection
- collector launcher
- collector file logging
- frozen GUI → collector log-path handoff
- no development env leakage
- runtime paths
- database location
- per-machine OPC UA configuration
- OPC UA security/authentication
- namespace browsing
- OPC UA Server
- reports
- SMTP
- DPAPI credential persistence
- GUI single-instance protection
- repository error paths
- packaging-related behaviour

## Latest regression coverage

The current v1.0 candidate verifies that the collector:

- creates its configured log file
- writes INFO records
- does not duplicate its owned file handler
- preserves exception propagation from `main()`
- uses normal `LOG_FILE` in development
- uses the GUI-provided log path in frozen builds

Installed-build smoke testing is still required in addition to pytest.
