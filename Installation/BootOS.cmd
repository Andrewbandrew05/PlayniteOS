@echo off
set "PLAYNITE_DIR=%USERPROFILE%\Playnite"
set "CONFIG_FILE=%PLAYNITE_DIR%\config.json"

:: GAMER MODE: Explorer never starts.
:: Visual indicator for Gamer Mode
echo PlayniteOS: Entering Gamer Mode...

reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam" /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul
reg add "HKCU\Software\Ubisoft\Launcher" /v "InstallDir" /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul
reg add "HKCU\Software\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f >nul
reg add "HKCU\Software\Microsoft\GamingApp" /v "GameContentPath" /t REG_SZ /d "C:\Games\Xbox" /f >nul

"%PLAYNITE_DIR%\Playnite.FullscreenApp.exe"