# PlayniteOS Bootstrapper
$RepoUrl = "https://raw.githubusercontent.com/Andrewbandrew05/PlayniteOS/main"
$PyZip = "$env:TEMP\py_portable.zip"; $PyDir = "$env:TEMP\PlayniteInstallerPy"

Write-Host "Bootstrapping Python Environment..." -ForegroundColor Cyan
Invoke-WebRequest "https://www.python.org/ftp/python/3.11.5/python-3.11.5-embed-amd64.zip" -OutFile $PyZip
if (Test-Path $PyDir) { Remove-Item $PyDir -Recurse -Force }
Expand-Archive $PyZip -DestinationPath $PyDir -Force

Write-Host "Downloading Installer from GitHub..." -ForegroundColor Cyan
Invoke-WebRequest "$RepoUrl/Installation/installer.py" -OutFile "$env:TEMP\installer.py"

Write-Host "Handing over to Python..." -ForegroundColor Green
& "$PyDir\python.exe" "$env:TEMP\installer.py"
