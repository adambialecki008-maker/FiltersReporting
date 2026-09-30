# v1.0.0 Release Checklist

## Automated tests

-   [x] `python -m pytest`
-   [x] `359 passed`
-   [x] no failed tests

## Installed-build smoke test

-   [x] final installer tested
-   [x] installed GUI launches
-   [x] Dashboard recent-events section visible
-   [x] collector start / clean stop / restart
-   [x] collector logging
-   [x] 5/5 simulated OPC UA machines
-   [x] sustained sample collection
-   [x] settings persistence after restart

## Reports

-   [x] Excel generated
-   [x] TXT generated
-   [x] manual e-mail send works
-   [x] automatic daily report works

## Repository hygiene

-   [x] standalone FiltersReporting Git repository
-   [x] no `.env`
-   [x] no runtime databases or logs
-   [x] no private keys or production certificates
-   [x] public screenshots anonymised
-   [x] proprietary license included
-   [ ] optional anonymised sample report added

## Git release

Release commit:

``` text
b04e15e Release FiltersReporting v1.0.0
```

Tag:

``` text
v1.0.0
```

The tag marks the frozen technical v1.0.0 release.
Portfolio/documentation cleanup performed afterward should remain normal
post-release commits rather than moving the release tag.
