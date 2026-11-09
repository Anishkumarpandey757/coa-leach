$ErrorActionPreference = 'Stop'
$windowsProject = $PSScriptRoot.Replace('\', '/')
$linuxProject = (wsl -d Ubuntu -- wslpath -u $windowsProject).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the project path in Ubuntu.' }
Start-Process -FilePath wsl.exe -WindowStyle Hidden -ArgumentList @(
    '-d', 'Ubuntu', '--', 'sh', "`"$linuxProject/launch_cooja.sh`""
)
