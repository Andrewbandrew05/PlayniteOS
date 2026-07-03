Set WshShell = CreateObject("WScript.Shell")

:: 1. Patch placeholders
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%USERPROFILE%\Playnite' -Recurse -Include *.json,*.xml,*.cfg,*.ini -ErrorAction SilentlyContinue | ForEach-Object { $content = [System.IO.File]::ReadAllText($_.FullName); if ($content.Contains('INSERTUSERNAMEHERE')) { [System.IO.File]::WriteAllText($_.FullName, $content.Replace('INSERTUSERNAMEHERE', '%USERNAME%')) } }"

:: 2. Check for config.json
if not exist "%CONFIG_FILE%" (
    :: SETUP MODE: Launch Explorer and WAIT so the session doesn't end (Prevents Grey Screen)
    echo PlayniteOS is in Setup Mode. Initializing Desktop...
    
    start explorer.exe
    
) else {
    ' --- RUN MAIN LOGIC ---
    ' Runs the BootOS.cmd script. 
    ' 0 = Hide the console window
    ' True = Wait for the script to finish before the shell process ends
    WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\Playnite\BootOS.cmd""", 0, True
}