@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo ============================================================
echo FiltersReporting v1.0 - TEST + BUILD + INSTALLER
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1. Python
REM ------------------------------------------------------------

set "PYTHON="

if defined VIRTUAL_ENV (
    if exist "%VIRTUAL_ENV%\Scripts\python.exe" (
        set "PYTHON=%VIRTUAL_ENV%\Scripts\python.exe"
    )
)

if not defined PYTHON (
    if exist ".venv\Scripts\python.exe" (
        set "PYTHON=%CD%\.venv\Scripts\python.exe"
    )
)

if not defined PYTHON (
    where python.exe >nul 2>&1

    if not errorlevel 1 (
        set "PYTHON=python.exe"
    )
)

if not defined PYTHON (
    echo.
    echo [ERROR] Nie znaleziono interpretera Python.
    echo.
    exit /b 1
)

echo Uzywam Python:
"%PYTHON%" --version

if errorlevel 1 (
    echo.
    echo [ERROR] Nie udalo sie uruchomic Python.
    exit /b 1
)

"%PYTHON%" -c "import pytest, PyInstaller, asyncua" >nul 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Brakuje wymaganych pakietow.
    echo.
    echo Sprawdz:
    echo   python -m pip install -r requirements.txt
    echo   python -m pip install pyinstaller pytest
    echo.
    exit /b 1
)

echo.

REM ------------------------------------------------------------
REM 2. Tests
REM ------------------------------------------------------------

echo [1/5] Uruchamiam testy...

"%PYTHON%" -m pytest -q

if errorlevel 1 (
    echo.
    echo [ERROR] Testy nie przeszly.
    echo Build zostal przerwany.
    echo.
    exit /b 1
)

echo.
echo [OK] Testy przeszly.
echo.

REM ------------------------------------------------------------
REM 3. Clean
REM ------------------------------------------------------------

echo [2/5] Czyszcze poprzedni build...

if exist "build" (
    rmdir /s /q "build"
)

if exist "dist\FiltersReporting" (
    rmdir /s /q "dist\FiltersReporting"
)

if exist "dist\FiltersReportingCollector" (
    rmdir /s /q "dist\FiltersReportingCollector"
)

if not exist "dist" (
    mkdir "dist"
)

if not exist "release" (
    mkdir "release"
)

REM Usuwamy stary installer, żeby nie dało się
REM przypadkiem zainstalować poprzedniej wersji.
if exist "release\FiltersReporting-v1.00-Setup.exe" (
    del /f /q "release\FiltersReporting-v1.00-Setup.exe"
)

echo [OK] Poprzedni build usuniety.
echo.

REM ------------------------------------------------------------
REM 4. GUI executable
REM ------------------------------------------------------------

echo [3/5] Buduje FiltersReporting.exe...

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --name "FiltersReporting" ^
    --icon "packaging\FiltersReporting.ico" ^
    --version-file "packaging\version_info.txt" ^
    --runtime-hook "packaging\runtime_hook.py" ^
    --collect-all asyncua ^
    --copy-metadata asyncua ^
    "filters_reporting\gui\app.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build FiltersReporting.exe nie powiodl sie.
    echo.
    exit /b 1
)

if not exist "dist\FiltersReporting\FiltersReporting.exe" (
    echo.
    echo [ERROR] Nie znaleziono:
    echo dist\FiltersReporting\FiltersReporting.exe
    echo.
    exit /b 1
)

echo [OK] GUI zbudowane.
echo.

REM ------------------------------------------------------------
REM 5. Collector executable
REM ------------------------------------------------------------

echo [4/5] Buduje FiltersReportingCollector.exe...

"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --console ^
    --hide-console=hide-early ^
    --name "FiltersReportingCollector" ^
    --icon "packaging\FiltersReporting.ico" ^
    --version-file "packaging\version_info.txt" ^
    --runtime-hook "packaging\runtime_hook.py" ^
    --collect-all asyncua ^
    --copy-metadata asyncua ^
    "filters_reporting\collection\data_collector.py"

if errorlevel 1 (
    echo.
    echo [ERROR] Build FiltersReportingCollector.exe nie powiodl sie.
    echo.
    exit /b 1
)

if not exist "dist\FiltersReportingCollector\FiltersReportingCollector.exe" (
    echo.
    echo [ERROR] Nie znaleziono:
    echo dist\FiltersReportingCollector\FiltersReportingCollector.exe
    echo.
    exit /b 1
)

echo [OK] Collector zbudowany.
echo.

REM ------------------------------------------------------------
REM 6. Inno Setup
REM ------------------------------------------------------------

echo [5/5] Buduje installer Inno Setup...

set "ISCC="

if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    where ISCC.exe >nul 2>&1

    if not errorlevel 1 (
        set "ISCC=ISCC.exe"
    )
)

if not defined ISCC (
    echo.
    echo [ERROR] Nie znaleziono Inno Setup 6.
    echo.
    echo EXE zostaly zbudowane, ale installer nie powstal.
    echo.
    exit /b 1
)

echo [OK] Inno Setup:
echo   %ISCC%
echo.

"%ISCC%" "packaging\FiltersReporting.iss"

if errorlevel 1 (
    echo.
    echo [ERROR] Kompilacja installera nie powiodla sie.
    echo.
    exit /b 1
)

if not exist "release\FiltersReporting-v1.00-Setup.exe" (
    echo.
    echo [ERROR] Inno Setup zakonczyl prace,
    echo ale nie znaleziono:
    echo.
    echo release\FiltersReporting-v1.00-Setup.exe
    echo.
    exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] FiltersReporting v1.0 gotowy do smoke testu.
echo ============================================================
echo.
echo Testy:
echo   PASSED
echo.
echo GUI:
echo   dist\FiltersReporting\FiltersReporting.exe
echo.
echo Collector:
echo   dist\FiltersReportingCollector\FiltersReportingCollector.exe
echo.
echo Installer:
echo   release\FiltersReporting-v1.00-Setup.exe
echo.
echo UWAGA:
echo   To jest NOWY installer utworzony z aktualnego kodu.
echo ============================================================
echo.

exit /b 0