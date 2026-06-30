param([string]$UserName)
$session = (qwinsta $UserName | ForEach-Object { $_ -split "\s+" } | Select-Object -Index 2)
if ($session) { 
    logoff $session 
    Write-Output "User $UserName logged off."
} else {
    Write-Error "User $UserName not found or not logged in."
}
