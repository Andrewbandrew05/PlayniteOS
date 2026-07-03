import os, subprocess, urllib.request, zipfile, shutil, io, json, time

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

    # [0/17] Cleanup
    old_update_script = r"C:\Users\Public\PlayniteOS-Update.ps1"
    old_shortcut = os.path.join(os.path.join(os.environ['USERPROFILE'], 'Desktop'), "Update PlayniteOS.lnk")
    if os.path.exists(old_update_script): os.remove(old_update_script)
    if os.path.exists(old_shortcut): os.remove(old_shortcut)

    DEFAULT_ROOT     = r"C:\Users\Default"
    DEFAULT_PLAYNITE = r"C:\Users\Default\Playnite"
    TEMP_DIR         = r"C:\PlayniteOS\tmp"

    # [1/17] Silos
    for silo in [r"Steam\steamapps", "Epic", "GOG", "Xbox", "Ubisoft", "EA", "BattleNet", "Amazon", "itchio"]:
        os.makedirs(fr"C:\Games\{silo}", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Installation", exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    run_cmd("winget source update --disable-interactivity --accept-source-agreements")
    run_cmd("winget install --id Microsoft.EdgeWebView2Runtime --silent --accept-source-agreements --accept-package-agreements")
    run_cmd("winget install --id Microsoft.VCRedist.2015+.x64 --silent --accept-source-agreements --accept-package-agreements")

    # [2/17] Playnite
    os.makedirs(DEFAULT_PLAYNITE, exist_ok=True)
    pn_zip = fr"{TEMP_DIR}\playnite.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, "r") as z: z.extractall(DEFAULT_PLAYNITE)
    open(os.path.join(DEFAULT_PLAYNITE, "playnite.portable"), "a").close()

    # [3/17] Steam
    steam_path  = os.path.join(DEFAULT_PLAYNITE, "Launchers", "Steam")
    steam_setup = fr"{TEMP_DIR}\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")
    run_cmd(fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' -ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"')

    # [4-11/17] Launchers
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

    # [12/17] Pull GitHub Assets
    print("\n[12/17] Pulling GitHub Assets...")
    repo_tmp = fr"{TEMP_DIR}\repo"
    req = urllib.request.Request(REPO_ZIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as z: z.extractall(repo_tmp)
    repo_root = os.path.join(repo_tmp, "PlayniteOS-main")
    for folder in ["Scripts", "Core", "Installation"]:
        src_path = os.path.join(repo_root, folder)
        if os.path.exists(src_path): shutil.copytree(src_path, fr"C:\PlayniteOS\{folder}", dirs_exist_ok=True)

    # [13/17] Configs
    time.sleep(30) 
    run_cmd("sc stop EABackgroundService >nul 2>&1")
    for proc in ["EpicGamesLauncher.exe", "GalaxyClient.exe", "UbisoftConnect.exe", "EADesktop.exe", "Battle.net.exe", "AmazonGamesUI.exe"]:
        run_cmd(fr'taskkill /F /IM "{proc}" /T >nul 2>&1')
    run_cmd(r'reg add "HKLM\SOFTWARE\Amazon\Amazon Games App" /v "GameInstallLocation" /t REG_SZ /d "C:\Games\Amazon" /f')
    run_cmd(r'reg add "HKLM\SOFTWARE\Microsoft\GamingServices" /v "GamingRootPath" /t REG_SZ /d "C:\Games\Xbox" /f')

    # [14/17] Python Service
    py_tmp = fr"{TEMP_DIR}\py_core.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, "r") as z: z.extractall(r"C:\PlayniteOS\Core\Python")
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

    # [15/17] Shell Replacement
    default_hive = os.path.join(DEFAULT_ROOT, "NTUSER.DAT")
    run_cmd(f'reg load HKU\DefaultTemplate "{default_hive}"')
    run_cmd('reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "Wallpaper" /t REG_SZ /d "" /f')
    run_cmd('reg add "HKU\DefaultTemplate\Control Panel\Colors" /v "Background" /t REG_SZ /d "0 0 0" /f')
    run_cmd('reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "HideIcons" /t REG_DWORD /d 1 /f')
    run_cmd('reg add "HKU\DefaultTemplate\Keyboard Layout" /v "Scancode Map" /t REG_BINARY /d 00000000000000000300000000005BE000005CE000000000 /f')
    shell_cmd = r'wscript.exe //B "%USERPROFILE%\Playnite\BootOS.vbs"'
    run_cmd(f'reg add "HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" /v "Shell" /t REG_SZ /d "{shell_cmd}" /f')
    run_cmd('reg unload HKU\DefaultTemplate')

    # [16/17] Deploy Shell Scripts
    print("\n[16/17] Deploying Shell Scripts...")
    shutil.copy2(r"C:\PlayniteOS\Installation\BootOS.cmd", os.path.join(DEFAULT_PLAYNITE, "BootOS.cmd"))
    shutil.copy2(r"C:\PlayniteOS\Installation\BootOS.vbs", os.path.join(DEFAULT_PLAYNITE, "BootOS.vbs"))
    startup_dir = os.path.join(DEFAULT_ROOT, r"AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup")
    os.makedirs(startup_dir, exist_ok=True)
    shutil.copy2(r"C:\PlayniteOS\Installation\Setup.cmd", os.path.join(startup_dir, "Setup.cmd"))

    # [17/17] Updater Shortcut
    print("\n[17/17] Creating Desktop Updater...")
    update_script_path = r"C:\Users\Public\PlayniteOS-Update.ps1"
    shutil.copy2(r"C:\PlayniteOS\Installation\Update.ps1", update_script_path)
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop, "Update PlayniteOS.lnk")
    vbs_script = f'Set WshShell = WScript.CreateObject("WScript.Shell")\nSet oShellLink = WshShell.CreateShortcut("{shortcut_path}")\noShellLink.TargetPath = "powershell.exe"\noShellLink.Arguments = "-NoProfile -ExecutionPolicy Bypass -File " & Chr(34) & "{update_script_path}" & Chr(34)\noShellLink.WindowStyle = 1\noShellLink.IconLocation = "C:\\Windows\\System32\\shell32.dll,238"\noShellLink.Save'
    with open(os.path.join(TEMP_DIR, "shortcut.vbs"), "w") as f: f.write(vbs_script)
    run_cmd(f"wscript.exe {os.path.join(TEMP_DIR, 'shortcut.vbs')}")

    # Finalize
    run_cmd('sc config "NahimicService" start= disabled >nul 2>&1')
    run_cmd('net stop "NahimicService" /y >nul 2>&1')
    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd('powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"')
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    print("\n--- INSTALLATION COMPLETE! Rebooting... ---")
    run_cmd("shutdown /r /t 15")

if __name__ == "__main__":
    main()