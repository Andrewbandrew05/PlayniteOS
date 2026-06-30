param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    
    [Parameter(Mandatory=$true)]
    [string]$Password
)

try {
    Write-Output "--- Preparing Switch to $UserName ---"

    # 1. Set the AutoLogon Registry Keys (Using reg.exe for reliability)
    $RegistryPath = "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    & reg add "$RegistryPath" /v "AutoAdminLogon" /t REG_SZ /d "1" /f | Out-Null
    & reg add "$RegistryPath" /v "DefaultUserName" /t REG_SZ /d "$UserName" /f | Out-Null
    & reg add "$RegistryPath" /v "DefaultPassword" /t REG_SZ /d "$Password" /f | Out-Null
    & reg add "$RegistryPath" /v "DefaultDomainName" /t REG_SZ /d "." /f | Out-Null

    # 2. Find the Active Console Session ID
    # We look for the session that is 'Active' and attached to the 'console'
    $SessionInfo = qwinsta | Out-String
    $ActiveSession = $SessionInfo -split "`n" | Where-Object { $_ -match "Active" }
    
    # Extract the ID (the number in the middle of the qwinsta output)
    if ($ActiveSession -match "\s+(\d+)\s+Active") {
        $SessionId = $matches[1]
        Write-Output "Found Active Session ID: $SessionId. Triggering logoff..."
        
        # 3. Force the logoff of the interactive session
        # This kicks the current user off the monitor
        & logoff $SessionId
    } else {
        # If no one is logged in, we just restart the login manager
        Write-Output "No active session found. Restarting Winlogon..."
        Stop-Process -Name winlogon -Force
    }

    Write-Output "Switch command sent successfully."
}
catch {
    Write-Error "Switch failed: $_"
    exit 1
}
