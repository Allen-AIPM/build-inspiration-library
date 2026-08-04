@echo off
setlocal
cd /d "%~dp0"

set "LOG=gallery-update.log"
> "%LOG%" echo [%date% %time%] Starting gallery update

where py >nul 2>nul
if errorlevel 1 (
  set "PYTHON=python"
) else (
  set "PYTHON=py -3"
)

echo.
echo [1/3] Checking new images for near duplicates...
%PYTHON% dedupe_images.py >> "%LOG%" 2>&1
if errorlevel 1 goto failed

echo [2/3] Updating gallery data...
%PYTHON% update_gallery.py >> "%LOG%" 2>&1
if errorlevel 1 goto failed

echo [3/3] Creating AI tags for new images...
%PYTHON% ai_tag_images.py >> "%LOG%" 2>&1
if errorlevel 1 goto failed

echo.
echo Done. Check gallery-update.log for details.
echo [%date% %time%] Completed >> "%LOG%"
goto done

:failed
echo.
echo Failed. Check gallery-update.log for details.
echo [%date% %time%] Failed with exit code %errorlevel% >> "%LOG%"
type "%LOG%"

:done
echo.
pause
endlocal
