from __future__ import annotations

from pathlib import Path


def test_installer_does_not_package_tools_directory():
    installer = Path(
        "packaging/FiltersReporting.iss"
    ).read_text(
        encoding="utf-8",
    ).casefold()

    assert "\\tools\\" not in installer
    assert "opcua_machine_simulator" not in installer


def test_build_script_has_no_simulator_entrypoint():
    build_script = Path(
        "FiltersReporting_build_exe.cmd"
    ).read_text(
        encoding="utf-8",
    ).casefold()

    assert (
        "tools\\opcua_machine_simulator.py"
        not in build_script
    )

    assert (
        "--name \"filtersreportingsimulator\""
        not in build_script
    )
