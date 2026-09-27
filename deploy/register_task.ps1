<#
    register_task.ps1 — Registra la tarea programada "AdmonBuild" para desplegar la app
    con un comando, igual que WorkersBuild en el proyecto de workers.

    Uso (una sola vez, como Administrador en el ServerVM):
        powershell -ExecutionPolicy Bypass -File C:\admon\deploy\register_task.ps1
        # o sin prompt, con la contraseña en el entorno:
        $env:DEPLOY_TASK_PASSWORD = '...'; powershell -File C:\admon\deploy\register_task.ps1

    Después, para desplegar:
        schtasks /run /tn AdmonBuild
        Get-Content C:\admon\build.log -Wait     # hasta "FIN rc=0"

    ── Lecciones de Windows (2026-09-27) ───────────────────────────────────────
    · No existe /sc ondemand: schtasks /create responde "tipo de programa no válido".
    · Una tarea con fecha (/sd) YA VENCIDA no se puede lanzar: /run responde
      "CORRECTO" pero no arranca y build.log nunca aparece. Por eso se programa
      UNA sola vez en un futuro lejano (31/12/2099): no se auto-dispara nunca y
      /run sí funciona.
    · Se registra con /ru <usuario> /rp <contraseña> → LogonType "Password" (modo
      batch). Sin /it. No se usa /ru SYSTEM porque entonces git rechazaría el repo
      con "dubious ownership" (safe.directory) en el `git pull` de build.ps1.

    La contraseña NO está en el repo: se pide por parámetro, por
    $env:DEPLOY_TASK_PASSWORD o de forma interactiva, y queda solo dentro de la
    tarea programada (protegida por LSA).

    Requisito previo: C:\admon debe ser un clon de https://github.com/hector1516/AdmonApp
    (sin eso, `git pull` dentro de build.ps1 falla).
#>

param(
    [string]$Password = $env:DEPLOY_TASK_PASSWORD
)

$ErrorActionPreference = 'Stop'
$repo     = 'C:\admon'
$script   = Join-Path $repo 'deploy\build.ps1'
$taskName = 'AdmonBuild'
$user     = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Test-Path $script)) { throw "No existe $script (¿el repo está en $repo?)" }

if (-not $Password) {
    $sec = Read-Host "Contraseña de Windows para $user (solo queda en la tarea, no en el repo)" -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    $Password = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

$action = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $script + '"'
schtasks /create /tn $taskName /tr $action /sc once /st 12:00 /sd 31/12/2099 /ru $user /rp $Password /f | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'schtasks /create falló' }

Write-Output "Tarea $taskName registrada (una vez, 31/12/2099 -> nunca se auto-dispara)."
Write-Output "  ejecuta : $action"
Write-Output "  usuario : $user (modo batch, con contraseña)"
Write-Output "Desplegar:  schtasks /run /tn $taskName"
Write-Output "Ver log:     Get-Content $repo\build.log -Wait"
