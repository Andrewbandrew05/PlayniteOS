import os
import subprocess
import urllib.request
import zipfile
import shutil
import io

# --- ENFORCE NATIVE WINDOWS TRUST STORE ---
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass 

# --- CONFIGURATION ---
REPO_ZIP_URL = "https://github.com/Andrewbandrew05/PlayniteOS/archive/refs/heads/main.zip"
PLAYNITE_URL = "https://github.com/JosefNemec/Playnite/releases/download/10.31/Playnite1031.zip"
STEAM_URL = "https://cdn.akamai.steamstatic.com/client/installer/SteamSetup.exe"
EPIC_URL = "https://launcher-public-service-prod06.ol.epicgames.com/launcher/api/installer/download/EpicGamesLauncherInstaller.msi"
WINSW_URL = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip"

def run_cmd(cmd):
    print(f" > {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def download(url, dest):
    print(f"Downloading: {url}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(dest, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def main():
    print("==========================================")
    print("    PlayniteOS Mark 1.5: Multi-Launcher   ")
    print("==========================================")

    # 1. Create Global Silos
    print("\n[1/9] Creating Global Silos...")
    os.makedirs(r"C:\Games\Steam\steamapps", exist_ok=True)
    os.makedirs(r"C:\Games\Epic", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)

    # 2. Build Master Seed in Default User
    print("\n[2/9] Building Master Seed in Default User...")
    default_playnite = r"C:\Users\Default\Playnite"
    os.makedirs(default_playnite, exist_ok=True)
    
    pn_zip = r"C:\PlayniteOS\playnite_tmp.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, 'r') as zip_ref:
        zip_ref.extractall(default_playnite)
    open(os.path.join(default_playnite, "playnite.portable"), 'a').close()
    os.remove(pn_zip)

    # 3. Install Steam (Per-User Template)
    print("\n[3/9] Installing Steam into Default Template...")
    steam_path = os.path.join(default_playnite, "Launchers", "Steam")
    steam_setup = r"C:\PlayniteOS\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")
    
    # Register Steam Client Service (Global)
    print("Registering Steam Client Service...")
    steam_service = r"C:\Program Files (x86)\Common Files\Steam\bin\steamservice.exe"
    run_cmd(fr'"{steam_service}" /Install')
    
    # Create Steam Junction
    junction_cmd = fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' -ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"'
    run_cmd(junction_cmd)

    # 4. Install Epic Games Launcher (Global)
    print("\n[4/9] Installing Epic Games Launcher (Global)...")
    epic_setup = r"C:\PlayniteOS\epic_setup.msi"
    download(EPIC_URL, epic_setup)
    run_cmd(f"msiexec /i {epic_setup} /qn /norestart")
    print("Epic Launcher installed. EOS Service will initialize on first run.")

    # 5. Pull GitHub Assets
    print("\n[5/9] Pulling GitHub Assets...")
    temp_extract_path = r"C:\PlayniteOS\repo_tmp"
    req = urllib.request.Request(REPO_ZIP_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
            zip_ref.extractall(temp_extract_path)
    
    repo_root = os.path.join(temp_extract_path, "PlayniteOS-main")
    shutil.copytree(os.path.join(repo_root, "Scripts"), r"C:\PlayniteOS\Scripts", dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Core"), r"C:\PlayniteOS\Core", dirs_exist_ok=True)
    
    # Inject Configs
    steam_guid = "cb91dfc9-b977-43bf-8e70-55f46e410fab"
    epic_guid = "91288519-6d85-46c2-a34d-cfcf9961e770"
    
    # Steam Config
    s_conf = os.path.join(default_playnite, "ExtensionsData", steam_guid, "config.json")
    os.makedirs(os.path.dirname(s_conf), exist_ok=True)
    shutil.copy2(os.path.join(repo_root, "Configs", "SteamConfig.json"), s_conf)
    
    # Epic Config
    e_conf = os.path.join(default_playnite, "ExtensionsData", epic_guid, "config.json")
    os.makedirs(os.path.dirname(e_conf), exist_ok=True)
    shutil.copy2(os.path.join(repo_root, "Configs", "EpicConfig.json"), e_conf)

    shutil.rmtree(temp_extract_path)

    # 6. Setup Python Core & WinSW
    print("\n[6/9] Setting up Python Core & Service...")
    py_tmp = r"C:\PlayniteOS\Core\py_tmp.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, 'r') as zip_ref:
        zip_ref.extractall(r"C:\PlayniteOS\Core\Python")
    os.remove(py_tmp)
    
    pth_file = r"C:\PlayniteOS\Core\Python\python311._pth"
    with open(pth_file, 'r') as f:
        lines = f.readlines()
    with open(pth_file, 'w') as f:
        for line in lines:
            f.write(line.replace('#import site', 'import site'))

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
    with open(r"C:\PlayniteOS\Core\PlayniteOS-Service.xml", 'w') as f:
        f.write(xml_content)
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe install")
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe start")

    # 7. Create BootOS Shell Scripts
    print("\n[7/9] Creating BootOS Shell Scripts...")
    boot_script_path = os.path.join(default_playnite, "BootOS.cmd")
    boot_script_content = """@echo off
:: Prime Steam Registry
reg add "HKCU\\Software\\Valve\\Steam" /v "SteamPath" /t REG_SZ /d "%USERPROFILE%\\Playnite\\Launchers\\Steam" /f >nul
reg add "HKCU\\Software\\Valve\\Steam" /v "SteamExe" /t REG_SZ /d "%USERPROFILE%\\Playnite\\Launchers\\Steam\\steam.exe" /f >nul

:: Launch Steam Silent
start "" "%USERPROFILE%\\Playnite\\Launchers\\Steam\\steam.exe" -silent

:: Launch Playnite Fullscreen
"%USERPROFILE%\\Playnite\\Playnite.FullscreenApp.exe"

:: logoff (Commented for testing)
:: logoff
"""
    with open(boot_script_path, "w") as f:
        f.write(boot_script_content)

    vbs_script_path = os.path.join(default_playnite, "BootOS.vbs")
    vbs_script_content = '''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\\Playnite\\BootOS.cmd""", 0, True
'''
    with open(vbs_script_path, "w") as f:
        f.write(vbs_script_content)
    
    # 8. Registry Lockdown
    print("\n[8/9] Applying Lockdown...")
    run_cmd('reg load "HKU\\DefaultTemplate" "C:\\Users\\Default\\NTUSER.DAT"')
    reg_key = r"HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    reg_data = r"wscript.exe %USERPROFILE%\Playnite\BootOS.vbs"
    subprocess.run(["reg", "add", reg_key, "/v", "Shell", "/t", "REG_EXPAND_SZ", "/d", reg_data, "/f"], capture_output=True)
    run_cmd(r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnumerateLocalUsersOnDomainJoinedComputers" /t REG_DWORD /d 1 /f')
    run_cmd('reg unload "HKU\\DefaultTemplate"')

    # 9. Finalize
    print("\n[9/9] Finalizing Permissions...")
    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd('powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"')

    print("\n--- INSTALLATION COMPLETE! REBOOT NOW. ---")

if __name__ == "__main__":
    main()
