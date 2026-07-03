@echo off
set "PLAYNITE_DIR=%USERPROFILE%\Playnite"
set "CONFIG_FILE=%PLAYNITE_DIR%\config.json"

:: --- VISUAL INDICATOR ---
:: This creates a popup that stays on screen for 3 seconds to confirm the script is alive.
powershell -ExecutionPolicy Bypass -Command "$w = New-Object -ComObject WScript.Shell; $w.Popup('PlayniteOS: Initializing Shell Logic...', 60, 'System Boot', 64)"

:: 1. Patch placeholders
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%USERPROFILE%\Playnite' -Recurse -Include *.json,*.xml,*.cfg,*.ini -ErrorAction SilentlyContinue | ForEach-Object { $content = [System.IO.File]::ReadAllText($_.FullName); if ($content.Contains('INSERTUSERNAMEHERE')) { [System.IO.File]::WriteAllText($_.FullName, $content.Replace('INSERTUSERNAMEHERE', '%USERNAME%')) } }"

:: 2. Check for config.json
if not exist "%CONFIG_FILE%" (
    :: SETUP MODE: Launch Explorer and WAIT so the session doesn't end (Prevents Grey Screen)
    echo PlayniteOS is in Setup Mode. Initializing Desktop...
    
    :: Visual indicator for Setup Mode
    powershell -ExecutionPolicy Bypass -Command "$w = New-Object -ComObject WScript.Shell; $w.Popup('First Boot Detected: Entering Setup Mode (Explorer)...', 5, 'PlayniteOS Setup', 48)"
    
    start explorer.exe
    
    :setup_loop
    timeout /t 10 /nobreak >nul
    if not exist "%CONFIG_FILE%" goto setup_loop
    exit /b
)

:: GAMER MODE: Explorer never starts.
:: Visual indicator for Gamer Mode
echo PlayniteOS: Entering Gamer Mode...

reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam" /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul
reg add "HKCU\Software\Ubisoft\Launcher" /v "InstallDir" /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul
reg add "HKCU\Software\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f >nul
reg add "HKCU\Software\Microsoft\GamingApp" /v "GameContentPath" /t REG_SZ /d "C:\Games\Xbox" /f >nul

"%PLAYNITE_DIR%\Playnite.FullscreenApp.exe"