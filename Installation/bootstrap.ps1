# PlayniteOS Bootstrapper
$RepoUrl = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main"
$PyZip = "$env:TEMP\py_portable.zip"
$PyDir = "$env:TEMP\PlayniteInstallerPy"
$LocalInstallDir = "$env:TEMP\Installation"

# 1. Ensure the local installation folder exists in TEMP
if (!(Test-Path $LocalInstallDir)) { 
    New-Item -ItemType Directory -Path $LocalInstallDir -Force | Out-Null 
}

# 2. Bootstrap Python Environment
Write-Host "Bootstrapping Python Environment..." -ForegroundColor Cyan
Invoke-WebRequest "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip" -OutFile $PyZip
if (Test-Path $PyDir) { Remove-Item $PyDir -Recurse -Force }
Expand-Archive $PyZip -DestinationPath $PyDir -Force

# 3. Clean up the old local installer script if it exists
Write-Host "Downloading Installer from GitHub..." -ForegroundColor Cyan
if (Test-Path "$LocalInstallDir\installer.py") { 
    Remove-Item "$LocalInstallDir\installer.py" -Force 
}

# 4. Use headers to smash through GitHub's CDN cache and fetch the fresh script
$Headers = @{
    "Cache-Control" = "no-cache"
    "Pragma"        = "no-cache"
}
Invoke-WebRequest "$RepoUrl/Installation/installer.py" -OutFile "$LocalInstallDir\installer.py" -Headers $Headers

# 5. Hand over control to Python
Write-Host "Handing over to Python..." -ForegroundColor Green
& "$PyDir\python.exe" "$LocalInstallDir\installer.py"