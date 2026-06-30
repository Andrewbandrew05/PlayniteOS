param([string]$Password)
net user PlayniteAdmin /active:yes
if ($Password) { net user PlayniteAdmin $Password }
Write-Output "PlayniteAdmin account has been enabled."
