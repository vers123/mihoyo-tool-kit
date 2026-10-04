@echo off
REM Wrapper to call build.ps1
powershell -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
