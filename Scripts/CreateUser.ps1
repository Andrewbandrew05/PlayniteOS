param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    # Check if user already exists
    if (Get-LocalUser -Name $UserName -ErrorAction SilentlyContinue) {
        throw "User '$UserName' already exists."
    }

    Write-Output "--- Creating PlayniteOS User: $UserName ---"

    # 1. Create the Local User
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $UserObj = New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    
    # 2. Make user visible on login screen
    $UserListPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon\SpecialAccounts\UserList"
    & reg add "$UserListPath" /v "$UserName" /t REG_DWORD /d 1 /f | Out-Null

    Write-Output "--- SUCCESS: $UserName created. ---"
    Write-Output "Note: The first login will take a moment as Windows clones the Golden Template."
}
catch {
    Write-Error "Failed to create user: $_"
    exit 1
}