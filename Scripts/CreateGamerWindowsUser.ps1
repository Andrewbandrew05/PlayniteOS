param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"
$BackupDir      = "C:\PlayniteOS\DefaultProfileBackup"

# Helper for robust directory removal
function Remove-Tree {
    param([string]$Path)
    if (!(Test-Path $Path)) { return }
    & cmd /c rmdir /s /q "$Path" 2>$null
}

try {
    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'."
    }

    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # 1. Create the Windows account
    & net user $UserName $Password /add /comment:"PlayniteOS Gamer" /y
    if ($LASTEXITCODE -ne 0) { throw "Failed to create user." }

    $SID = (Get-WmiObject Win32_UserAccount -Filter "Name='$UserName' and LocalAccount='True'").SID
    if (!$SID) { throw "Could not retrieve SID." }

    # 2. Back up Default profile
    Write-Output "Backing up Default profile..."
    if (Test-Path $BackupDir) { Remove-Tree $BackupDir }
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    robocopy $DefaultProfile $BackupDir /E /COPYALL /XJ /NFL /NDL /NJH /NJS | Out-Null

    # 3. Overlay GamerUser onto Default (Safety fallback)
    Write-Output "Overlaying GamerUser onto Default..."
    robocopy $GamerTemplate $DefaultProfile /E /COPYALL /XJ /NFL /NDL /NJH /NJS | Out-Null

    # 4. Pre-stage the new user's profile directory
    $UserProfile = "C:\Users\$UserName"
    Write-Output "Pre-staging profile at $UserProfile ..."
    if (Test-Path $UserProfile) { Remove-Tree $UserProfile }
    
    # We copy DATA and ATTRIBUTES. We do NOT copy Security (/COPY:DA) 
    # so that the files don't keep the GamerUser SID permissions.
    robocopy $GamerTemplate $UserProfile /E /COPY:DA /XJ /NFL /NDL /NJH /NJS | Out-Null

    # 5. Fix Ownership and Permissions (The "Group Policy Fix")
    Write-Output "Applying permissions and ownership..."
    
    # Take ownership of the folder and everything inside
    & takeown /f "$UserProfile" /r /d y | Out-Null
    
    # Grant the new user Full Control recursively
    # /T = recursive, /C = continue on errors, /Q = quiet
    & icacls "$UserProfile" /grant "${UserName}:(OI)(CI)F" /T /C /Q | Out-Null

    # CRITICAL: Ensure NTUSER.DAT is handled. 
    # Sometimes it's hidden and missed by recursive commands.
    $NtUserDat = Join-Path $UserProfile "NTUSER.DAT"
    if (Test-Path $NtUserDat -ErrorAction SilentlyContinue) {
        & icacls "$NtUserDat" /grant "${UserName}:F" | Out-Null
        & attrib -s -h "$NtUserDat"
        & icacls "$NtUserDat" /setowner "$UserName" | Out-Null
        & attrib +s +h "$NtUserDat"
    }

    # 6. Register the profile in ProfileList
    Write-Output "Registering profile in Registry..."
    $ProfileListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    if (Test-Path $ProfileListPath) { Remove-Item $ProfileListPath -Recurse -Force }
    
    New-Item -Path $ProfileListPath -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileImagePath" -Value $UserProfile -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "Flags"            -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "State"            -Value 0 -PropertyType DWord -Force | Out-Null
    
    $SIDObj    = New-Object System.Security.Principal.SecurityIdentifier($SID)
    $SIDBinary = New-Object byte[] $SIDObj.BinaryLength
    $SIDObj.GetBinaryForm($SIDBinary, 0)
    New-ItemProperty -Path $ProfileListPath -Name "Sid" -Value $SIDBinary -PropertyType Binary -Force | Out-Null

    # 7. Revert Default profile
    Write-Output "Reverting Default profile..."
    Remove-Tree $DefaultProfile
    New-Item -ItemType Directory -Path $DefaultProfile -Force | Out-Null
    robocopy $BackupDir $DefaultProfile /E /COPYALL /XJ /NFL /NDL /NJH /NJS | Out-Null
    Remove-Tree $BackupDir

    # 8. Make visible on login screen
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) { New-Item -Path $UserListPath -Force | Out-Null }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS ---"
}
catch {
    Write-Output "ERROR: $_"
    if (Test-Path $BackupDir) {
        Write-Output "Restoring Default profile from backup..."
        Remove-Tree $DefaultProfile
        New-Item -ItemType Directory -Path $DefaultProfile -Force | Out-Null
        robocopy $BackupDir $DefaultProfile /E /COPYALL /XJ /NFL /NDL /NJH /NJS | Out-Null
    }
    exit 1
}