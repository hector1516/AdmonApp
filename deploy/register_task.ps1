<#
    register_task.ps1 — Registra la tarea programada "AdmonBuild" para desplegar la app
    con un comando, igual que WorkersBuild en el proyecto de workers.

    Uso (una sola vez, desde PowerShell como Administrador en el ServerVM):
        powershell -ExecutionPolicy Bypass -File C:\admon\deploy\register_task.ps1

    Después, para desplegar:
        schtasks /run /tn AdmonBuild
        Get-Content C:\admon\build.log -Wait     # hasta "FIN rc=0"

    Programación: "una vez" con fecha ya pasada = NUNCA se auto-dispara; la tarea
    existe solo para lanzarla a mano con /run. (No existe /sc ondemand en Windows:
    da "tipo de programa no válido". Mismo patrón que WorkersBuild.)
    Se registra con el usuario actual (como WorkersBuild) para que /run funcione
    desde la sesión del operador.

    Requisito previo: C:\admon debe ser un clon de https://github.com/hector1516/AdmonApp
    (sin eso, `git pull` dentro de build.ps1 falla).
#>

$ErrorActionPreference = 'Stop'
$repo = 'C:\admon'
$script = Join-Path $repo 'deploy\build.ps1'

if (-not (Test-Path $script)) { throw "No existe $script (¿el repo está en $repo?)" }

# Fecha/hora pasadas: la tarea queda como "solo una vez" ya vencida => solo /run manual.
$sd = (Get-Date).AddDays(-30).ToString('dd/MM/yyyy')
$st = (Get-Date).AddHours(1).ToString('HH:mm')
$action = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $script + '"'

schtasks /create /tn AdmonBuild /tr $action /sc once /st $st /sd $sd /f | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'schtasks /create falló' }

Write-Output "Tarea AdmonBuild registrada (programación: una vez, $sd $st -> solo manual)."
Write-Output "Desplegar:  schtasks /run /tn AdmonBuild"
Write-Output "Ver log:     Get-Content $repo\build.log -Wait"
