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

# Enable 'site' packages so the portable installer environment can run Pip
$PthFile = "$PyDir\python311._pth"
(Get-Content $PthFile) -replace '#import site', 'import site' | Set-Content $PthFile

# 3. Secure the Bootstrapper Environment using native Windows Trust Store
Write-Host "Injecting Windows SSL Truststore..." -ForegroundColor Cyan
Invoke-WebRequest "https://bootstrap.pypa.io/get-pip.py" -OutFile "$PyDir\get-pip.py"
& "$PyDir\python.exe" "$PyDir\get-pip.py" --quiet
# Use trusted-host flags JUST for this bootstrap pip install, as we don't have truststore yet
& "$PyDir\python.exe" -m pip install truststore --quiet --trusted-host pypi.org --trusted-host files.pythonhosted.org

# 4. Clean up the old local installer script if it exists
Write-Host "Downloading Installer from GitHub..." -ForegroundColor Cyan
if (Test-Path "$LocalInstallDir\installer.py") { 
    Remove-Item "$LocalInstallDir\installer.py" -Force 
}

# 5. Use headers to smash through GitHub's CDN cache and fetch the fresh script
$Headers = @{
    "Cache-Control" = "no-cache"
    "Pragma"        = "no-cache"
}
Invoke-WebRequest "$RepoUrl/Installation/installer.py" -OutFile "$LocalInstallDir\installer.py" -Headers $Headers

# 6. Hand over control to Python wrapped in the Truststore injection layer
Write-Host "Handing over to Python..." -ForegroundColor Green

# Sanitize paths to use forward slashes so Python doesn't trip over \U or \T
$PyExeClean = "$PyDir\python.exe".Replace("\", "/")
$InstallerClean = "$LocalInstallDir\installer.py".Replace("\", "/")

# Use a clean multi-line block passed directly via standard input
$PythonScript = @"
import truststore
import subprocess

truststore.inject_into_ssl()
subprocess.run(['$PyExeClean', '$InstallerClean'])
"@

$PythonScript | & "$PyDir\python.exe"
& "$PyDir\python.exe" -c "import truststore; truststore.inject_into_ssl(); import subprocess; subprocess.run(['$PyExeClean', '$InstallerClean'])"
