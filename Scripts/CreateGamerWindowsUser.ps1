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

    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'."
    }

    # ------------------------------------------------------------------
    # 1. Overlay GamerUser files into Default
    # ------------------------------------------------------------------
    Write-Output "Staging GamerUser content into Default profile..."
    & robocopy $GamerTemplate $DefaultProfile /E /COPY:DAT /XJ `
        /XF NTUSER.DAT "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" NTUSER.MAN ntuser.ini `
             usrclass.dat "usrclass.dat.LOG1" "usrclass.dat.LOG2" `
        /NFL /NDL /NJH /NJS | Out-Null

    # ------------------------------------------------------------------
    # 2. "Delete" Desktop Apps and Start Menu Items from the Template
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # 3. Modify the Default Registry Hive (The "Phantom Explorer" Lockdown)
    # ------------------------------------------------------------------
    Write-Output "Applying Registry restrictions to Default Hive..."
    
    # Load the Default NTUSER.DAT into a temporary mount point
    & reg load HKU\DefaultTemp "$DefaultHive" | Out-Null

    try {
        $RegPaths = @(
            "HKU\DefaultTemp\Control Panel\Colors",
            "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\System",
            "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
            "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
            "HKU\DefaultTemp\Keyboard Layout"
        )
        foreach ($p in $RegPaths) { if (!(Test-Path $p)) { New-Item $p -Force | Out-Null } }

        # A. Force Background to Plain Black (Requires Policy to survive first login)
        $PolSystem = "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\System"
        Set-ItemProperty -Path $PolSystem -Name "Wallpaper" -Value "" -Type String -Force
        Set-ItemProperty -Path $PolSystem -Name "WallpaperStyle" -Value "0" -Type String -Force
        Set-ItemProperty -Path "HKU\DefaultTemp\Control Panel\Colors" -Name "Background" -Value "0 0 0" -Type String -Force

        # B. Hide all Desktop Icons (CRITICAL: Must be DWord)
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "HideIcons" -Value 1 -Type DWord -Force

        # C. Disable Taskbar and Start Menu Features (CRITICAL: Must be DWord)
        $PolExplorer = "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        Set-ItemProperty -Path $PolExplorer -Name "NoSetTaskbar" -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $PolExplorer -Name "NoTrayItemsDisplay" -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $PolExplorer -Name "NoStartMenuMorePrograms" -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $PolExplorer -Name "NoTaskGrouping" -Value 1 -Type DWord -Force

        # D. Disable the Windows Keys (Left and Right)
        # Prevents the Start Menu from opening if a controller guide button or Win key is pressed.
        $ScancodeMap = [byte[]](0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x03,0x00,0x00,0x00, 0x00,0x00,0x5B,0xE0, 0x00,0x00,0x5C,0xE0, 0x00,0x00,0x00,0x00)
        Set-ItemProperty -Path "HKU\DefaultTemp\Keyboard Layout" -Name "Scancode Map" -Value $ScancodeMap -Type Binary -Force

        # NOTE: We intentionally leave the "Shell" alone so explorer.exe runs.
        # This allows Epic Games, EA App, and Xbox to initialize their COM objects and System Trays.
    }
    finally {
        # CRITICAL: Always unload the hive or the user creation will fail
        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
        & reg unload HKU\DefaultTemp | Out-Null
    }

    # ------------------------------------------------------------------
    # 4. Patch placeholders
    # ------------------------------------------------------------------
    Write-Output "Patching username placeholders..."
    Get-ChildItem -Path "$DefaultProfile\Playnite" -Recurse -Include "*.json","*.xml","*.cfg","*.ini" -ErrorAction SilentlyContinue | ForEach-Object {
        $raw = [System.IO.File]::ReadAllText($_.FullName)
        if ($raw.Contains("INSERTUSERNAMEHERE")) {
            [System.IO.File]::WriteAllText($_.FullName, $raw.Replace("INSERTUSERNAMEHERE", $UserName))
        }
    }

    # ------------------------------------------------------------------
    # 5. Create the Windows account
    # ------------------------------------------------------------------
    Write-Output "Creating Windows account..."
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS Gamer" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName

    # ------------------------------------------------------------------
    # 6. Make user visible
    # ------------------------------------------------------------------
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) { New-Item -Path $UserListPath -Force | Out-Null }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: $UserName created with restricted UI ---"
}
catch {
    Write-Output "ERROR: $_"
    # Emergency unload if script crashed while hive was mounted
    & reg unload HKU\DefaultTemp 2>$null
    exit 1
}