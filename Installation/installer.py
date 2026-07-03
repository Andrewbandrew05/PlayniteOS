import os
import subprocess
import urllib.request
import zipfile
import shutil
import io
import json
import time

# --- ENFORCE NATIVE WINDOWS TRUST STORE ---
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# --- CONFIGURATION ---
REPO_ZIP_URL    = "https://github.com/Andrewbandrew05/PlayniteOS/archive/refs/heads/main.zip"
PLAYNITE_URL    = "https://github.com/JosefNemec/Playnite/releases/download/10.31/Playnite1031.zip"
STEAM_URL       = "https://cdn.akamai.steamstatic.com/client/installer/SteamSetup.exe"
EA_URL          = "https://origin-a.akamaihd.net/EA-Desktop-Client-Download/installer-releases/EAappInstaller.exe"
WINSW_URL       = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip"

def run_cmd(cmd):
    print(f" > {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def download(url, dest):
    print(f"Downloading: {url}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(dest, "wb") as out_file:
        shutil.copyfileobj(response, out_file)

def main():
    print("==========================================")
    print("  PlayniteOS Mark 2.0: True Console Mode  ")
    print("==========================================")

    DEFAULT_ROOT     = r"C:\Users\Default"
    DEFAULT_PLAYNITE = r"C:\Users\Default\Playnite"
    TEMP_DIR         = r"C:\PlayniteOS\tmp"

    # ===========================================================
    # [1/17] Create Global Game Silos
    # ===========================================================
    print("\n[1/17] Creating Global Game Silos...")
    for silo in [r"Steam\steamapps", "Epic", "GOG", "Xbox", "Ubisoft", "EA", "BattleNet", "Amazon", "itchio"]:
        os.makedirs(fr"C:\Games\{silo}", exist_ok=True)
    
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    run_cmd("winget source update --disable-interactivity --accept-source-agreements")
    run_cmd("winget install --id Microsoft.EdgeWebView2Runtime --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install --id Microsoft.VCRedist.2015+.x64 --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [2/17] Build Playnite Master Seed
    # ===========================================================
    print("\n[2/17] Building Playnite in Default Profile...")
    os.makedirs(DEFAULT_PLAYNITE, exist_ok=True)
    pn_zip = fr"{TEMP_DIR}\playnite.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, "r") as z:
        z.extractall(DEFAULT_PLAYNITE)
    open(os.path.join(DEFAULT_PLAYNITE, "playnite.portable"), "a").close()

    # ===========================================================
    # [3/17] Install Steam (Directly into Default Profile)
    # ===========================================================
    print("\n[3/17] Installing Steam into Default Profile...")
    steam_path  = os.path.join(DEFAULT_PLAYNITE, "Launchers", "Steam")
    steam_setup = fr"{TEMP_DIR}\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")
    run_cmd(fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' -ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"')

    # ===========================================================
    # [4-11/17] Install Launchers (Global)
    # ===========================================================
    print("\n[4-11/17] Installing Global Launchers...")
    run_cmd("winget install -e --id EpicGames.EpicGamesLauncher --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install -e --id GOG.Galaxy --silent --accept-source-agreements --accept-package-agreements")
    
    ubi_setup = fr"{TEMP_DIR}\UbisoftConnectInstaller.exe"
    download("https://ubistatic3-a.akamaihd.net/orbit/launcher_installer/UbisoftConnectInstaller.exe", ubi_setup)
    run_cmd(fr'"{ubi_setup}" /S')

    ea_setup = fr"{TEMP_DIR}\ea_setup.exe"
    download(EA_URL, ea_setup)
    run_cmd(fr'"{ea_setup}" /quiet /norestart')

    bnet_setup = fr"{TEMP_DIR}\Battle.net-Setup.exe"
    download("https://www.battle.net/download/getInstallerForGame?os=win&gameProgram=BATTLENET_APP&version=Live", bnet_setup)
    subprocess.Popen(fr'"{bnet_setup}" --lang=enUS --installpath=C:\BattleNet')

    run_cmd("winget install -e --id Amazon.Games --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install --id Microsoft.GamingApp --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install -e --id ItchIo.Itch --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [12/17] Pull GitHub Assets
    # ===========================================================
    print("\n[12/17] Pulling GitHub Assets...")
    repo_tmp = fr"{TEMP_DIR}\repo"
    req = urllib.request.Request(REPO_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            z.extractall(repo_tmp)

    repo_root = os.path.join(repo_tmp, "PlayniteOS-main")
    for folder in ["Scripts", "Core"]:
        src_path = os.path.join(repo_root, folder)
        if os.path.exists(src_path):
            shutil.copytree(src_path, fr"C:\PlayniteOS\{folder}", dirs_exist_ok=True)

    # ===========================================================
    # [13/17] Configure Shared Game Library Paths
    # ===========================================================
    print("\n[13/17] Configuring shared game library paths...")
    time.sleep(30) 
    run_cmd("sc stop EABackgroundService >nul 2>&1")
    for proc in ["EpicGamesLauncher.exe", "GalaxyClient.exe", "UbisoftConnect.exe", "EADesktop.exe", "Battle.net.exe", "AmazonGamesUI.exe"]:
        run_cmd(fr'taskkill /F /IM "{proc}" /T >nul 2>&1')

    epic_cfg = os.path.join(DEFAULT_ROOT, r"AppData\Local\EpicGamesLauncher\Saved\Config\Windows")
    os.makedirs(epic_cfg, exist_ok=True)
    with open(os.path.join(epic_cfg, "GameUserSettings.ini"), "w") as f:
        f.write("[Launcher]\nDefaultAppInstallLocation=C:\\Games\\Epic\n")

    ubi_cfg = os.path.join(DEFAULT_ROOT, r"AppData\Local\Ubisoft Game Launcher")
    os.makedirs(ubi_cfg, exist_ok=True)
    with open(os.path.join(ubi_cfg, "settings.yml"), "w") as f:
        f.write("instpath: C:\\Games\\Ubisoft\\\nminimize_to_systray: true\n")

    run_cmd(r'reg add "HKLM\SOFTWARE\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f')
    run_cmd(r'reg add "HKLM\SOFTWARE\Microsoft\GamingServices" /v "GamingRootPath" /t REG_SZ /d "C:\Games\Xbox" /f')

    # ===========================================================
    # [14/17] Setup Python Core & WinSW Service
    # ===========================================================
    print("\n[14/17] Setting up Python Core & Service...")
    py_tmp = fr"{TEMP_DIR}\py_core.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, "r") as z:
        z.extractall(r"C:\PlayniteOS\Core\Python")
    
    pth_file = r"C:\PlayniteOS\Core\Python\python311._pth"
    with open(pth_file, "w") as f: f.write("python311.zip\n.\nimport site\n")

    download("https://bootstrap.pypa.io/get-pip.py", r"C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe -m pip install truststore fastapi uvicorn pynacl pyyaml requests")

    download(WINSW_URL, r"C:\PlayniteOS\Core\PlayniteOS-Service.exe")
    xml_content = """<service><id>PlayniteOS-Core</id><name>PlayniteOS Core API</name><executable>C:\\PlayniteOS\\Core\\Python\\python.exe</executable><arguments>-c "import truststore; truststore.inject_into_ssl(); import subprocess; subprocess.run(['C:\\PlayniteOS\\Core\\Python\\python.exe', 'C:\\PlayniteOS\\Core\\main.py'])"</arguments><log mode="roll"></log></service>"""
    with open(r"C:\PlayniteOS\Core\PlayniteOS-Service.xml", "w") as f: f.write(xml_content)
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe install")
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe start")

    # ===========================================================
    # [15/17] Lockdown & Shell Replacement
    # ===========================================================
    print("\n[15/17] Replacing Windows Shell in Default Profile...")
    default_hive = os.path.join(DEFAULT_ROOT, "NTUSER.DAT")
    run_cmd(f'reg load HKU\DefaultTemplate "{default_hive}"')
    run_cmd('reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "Wallpaper" /t REG_SZ /d "" /f')
    run_cmd('reg add "HKU\DefaultTemplate\Control Panel\Colors" /v "Background" /t REG_SZ /d "0 0 0" /f')
    run_cmd('reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "HideIcons" /t REG_DWORD /d 1 /f')
    run_cmd('reg add "HKU\DefaultTemplate\Keyboard Layout" /v "Scancode Map" /t REG_BINARY /d 00000000000000000300000000005BE000005CE000000000 /f')
    shell_cmd = r'wscript.exe //B "%USERPROFILE%\Playnite\BootOS.vbs"'
    run_cmd(f'reg add "HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" /v "Shell" /t REG_SZ /d "{shell_cmd}" /f')
    run_cmd('reg unload HKU\DefaultTemplate')

    # ===========================================================
    # [16/17] Create BootOS Shell Scripts
    # ===========================================================
    print("\n[16/17] Creating BootOS Shell Scripts...")
    boot_cmd_content = r"""@echo off
set "PLAYNITE_DIR=%USERPROFILE%\Playnite"
set "CONFIG_FILE=%PLAYNITE_DIR%\config.json"
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%USERPROFILE%\Playnite' -Recurse -Include *.json,*.xml,*.cfg,*.ini -ErrorAction SilentlyContinue | ForEach-Object { $content = [System.IO.File]::ReadAllText($_.FullName); if ($content.Contains('INSERTUSERNAMEHERE')) { [System.IO.File]::WriteAllText($_.FullName, $content.Replace('INSERTUSERNAMEHERE', '%USERNAME%')) } }"
if not exist "%CONFIG_FILE%" (
    start explorer.exe
    exit /b
)
reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam" /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul
reg add "HKCU\Software\Ubisoft\Launcher" /v "InstallDir" /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul
reg add "HKCU\Software\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f >nul
reg add "HKCU\Software\Microsoft\GamingApp" /v "GameContentPath" /t REG_SZ /d "C:\Games\Xbox" /f >nul
"%PLAYNITE_DIR%\Playnite.FullscreenApp.exe"
"""
    with open(os.path.join(DEFAULT_PLAYNITE, "BootOS.cmd"), "w") as f: f.write(boot_cmd_content)
    vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\r\nWshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\\Playnite\\BootOS.cmd""", 0, True\r\n'
    with open(os.path.join(DEFAULT_PLAYNITE, "BootOS.vbs"), "w") as f: f.write(vbs_content)
    setup_cmd_content = r"""@echo off
if exist "%USERPROFILE%\Playnite\config.json" exit /b
powershell -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('Welcome to PlayniteOS Setup!`n`nPlease sign into your launchers and configure Playnite.`n`nWhen finished, REBOOT to enter Console Mode.', 'PlayniteOS')"
start "" "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe"
start "" "%USERPROFILE%\Playnite\Playnite.DesktopApp.exe"
"""
    startup_dir = os.path.join(DEFAULT_ROOT, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")
    os.makedirs(startup_dir, exist_ok=True)
    with open(os.path.join(startup_dir, "Setup.cmd"), "w") as f: f.write(setup_cmd_content)

    # ===========================================================
    # [17/17] Create Desktop Updater (Shortcut)
    # ===========================================================
    print("\n[17/17] Creating Desktop Updater...")
    
    update_ps1_content = r"""# PlayniteOS Universal Updater
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}
Write-Host "Stopping services and cleaning system..." -ForegroundColor Cyan
sc.exe stop "PlayniteOS-Core" > $null 2>&1
taskkill /F /IM "Playnite*" /T > $null 2>&1
taskkill /F /IM "python.exe" /T > $null 2>&1

& reg load HKU\DefaultTemplate "C:\Users\Default\NTUSER.DAT" > $null 2>&1
& reg add "HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" /v "Shell" /t REG_SZ /d "explorer.exe" /f > $null 2>&1
& reg unload HKU\DefaultTemplate > $null 2>&1

Remove-Item -Recurse -Force "C:\PlayniteOS" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "C:\Users\Default\Playnite" -ErrorAction SilentlyContinue

Write-Host "Downloading fresh installer..." -ForegroundColor Green
$Url = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main/installer.py"
$Dest = "$env:TEMP\installer.py"
Invoke-WebRequest -Uri $Url -OutFile $Dest
python $Dest
"""
    update_script_path = r"C:\Users\Public\PlayniteOS-Update.ps1"
    with open(update_script_path, "w") as f: f.write(update_ps1_content)

    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop, "Update PlayniteOS.lnk")
    icon_path = r"C:\Windows\System32\shell32.dll,238"
    
    # Fixed VBScript generation using Chr(34) to avoid triple-quote termination errors
    vbs_script = f"""
Set WshShell = WScript.CreateObject("WScript.Shell")
Set oShellLink = WshShell.CreateShortcut("{shortcut_path}")
oShellLink.TargetPath = "powershell.exe"
oShellLink.Arguments = "-NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & "{update_script_path}" & Chr(34)
oShellLink.WindowStyle = 1
oShellLink.IconLocation = "{icon_path}"
oShellLink.Description = "Update PlayniteOS to the latest version"
oShellLink.WorkingDirectory = "C:\\"
oShellLink.Save
"""
    vbs_temp = os.path.join(TEMP_DIR, "create_shortcut.vbs")
    with open(vbs_temp, "w") as f: f.write(vbs_script)
    run_cmd(f"wscript.exe {vbs_temp}")

    # Finalize Bloatware & Reboot
    run_cmd('sc config "NahimicService" start= disabled >nul 2>&1')
    run_cmd('net stop "NahimicService" /y >nul 2>&1')
    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd('powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"')

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\n--- INSTALLATION COMPLETE! Rebooting in 15 seconds... ---")
    run_cmd("shutdown /r /t 15 /c \"PlayniteOS installation complete. Rebooting...\"")

if __name__ == "__main__":
    main()