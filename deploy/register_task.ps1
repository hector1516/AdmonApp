<#
    register_task.ps1 — Registra la tarea programada "AdmonBuild" para desplegar la app
    con un comando, igual que WorkersBuild en el proyecto de workers.

    Uso (una sola vez, desde PowerShell como Administrador en el ServerVM):
        powershell -ExecutionPolicy Bypass -File C:\admon\deploy\register_task.ps1

    Después, para desplegar:
        schtasks /run /tn AdmonBuild
        Get-Content C:\admon\build.log -Wait     # hasta "FIN rc=0"

    Requisito previo: C:\admon debe ser un clon de https://github.com/hector1516/AdmonApp
    (sin esto, `git pull` dentro de build.ps1 falla).
#>

$ErrorActionPreference = 'Stop'
$repo = 'C:\admon'
$script = Join-Path $repo 'deploy\build.ps1'

if (-not (Test-Path $script)) { throw "No existe $script (¿el repo está en $repo?)" }

$action = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$script`""
schtasks /create /tn AdmonBuild /tr $action /sc ondemand /ru SYSTEM /rl highest /f | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'schtasks /create falló' }

Write-Output "Tarea AdmonBuild registrada."
Write-Output "Desplegar:  schtasks /run /tn AdmonBuild"
Write-Output "Ver log:     Get-Content $repo\build.log -Wait"
