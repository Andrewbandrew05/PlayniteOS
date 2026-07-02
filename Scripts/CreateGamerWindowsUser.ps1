param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"

function Remove-Tree {
    param([string]$Path)
    if (!(Test-Path $Path)) { return }
    & cmd /c rmdir /s /q "$Path" 2>$null
}

try {
    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # 1. Create the Windows account
    & net user $UserName $Password /add /comment:"PlayniteOS Gamer" /y
    if ($LASTEXITCODE -ne 0) { throw "Failed to create user." }

    $SID = (Get-WmiObject Win32_UserAccount -Filter "Name='$UserName' and LocalAccount='True'").SID
    if (!$SID) { throw "Could not retrieve SID." }

    # 2. Pre-stage the new user's profile directory
    $UserProfile = "C:\Users\$UserName"
    if (Test-Path $UserProfile) { Remove-Tree $UserProfile }
    New-Item -ItemType Directory -Path $UserProfile -Force | Out-Null
    
    # 3. Copy everything EXCEPT the registry hives from the GamerTemplate
    Write-Output "Copying GamerUser files (skipping registry hives)..."
    # /XF excludes files, /XD excludes directories, /XJ excludes junctions
    robocopy $GamerTemplate $UserProfile /E /COPY:DAT /XJ /XF "NTUSER.DAT*" "usrclass.dat*" /NFL /NDL /NJH /NJS | Out-Null

    # 4. Copy the CLEAN NTUSER.DAT directly from Windows Default
    Write-Output "Seeding clean NTUSER.DAT from Windows Default..."
    # We use robocopy here because it handles Hidden/System files correctly
    robocopy $DefaultProfile $UserProfile "NTUSER.DAT" /B /COPY:DAT /NFL /NDL /NJH /NJS | Out-Null

    if (!(Test-Path "$UserProfile\NTUSER.DAT" -ErrorAction SilentlyContinue)) {
        throw "Failed to copy NTUSER.DAT from $DefaultProfile. Profile cannot initialize."
    }

    # 5. Fix Permissions (Crucial for Group Policy)
    Write-Output "Applying permissions..."
    
    # Take ownership of the folder
    & takeown /f "$UserProfile" /r /d y /a | Out-Null
    
    # Grant Full Control to User and SYSTEM (SYSTEM is required for Group Policy)
    & icacls "$UserProfile" /grant "${UserName}:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "SYSTEM:(OI)(CI)F" /T /C /Q | Out-Null
    
    # Ensure the NTUSER.DAT specifically is owned by the user and accessible
    $NtUserDat = "$UserProfile\NTUSER.DAT"
    & attrib -s -h "$NtUserDat"
    & icacls "$NtUserDat" /setowner "$UserName" | Out-Null
    & icacls "$NtUserDat" /grant "SYSTEM:F" /grant "${UserName}:F" | Out-Null
    & attrib +s +h "$NtUserDat"

    # 6. Register the profile in ProfileList
    Write-Output "Registering profile in Registry..."
    $ProfileListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    if (Test-Path $ProfileListPath) { Remove-Item $ProfileListPath -Recurse -Force }
    
    New-Item -Path $ProfileListPath -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileImagePath" -Value $UserProfile -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "Flags"            -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "State"            -Value 0 -PropertyType DWord -Force | Out-Null
    
    $SIDObj = New-Object System.Security.Principal.SecurityIdentifier($SID)
    $SIDBinary = New-Object byte[] $SIDObj.BinaryLength
    $SIDObj.GetBinaryForm($SIDBinary, 0)
    New-ItemProperty -Path $ProfileListPath -Name "Sid" -Value $SIDBinary -PropertyType Binary -Force | Out-Null

    # 7. Make visible on login screen
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) { New-Item -Path $UserListPath -Force | Out-Null }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: User '$UserName' created with clean registry hive ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}