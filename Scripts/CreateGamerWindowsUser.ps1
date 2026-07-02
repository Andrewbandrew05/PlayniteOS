param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

# ---------------------------------------------------------------------------
# CreateGamerWindowsUser.ps1
#
# Creates a PlayniteOS gamer account seeded from the GamerUser profile template
# that the installer prepared at C:\Users\GamerUser.
#
# Strategy (swap-and-revert + direct pre-stage):
#   1. Back up C:\Users\Default               -- so we can restore it afterwards
#   2. Overlay GamerUser onto Default          -- in case Windows ever needs to
#                                                 re-init the profile from Default
#   3. Create the Windows account
#   4. Pre-stage the profile at C:\Users\<name> by copying GamerUser directly
#      (more reliable than relying on the first-login copy of Default)
#   5. Register the profile in ProfileList     -- prevents Windows re-creating it
#   6. Fix ownership / ACLs
#   7. Revert Default to the backup
#   8. Make visible on the login screen
#
# Error recovery: if anything fails after the backup is taken, the catch block
# attempts to restore Default from the backup automatically.
# ---------------------------------------------------------------------------

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"
$BackupDir      = "C:\PlayniteOS\DefaultProfileBackup"

# Removes a directory tree safely, handling Windows junction points (Application Data,
# Local Settings, etc.) by removing only the link rather than recursing into the target.
function Remove-Tree {
    param([string]$Path)
    if (!(Test-Path $Path -ErrorAction SilentlyContinue)) { return }
    Get-ChildItem $Path -Force -ErrorAction SilentlyContinue | ForEach-Object {
        if ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            # Junction/symlink — delete the link entry only, never recurse into it
            & cmd /c rmdir "$($_.FullName)" 2>$null
        } elseif ($_.PSIsContainer) {
            Remove-Tree $_.FullName
        } else {
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
        }
    }
    & cmd /c rmdir "$Path" 2>$null
    Remove-Item $Path -Force -ErrorAction SilentlyContinue
}

# Clears the children of a directory (leaving the directory itself) the same way.
function Clear-Tree {
    param([string]$Path, [string[]]$Exclude = @())
    Get-ChildItem $Path -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notin $Exclude } |
        ForEach-Object { Remove-Tree $_.FullName }
}

try {
    # ------------------------------------------------------------------
    # Guard: GamerUser template must exist
    # ------------------------------------------------------------------
    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'. Run the PlayniteOS installer first."
    }

    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    # ------------------------------------------------------------------
    # 1. Create the Windows account (SYSTEM-safe native commands)
    # ------------------------------------------------------------------
    # Create the user using net user (bypasses the New-LocalUser SYSTEM hang bug)
    & net user $UserName $Password /add /comment:"PlayniteOS Gamer" /y
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create local user '$UserName' via net user."
    }
    
    # Add to Users group (usually redundant for local users, but ensures it matches your logic)
    & net localgroup "Users" $UserName /add
    
    # Fetch the SID cleanly
    $SID = (Get-WmiObject Win32_UserAccount -Filter "Name='$UserName' and LocalAccount='True'").SID
    if (!$SID) {
        throw "Could not retrieve SID for created user '$UserName'."
    }
    Write-Output "Account created. SID: $SID"

    # ------------------------------------------------------------------
    # 2. Back up the current Default profile
    # ------------------------------------------------------------------
    Write-Output "Backing up Default profile to $BackupDir ..."
    Remove-Tree $BackupDir
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    robocopy $DefaultProfile $BackupDir /E /COPYALL /NFL /NDL /NJH /NJS | Out-Null

    # ------------------------------------------------------------------
    # 3. Overlay GamerUser onto Default
    #    (ensures Windows uses the correct base if it ever needs to
    #     re-create the profile from the Default template)
    # ------------------------------------------------------------------
    Write-Output "Overlaying GamerUser template onto Default profile ..."
    robocopy $GamerTemplate $DefaultProfile /E /COPYALL /NFL /NDL /NJH /NJS | Out-Null

    # ------------------------------------------------------------------
    # 4. Pre-stage the new user's profile directory from GamerUser
    #    (direct copy — does not wait for the first login)
    # ------------------------------------------------------------------
    $UserProfile = "C:\Users\$UserName"
    Write-Output "Pre-staging profile at $UserProfile ..."
    if (!(Test-Path $UserProfile)) {
        New-Item -ItemType Directory -Path $UserProfile -Force | Out-Null
    }
    robocopy $GamerTemplate $UserProfile /E /COPYALL /NFL /NDL /NJH /NJS | Out-Null

    # ------------------------------------------------------------------
    # 5. Register the profile in the Windows ProfileList so Windows
    #    treats it as an existing, fully initialised profile and does
    #    not attempt to copy Default on top of it at first login.
    # ------------------------------------------------------------------
    Write-Output "Registering profile in ProfileList ..."
    $ProfileListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\$SID"
    New-Item -Path $ProfileListPath -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileImagePath"    -Value $UserProfile -PropertyType ExpandString -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "Flags"               -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "State"               -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileLoadTimeLow"  -Value 0 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $ProfileListPath -Name "ProfileLoadTimeHigh" -Value 0 -PropertyType DWord -Force | Out-Null

    # ------------------------------------------------------------------
    # 6. Grant the new user full ownership / control of their profile
    # ------------------------------------------------------------------
    Write-Output "Setting ownership and ACLs ..."
    $Acl  = Get-Acl $UserProfile
    $Rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $UserName, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"
    )
    $Acl.SetOwner([System.Security.Principal.NTAccount]$UserName)
    $Acl.AddAccessRule($Rule)
    Set-Acl -Path $UserProfile -AclObject $Acl

    # ------------------------------------------------------------------
    # 7. Revert Default profile back to the original Windows default
    # ------------------------------------------------------------------
    Write-Output "Reverting Default profile ..."
    Clear-Tree $DefaultProfile -Exclude @("desktop.ini")
    robocopy $BackupDir $DefaultProfile /E /COPYALL /NFL /NDL /NJH /NJS | Out-Null
    Remove-Tree $BackupDir

    # ------------------------------------------------------------------
    # 8. Make the user visible on the PlayniteOS login screen
    # ------------------------------------------------------------------
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) {
        New-Item -Path $UserListPath -Force | Out-Null
    }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: $UserName created with GamerUser template. ---"
}
catch {
    Write-Output "ERROR: $_"

    # Attempt automatic restore of Default if the backup was already taken
    if (Test-Path $BackupDir) {
        Write-Output "Attempting to restore Default profile from backup ..."
        Clear-Tree $DefaultProfile -Exclude @("desktop.ini")
        robocopy $BackupDir $DefaultProfile /E /COPYALL /NFL /NDL /NJH /NJS | Out-Null
        Remove-Tree $BackupDir
        Write-Output "Default profile restored."
    }

    exit 1
}
