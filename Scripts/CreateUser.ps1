param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    Write-Output "--- Creating PlayniteOS User: $UserName ---"

    # 1. Create the Local User
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $UserObj = New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    
    # 2. Make user visible on login screen
    $UserListPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    & reg add "`"$UserListPath`"" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created. Windows will now build the profile from the Golden Template. ---"
}
catch {
    Write-Error "Failed: $_"
}
