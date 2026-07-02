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

    # Pre-cleanup in case of previous failure
    & reg unload HKU\DefaultTemp 2>$null
    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()

    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'."
    }

    # 1. Overlay GamerUser files into Default
    Write-Output "Staging GamerUser content into Default profile..."
    & robocopy $GamerTemplate $DefaultProfile /E /COPY:DAT /XJ /R:5 /W:1 `
        /XF NTUSER.DAT "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" NTUSER.MAN ntuser.ini `
             usrclass.dat "usrclass.dat.LOG1" "usrclass.dat.LOG2" `
        /NFL /NDL /NJH /NJS | Out-Null

    # 2. Clear Desktop and Start Menu
    Write-Output "Clearing Desktop and Start Menu shortcuts..."
    $PathsToClear = @(
        "$DefaultProfile\Desktop",
        "$DefaultProfile\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
    )
    foreach ($path in $PathsToClear) {
        if (Test-Path $path) {
            Get-ChildItem -Path $path -Recurse -Include *.lnk, *.url | Remove-Item -Force
        }
    }

    # 3. Modify the Default Registry Hive (Using native REG.EXE for maximum reliability)
    Write-Output "Applying Registry restrictions to Default Hive..."
    & reg load HKU\DefaultTemp "$DefaultHive" | Out-Null

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

        # D. Disable the Windows Keys (Binary Scancode Map)
        # 00000000 00000000 03000000 00005BE0 00005CE0 00000000
        & reg add "HKU\DefaultTemp\Keyboard Layout" /v "Scancode Map" /t REG_BINARY /d 00000000000000000300000000005BE000005CE000000000 /f | Out-Null

        Write-Output "Registry restrictions applied."
    }
    finally {
        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
        & reg unload HKU\DefaultTemp | Out-Null
    }

    # 4. Patch placeholders
    Write-Output "Patching username placeholders..."
    Get-ChildItem -Path "$DefaultProfile\Playnite" -Recurse -Include "*.json","*.xml","*.cfg","*.ini" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $raw = [System.IO.File]::ReadAllText($_.FullName)
            if ($raw.Contains("INSERTUSERNAMEHERE")) {
                [System.IO.File]::WriteAllText($_.FullName, $raw.Replace("INSERTUSERNAMEHERE", $UserName))
            }
        } catch { }
    }

    # 5. Create the Windows account
    Write-Output "Creating Windows account..."
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS Gamer" -ErrorAction Stop | Out-Null
    Add-LocalGroupMember -Group "Users" -Member $UserName | Out-Null

    # 6. Make user visible on login screen
    $UserListPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    & reg add "$UserListPath" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created ---"
}
catch {
    Write-Output "ERROR: $_"
    & reg unload HKU\DefaultTemp 2>$null
    exit 1
}