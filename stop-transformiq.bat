@echo off
taskkill /FI "WINDOWTITLE eq TransformIQ Backend*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq TransformIQ Frontend*" /T /F >nul 2>&1
echo TransformIQ processes stopped.
