@echo off
REM 米游社工具箱构建脚本 —— cmd 包装器（转发到 build.ps1）
REM 用法: build.bat deps / build.bat exe-onedir / build.bat clean
powershell -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
