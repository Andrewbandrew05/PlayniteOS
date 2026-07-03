# ---------------------------------------------------------------------------
# PlayniteOS Universal Updater & Reset Script
# ---------------------------------------------------------------------------

# 1. Self-Elevate to Administrator
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$InstallerUrl = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main/Installation/installer.py"
$DefaultHive = "C:\Users\Default\NTUSER.DAT"

Write-Host "!!! STARTING PLAYNITEOS RESET & UPDATE !!!" -ForegroundColor Cyan

# 2. Kill all possible locking processes
Write-Host "Stopping services and launchers..."
sc.exe stop "PlayniteOS-Core" > $null 2>&1
taskkill /F /IM "Playnite*" /T > $null 2>&1
taskkill /F /IM "python.exe" /T > $null 2>&1
taskkill /F /IM "EpicGamesLauncher.exe" /T > $null 2>&1
taskkill /F /IM "EADesktop.exe" /T > $null 2>&1
taskkill /F /IM "Battle.net.exe" /T > $null 2>&1

# 3. Revert Registry Lockdown on Default Profile
Write-Host "Reverting Registry Lockdown..."
& reg unload HKU\DefaultTemplate > $null 2>&1
& reg load HKU\DefaultTemplate "$DefaultHive" > $null 2>&1

if ($LASTEXITCODE -eq 0) {
    # Remove Policies
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "Wallpaper" /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v "NoSetTaskbar" /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v "NoTrayItemsDisplay" /f > $null 2>&1
    
    # Restore UI Defaults
    & reg add "HKU\DefaultTemplate\Control Panel\Colors" /v "Background" /t REG_SZ /d "0 120 215" /f > $null 2>&1
    & reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "HideIcons" /t REG_DWORD /d 0 /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Keyboard Layout" /v "Scancode Map" /f > $null 2>&1
    
    & reg unload HKU\DefaultTemplate > $null 2>&1
}

# 4. Wipe PlayniteOS Files (Except Games)
Write-Host "Wiping old files..."
$PathsToDelete = @(
    "C:\PlayniteOS",
    "C:\Users\Default\Playnite",
    "C:\Users\Default\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\BootOS.vbs"
)

foreach ($Path in $PathsToDelete) {
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
        Write-Host "  Deleted: $Path"
    }
}

# 5. Re-enable Nahimic (Installer will disable it again if needed)
& sc.exe config "NahimicService" start= auto > $null 2>&1

# 6. Download and Run the New Installer
Write-Host "Downloading fresh installer from GitHub..." -ForegroundColor Green
$TempInstaller = "$env:TEMP\installer.py"
Invoke-WebRequest -Uri $InstallerUrl -OutFile $TempInstaller

Write-Host "Launching Installer..." -ForegroundColor Green
# This assumes 'python' is in your system PATH. 
# If not, the installer will handle its own environment once it starts.
python $TempInstaller