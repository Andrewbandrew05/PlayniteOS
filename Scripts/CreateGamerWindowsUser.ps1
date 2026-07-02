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
    # 3. Modify the Default Registry Hive (The "Gamer Lockdown")
    # ------------------------------------------------------------------
    Write-Output "Applying Registry restrictions to Default Hive..."
    
    # Load the Default NTUSER.DAT into a temporary mount point
    & reg load HKU\DefaultTemp "$DefaultHive" | Out-Null

    try {
        $RegPaths = @(
            "HKU\DefaultTemp\Control Panel\Colors",
            "HKU\DefaultTemp\Control Panel\Desktop",
            "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer",
            "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        )
        foreach ($p in $RegPaths) { if (!(Test-Path $p)) { New-Item $p -Force | Out-Null } }

        # A. Set Background to Plain Black
        Set-ItemProperty -Path "HKU\DefaultTemp\Control Panel\Colors" -Name "Background" -Value "0 0 0"
        Set-ItemProperty -Path "HKU\DefaultTemp\Control Panel\Desktop" -Name "WallPaper" -Value ""

        # B. Hide all Desktop Icons
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "HideIcons" -Value 1

        # C. Disable Taskbar and Start Menu (NoRun, NoSetTaskbar, NoStartMenu)
        # This effectively "kills" the interaction with the taskbar
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" -Name "NoSetTaskbar" -Value 1
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" -Name "NoTrayItemsDisplay" -Value 1
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" -Name "NoStartMenuMorePrograms" -Value 1
        Set-ItemProperty -Path "HKU\DefaultTemp\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer" -Name "NoTaskGrouping" -Value 1

        # D. OPTIONAL: Replace Shell with Playnite (The "Nuclear" Option)
        # If you want the Taskbar to NEVER even load, uncomment the lines below.
        # This replaces Explorer.exe with Playnite for this user.
        # $WinlogonPath = "HKU\DefaultTemp\Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
        # if (!(Test-Path $WinlogonPath)) { New-Item $WinlogonPath -Force | Out-Null }
        # Set-ItemProperty -Path $WinlogonPath -Name "Shell" -Value "C:\Users\$UserName\Playnite\Playnite.DesktopApp.exe"
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