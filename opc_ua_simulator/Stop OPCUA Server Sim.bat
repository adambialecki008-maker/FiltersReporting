@echo off
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*opc_ua_server_simulator.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
exit