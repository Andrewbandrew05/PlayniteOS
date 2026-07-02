param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

$GamerFiles   = "C:\Users\GamerUser"
$GamerMaster  = "C:\PlayniteOS\GamerMaster"
$UserProfile  = "C:\Users\$UserName"

try {
    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # 1. Create the Windows account
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $UserObj = New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS Gamer" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName | Out-Null
    $SID = $UserObj.Sid.Value

    # 2. Clean up any old folders
    if (Test-Path $UserProfile) { 
        & cmd /c rmdir /s /q "$UserProfile" 
    }
    New-Item -Path $UserProfile -ItemType Directory -Force | Out-Null

    # 3. Copy Gamer Files + The Locked Master Hive
    Write-Output "Staging profile files..."
    # We copy ONLY the NTUSER.DAT, skipping the hidden transaction logs (.blf, .regtrans-ms)
    # These logs are what usually cause the Group Policy Sign-in error.
    & cmd /c "copy /y `"$GamerMaster\NTUSER.DAT`" `"$UserProfile\NTUSER.DAT`"" | Out-Null
    
    # Copy the rest of the files
    & robocopy $GamerFiles $UserProfile /E /COPY:DAT /XJ /R:3 /W:1 /XF NTUSER.DAT /NFL /NDL /NJH /NJS | Out-Null

    # 4. Fix Permissions (The Group Policy Fix)
    Write-Output "Applying security descriptors..."
    
    # Take ownership of everything
    & takeown /f "$UserProfile" /r /d y /a | Out-Null
    
    # Grant Full Control to User, SYSTEM, and Administrators
    # SYSTEM is the most important one for the Group Policy Service
    & icacls "$UserProfile" /grant "${UserName}:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "SYSTEM:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "Administrators:(OI)(CI)F" /T /C /Q | Out-Null

    # Explicitly ensure NTUSER.DAT is not hidden/system so we can verify permissions
    $NtUserDat = "$UserProfile\NTUSER.DAT"
    & attrib -s -h -r "$NtUserDat"
    & icacls "$NtUserDat" /grant "SYSTEM:F" /grant "${UserName}:F" | Out-Null
    & attrib +s +h "$NtUserDat"

    # 5. Register the profile in ProfileList
    Write-Output "Registering SID in ProfileList..."
    $PList = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    
    # Use PowerShell to write the registry keys to ensure correct data types
    New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID" -Force | Out-Null
    New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID" -Name "ProfileImagePath" -Value $UserProfile -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID" -Name "Flags" -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID" -Name "State" -Value 0 -PropertyType DWord -Force | Out-Null
    
    # Convert SID to Binary for the 'Sid' property (Required for Group Policy)
    $SIDObj = New-Object System.Security.Principal.SecurityIdentifier($SID)
    $ByteSID = New-Object byte[] $SIDObj.BinaryLength
    $SIDObj.GetBinaryForm($ByteSID, 0)
    New-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID" -Name "Sid" -Value $ByteSID -PropertyType Binary -Force | Out-Null

    # 6. Make visible on login screen
    & reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}