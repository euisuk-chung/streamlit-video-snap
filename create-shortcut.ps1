$WshShell = New-Object -ComObject WScript.Shell
$StartupPath = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupPath "YouTube-Tools-Streamlit.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "d:\Repo\streamlit-video-snap\start-streamlit.bat"
$Shortcut.WorkingDirectory = "d:\Repo\streamlit-video-snap"
$Shortcut.WindowStyle = 7
$Shortcut.Save()

Write-Host "Shortcut created at: $ShortcutPath"
