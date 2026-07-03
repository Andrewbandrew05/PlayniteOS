@echo off
if exist "%USERPROFILE%\Playnite\config.json" exit /b

:: Inform the user
powershell -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Welcome to PlayniteOS Setup!`n`nPlease sign into your launchers and configure Playnite.`n`nWhen finished, REBOOT to enter Console Mode.', 'PlayniteOS')"

:: Launch everything
start "" "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe"
start "" "%USERPROFILE%\Playnite\Playnite.DesktopApp.exe"