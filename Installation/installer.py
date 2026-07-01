import os
import subprocess
import urllib.request
import zipfile
import shutil
import io

# --- CONFIGURATION ---
REPO_ZIP_URL = "https://github.com/Andrewbandrew05/PlayniteOS/archive/refs/heads/main.zip"
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
    print("    PlayniteOS Mark 1: Pure Golden Image  ")
    print("==========================================")

    # 1. Create Global Silos
    print("\n[1/7] Creating Global Silos...")
    os.makedirs(r"C:\Games\Steam\steamapps", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Core\Python", exist_ok=True)
    os.makedirs(r"C:\PlayniteOS\Scripts", exist_ok=True)

    # 2. Build the Master Seed in the DEFAULT USER folder
    print("\n[2/7] Building Master Seed in Default User...")
    default_playnite = r"C:\Users\Default\Playnite"
    os.makedirs(default_playnite, exist_ok=True)
    
    # Download and Extract Playnite
    pn_zip = r"C:\PlayniteOS\playnite_tmp.zip"
    download(PLAYNITE_URL, pn_zip)
    with zipfile.ZipFile(pn_zip, 'r') as zip_ref:
        zip_ref.extractall(default_playnite)
    open(os.path.join(default_playnite, "playnite.portable"), 'a').close()
    os.remove(pn_zip)

    # 3. Install Steam into the Default Template
    print("\n[3/7] Installing Steam into Default Template...")
    steam_path = os.path.join(default_playnite, "Launchers", "Steam")
    steam_setup = r"C:\PlayniteOS\steam_setup.exe"
    download(STEAM_URL, steam_setup)
    run_cmd(fr"{steam_setup} /S /D={steam_path}")
    
    # Create the Junction inside the Default Template
    # Windows will copy this junction to every new user!
    junction_cmd = fr'powershell -Command "New-Item -Path \'{steam_path}\steamapps\' -ItemType Junction -Value \'C:\Games\Steam\steamapps\' -Force"'
    run_cmd(junction_cmd)

    # 4. Pull GitHub Assets (Core, Scripts, and Golden Config)
    print("\n[4/7] Pulling GitHub Assets...")
    temp_extract_path = r"C:\PlayniteOS\repo_tmp"
    with urllib.request.urlopen(REPO_ZIP_URL) as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
            zip_ref.extractall(temp_extract_path)
    
    repo_root = os.path.join(temp_extract_path, "PlayniteOS-main")
    shutil.copytree(os.path.join(repo_root, "Scripts"), r"C:\PlayniteOS\Scripts", dirs_exist_ok=True)
    shutil.copytree(os.path.join(repo_root, "Core"), r"C:\PlayniteOS\Core", dirs_exist_ok=True)
    
    # Inject Golden Steam Config into Default Template
    steam_config_dest = os.path.join(default_playnite, "ExtensionsData", "Playnite.SteamLibrary", "config.json")
    os.makedirs(os.path.dirname(steam_config_dest), exist_ok=True)
    shutil.copy2(os.path.join(repo_root, "Configs", "SteamConfig.json"), steam_config_dest)
    shutil.rmtree(temp_extract_path)

    # 5. Setup Embedded Python Core & WinSW
    print("\n[5/7] Setting up Python Core & Service...")
    py_tmp = r"C:\PlayniteOS\Core\py_tmp.zip"
    download(PYTHON_EMBED_URL, py_tmp)
    with zipfile.ZipFile(py_tmp, 'r') as zip_ref:
        zip_ref.extractall(r"C:\PlayniteOS\Core\Python")
    os.remove(py_tmp)
    
    # Enable site-packages
    pth_file = r"C:\PlayniteOS\Core\Python\python311._pth"
    with open(pth_file, 'r') as f:
        lines = f.readlines()
    with open(pth_file, 'w') as f:
        for line in lines:
            f.write(line.replace('#import site', 'import site'))

    # Install Dependencies
    download("https://bootstrap.pypa.io/get-pip.py", r"C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe C:\PlayniteOS\Core\Python\get-pip.py")
    run_cmd(r"C:\PlayniteOS\Core\Python\python.exe -m pip install fastapi uvicorn pynacl pyyaml requests")

    # Configure WinSW
    download(WINSW_URL, r"C:\PlayniteOS\Core\PlayniteOS-Service.exe")
    xml_content = """<service>
    <id>PlayniteOS-Core</id>
    <name>PlayniteOS Core API</name>
    <executable>C:\\PlayniteOS\\Core\\Python\\python.exe</executable>
    <arguments>C:\\PlayniteOS\\Core\\main.py</arguments>
    <log mode="roll"></log>
    </service>"""
    with open(r"C:\PlayniteOS\Core\PlayniteOS-Service.xml", 'w') as f:
        f.write(xml_content)
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe install")
    run_cmd(r"C:\PlayniteOS\Core\PlayniteOS-Service.exe start")

    # 6. Registry Lockdown (Default Template)
    print("\n[6/7] Applying Lockdown to Default Template...")
    run_cmd('reg load "HKU\\DefaultTemplate" "C:\\Users\\Default\\NTUSER.DAT"')
    
    # We use a list to bypass the shell and force literal %USERPROFILE%
    reg_key = r"HKU\DefaultTemplate\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    reg_data = r"%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"
    subprocess.run(["reg", "add", reg_key, "/v", "Shell", "/t", "REG_EXPAND_SZ", "/d", reg_data, "/f"], capture_output=True)
    
    run_cmd(r'reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" /v "EnumerateLocalUsersOnDomainJoinedComputers" /t REG_DWORD /d 1 /f')
    run_cmd('reg unload "HKU\\DefaultTemplate"')

    # 7. Finalize Permissions & Firewall
    print("\n[7/7] Finalizing Permissions and Firewall...")
    run_cmd(r'icacls "C:\Games" /grant "Users:(OI)(CI)F" /T /C /Q')
    run_cmd(r'icacls "C:\PlayniteOS" /grant "Users:(OI)(CI)RX" /T /C /Q')
    run_cmd('powershell -Command "New-NetFirewallRule -DisplayName \'PlayniteOS-Core API\' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080"')

    print("\n--- INSTALLATION COMPLETE! REBOOT NOW. ---")

if __name__ == "__main__":
    main()
