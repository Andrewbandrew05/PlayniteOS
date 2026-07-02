param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

# ---------------------------------------------------------------------------
# CreateGamerWindowsUser.ps1
#
# Strategy (no NTUSER.DAT manipulation):
#   1. Overlay GamerUser non-registry files onto C:\Users\Default.
#      Windows copies Default -> new user profile on first login, so the
#      user inherits Playnite, Steam, configs, and the BootOS Startup entry.
#   2. Create the Windows account (no pre-staging, no ProfileList hacks).
#      Windows creates a brand-new NTUSER.DAT from Default's hive on first
#      login — Group Policy has nothing to complain about.
#   3. Show on login screen.
#
# Note: Default is left modified after this script. CreateStandardWindowsUser
#       restores it from C:\Users\DefaultUser before creating standard users.
# ---------------------------------------------------------------------------

$GamerTemplate  = "C:\Users\GamerUser"
$DefaultProfile = "C:\Users\Default"

try {
    Write-Output "--- Creating PlayniteOS Gamer User: $UserName ---"

    if (!(Test-Path $GamerTemplate)) {
        throw "GamerUser template not found at '$GamerTemplate'. Run the PlayniteOS installer first."
    }

    # ------------------------------------------------------------------
    # 1. Overlay GamerUser files into Default (registry hives untouched)
    #    /XJ  = skip junction points (Application Data, Local Settings etc.)
    #    /XF  = exclude registry hive files by name
    # ------------------------------------------------------------------
    Write-Output "Staging GamerUser content into Default profile..."
    & robocopy $GamerTemplate $DefaultProfile /E /COPY:DAT /XJ `
        /XF NTUSER.DAT "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" NTUSER.MAN ntuser.ini `
             usrclass.dat "usrclass.dat.LOG1" "usrclass.dat.LOG2" `
        /NFL /NDL /NJH /NJS | Out-Null
    Write-Output "Default profile staged."

    # ------------------------------------------------------------------
    # 2. Create the Windows account
    #    No pre-staging. Windows copies Default -> C:\Users\<UserName> on
    #    first login and creates a fresh NTUSER.DAT — no GP conflicts.
    # ------------------------------------------------------------------
    Write-Output "Creating Windows account..."
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword `
        -Description "PlayniteOS Gamer" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    Write-Output "Account created: $UserName"

    # ------------------------------------------------------------------
    # 3. Make user visible on the login screen
    # ------------------------------------------------------------------
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) { New-Item -Path $UserListPath -Force | Out-Null }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: Log out and sign in as '$UserName' to complete profile setup. ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}