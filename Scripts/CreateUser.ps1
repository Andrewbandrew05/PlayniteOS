param (
    [Parameter(Mandatory=$true)]
    [string]$UserName,
    [string]$Password
)

try {
    # 1. Create the User
    $SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force
    $UserObj = New-LocalUser -Name $UserName -Password $SecurePassword -Description "PlayniteOS User" -ErrorAction Stop
    Add-LocalGroupMember -Group "Users" -Member $UserName
    Write-Output "User $UserName created."

    # 2. Seed the Profile (Copy the 500MB MasterSeed)
    $UserPlayniteDir = "C:\Users\$UserName\Playnite"
    if (!(Test-Path $UserPlayniteDir)) { New-Item -ItemType Directory -Path $UserPlayniteDir -Force }
    robocopy "C:\PlayniteOS\MasterSeed" "$UserPlayniteDir" /E /XJ /MT /R:2 /W:5 | Out-Null

    # 3. THE SPACE SAVER: Junction the heavy Game Folders
    # We point the user's Steam Games folder to the Global C:\Games Silo
    $UserSteamApps = "$UserPlayniteDir\Launchers\Steam\steamapps"
    if (!(Test-Path $UserSteamApps)) { New-Item -ItemType Directory -Path $UserSteamApps -Force }
   
    # Link the user's empty steamapps folder to the 100GB Global Silo
    # 3. THE SPACE SAVER: Junction the heavy Game Folders
    $UserSteamApps = "$UserPlayniteDir\Launchers\Steam\steamapps"
    $GlobalSteamApps = "C:\Games\Steam\steamapps"
    
    if (!(Test-Path $UserSteamApps)) {
        Write-Output "Creating Junction for Steam Games..."
        # Use New-Item instead of mklink for PowerShell compatibility
        New-Item -Path $UserSteamApps -ItemType Junction -Value $GlobalSteamApps -Force | Out-Null
    }

    # 4. Permissions & Shell
    icacls "C:\Users\$UserName" /grant "${UserName}:(OI)(CI)F" /T /C /Q
    # (Insert your Registry Shell code here to point to the user's local Playnite.FullscreenApp.exe)

    Write-Output "--- SUCCESS: $UserName is isolated and space-efficient. ---"
}
catch {
    Write-Error "Failed: $_"
}
