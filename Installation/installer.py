import os
import subprocess
import urllib.request
import zipfile
import shutil
import io
import json

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
EPIC_URL        = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi"
UBISOFT_URL     = "https://static3.cdn.ubi.com/orbit/launcher_installer/UbisoftConnectInstaller.exe"
EA_URL          = "https://origin-a.akamaihd.net/EA-Desktop-Client-Download/installer-releases/EAappInstaller.exe"
BATTLENET_URL   = "https://downloader.battle.net/download/getInstaller?os=win&installer=Battle.net-Setup.exe"
AMAZON_URL      = "https://download.amazongames.com/AmazonGamesSetup.exe"
WINSW_URL       = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip"

# --- PLAYNITE LIBRARY PLUGIN GUIDs (built-in to Playnite 10) ---
# Amazon Games requires the community "Amazon Games Library" plugin installed separately.
STEAM_GUID    = "cb91dfc9-b977-43bf-8e70-55f46e410fab"
EPIC_GUID     = "91288519-6d85-46c2-a34d-cfcf9961e770"
GOG_GUID      = "aebe8b7c-6dc3-4a66-af31-e7375c6b997c"
XBOX_GUID     = "7e4fbb5e-2ae3-48d4-8ba0-6b30e7a4e287"
UBISOFT_GUID  = "c2f038e5-8b92-4877-91f1-da9094155fc5"
EA_GUID       = "85dd7072-2f20-4e76-a007-41035e390724"
BATTLENET_GUID = "e3c26a3d-d695-4cb7-a769-5ff7612c7edd"
AMAZON_GUID   = "44cf0b92-6200-4a0c-86e5-4f1f6f0d0a9e"  # community plugin


def run_cmd(cmd):
    print(f" > {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def download(url, dest):
    print(f"Downloading: {url}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response, open(dest, "wb") as out_file:
        shutil.copyfileobj(response, out_file)


def seed_playnite_config(playnite_base, plugin_guid, config_dict):
    """Write a Playnite library plugin config into the Default User template."""
    conf_path = os.path.join(playnite_base, "ExtensionsData", plugin_guid, "config.json")
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    with open(conf_path, "w") as f:
        json.dump(config_dict, f, indent=2)


def main():
    print("==========================================")
    print("  PlayniteOS Mark 2.0: Universal Launcher ")
    print("==========================================")

    GAMER_USER_ROOT  = r"C:\Users\GamerUser"
    GAMER_PLAYNITE   = r"C:\Users\GamerUser\Playnite"
    TEMP_DIR         = r"C:\PlayniteOS\tmp"

    # ===========================================================
    # [1/15] Create Global Game Silos
    # ===========================================================
    print("\n[1/15] Creating Global Game Silos...")
    for silo in [
        r"Steam\steamapps", "Epic", "GOG", "Xbox",
        "Ubisoft", "EA", "BattleNet", "Amazon",
    ]:
        os.makedirs(fr"C:\Games\{silo}", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Configs", exist_ok=True)
    os.makedirs(GAMER_USER_ROOT, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Pre-install shared system prerequisites required by multiple launchers.
    # GOG Galaxy 2.0, EA App, and Xbox all need WebView2; GOG Galaxy and others
    # need VC++ 2015-2022.  Installing here ensures they're present before any
    # launcher installer runs, even in --silent mode which skips bundled deps.
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
    # [2/15] Build Playnite Master Seed in GamerUser Template
    # ===========================================================
    print("\n[2/15] Building Playnite Master Seed in GamerUser Template...")
    os.makedirs(GAMER_PLAYNITE, exist_ok=True)
    pn_zip = fr"{TEMP_DIR}\playnite.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, "r") as z:
        z.extractall(GAMER_PLAYNITE)
    open(os.path.join(GAMER_PLAYNITE, "playnite.portable"), "a").close()
    os.remove(pn_zip)

    # ===========================================================
    # [3/15] Install Steam (Per-User Template + steamapps Junction)
    # ===========================================================
    print("\n[3/15] Installing Steam into GamerUser Template...")
    steam_path  = os.path.join(GAMER_PLAYNITE, "Launchers", "Steam")
    steam_setup = fr"{TEMP_DIR}\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")

    # Steam Client Service runs machine-wide as SYSTEM (handles game auth)
    steam_service = r"C:\Program Files (x86)\Common Files\Steam\bin\steamservice.exe"
    run_cmd(fr'"{steam_service}" /Install')

    # Junction: every user's per-user steamapps folder points at the shared silo.
    # Steam login/cloud saves stay per-user in %USERPROFILE%\Playnite\Launchers\Steam\userdata\
    run_cmd(
        fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' '
        fr'-ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"'
    )

    # ===========================================================
    # [4/15] Install Epic Games Launcher (Global)
    # ===========================================================
    print("\n[4/15] Installing Epic Games Launcher...")
    epic_setup = fr"{TEMP_DIR}\epic_setup.msi"
    download(EPIC_URL, epic_setup)
    run_cmd(f"msiexec /i {epic_setup} /qn /norestart")

    # ===========================================================
    # [5/15] Install GOG Galaxy (Global)
    # ===========================================================
    print("\n[5/15] Installing GOG Galaxy...")
    run_cmd(
        "winget install -e --id GOG.Galaxy --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [6/15] Install Ubisoft Connect (Global)
    # ===========================================================
    print("\n[6/15] Installing Ubisoft Connect...")
    ubisoft_setup = fr"{TEMP_DIR}\ubisoft_setup.exe"
    download(UBISOFT_URL, ubisoft_setup)
    run_cmd(fr'"{ubisoft_setup}" /S')

    # ===========================================================
    # [7/15] Install EA App (Global)
    # ===========================================================
    print("\n[7/15] Installing EA App...")
    ea_setup = fr"{TEMP_DIR}\ea_setup.exe"
    download(EA_URL, ea_setup)
    run_cmd(fr'"{ea_setup}" --quiet --norestart')

    # ===========================================================
    # [8/15] Install Battle.net (Global)
    # ===========================================================
    print("\n[8/15] Installing Battle.net...")
    bnet_setup = fr"{TEMP_DIR}\bnet_setup.exe"
    download(BATTLENET_URL, bnet_setup)
    run_cmd(fr'"{bnet_setup}" --lang=enUS --installpath="C:\Program Files (x86)\Battle.net"')

    # ===========================================================
    # [9/15] Install Amazon Games (Global)
    # ===========================================================
    print("\n[9/15] Installing Amazon Games...")
    amazon_setup = fr"{TEMP_DIR}\amazon_setup.exe"
    download(AMAZON_URL, amazon_setup)
    run_cmd(fr'"{amazon_setup}" /S')

    # ===========================================================
    # [10/15] Install Xbox Gaming Services (Global, via winget)
    # ===========================================================
    print("\n[10/15] Installing Xbox Gaming Services...")
    run_cmd(
        "winget install --id Microsoft.GamingApp --silent "
        "--accept-source-agreements --accept-package-agreements"
    )
    run_cmd(
        "winget install --id Microsoft.XboxGamingOverlay --silent "
        "--accept-source-agreements --accept-package-agreements"
    )

    # ===========================================================
    # [11/15] Pull GitHub Assets & Seed Playnite Plugin Configs
    # ===========================================================
    print("\n[11/15] Pulling GitHub Assets & Seeding Configs...")
    repo_tmp = fr"{TEMP_DIR}\repo"
    req = urllib.request.Request(REPO_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z:
            z.extractall(repo_tmp)

    repo_root = os.path.join(repo_tmp, "PlayniteOS-main")
    shutil.copytree(os.path.join(repo_root, "Scripts"), r"C:\PlayniteOS\Scripts", dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Core"),    r"C:\PlayniteOS\Core",    dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Configs"), r"C:\PlayniteOS\Configs", dirs_exist_ok=True)

    # Load the GamerUser registry config now so it's ready for the lockdown step.
    with open(r"C:\PlayniteOS\Configs\GamerUserRegistry.json") as f:
        gamer_reg = json.load(f)

    shutil.rmtree(repo_tmp)

    # Steam: per-user install, relative path from Playnite root.
    # Login tokens & cloud saves live in each user's %USERPROFILE%\Playnite\Launchers\Steam\userdata\
    seed_playnite_config(GAMER_PLAYNITE, STEAM_GUID, {
        "UseCustomSteamInstallationPath": True,
        "CustomSteamInstallationPath": "..\\..\\Launchers\\Steam",
        "ImportInstalledGames": True,
        "ImportUninstalledGames": True,
        "StartSteamClickAction": 1,
        "SteamQuietLaunch": True,
    })

    # Epic: global install; per-user login stored in %LOCALAPPDATA%\EpicGamesLauncher\
    seed_playnite_config(GAMER_PLAYNITE, EPIC_GUID, {
        "UseCustomLauncherPath": True,
        "CustomLauncherPath": r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        "LauncherArguments": "-SkipBuildPatchPrereq",
        "ImportInstalledGames": True,
        "ImportUninstalledGames": True,
    })

    # Remaining launchers are global installs auto-detected via registry.
    # Per-user login data lives in each user's %LOCALAPPDATA% / %APPDATA%.
    for guid in [GOG_GUID, UBISOFT_GUID, EA_GUID, BATTLENET_GUID, XBOX_GUID, AMAZON_GUID]:
        seed_playnite_config(GAMER_PLAYNITE, guid, {
            "ImportInstalledGames": True,
            "ImportUninstalledGames": True,
        })

    # ===========================================================
    # [12/15] Configure Shared Game Library Paths
    # ===========================================================
    print("\n[12/15] Configuring shared game library paths...")

    # --- Epic: seed default install path into GamerUser profile template ---
    # Per-user login & cloud saves stay in %LOCALAPPDATA%\EpicGamesLauncher\
    epic_cfg_dir = r"C:\Users\GamerUser\AppData\Local\EpicGamesLauncher\Saved\Config\Windows"
    os.makedirs(epic_cfg_dir, exist_ok=True)
    with open(os.path.join(epic_cfg_dir, "GameUserSettings.ini"), "w") as f:
        f.write("[Launcher]\nDefaultAppInstallLocation=C:\\Games\\Epic\n")

    # --- GOG Galaxy: machine-wide default install path (ProgramData applies to all users) ---
    gog_data = r"C:\ProgramData\GOG.com\Galaxy"
    os.makedirs(gog_data, exist_ok=True)
    with open(os.path.join(gog_data, "config.json"), "w") as f:
        json.dump({
            "defaultInstallationPath": r"C:\Games\GOG",
            "runAtSystemStartup": False,
            "startMinimized": True,
        }, f, indent=2)

    # --- Ubisoft Connect: seed settings.yml into GamerUser profile template ---
    # Per-user Ubisoft account data lives in %LOCALAPPDATA%\Ubisoft Game Launcher\
    ubisoft_cfg_dir = r"C:\Users\GamerUser\AppData\Local\Ubisoft Game Launcher"
    os.makedirs(ubisoft_cfg_dir, exist_ok=True)
    with open(os.path.join(ubisoft_cfg_dir, "settings.yml"), "w") as f:
        f.write("instpath: C:\\Games\\Ubisoft\\\nminimize_to_systray: true\n")

    # --- EA App: machine-level game install path ---
    run_cmd(
        r'reg add "HKLM\SOFTWARE\Electronic Arts\EA Desktop" '
        r'/v "InstallPath" /t REG_SZ /d "C:\Games\EA\" /f'
    )

    # --- Battle.net: seed default game directory (ProgramData) ---
    os.makedirs(r"C:\ProgramData\Battle.net\Agent", exist_ok=True)
    with open(r"C:\ProgramData\Battle.net\Agent\agent.db", "w") as f:
        json.dump({"game_dir": r"C:\Games\BattleNet"}, f, indent=2)

    # --- Amazon Games: machine-level default ---
    run_cmd(
        r'reg add "HKLM\SOFTWARE\Amazon\Amazon Games App" '
        r'/v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f'
    )

    # --- Xbox Gaming Services: machine-level content root ---
    run_cmd(
        r'reg add "HKLM\SOFTWARE\Microsoft\GamingServices" '
        r'/v "GamingRootPath" /t REG_SZ /d "C:\Games\Xbox" /f'
    )

    # ===========================================================
    # [13/15] Setup Python Core & WinSW Service
    # ===========================================================
    print("\n[13/15] Setting up Python Core & Service...")
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
    # [14/15] Create BootOS Shell Scripts & Registry Lockdown
    # ===========================================================
    print("\n[14/15] Creating BootOS Shell Scripts...")

    # BootOS.cmd - the per-user shell that runs on every login.
    #
    # Design:
    #   1. Start explorer.exe as a background shell backdrop.
    #      This is required for launcher COM objects, file-open dialogs, and
    #      WebView2-based launcher UIs to work correctly.  Playnite Fullscreen
    #      runs on top and fills the entire screen so the desktop is never visible.
    #   2. Prime per-user registry keys that launchers read at startup.
    #      These override any defaults so every user gets the shared library paths.
    #   3. Launch Playnite Fullscreen - the only thing the user sees.
    boot_cmd_content = r"""@echo off
:: ---------------------------------------------------------------
:: BootOS - PlayniteOS Universal Launcher Shell
:: ---------------------------------------------------------------

:: 1. Start Windows Explorer as a hidden shell backdrop.
::    Required for launcher COM objects and WebView2-based UIs.
::    Playnite Fullscreen will cover the entire screen on top.
start "" explorer.exe

:: 2. Prime per-user registry keys (refreshed every login so launcher
::    updates that reset paths do not break the shared library setup).

:: Steam (per-user install in Playnite\Launchers\Steam)
reg add "HKCU\Software\Valve\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam"     /f >nul
reg add "HKCU\Software\Valve\Steam" /v "SteamExe"  /t REG_SZ /d "%USERPROFILE%\Playnite\Launchers\Steam\steam.exe" /f >nul

:: Ubisoft Connect - shared game library
reg add "HKCU\Software\Ubisoft\Launcher"           /v "InstallDir"         /t REG_SZ /d "C:\Games\Ubisoft\" /f >nul

:: Amazon Games - shared game library
reg add "HKCU\Software\Amazon\Amazon Games App"    /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon"  /f >nul

:: Xbox Gaming App - shared content root
reg add "HKCU\Software\Microsoft\GamingApp"        /v "GameContentPath"    /t REG_SZ /d "C:\Games\Xbox"     /f >nul

:: 3. Launch Playnite Fullscreen - covers the entire screen.
::    All launcher interactions happen through Playnite; users never see the desktop.
"%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"

:: 4. Logoff when Playnite exits (user switch / power-off flows)
:: logoff
"""
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.cmd"), "w") as f:
        f.write(boot_cmd_content)

    # BootOS.vbs - invisible launcher for BootOS.cmd (no console window)
    vbs_content = (
        'Set WshShell = CreateObject("WScript.Shell")\r\n'
        'WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%")'
        ' & "\\Playnite\\BootOS.cmd""", 0, True\r\n'
    )
    with open(os.path.join(GAMER_PLAYNITE, "BootOS.vbs"), "w") as f:
        f.write(vbs_content)

    # --- Bake GamerUser registry template from GamerUserRegistry.json ---
    # The GamerUser hive is initialised from the clean Windows Default hive,
    # then every key defined in GamerUserRegistry.json is applied on top.
    # Edit GamerUserRegistry.json to adjust what new gamer accounts inherit
    # without touching this script.
    print("Baking GamerUser registry template from GamerUserRegistry.json...")
    shutil.copy2(r"C:\Users\Default\NTUSER.DAT", r"C:\Users\GamerUser\NTUSER.DAT")
    run_cmd('reg load "HKU\\GamerTemplate" "C:\\Users\\GamerUser\\NTUSER.DAT"')

    for entry in gamer_reg["keys"]:
        full_path = fr"HKU\GamerTemplate\{entry['path']}"
        for v in entry["values"]:
            subprocess.run(
                ["reg", "add", full_path, "/v", v["name"], "/t", v["type"], "/d", v["data"], "/f"],
                capture_output=True,
            )

    run_cmd(
        r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" '
        r'/v "EnumerateLocalUsersOnDomainJoinedComputers" /t REG_DWORD /d 1 /f'
    )
    run_cmd('reg unload "HKU\\GamerTemplate"')

    # ===========================================================
    # [15/15] Finalize Permissions & Firewall
    # ===========================================================
    print("\n[15/15] Finalizing Permissions...")
    # Users get full control over all shared game silos so launchers can install/patch
    run_cmd(r'icacls "C:\Games"     /grant "Users:(OI)(CI)F"  /T /C /Q')
    # Users can read/execute the PlayniteOS core but cannot tamper with it
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd(
        'powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' '
        '-Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"'
    )

    # Clean up installer temp files
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

    print("\n--- INSTALLATION COMPLETE! REBOOT TO APPLY. ---")


if __name__ == "__main__":
    main()
