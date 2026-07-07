# Makes Stelly start automatically when Windows logs in.
# Run once from the repo root:  powershell -ExecutionPolicy Bypass -File scripts\install_startup_windows.ps1
# Undo any time: delete Stelly.lnk from the folder this prints.

$repo = Split-Path -Parent $PSScriptRoot
$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "Stelly.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = Join-Path $repo "scripts\stelly.bat"
$shortcut.WorkingDirectory = $repo
$shortcut.Description = "Stelly the companion robot"
$shortcut.Save()

Write-Host "Done. Stelly will start at login."
Write-Host "Shortcut created at: $shortcutPath"
Write-Host "To undo, delete that shortcut."
