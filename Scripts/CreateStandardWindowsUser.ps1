param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    Write-Output "--- Creating Standard Windows User: $UserName ---"

    # 1. Create the Local User (inherits the clean Windows Default profile)
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    New-LocalUser -Name $UserName -Password $SecurePassword -Description "Standard User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName

    # 2. Make user visible on the PlayniteOS login screen
    $UserListPath = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    if (!(Test-Path $UserListPath)) {
        New-Item -Path $UserListPath -Force | Out-Null
    }
    New-ItemProperty -Path $UserListPath -Name $UserName -Value 1 -PropertyType DWord -Force | Out-Null

    Write-Output "--- SUCCESS: $UserName created. Profile will be built from the standard Windows Default on first login. ---"
}
catch {
    Write-Error "Failed: $_"
    exit 1
}
