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
    print("  PlayniteOS Mark 2.0: Universal Launcher ")
    print("==========================================")

    GAMER_USER_ROOT  = r"C:\Users\GamerUser"
    GAMER_PLAYNITE   = r"C:\Users\GamerUser\Playnite"
    TEMP_DIR         = r"C:\PlayniteOS\tmp"
    GAMER_MASTER     = r"C:\PlayniteOS\GamerMaster"

    # ===========================================================
    # [1/17] Create Global Game Silos
    # ===========================================================
    print("\n[1/17] Creating Global Game Silos...")
    # Removed Humble from silos as the app is discontinued
    for silo in [
        r"Steam\steamapps", "Epic", "GOG", "Xbox",
        "Ubisoft", "EA", "BattleNet", "Amazon", "itchio"
    ]:
        os.makedirs(fr"C:\Games\{silo}", exist_ok=True)
    
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Configs", exist_ok=True)
    os.makedirs(GAMER_MASTER, exist_ok=True)
    os.makedirs(GAMER_USER_ROOT, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Snapshot Default for Standard User restoration
    print("Snapshotting Default profile to DefaultUser...")
    os.makedirs(r"C:\Users\DefaultUser", exist_ok=True)
    run_cmd(
        r'robocopy "C:\Users\Default" "C:\Users\DefaultUser" /E /COPY:DAT /XJ '
        r'/XF NTUSER.DAT NTUSER.MAN ntuser.ini "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" '
        r'/NFL /NDL /NJH /NJS'
    )

    print("Updating winget sources...")
    run_cmd("winget source update --disable-interactivity --accept-source-agreements")

    print("Installing shared prerequisites (WebView2, VC++ Redist)...")
    run_cmd("winget install --id Microsoft.EdgeWebView2Runtime --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install --id Microsoft.VCRedist.2015+.x64 --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [2/17] Build Playnite Master Seed
    # ===========================================================
    print("\n[2/17] Building Playnite Master Seed...")
    os.makedirs(GAMER_PLAYNITE, exist_ok=True)
    pn_zip = fr"{TEMP_DIR}\playnite.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, "r") as z:
        z.extractall(GAMER_PLAYNITE)
    open(os.path.join(GAMER_PLAYNITE, "playnite.portable"), "a").close()

    # ===========================================================
    # [3/17] Install Steam (Per-User Template)
    # ===========================================================
    print("\n[3/17] Installing Steam into GamerUser Template...")
    steam_path  = os.path.join(GAMER_PLAYNITE, "Launchers", "Steam")
    steam_setup = fr"{TEMP_DIR}\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")
    run_cmd(fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' -ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"')

    # ===========================================================
    # [4/17] Install Epic (Global)
    # ===========================================================
    print("\n[4/17] Installing Epic Games Launcher...")
    run_cmd("winget install -e --id EpicGames.EpicGamesLauncher --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [5/17] Install GOG (Global)
    # ===========================================================
    print("\n[5/17] Installing GOG Galaxy...")
    run_cmd("winget install -e --id GOG.Galaxy --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [6/17] Install Ubisoft (Direct Download - Hash Fix)
    # ===========================================================
    print("\n[6/17] Installing Ubisoft Connect...")
    ubi_setup = fr"{TEMP_DIR}\UbisoftConnectInstaller.exe"
    download("https://ubistatic3-a.akamaihd.net/orbit/launcher_installer/UbisoftConnectInstaller.exe", ubi_setup)
    run_cmd(fr'"{ubi_setup}" /S')

    # ===========================================================
    # [7/17] Install EA App (Global)
    # ===========================================================
    print("\n[7/17] Installing EA App...")
    ea_setup = fr"{TEMP_DIR}\ea_setup.exe"
    download(EA_URL, ea_setup)
    run_cmd(fr'"{ea_setup}" /quiet /norestart')

    # ===========================================================
    # [8/17] Install Battle.net (Direct Download - Async)
    # ===========================================================
    print("\n[8/17] Launching Battle.net installer in background...")
    bnet_setup = fr"{TEMP_DIR}\Battle.net-Setup.exe"
    download("https://www.battle.net/download/getInstallerForGame?os=win&gameProgram=BATTLENET_APP&version=Live", bnet_setup)
    subprocess.Popen(fr'"{bnet_setup}" --lang=enUS --installpath=C:\BattleNet')

    # ===========================================================
    # [9/17] Install Amazon Games (Global)
    # ===========================================================
    print("\n[9/17] Installing Amazon Games...")
    run_cmd("winget install -e --id Amazon.Games --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [10/17] Install Xbox (Global)
    # ===========================================================
    print("\n[10/17] Installing Xbox Gaming Services...")
    run_cmd("winget install --id Microsoft.GamingApp --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [11/17] Install itch.io (Correct ID)
    # ===========================================================
    print("\n[11/17] Installing itch.io...")
    run_cmd("winget install -e --id ItchIo.Itch --silent --accept-source-agreements --accept-package-agreements")

    # ===========================================================
    # [12/17] Pull GitHub Assets & Seed Configs
    # ===========================================================
    print("\n[12/17] Pulling GitHub Assets & Seeding Configs...")
    repo_tmp = fr"{TEMP_DIR}\repo"
    req = urllib.request.Request(REPO_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            z.extractall(repo_tmp)

    repo_root = os.path.join(repo_tmp, "PlayniteOS-main")
    for folder in ["Scripts", "Core", "Configs"]:
        shutil.copytree(os.path.join(repo_root, folder), fr"C:\PlayniteOS\{folder}", dirs_exist_ok=True)

    playnite_configs_src = r"C:\PlayniteOS\Configs\Playnite"
    if os.path.isdir(playnite_configs_src):
        shutil.copytree(playnite_configs_src, GAMER_PLAYNITE, dirs_exist_ok=True)

    # ===========================================================
    # [13/17] Configure Shared Game Library Paths
    # ===========================================================
    print("\n[13/17] Configuring shared game library paths...")
    time.sleep(30) # Wait for Battle.net/EA to settle
    
    run_cmd("sc stop EABackgroundService >nul 2>&1")
    for proc in ["EpicGamesLauncher.exe", "GalaxyClient.exe", "UbisoftConnect.exe", "EADesktop.exe", "Battle.net.exe", "AmazonGamesUI.exe"]:
        run_cmd(fr'taskkill /F /IM "{proc}" /T >nul 2>&1')

    # Epic
    epic_cfg = r"C:\Users\GamerUser\AppData\Local\EpicGamesLauncher\Saved\Config\Windows"
    os.makedirs(epic_cfg, exist_ok=True)
    with open(os.path.join(epic_cfg, "GameUserSettings.ini"), "w") as f:
        f.write("[Launcher]\nDefaultAppInstallLocation=C:\\Games\\Epic\n")

    # GOG
    gog_data = r"C:\ProgramData\GOG.com\Galaxy"
    os.makedirs(gog_data, exist_ok=True)
    with open(os.path.join(gog_data, "config.json"), "w") as f:
        json.dump({"defaultInstallationPath": r"C:\Games\GOG", "runAtSystemStartup": False, "startMinimized": True}, f)

    # Ubisoft
    ubi_cfg = r"C:\Users\GamerUser\AppData\Local\Ubisoft Game Launcher"
    os.makedirs(ubi_cfg, exist_ok=True)
    with open(os.path.join(ubi_cfg, "settings.yml"), "w") as f:
        f.write("instpath: C:\\Games\\Ubisoft\\\nminimize_to_systray: true\n")

    # Battle.net
    os.makedirs(r"C:\ProgramData\Battle.net\Agent", exist_ok=True)
    with open(r"C:\ProgramData\Battle.net\Agent\agent.db", "w") as f:
        json.dump({"game_dir": r"C:\Games\BattleNet"}, f)

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
    # [15/17] Create Anti-Duplicate Gamer Master Template
    # ===========================================================
    print("\n[15/17] Creating Locked Gamer Master Template...")
    # Copy clean hive
    run_cmd(f'copy /y "C:\\Users\\Default\\NTUSER.DAT" "{GAMER_MASTER}\\NTUSER.DAT"')
    
    # Mount and Lockdown
    run_cmd(f'reg load HKU\\GamerMaster "{GAMER_MASTER}\\NTUSER.DAT"')
    
    # Black Background & Policies
    run_cmd('reg add "HKU\\GamerMaster\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" /v "Wallpaper" /t REG_SZ /d "" /f')
    run_cmd('reg add "HKU\\GamerMaster\\Control Panel\\Colors" /v "Background" /t REG_SZ /d "0 0 0" /f')
    
    # Hide Icons & Taskbar interaction
    run_cmd('reg add "HKU\\GamerMaster\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced" /v "HideIcons" /t REG_DWORD /d 1 /f')
    run_cmd('reg add "HKU\\GamerMaster\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoSetTaskbar" /t REG_DWORD /d 1 /f')
    run_cmd('reg add "HKU\\GamerMaster\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer" /v "NoTrayItemsDisplay" /t REG_DWORD /d 1 /f')
    
    # Disable Windows Keys (Scancode Map)
    run_cmd('reg add "HKU\\GamerMaster\\Keyboard Layout" /v "Scancode Map" /t REG_BINARY /d 00000000000000000300000000005BE000005CE000000000 /f')
    
    run_cmd('reg unload HKU\\GamerMaster')

    # ===========================================================
    # [16/17] Create BootOS Shell Scripts (Phantom Explorer)
    # ===========================================================
    print("\n[16/17] Creating BootOS Shell Scripts...")
    boot_cmd_content = r"""@echo off
:: 1. Prime Launcher Paths
reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam" /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul
reg add "HKCU\Software\Ubisoft\Launcher" /v "InstallDir" /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul
reg add "HKCU\Software\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f >nul
reg add "HKCU\Software\Microsoft\GamingApp" /v "GameContentPath" /t REG_SZ /d "C:\Games\Xbox" /f >nul

:: 2. SMART TASKBAR HIDE (Zero-Gap Fix)
powershell -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command "$h=0; while($h -eq 0){ $h=[int](Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class TB { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string c, string w); }' -PassThru)::FindWindow(\"Shell_TrayWnd\",$null); Start-Sleep -m 50 }; Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class TB { [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int c); }'; [TB]::ShowWindow($h, 0)"

:: 3. Launch Playnite Fullscreen
"%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"

:: 4. Restore Taskbar on exit
powershell -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class TB { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string c, string w); [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int c); public static void Show(){ ShowWindow(FindWindow(\"Shell_TrayWnd\", null), 5); } }'; [TB]::Show()"
"""
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.cmd"), "w") as f: f.write(boot_cmd_content)

    vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\r\nWshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\\Playnite\\BootOS.cmd""", 0, True\r\n'
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.vbs"), "w") as f: f.write(vbs_content)

    startup_dir = os.path.join(GAMER_USER_ROOT, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")
    os.makedirs(startup_dir, exist_ok=True)
    shutil.copy2(os.path.join(GAMER_PLAYNITE, "BootOS.vbs"), os.path.join(startup_dir, "BootOS.vbs"))

    # ===========================================================
    # [17/17] Finalize Permissions & Bloatware
    # ===========================================================
    print("\n[17/17] Finalizing Permissions & Disabling Bloatware...")
    run_cmd('sc config "NahimicService" start= disabled >nul 2>&1')
    run_cmd('net stop "NahimicService" /y >nul 2>&1')
    run_cmd('sc config "SS3Svc32" start= disabled >nul 2>&1')
    run_cmd('sc config "SS3Svc64" start= disabled >nul 2>&1')

    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd('powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"')

    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\n--- INSTALLATION COMPLETE! Rebooting in 15 seconds... ---")
    run_cmd("shutdown /r /t 15 /c \"PlayniteOS installation complete. Rebooting...\"")

if __name__ == "__main__":
    main()