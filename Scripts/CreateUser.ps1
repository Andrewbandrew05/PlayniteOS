param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    Write-Output "--- Starting Plan9OS User Creation for $UserName ---"

    # 1. Create the Local User
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $UserObj = New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    $UserSID = $UserObj.SID.Value
    Write-Output "Step 1: User $UserName created (SID: $UserSID)."

    # 2. Define Paths
    $ProfilePath = "C:\Users\$UserName"
    $PlayniteDir = "$ProfilePath\Playnite"
    $PlayniteExe = "%USERPROFILE%\Playnite\Playnite.FullscreenApp.exe"

    # 3. Pre-stage the Profile Folder and Hive
    # Windows won't create the NTUSER.DAT until the first login, so we do it now
    if (!(Test-Path $ProfilePath)) { New-Item -ItemType Directory -Path $ProfilePath -Force | Out-Null }
    if (!(Test-Path "$ProfilePath\NTUSER.DAT")) {
        Copy-Item "C:\Users\Default\NTUSER.DAT" -Destination "$ProfilePath\NTUSER.DAT" -Force
    }

    # 4. Seed the Profile (Copy the MasterSeed)
    Write-Output "Step 2: Seeding Playnite files..."
    if (!(Test-Path $PlayniteDir)) { New-Item -ItemType Directory -Path $PlayniteDir -Force | Out-Null }
    robocopy "C:\PlayniteOS\MasterSeed" "$PlayniteDir" /E /XJ /MT /R:2 /W:5 | Out-Null

    # 5. THE SPACE SAVER: Junction the heavy Game Folders
    Write-Output "Step 3: Creating Steam Junction..."
    $UserSteamApps = "$PlayniteDir\Launchers\Steam\steamapps"
    $GlobalSteamApps = "C:\Games\Steam\steamapps"
    
    if (!(Test-Path $UserSteamApps)) {
        New-Item -Path $UserSteamApps -ItemType Junction -Value $GlobalSteamApps -Force | Out-Null
    }

    # 6. SET THE SHELL (Registry Hive Injection)
    Write-Output "Step 4: Injecting Custom Shell into Registry..."
    
    # MOUNT the user's registry file so we can edit it
    & reg load "HKU\TempHive_$UserName" "$ProfilePath\NTUSER.DAT" | Out-Null
    
    $WinlogonKey = "HKU\TempHive_$UserName\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    
    # ADD the Shell key (Note the extra quotes to handle the space in 'Windows NT')
    & reg add "`"$WinlogonKey`"" /v "Shell" /t REG_EXPAND_SZ /d "$PlayniteExe" /f | Out-Null
    
    # UNLOAD the registry file to save changes
    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()
    & reg unload "HKU\TempHive_$UserName" | Out-Null

    # 7. Finalize Permissions & Visibility
    Write-Output "Step 5: Finalizing Permissions and Visibility..."
    icacls "$ProfilePath" /setowner "$UserName" /T /C /Q
    icacls "$ProfilePath" /grant "${UserName}:(OI)(CI)F" /T /C /Q
    
    # Make user visible on login screen
    $UserListPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    & reg add "`"$UserListPath`"" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName is ready for PlayniteOS ---"
}
catch {
    Write-Error "Failed: $_"
    # Emergency unload if something crashed
    & reg unload "HKU\TempHive_$UserName" 2>$null
}
