@echo off
setlocal enabledelayedexpansion

:: If powershell.exe exists in system directory, run it
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" %*
    exit /b %ERRORLEVEL%
)

if exist "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" (
    "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" %*
    exit /b %ERRORLEVEL%
)

:: Otherwise, extract command after -Command if present
set "CMD_TO_RUN="
:arg_loop
if "%~1"=="" goto run_cmd
if /i "%~1"=="-Command" (
    shift
    set "CMD_TO_RUN=%~1"
    goto run_cmd
)
shift
goto arg_loop

:run_cmd
if defined CMD_TO_RUN (
    cmd.exe /c "%CMD_TO_RUN%"
    exit /b %ERRORLEVEL%
)

cmd.exe /c %*
exit /b %ERRORLEVEL%

