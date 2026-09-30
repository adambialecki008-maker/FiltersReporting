# Testing

## v1.0.0 status

``` text
359 passed
```

Run:

``` powershell
python -m pytest
```

## Covered areas

The suite covers collector behaviour, single-instance protection,
collector launching and logging, frozen GUI → collector log-path
handoff, runtime paths, database location, per-machine OPC UA
configuration, OPC UA security/authentication, namespace browsing, local
OPC UA Server, reports, SMTP, Windows DPAPI credential persistence, GUI
protection, repository error paths and packaging-related behaviour.

## Installed-build smoke test

The final installed v1.0.0 build was also validated manually.

Passed:

-   GUI startup
-   Dashboard recent-events section
-   collector start / clean stop / restart
-   5/5 simulated OPC UA machines connected
-   5/5 sample collection with `OPC_OK`
-   sustained collection over multiple cycles
-   collector log creation and updates
-   settings persistence after restart
-   manual Excel report generation
-   manual TXT report generation
-   manual SMTP report delivery
-   automatic daily report

Automated tests and installed-build smoke testing cover different
failure modes; both were completed before the v1.0.0 release was frozen.
