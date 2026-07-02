param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    Write-Output "--- Creating Standard Windows User: $UserName ---"

    # 1. Restore Default from the DefaultUser backup so any GamerUser content
    #    left by a previous CreateGamerWindowsUser run is cleaned out.
    #    /MIR mirrors the non-registry content (deletes extras, copies new).
    #    /XJ skips junction points; /XF excludes registry hive files.
    if (Test-Path "C:\Users\DefaultUser") {
        Write-Output "Restoring clean Default profile from DefaultUser backup..."
        & robocopy "C:\Users\DefaultUser" "C:\Users\Default" /MIR /COPY:DAT /XJ `
            /XF NTUSER.DAT "NTUSER.DAT.LOG1" "NTUSER.DAT.LOG2" NTUSER.MAN ntuser.ini `
                 usrclass.dat "usrclass.dat.LOG1" "usrclass.dat.LOG2" `
            /NFL /NDL /NJH /NJS | Out-Null
        Write-Output "Default profile restored."
    } else {
        Write-Output "WARNING: DefaultUser backup not found at C:\Users\DefaultUser — using Default as-is."
    }

    # 2. Create the Local User (inherits the clean Windows Default profile)
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword -Description "Standard User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    Write-Output "Account created: $UserName"

    # 3. Make user visible on the PlayniteOS login screen
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) {
        New-Item -Path $UserListPath -Force | Out-Null
    }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: $UserName created. Profile will be built from the standard Windows Default on first login. ---"
}
catch {
    Write-Output "ERROR: $_"
    exit 1
}

