# ---------------------------------------------------------------------------
# PlayniteOS Universal Updater & Reset Script (Bootstrap Edition)
# ---------------------------------------------------------------------------

# 1. Self-Elevate to Administrator
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$InstallerUrl = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main/Installation/installer.py"
$PythonUrl = "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip"
$DefaultHive = "C:\Users\Default\NTUSER.DAT"

$TempDir = "$env:TEMP\PlayniteOS_Update"
$PyZip = "$TempDir\py_bootstrap.zip"
$PyExeDir = "$TempDir\Python"
$TempInstaller = "$TempDir\installer.py"

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
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "Wallpaper" /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v "NoSetTaskbar" /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" /v "NoTrayItemsDisplay" /f > $null 2>&1
    & reg add "HKU\DefaultTemplate\Control Panel\Colors" /v "Background" /t REG_SZ /d "0 120 215" /f > $null 2>&1
    & reg add "HKU\DefaultTemplate\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "HideIcons" /t REG_DWORD /d 0 /f > $null 2>&1
    & reg delete "HKU\DefaultTemplate\Keyboard Layout" /v "Scancode Map" /f > $null 2>&1
    & reg unload HKU\DefaultTemplate > $null 2>&1
}

# 4. Wipe PlayniteOS Files
Write-Host "Wiping old files..."
$PathsToDelete = @(
    "C:\PlayniteOS",
    "C:\Users\Default\Playnite",
    "C:\Users\Default\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\BootOS.vbs",
    "C:\Users\Default\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Setup.cmd"
)

foreach ($Path in $PathsToDelete) {
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
        Write-Host "  Deleted: $Path"
    }
}

# 5. Setup Temporary Python Runtime
Write-Host "Setting up temporary Python runtime..." -ForegroundColor Yellow
if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
New-Item -ItemType Directory -Path $PyExeDir -Force | Out-Null

Write-Host "  Downloading Python..."
Invoke-WebRequest -Uri $PythonUrl -OutFile $PyZip
Write-Host "  Extracting Python..."
Expand-Archive -Path $PyZip -DestinationPath $PyExeDir -Force

# Enable site-packages for the embedded runtime
$PthFile = Get-ChildItem -Path $PyExeDir -Filter "*._pth" | Select-Object -First 1
if ($PthFile) {
    $Content = Get-Content $PthFile.FullName
    $Content = $Content -replace "#import site", "import site"
    Set-Content -Path $PthFile.FullName -Value $Content
}

# 6. Download and Run the New Installer
Write-Host "Downloading fresh installer..." -ForegroundColor Green
Invoke-WebRequest -Uri $InstallerUrl -OutFile $TempInstaller

Write-Host "Launching Installer..." -ForegroundColor Green
# Run the installer and wait for it to finish
Start-Process -FilePath "$PyExeDir\python.exe" -ArgumentList "`"$TempInstaller`"" -Wait

# 7. Cleanup
Write-Host "Cleaning up temporary runtime..." -ForegroundColor Cyan
Set-Location $env:USERPROFILE
Remove-Item -Recurse -Force $TempDir -ErrorAction SilentlyContinue

Write-Host "Update process complete." -ForegroundColor Green