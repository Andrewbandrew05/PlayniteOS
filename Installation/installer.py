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

# --- PLAYNITE LIBRARY PLUGIN GUIDs (built-in to Playnite 10) ---
STEAM_GUID    = "cb91dfc9-b977-43bf-8e70-55f46e410fab"
EPIC_GUID     = "91288519-6d85-46c2-a34d-cfcf9961e770"
GOG_GUID      = "aebe8b7c-6dc3-4a66-af31-e7375c6b997c"
XBOX_GUID     = "7e4fbb5e-2ae3-48d4-8ba0-6b30e7a4e287"
UBISOFT_GUID  = "c2f038e5-8b92-4877-91f1-da9094155fc5"
EA_GUID       = "85dd7072-2f20-4e76-a007-41035e390724"
BATTLENET_GUID = "e3c26a3d-d695-4cb7-a769-5ff7612c7edd"
AMAZON_GUID   = "402674cd-4af6-4886-b6ec-0e695bfa0688"

# Amazon Games Library plugin (first-party, not bundled in the Playnite zip)
AMAZON_PLUGIN_URL = "https://github.com/JosefNemec/PlayniteExtensions/releases/download/2.2/AmazonLibrary_Builtin_2_11.pext"


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

    # ===========================================================
    # [1/16] Create Global Game Silos
    # ===========================================================
    print("\n[1/16] Creating Global Game Silos...")
    for silo in [
        r"Steam\steamapps", "Epic", "GOG", "Xbox",
        "Ubisoft", "EA", "BattleNet", "Amazon", "itchio"
    ]:
        os.makedirs(fr"C:\Games\{silo}", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Configs", exist_ok=True)
    os.makedirs(GAMER_USER_ROOT, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    print("Snapshotting Default profile to DefaultUser...")
    os.makedirs(r"C:\Users\DefaultUser", exist_ok=True)
    run_cmd(
        r'robocopy "C:\Users\Default" "C:\Users\DefaultUser" /E /COPY:DAT /XJ '
        r'/XF NTUSER.DAT NTUSER.MAN ntuser.ini "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" '
        r'/NFL /NDL /NJH /NJS'
    )
    
    print("Updating winget sources...")
    run_cmd(
        "winget source update --disable-interactivity "
        "--accept-source-agreements"
    )

    print("Installing shared prerequisites (WebView2, VC++ Redist)...")
    run_cmd(
        "winget install --id Microsoft.EdgeWebView2Runtime --silent "
        "--accept-source-agreements --accept-package-agreements"
    )
    run_cmd(
        "winget install --id Microsoft.VCRedist.2015+.x64 --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [2/16] Build Playnite Master Seed in GamerUser Template
    # ===========================================================
    print("\n[2/16] Building Playnite Master Seed in GamerUser Template...")
    os.makedirs(GAMER_PLAYNITE, exist_ok=True)
    pn_zip = fr"{TEMP_DIR}\playnite.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, "r") as z:
        z.extractall(GAMER_PLAYNITE)
    open(os.path.join(GAMER_PLAYNITE, "playnite.portable"), "a").close()
    os.remove(pn_zip)

    print("  Installing Amazon Games Library plugin...")
    amazon_pext = fr"{TEMP_DIR}\amazon_plugin.pext"
    download(AMAZON_PLUGIN_URL, amazon_pext)
    amazon_ext_dir = os.path.join(GAMER_PLAYNITE, "Extensions", "AmazonLibrary_Builtin")
    os.makedirs(amazon_ext_dir, exist_ok=True)
    with zipfile.ZipFile(amazon_pext, "r") as z:
        z.extractall(amazon_ext_dir)
    os.remove(amazon_pext)

    # ===========================================================
    # [3/16] Install Steam (Per-User Template + steamapps Junction)
    # ===========================================================
    print("\n[3/16] Installing Steam into GamerUser Template...")
    steam_path  = os.path.join(GAMER_PLAYNITE, "Launchers", "Steam")
    steam_setup = fr"{TEMP_DIR}\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")

    steam_service = r"C:\Program Files (x86)\Common Files\Steam\bin\steamservice.exe"
    run_cmd(fr'"{steam_service}" /Install')

    run_cmd(
        fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' '
        fr'-ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"'
    )

    # ===========================================================
    # [4/16] Install Epic Games Launcher (Global)
    # ===========================================================
    print("\n[4/16] Installing Epic Games Launcher...")
    run_cmd(
        "winget install -e --id EpicGames.EpicGamesLauncher --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [5/16] Install GOG Galaxy (Global)
    # ===========================================================
    print("\n[5/16] Installing GOG Galaxy...")
    run_cmd(
        "winget install -e --id GOG.Galaxy --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [6/16] Install Ubisoft Connect (Global)
    # ===========================================================
    print("\n[6/16] Installing Ubisoft Connect...")
    ubi_setup = fr"{TEMP_DIR}\UbisoftConnectInstaller.exe"
    ubi_url = "https://ubistatic3-a.akamaihd.net/orbit/launcher_installer/UbisoftConnectInstaller.exe"
    download(ubi_url, ubi_setup)
    run_cmd(fr'"{ubi_setup}" /S')

    # ===========================================================
    # [7/16] Install EA App (Global)
    # ===========================================================
    print("\n[7/16] Installing EA App...")
    ea_setup = fr"{TEMP_DIR}\ea_setup.exe"
    download(EA_URL, ea_setup)
    run_cmd(fr'"{ea_setup}" /quiet /norestart')

    # ===========================================================
    # [8/16] Install Battle.net
    # ===========================================================
    print("\n[8/16] Downloading and launching Battle.net installer...")
    bnet_setup = fr"{TEMP_DIR}\Battle.net-Setup.exe"
    bnet_url = "https://www.battle.net/download/getInstallerForGame?os=win&gameProgram=BATTLENET_APP&version=Live"
    download(bnet_url, bnet_setup)
    subprocess.Popen(fr'"{bnet_setup}" --lang=enUS --installpath=C:\BattleNet')

    # ===========================================================
    # [9/16] Install Amazon Games (Global)
    # ===========================================================
    print("\n[9/16] Installing Amazon Games...")
    run_cmd(
        "winget install -e --id Amazon.Games --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [10/16] Install Xbox Gaming Services (Global)
    # ===========================================================
    print("\n[10/16] Installing Xbox Gaming Services...")
    run_cmd(
        "winget install --id Microsoft.GamingApp --silent "
        "--accept-source-agreements --accept-package-agreements"
    )
    run_cmd(
        "winget install --id Microsoft.XboxGamingOverlay --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [11/16] Install itch.io
    # ===========================================================
    print("\n[11/16] Installing itch.io...")
    run_cmd(
        "winget install -e --id ItchIo.Itch --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [12/16] Pull GitHub Assets & Seed Playnite Plugin Configs
    # ===========================================================
    print("\n[12/16] Pulling GitHub Assets & Seeding Configs...")
    repo_tmp = fr"{TEMP_DIR}\repo"
    req = urllib.request.Request(REPO_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            z.extractall(repo_tmp)

    repo_root = os.path.join(repo_tmp, "PlayniteOS-main")
    shutil.copytree(os.path.join(repo_root, "Scripts"), r"C:\PlayniteOS\Scripts", dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Core"),    r"C:\PlayniteOS\Core",    dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Configs"), r"C:\PlayniteOS\Configs", dirs_exist_ok=True)

    shutil.rmtree(repo_tmp)

    playnite_configs_src = r"C:\PlayniteOS\Configs\Playnite"
    if os.path.isdir(playnite_configs_src):
        shutil.copytree(playnite_configs_src, GAMER_PLAYNITE, dirs_exist_ok=True)
        print("  Playnite configs applied from Configs/Playnite/.")
    else:
        print("  WARNING: Configs/Playnite/ not found — skipping Playnite config seeding.")

    # ===========================================================
    # [13/16] Configure Shared Game Library Paths
    # ===========================================================
    print("\n[13/16] Configuring shared game library paths...")

    print("  Waiting 30s for installers to settle...")
    time.sleep(30)
    print("  Killing launcher processes before modifying config files...")
    
    run_cmd("sc stop EABackgroundService >nul 2>&1")
    run_cmd("sc stop EALocalHostSvc >nul 2>&1")
    time.sleep(3)
    for proc in [
        "EpicGamesLauncher.exe",
        "GalaxyClient.exe", "GalaxyClientService.exe",
        "UbisoftConnect.exe", "UplayWebCore.exe",
        "EADesktop.exe", "EABackgroundService.exe", "EALauncher.exe",
        "EALocalHostSvc.exe", "EACrashReporter.exe", "EAGEP.exe", "EAUpdater.exe",
        "Battle.net.exe", "Battle.net Helper.exe",
        "AmazonGamesUI.exe",
        "XboxPcApp.exe", "GamingServices.exe",
    ]:
        run_cmd(fr'taskkill /F /IM "{proc}" /T >nul 2>&1')
    time.sleep(5)

    epic_cfg_dir = r"C:\Users\GamerUser\AppData\Local\EpicGamesLauncher\Saved\Config\Windows"
    os.makedirs(epic_cfg_dir, exist_ok=True)
    with open(os.path.join(epic_cfg_dir, "GameUserSettings.ini"), "w") as f:
        f.write("[Launcher]\nDefaultAppInstallLocation=C:\\Games\\Epic\n")

    gog_data = r"C:\ProgramData\GOG.com\Galaxy"
    os.makedirs(gog_data, exist_ok=True)
    with open(os.path.join(gog_data, "config.json"), "w") as f:
        json.dump({
            "defaultInstallationPath": r"C:\Games\GOG",
            "runAtSystemStartup": False,
            "startMinimized": True,
        }, f, indent=2)

    ubisoft_cfg_dir = r"C:\Users\GamerUser\AppData\Local\Ubisoft Game Launcher"
    os.makedirs(ubisoft_cfg_dir, exist_ok=True)
    with open(os.path.join(ubisoft_cfg_dir, "settings.yml"), "w") as f:
        f.write("instpath: C:\\Games\\Ubisoft\\\nminimize_to_systray: true\n")

    try:
        subprocess.run(
            'powershell -NonInteractive -Command "'
            'New-Item -Path \'HKLM:\\SOFTWARE\\Electronic Arts\\EA Desktop\' -Force | Out-Null; '
            'Set-ItemProperty -Path \'HKLM:\\SOFTWARE\\Electronic Arts\\EA Desktop\' '
            '-Name InstallPath -Value \'C:\\Games\\EA\\\' -Type String -Force'
            '"',
            shell=True, capture_output=True, text=True
        )
    except subprocess.TimeoutExpired:
        print("  EA registry write timed out, skipping.")

    os.makedirs(r"C:\ProgramData\Battle.net\Agent", exist_ok=True)
    with open(r"C:\ProgramData\Battle.net\Agent\agent.db", "w") as f:
        json.dump({"game_dir": r"C:\Games\BattleNet"}, f, indent=2)

    run_cmd(
        r'reg add "HKLM\SOFTWARE\Amazon\Amazon Games App" '
        r'/v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f'
    )

    run_cmd(
        r'reg add "HKLM\SOFTWARE\Microsoft\GamingServices" '
        r'/v "GamingRootPath" /t REG_SZ /d "C:\Games\Xbox" /f'
    )

    # ===========================================================
    # [14/16] Setup Python Core & WinSW Service
    # ===========================================================
    print("\n[14/16] Setting up Python Core & Service...")
    py_tmp = fr"{TEMP_DIR}\py_core.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, "r") as z:
        z.extractall(r"C:\PlayniteOS\Core\Python")
    os.remove(py_tmp)

    pth_file = r"C:\PlayniteOS\Core\Python\python311._pth"
    with open(pth_file, "r") as f:
        content = f.read()
    with open(pth_file, "w") as f:
        f.write(content.replace("#import site", "import site"))

    download("https://bootstrap.pypa.io/get-pip.py", r"C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe -m pip install truststore fastapi uvicorn pynacl pyyaml requests")

    download(WINSW_URL, r"C:\PlayniteOS\Core\PlayniteOS-Service.exe")
    xml_content = """<service>
    <id>PlayniteOS-Core</id>
    <name>PlayniteOS Core API</name>
    <executable>C:\\PlayniteOS\\Core\\Python\\python.exe</executable>
    <arguments>-c "import truststore; truststore.inject_into_ssl(); import subprocess; subprocess.run(['C:\\PlayniteOS\\Core\\Python\\python.exe', 'C:\\PlayniteOS\\Core\\main.py'])"</arguments>
    <log mode="roll"></log>
    </service>"""
    with open(r"C:\PlayniteOS\Core\PlayniteOS-Service.xml", "w") as f:
        f.write(xml_content)
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe install")
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe start")

    # ===========================================================
    # [15/16] Create BootOS Shell Scripts & Registry Lockdown
    # ===========================================================
    print("\n[15/16] Creating BootOS Shell Scripts...")

    boot_cmd_content = r"""@echo off
:: ---------------------------------------------------------------
:: BootOS - PlayniteOS Universal Launcher Shell
:: ---------------------------------------------------------------

:: 1. Prime per-user registry keys
reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam" /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul
reg add "HKCU\Software\Ubisoft\Launcher" /v "InstallDir" /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul
reg add "HKCU\Software\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f >nul
reg add "HKCU\Software\Microsoft\GamingApp" /v "GameContentPath" /t REG_SZ /d "C:\Games\Xbox" /f >nul

:: 2. Wait for Explorer to finish drawing the Taskbar (CRITICAL FIX)
timeout /t 4 /nobreak >nul

:: 3. THE PHANTOM EXPLORER HACK (Hide Taskbar)
powershell -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class TB { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string c, string w); [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int c); public static void Hide(){ ShowWindow(FindWindow(\"Shell_TrayWnd\", null), 0); } }'; [TB]::Hide()"

:: 4. Launch Playnite Fullscreen
"%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"

:: 5. Restore the Taskbar on exit
powershell -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -Command "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class TB { [DllImport(\"user32.dll\")] public static extern IntPtr FindWindow(string c, string w); [DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int c); public static void Show(){ ShowWindow(FindWindow(\"Shell_TrayWnd\", null), 5); } }'; [TB]::Show()"
"""
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.cmd"), "w") as f:
        f.write(boot_cmd_content)

    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\r\n'
        'WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%")'
        ' & "\\Playnite\\BootOS.cmd""", 0, True\r\n'
    )
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.vbs"), "w") as f:
        f.write(vbs_content)

    startup_dir = os.path.join(
        GAMER_USER_ROOT,
        r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
    )
    os.makedirs(startup_dir, exist_ok=True)
    shutil.copy2(
        os.path.join(GAMER_PLAYNITE, "BootOS.vbs"),
        os.path.join(startup_dir, "BootOS.vbs")
    )

    run_cmd(
        r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" '
        r'/v "EnumerateLocalUsersOnDomainJoinedComputers" /t REG_DWORD /d 1 /f'
    )

    # ===========================================================
    # [16/16] Finalize Permissions & Firewall
    # ===========================================================
    print("\n[16/16] Finalizing Permissions...")
    
    print("  Disabling conflicting bloatware (Nahimic / ASUS OSD)...")
    run_cmd('sc config "NahimicService" start= disabled >nul 2>&1')
    run_cmd('net stop "NahimicService" /y >nul 2>&1')
    run_cmd('sc config "SS3Svc32" start= disabled >nul 2>&1')
    run_cmd('sc config "SS3Svc64" start= disabled >nul 2>&1')

    run_cmd(r'icacls "C:\Games"     /grant "Users:(OI)(CI)F"  /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd(
        'powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' '
        '-Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"'
    )

    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    print("\n--- INSTALLATION COMPLETE! Rebooting in 15 seconds... ---")
    run_cmd("shutdown /r /t 15 /c \"PlayniteOS installation complete. Rebooting...\"")


if __name__ == "__main__":
    main()