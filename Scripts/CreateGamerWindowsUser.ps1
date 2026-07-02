param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"
$BackupDir      = "C:\PlayniteOS\DefaultProfileBackup"

function Remove-Tree {
    param([string]$Path)
    if (!(Test-Path $Path)) { return }
    & cmd /c rmdir /s /q "$Path" 2>$null
}

try {
    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # 1. Create the Windows account
    & net user $UserName $Password /add /comment:"PlayniteOS Gamer" /y
    $SID = (Get-WmiObject Win32_UserAccount -Filter "Name='$UserName' and LocalAccount='True'").SID
    if (!$SID) { throw "Could not retrieve SID." }

    # 2. Back up the CLEAN Default profile (if not already backed up)
    if (!(Test-Path $BackupDir)) {
        Write-Output "Creating fresh backup of Default profile..."
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
        robocopy $DefaultProfile $BackupDir /E /COPYALL /XJ /NFL /NDL /NJH /NJS | Out-Null
    }

    # 3. Pre-stage the new user's profile directory
    $UserProfile = "C:\Users\$UserName"
    if (Test-Path $UserProfile) { Remove-Tree $UserProfile }
    New-Item -ItemType Directory -Path $UserProfile -Force | Out-Null
    
    # 4. Copy everything EXCEPT the registry hives from the GamerTemplate
    Write-Output "Copying GamerUser files (skipping registry hives)..."
    robocopy $GamerTemplate $UserProfile /E /COPY:DAT /XJ /XF "NTUSER.DAT*" "usrclass.dat*" /NFL /NDL /NJH /NJS | Out-Null

    # 5. Copy the CLEAN NTUSER.DAT from the Windows Default backup
    Write-Output "Seeding clean NTUSER.DAT from Windows Default..."
    Copy-Item "$BackupDir\NTUSER.DAT" "$UserProfile\NTUSER.DAT" -Force

    # 6. Fix Permissions (Crucial for Group Policy)
    Write-Output "Applying permissions..."
    & takeown /f "$UserProfile" /r /d y /a | Out-Null
    & icacls "$UserProfile" /grant "${UserName}:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "SYSTEM:(OI)(CI)F" /T /C /Q | Out-Null
    
    # Ensure the NTUSER.DAT specifically is owned by the user and accessible by SYSTEM
    $NtUserDat = "$UserProfile\NTUSER.DAT"
    & attrib -s -h "$NtUserDat"
    & icacls "$NtUserDat" /setowner "$UserName" | Out-Null
    & icacls "$NtUserDat" /grant "SYSTEM:F" /grant "${UserName}:F" | Out-Null
    & attrib +s +h "$NtUserDat"

    # 7. Register the profile in ProfileList
    Write-Output "Registering profile in Registry..."
    $ProfileListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    New-Item -Path $ProfileListPath -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileImagePath" -Value $UserProfile -PropertyType ExpandString -Force | Out-Null
    
    $SIDObj = New-Object System.Security.Principal.SecurityIdentifier($SID)
    $SIDBinary = New-Object byte[] $SIDObj.BinaryLength
    $SIDObj.GetBinaryForm($SIDBinary, 0)
    New-ItemProperty -Path $ProfileListPath -Name "Sid" -Value $SIDBinary -PropertyType Binary -Force | Out-Null

    # 8. Make visible on login screen
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) { New-Item -Path $UserListPath -Force | Out-Null }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}