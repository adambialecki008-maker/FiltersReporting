# v1.0 Release Checklist

## Automated tests

- [x] `python -m pytest`
- [x] `359 passed`
- [x] no failed tests

## Source smoke test

- [x] GUI starts
- [x] recent-events section is visible
- [x] collector starts
- [x] collector log works in source mode

## Installed-build smoke test

- [ ] install newest `FiltersReporting-v1.00-Setup.exe`
- [ ] launch installed GUI
- [ ] start collector
- [ ] verify collector log contains bootstrap/start entries
- [ ] verify collector can be stopped cleanly
- [ ] verify samples appear in SQLite
- [ ] verify settings persist after restart

## Reports

- [ ] Excel generated
- [ ] TXT generated
- [ ] statistics verified
- [ ] manual email send works
- [ ] automatic daily report works

## Repository cleanup

- [ ] no `.venv`
- [ ] no `build/`
- [ ] no `dist/`
- [ ] no `release/`
- [ ] no databases
- [ ] no logs
- [ ] no passwords
- [ ] no private keys
- [ ] no production certificates
- [ ] screenshots added
- [ ] anonymised sample report added

## Screenshots

Add:

```text
docs/screenshots/dashboard.png
docs/screenshots/filters.png
docs/screenshots/reports.png
docs/screenshots/opc-ua-client.png
docs/screenshots/opc-ua-server.png
```

## Samples

Add:

```text
samples/sample_daily_report.xlsx
samples/sample_daily_report.txt
```

## Git release

```powershell
git status
git add .
git commit -m "Prepare FiltersReporting v1.0 portfolio release"
git tag v1.0.0
```
