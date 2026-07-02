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

    # 2. Clean up any old "zombie" folders to prevent .000 issues
    if (Test-Path $UserProfile) { 
        Write-Output "Removing existing profile folder..."
        & cmd /c rmdir /s /q "$UserProfile" 
    }
    New-Item -Path $UserProfile -ItemType Directory -Force | Out-Null

    # 3. Copy Gamer Files + The Locked Master Hive
    Write-Output "Staging profile files..."
    & cmd /c "copy /y `"$GamerMaster\NTUSER.DAT`" `"$UserProfile\NTUSER.DAT`"" | Out-Null
    & robocopy $GamerFiles $UserProfile /E /COPY:DAT /XJ /R:3 /W:1 /XF NTUSER.DAT /NFL /NDL /NJH /NJS | Out-Null

    # 4. Fix Permissions (Crucial for avoiding "Temporary Profile" errors)
    Write-Output "Applying security descriptors..."
    & takeown /f "$UserProfile" /r /d y /a | Out-Null
    & icacls "$UserProfile" /grant "${UserName}:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "SYSTEM:(OI)(CI)F" /T /C /Q | Out-Null
    & icacls "$UserProfile" /grant "Administrators:(OI)(CI)F" /T /C /Q | Out-Null

    # 5. THE SID FIX: Register the profile with the Binary SID
    Write-Output "Registering SID in ProfileList..."
    $PList = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    & reg add "$PList" /v "ProfileImagePath" /t REG_EXPAND_SZ /d "$UserProfile" /f | Out-Null
    & reg add "$PList" /v "Flags" /t REG_DWORD /d 0 /f | Out-Null
    & reg add "$PList" /v "State" /t REG_DWORD /d 0 /f | Out-Null
    
    # Convert SID string to Binary Hex for the registry
    $SIDObj = New-Object System.Security.Principal.SecurityIdentifier($SID)
    $ByteSID = New-Object byte[] $SIDObj.BinaryLength
    $SIDObj.GetBinaryForm($ByteSID, 0)
    $HexSID = ($ByteSID | ForEach-Object { "{0:X2}" -f $_ }) -join ""
    & reg add "$PList" /v "Sid" /t REG_BINARY /d $HexSID /f | Out-Null

    # 6. Make visible on login screen
    & reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created (No Duplicates) ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}