Set WshShell = CreateObject("WScript.Shell")

' --- VISUAL INDICATOR ---
' Displays a popup for 3 seconds to confirm the VBS script has started.
' 64 = Information Icon
WshShell.Popup "PlayniteOS: VBS Shell Entry Point Active", 3, "Boot Loader", 64

' --- FORCED TESTING MODE ---
' This ensures explorer.exe (Taskbar/Desktop) always launches regardless of other logic.
WshShell.Run "explorer.exe"

' --- RUN MAIN LOGIC ---
' Runs the BootOS.cmd script. 
' 0 = Hide the console window
' True = Wait for the script to finish before the shell process ends
WshShell.Run """" & WshShell.ExpandEnvironmentStrings("%USERPROFILE%") & "\Playnite\BootOS.cmd""", 0, True