param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"
$DefaultHive    = "$DefaultProfile\NTUSER.DAT"

try {
    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # 1. Pre-cleanup: Forcefully unload any orphaned mounts from previous failed runs
    # We use a loop to ensure it's actually gone.
    Write-Output "Ensuring registry is clean..."
    for ($i=1; $i -le 3; $i++) {
        & reg unload HKU\DefaultTemp 2>$null
        Start-Sleep -Milliseconds 500
    }

    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'."
    }

    # 2. Overlay GamerUser files into Default
    Write-Output "Staging GamerUser content into Default profile..."
    & robocopy $GamerTemplate $DefaultProfile /E /COPY:DAT /XJ /R:3 /W:1 `
        /XF NTUSER.DAT "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" NTUSER.MAN ntuser.ini `
             usrclass.dat "usrclass.dat.LOG1" "usrclass.dat.LOG2" `
        /NFL /NDL /NJH /NJS | Out-Null

    # 3. Clear Desktop and Start Menu
    Write-Output "Clearing Desktop and Start Menu shortcuts..."
    $PathsToClear = @(
        "$DefaultProfile\Desktop",
        "$DefaultProfile\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
    )
    foreach ($path in $PathsToClear) {
        if (Test-Path $path) {
            Get-ChildItem -Path $path -Recurse -Include *.lnk, *.url -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
        }
    }

    # --- CRITICAL FIX: THE SETTLING PERIOD ---
    # Give Windows Defender and Search Indexer 2 seconds to stop touching the files
    # we just copied/deleted before we try to mount the registry hive.
    Write-Output "Waiting for file system to settle..."
    Start-Sleep -Seconds 2

    # 4. Modify the Default Registry Hive
    Write-Output "Applying Registry restrictions to Default Hive..."
    
    # Verify file exists and is not read-only before loading
    if (!(Test-Path $DefaultHive)) { throw "Default NTUSER.DAT missing!" }
    & attrib -r "$DefaultHive"

    # Attempt to load the hive
    & reg load HKU\DefaultTemp "$DefaultHive" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to load registry hive. The file may be locked by another process."
    }

    try {
        # A. Force Background to Plain Black
        & reg add "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "Wallpaper" /t REG_SZ /d "" /f | Out-Null
        & reg add "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v "WallpaperStyle" /t REG_SZ /d "0" /f | Out-Null
        & reg add "HKU\DefaultTemp\Control Panel\Colors" /v "Background" /t REG_SZ /d "0 0 0" /f | Out-Null

        # B. Hide all Desktop Icons
        & reg add "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" /v "HideIcons" /t REG_DWORD /d 1 /f | Out-Null

        # C. Disable Taskbar and Start Menu Features
        $PolExplorer = "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        & reg add "$PolExplorer" /v "NoSetTaskbar" /t REG_DWORD /d 1 /f | Out-Null
        & reg add "$PolExplorer" /v "NoTrayItemsDisplay" /t REG_DWORD /d 1 /f | Out-Null
        & reg add "$PolExplorer" /v "NoStartMenuMorePrograms" /t REG_DWORD /d 1 /f | Out-Null
        & reg add "$PolExplorer" /v "NoTaskGrouping" /t REG_DWORD /d 1 /f | Out-Null

        # D. Disable the Windows Keys
        & reg add "HKU\DefaultTemp\Keyboard Layout" /v "Scancode Map" /t REG_BINARY /d 00000000000000000300000000005BE000005CE000000000 /f | Out-Null

        Write-Output "Registry restrictions applied."
    }
    finally {
        # Ensure we release the file handle no matter what
        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
        Start-Sleep -Milliseconds 500
        & reg unload HKU\DefaultTemp | Out-Null
    }

    # 5. Patch placeholders
    Write-Output "Patching username placeholders..."
    Get-ChildItem -Path "$DefaultProfile\Playnite" -Recurse -Include "*.json","*.xml","*.cfg","*.ini" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $raw = [System.IO.File]::ReadAllText($_.FullName)
            if ($raw.Contains("INSERTUSERNAMEHERE")) {
                [System.IO.File]::WriteAllText($_.FullName, $raw.Replace("INSERTUSERNAMEHERE", $UserName))
            }
        } catch { }
    }

    # 6. Create the Windows account
    Write-Output "Creating Windows account..."
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS Gamer" -ErrorAction Stop | Out-Null
    Add-LocalGroupMember -Group "Users" -Member $UserName | Out-Null

    # 7. Make user visible on login screen
    $UserListPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    & reg add "$UserListPath" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created ---"
}
catch {
    Write-Output "ERROR: $_"
    & reg unload HKU\DefaultTemp 2>$null
    exit 1
}