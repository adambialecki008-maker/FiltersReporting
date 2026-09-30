FiltersReporting_build_installer.cmd@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

echo.
echo ==========================================
echo  FiltersReporting v1.00 - CLIENT INSTALLER
echo ==========================================
echo.

echo [1/5] Looking for Inno Setup compiler...

set "ISCC="

for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
    if not defined ISCC (
        set "ISCC=%%I"
    )
)

if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" (
        set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" (
        set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%LocalAppData%\Programs\Inno Setup 7\ISCC.exe" (
        set "ISCC=%LocalAppData%\Programs\Inno Setup 7\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
        set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    )
)

if not defined ISCC (
    echo.
    echo ERROR: Inno Setup compiler not found.
    echo.
    echo Install it with:
    echo.
    echo winget install --id JRSoftware.InnoSetup -e
    echo.
    exit /b 1
)

echo Found:
echo %ISCC%
echo.

echo [2/5] Stopping running application...

taskkill /F /IM FiltersReporting.exe >nul 2>&1
taskkill /F /IM FiltersReportingCollector.exe >nul 2>&1

echo.
echo [3/5] Building application...

call "%CD%\FiltersReporting_build_exe.cmd"

if errorlevel 1 (
    echo.
    echo ERROR: Application build failed.
    exit /b 1
)

if not exist "%CD%\dist\FiltersReporting\FiltersReporting.exe" (
    echo.
    echo ERROR: FiltersReporting.exe not found.
    exit /b 1
)

if not exist "%CD%\dist\FiltersReportingCollector\FiltersReportingCollector.exe" (
    echo.
    echo ERROR: FiltersReportingCollector.exe not found.
    exit /b 1
)

if not exist "%CD%\packaging\FiltersReporting.iss" (
    echo.
    echo ERROR: Missing installer script:
    echo %CD%\packaging\FiltersReporting.iss
    exit /b 1
)

echo.
echo [4/5] Building Windows installer...

if exist "%CD%\release\FiltersReporting-v1.00-Setup.exe" (
    del /F /Q "%CD%\release\FiltersReporting-v1.00-Setup.exe"
)

"%ISCC%" "%CD%\packaging\FiltersReporting.iss"

if errorlevel 1 (
    echo.
    echo ERROR: Installer build failed.
    exit /b 1
)

echo.
echo [5/5] Verifying installer...

if not exist "%CD%\release\FiltersReporting-v1.00-Setup.exe" (
    echo.
    echo ERROR: Installer was not created.
    exit /b 1
)

echo.
echo ==========================================
echo  INSTALLER BUILD OK
echo ==========================================
echo.
echo Installer:
echo %CD%\release\FiltersReporting-v1.00-Setup.exe
echo.
echo This is the file for the client.
echo.

exit /b 0