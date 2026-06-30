import os
import subprocess
import urllib.request
import zipfile
import shutil

# --- CONFIGURATION ---
REPO_RAW = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main"
PLAYNITE_URL = "https://github.com/JosefNemec/Playnite/releases/download/10.31/Playnite1031.zip"
STEAM_URL = "https://cdn.akamai.steamstatic.com/client/installer/SteamSetup.exe"
WINSW_URL = "https://github.com/winsw/winsw/releases/download/v2.12.0/WinSW-x64.exe"
PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip"

def run_cmd(cmd):
    print(f" > {cmd}")
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def download(url, dest):
    print(f"Downloading: {url}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    urllib.request.urlretrieve(url, dest)

def main():
    print("==========================================")
    print("   PlayniteOS Mark 1 Master Installer     ")
    print("==========================================")

    # 1. Create Directory Structure
    print("\n[1/9] Creating Directories...")
    paths = [
        r"C:\Games\Steam", r"C:\Games\Epic",
        r"C:\PlayniteOS\Core\Python", r"C:\PlayniteOS\Scripts",
        r"C:\PlayniteOS\MasterSeed\Playnite", r"C:\PlayniteOS\Launchers"
    ]
    for p in paths:
        os.makedirs(p, exist_ok=True)

    # 2. Setup Permanent Embedded Python for the Core Service
    print("\n[2/9] Setting up Reproducible Python Core...")
    py_tmp = r"C:\PlayniteOS\Core\py_tmp.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, 'r') as zip_ref:
        zip_ref.extractall(r"C:\PlayniteOS\Core\Python")
    os.remove(py_tmp)
    
    # Enable site-packages in the embedded environment
    pth_file = r"C:\PlayniteOS\Core\Python\python311._pth"
    with open(pth_file, 'r') as f:
        lines = f.readlines()
    with open(pth_file, 'w') as f:
        for line in lines:
            f.write(line.replace('#import site', 'import site'))

    # 3. Install Pip and Dependencies for the Core API
    print("\n[3/9] Installing API Dependencies...")
    get_pip = r"C:\PlayniteOS\Core\Python\get-pip.py"
    download("https://bootstrap.pypa.io/get-pip.py", get_pip)
    run_cmd(fr"C:\PlayniteOS\Core\Python\python.exe {get_pip}")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe -m pip install fastapi uvicorn pynacl pyyaml requests")

    # 4. Install Steam Globally
    print("\n[4/9] Installing Steam to Global Launchers...")
    steam_setup = r"C:\PlayniteOS\Launchers\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D=C:\PlayniteOS\Launchers\Steam")

    # 5. Setup Playnite Portable Master Seed
    print("\n[5/9] Setting up Playnite Portable Seed...")
    pn_zip = r"C:\PlayniteOS\playnite_tmp.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, 'r') as zip_ref:
        zip_ref.extractall(r"C:\PlayniteOS\MasterSeed\Playnite")
    # Create portable flag
    open(r"C:\PlayniteOS\MasterSeed\Playnite\playnite.portable", 'a').close()
    os.remove(pn_zip)

    # 6. Pull Assets from your GitHub Repo
    print("\n[6/9] Pulling Scripts and Configs from GitHub...")
    assets = [
        ("Scripts/CreateUser.ps1", r"C:\PlayniteOS\Scripts\CreateUser.ps1"),
        ("Core/main.py", r"C:\PlayniteOS\Core\main.py"),
        ("Configs/SteamConfig.json", r"C:\PlayniteOS\MasterSeed\Playnite\ExtensionsData\Playnite.SteamLibrary\config.json")
    ]
    for src, dest in assets:
        download(f"{REPO_RAW}/{src}", dest)

    # 7. Configure WinSW Service
    print("\n[7/9] Configuring PlayniteOS Background Service...")
    download(WINSW_URL, r"C:\PlayniteOS\Core\PlayniteOS-Service.exe")
    xml_content = """<service>
    <id>PlayniteOS-Core</id>
    <name>PlayniteOS Core API</name>
    <description>Manages PlayniteOS User Creation and Lockdown.</description>
    <executable>C:\\PlayniteOS\\Core\\Python\\python.exe</executable>
    <arguments>C:\\PlayniteOS\\Core\\main.py</arguments>
    <log mode="roll"></log>
    </service>"""
    with open(r"C:\PlayniteOS\Core\PlayniteOS-Service.xml", 'w') as f:
        f.write(xml_content)
    
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe install")
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe start")

    # 8. Registry Lockdown (Default Template)
    print("\n[8/9] Applying Windows Lockdown to Default Template...")
    run_cmd('reg load "HKU\\DefaultTemplate" "C:\\Users\\Default\\NTUSER.DAT"')
    
    # Set Shell to Playnite Fullscreen
    shell_val = r"%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"
    run_cmd(fr'reg add "HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon" /v "Shell" /t REG_EXPAND_SZ /d "{shell_val}" /f')
    
    # Force User List on Login
    run_cmd(r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnumerateLocalUsersOnDomainJoinedComputers" /t REG_DWORD /d 1 /f')
    
    run_cmd('reg unload "HKU\\DefaultTemplate"')

    # 9. Finalize Permissions
    print("\n[9/9] Finalizing Permissions...")
    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')

    print("\n==========================================")
    print("   INSTALLATION COMPLETE! REBOOT NOW.     ")
    print("==========================================")

if __name__ == "__main__":
    main()
