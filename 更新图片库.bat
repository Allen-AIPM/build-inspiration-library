@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 正在更新图片资料...
python update_gallery.py
if errorlevel 1 goto failed

echo.
echo [2/2] 正在进行 AI 打标...
python ai_tag_images.py --pause
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo 更新未完成，请查看 ai_tag_log.txt 或上方提示。
pause
exit /b 1
