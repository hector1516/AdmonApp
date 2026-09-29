<#
    build.ps1 — Build + deploy de la app Admon (FastAPI + Svelte) en el contenedor `admon`.

    Patrón equivalente al de WorkersAdmon: se ejecuta desde la raíz del repo en el
    ServerVM (C:\admon) y deja el resultado en build.log terminando con "FIN rc=<n>".
    Lanzamiento manual:  schtasks /run /tn AdmonBuild     (o powershell -File deploy\build.ps1)

    Pasos: git pull -> npm ci -> npm run build -> docker build (sat01) -> retag
          (rollback<-latest, latest/legends<-sat01) -> recrear el contenedor -> health.

    Decisiones de diseño (lecciones del 2026-09-26/27, ver docs/DEPLOY.md):
    - La configuración del contenedor (env con credenciales, puertos, binds, red,
      restart policy) se LEE del contenedor existente con `docker inspect`: nunca se
      hardcodean secretos ni se redeclaran a mano.
    - El `stop` puede reportar timeout y aun así aplicarse. Antes de renombrar se
      VERIFICA que el contenedor quedó detenido; si sigue corriendo se aborta y
      producción queda intacta (ese error tumbó admon ~2 min una vez).
    - Si el health check falla, se hace rollback: se borra el contenedor nuevo, se
      renombra y arranca el anterior.
#>

# 'Continue' (no 'Stop'): con 'Stop', cualquier escritura en stderr de un comando
# nativo (npm, docker) lanza NativeCommandError y Mata el script en seco — sin
# escribir ni el ERROR ni el FIN rc= en el log (pasó el 2026-09-27 con npm ci).
# El script valida cada paso explícitamente con $LASTEXITCODE, que es la forma
# correcta de detectar fallos de comandos nativos.
$ErrorActionPreference = 'Continue'
# Esta tarea corre en modo batch (sin consola). Si git no tiene credenciales,
# NO falla: abre un prompt por stdin y se queda esperando para siempre, y el
# watchdog solo puede reportar un timeout sin explicar nada. Con esta variable
# git falla al instante y con mensaje legible en vez de colgarse.
$env:GIT_TERMINAL_PROMPT = '0'

$root = Split-Path -Parent $PSScriptRoot
$log  = Join-Path $root 'build.log'
$image = 'hub-admon'
$newTag = 'sat01'
$healthUrl = 'http://localhost:8103/api/health'
$healthTimeoutSec = 60
# Servidor SQL del ecosistema = IP LOCAL (misma que usan Field y workersadmon).
# Es lo único que no se hereda del contenedor actual, para no arrastrar la IP de
# la VPN con la que se creó el contenedor la primera vez.
$DbServerLocal = '10.188.141.15'

function Log($msg) {
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
    Write-Output $line
    Add-Content -Path $log -Value $line
}

# Windows PowerShell 5.1 + $ErrorActionPreference='Stop' convierte CUALQUIER
# salida por stderr de un comando nativo en error terminante. docker build
# (BuildKit) escribe TODO su progreso por stderr, asi que sin esto el script
# muere en la linea 2 del build. Para esos comandos se baja a 'Continue' y se
# juzga por $LASTEXITCODE, que es lo que corresponde.
function Run-Native {
    param([scriptblock]$Cmd)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { & $Cmd } finally { $ErrorActionPreference = $prev }
}

function Fail($msg) {
    Log "ERROR: $msg"
    Add-Content -Path $log -Value ("FIN rc=1")
    exit 1
}

Set-Location $root
Set-Content -Path $log -Value ("=== build Admon {0} ===" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Log "root=$root"

# ── 0. Preflight ───────────────────────────────────────────────────────────────
if (-not (Test-Path (Join-Path $root 'package.json'))) { Fail 'no package.json: esto no es la raíz del repo' }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail 'docker no está en PATH' }
Log ("docker: " + (docker version --format '{{.Server.Version}}' 2>&1))

# ── 1. Código actualizado ─────────────────────────────────────────────────────
Log 'git pull --ff-only'
Run-Native { git pull --ff-only 2>&1 } | ForEach-Object { Log "  $_" }
if ($LASTEXITCODE -ne 0) { Fail 'git pull falló' }
$commit = (git rev-parse --short HEAD)
Log "commit=$commit"

# ── 2. Dependencias + build del frontend (dist/ está gitignored) ──────────────
# El ServerVM NO tiene node/npm instalados, así que el frontend se compila en el
# equipo de desarrollo y se sube el dist/ ya generado (por scp) a C:\admon\dist.
# Si algún día se instala node aquí, el script vuelve a compilarlo.
$hasNode = $null -ne (Get-Command npm -ErrorAction SilentlyContinue)
if ($hasNode) {
    Log 'npm ci'
    npm ci 2>&1 | Select-Object -Last 5 | ForEach-Object { Log "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Log 'npm ci fallo; reintento con npm install'
        npm install 2>&1 | Select-Object -Last 5 | ForEach-Object { Log "  $_" }
        if ($LASTEXITCODE -ne 0) { Fail 'npm install fallo' }
    }
    Log 'npm run build (genera dist/)'
    npm run build 2>&1 | Select-Object -Last 8 | ForEach-Object { Log "  $_" }
    if ($LASTEXITCODE -ne 0) { Fail 'npm run build fallo' }
} else {
    # El ServerVM no tiene node/npm en el host. En vez de comerse un dist/
    # viejo (así se perdieron las pestañas y las MAC: la imagen horneó un
    # index-*.js de días atrás y borró lo que hotsync ya había publicado),
    # se compila acá mismo con el mismo node que usa hotsync.sh: un contenedor
    # efímero node:20-alpine. Así el rebuild siempre hornea el código recién
    # hecho git pull, no el dist/ que quedó en disco.
    Log 'sin npm en el host → compilando el frontend en node:20-alpine (docker)'
    docker run --rm -v "${root}:/app" -v /app/node_modules -w /app node:20-alpine `
        sh -c 'npm ci && npm run build' 2>&1 | Select-Object -Last 8 | ForEach-Object { Log "  $_" }
    if ($LASTEXITCODE -ne 0) { Fail 'build del frontend en docker falló (producción NO se tocó)' }
    if (-not (Test-Path (Join-Path $root 'dist\assets'))) {
        Fail 'el build en docker no dejó dist/ (producción NO se tocó)'
    }
}
$bundle = (Get-ChildItem -Path (Join-Path $root 'dist\assets') -Filter 'index-*.js' -ErrorAction SilentlyContinue | Select-Object -First 1).Name
if (-not $bundle) { Fail 'no se encontró dist/assets/index-*.js tras el build' }
Log "bundle=$bundle"

# ── 3. Imagen ─────────────────────────────────────────────────────────────────
Log "docker build -t ${image}:${newTag} ."
Run-Native { docker build --progress=plain -t "${image}:${newTag}" . 2>&1 } | ForEach-Object { Log "  $_" }
if ($LASTEXITCODE -ne 0) { Fail "docker build fallo (rc=$LASTEXITCODE)" }
$newId = (docker images --format '{{.ID}}' "${image}:${newTag}" | Select-Object -First 1)
$oldLatest = (docker images --format '{{.ID}}' "${image}:latest" | Select-Object -First 1)
Log "imagen nueva=${image}:${newTag} ($newId)  anterior latest=$oldLatest"

# ── 4. Retag: el anterior queda como rollback ────────────────────────────────
if ($oldLatest -and $oldLatest -ne $newId) {
    docker tag "${image}:$($oldLatest)" "${image}:rollback" | Out-Null
    Log "rollback <- $oldLatest"
}
foreach ($t in @('latest', 'legends')) {
    docker tag "${image}:${newTag}" "${image}:$t" | Out-Null
    Log "$t <- ${newTag}"
}

# ── 5. Recrear el contenedor reutilizando su config actual ────────────────────
$existe = docker ps -a --filter 'name=^admon$' --format '{{.Names}}'
if ($existe -notcontains 'admon') { Fail 'no existe el contenedor admon: no sé su configuración' }
$inspect = docker inspect admon 2>$null | ConvertFrom-Json
if (-not $inspect) { Fail 'docker inspect admon no devolvió configuración' }
$c = $inspect[0]
Log "contenedor actual: $($c.Id.Substring(0,12)) image=$($c.Config.Image) running=$($c.State.Running)"

$runArgs = @('run', '-d', '--name', 'admon')
if ($c.HostConfig.RestartPolicy.Name) { $runArgs += @('--restart', $c.HostConfig.RestartPolicy.Name) }
if ($c.HostConfig.NetworkMode)          { $runArgs += @('--network', $c.HostConfig.NetworkMode) }
foreach ($b in @($c.HostConfig.Binds))    { if ($b) { $runArgs += @('-v', $b) } }
foreach ($p in $c.HostConfig.PortBindings.PSObject.Properties) {
    foreach ($b in @($p.Value)) {
        if ($null -eq $b) { continue }
        $hp = if ($b.HostIp) { "$($b.HostIp):$($b.HostPort)" } else { $b.HostPort }
        $runArgs += @('-p', "${hp}:$($p.Name)")
    }
}
# Env del contenedor: se clona el actual (para no perder las credenciales) y se
# sobrescribe la BD. El contenedor nació apuntando a la IP de la VPN
# (172.26.117.220) y, como acá se hereda su env, ese valor se arrastraba sola
# vez tras otra. Se fija en la IP LOCAL del servidor SQL para que la app no
# dependa de cómo se haya creado el contenedor.
$envList = @(@($c.Config.Env) | Where-Object { $_ })
$envList = $envList | ForEach-Object {
    if ($_ -like 'HUB_DB_SERVER=*') { "HUB_DB_SERVER=$DbServerLocal" } else { $_ }
}
if (-not ($envList | Where-Object { $_ -like 'HUB_DB_SERVER=*' })) {
    $envList += "HUB_DB_SERVER=$DbServerLocal"
}

# Secret de escritura del panel del kiosco (control remoto de la TV de la
# oficina). Vive como GitHub Secret y NO está en el repo. El rebuild se lanza
# por schtasks (proceso de otra sesión), así que la cadena de entorno del
# workflow no llega acá: el workflow deposita el valor en
# C:\admon\.secrets\panel_token (fuera de git) y este script lo lee de ahí.
#
# Precedencia: entorno ($env) > archivo .secrets\panel_token > env ya presente
# en el contenedor. Si no está en ninguno, se avisa y sigue: la app degrada con
# un mensaje claro en la UI, no revienta.
$panelToken = $env:HUB_PANEL_TOKEN
# Ruta ABSOLUTA a propósito (no $root): la tarea programada AdmonBuild puede
# resolver el script con otro $PSScriptRoot, y con $root el archivo no se
# encontraba. Es la misma ruta que escribe el workflow.
$tokenFile = 'C:\admon\.secrets\panel_token'
if (Test-Path $tokenFile) {
    Log ("HUB_PANEL_TOKEN: existe el archivo {0} ({1} bytes)" -f $tokenFile, (Get-Item $tokenFile).Length)
} else {
    Log ("HUB_PANEL_TOKEN: no existe {0}" -f $tokenFile)
}
if ((-not $panelToken) -and (Test-Path $tokenFile)) {
    $panelToken = (Get-Content $tokenFile -Raw).Trim()
    if ($panelToken) { Log 'HUB_PANEL_TOKEN: leido de .secrets\panel_token' }
}
if ($panelToken) {
    $envList = $envList | Where-Object { $_ -notlike 'HUB_PANEL_TOKEN=*' }
    $envList += "HUB_PANEL_TOKEN=$panelToken"
    Log 'HUB_PANEL_TOKEN: presente -> se inyecta al contenedor'
} elseif ($envList | Where-Object { $_ -like 'HUB_PANEL_TOKEN=*' }) {
    Log 'HUB_PANEL_TOKEN: ya venía en el contenedor -> se conserva'
} else {
    Log 'AVISO · HUB_PANEL_TOKEN no esta en el entorno, ni en .secrets\, ni en el contenedor.'
    Log '         El control remoto de la TV quedara deshabilitado (la app lo avisa).'
}

foreach ($e in $envList) { $runArgs += @('-e', $e) }
$runArgs += "${image}:latest"
# Oculta los secretos: el log se lee en pantalla y a veces se comparte.
$logArgs = $runArgs | ForEach-Object {
    if ($_ -match '^(.*(PASSWORD|SECRET|TOKEN|API_KEY)=)(.*)$') { $Matches[1] + '****' } else { $_ }
}
Log (" recrear: " + ($logArgs -join ' '))

# stop con verificación: el timeout del cliente no significa que no se aplicó
Log 'stop del contenedor actual (t=5)'
Run-Native { docker stop -t 5 admon 2>&1 } | ForEach-Object { Log "  $_" }
$stillRunning = (docker inspect -f '{{.State.Running}}' admon 2>$null)
if ($stillRunning -eq 'true') {
    Log 'el contenedor sigue corriendo: NO se renombra, producción intacta'
    Fail 'stop no completó; abortado para no dejar admon caído'
}
Log 'contenedor detenido OK'

docker rename admon admon_old
if ($LASTEXITCODE -ne 0) { Fail 'rename a admon_old falló' }

$newCid = docker @runArgs
if ($LASTEXITCODE -ne 0) {
    Log "docker run falló: $newCid"
    docker rename admon_old admon | Out-Null
    docker start admon | Out-Null
    Fail 'docker run falló; se restauró el contenedor anterior'
}
$newId12 = (($newCid | Select-Object -Last 1).ToString().Trim()).Substring(0, 12)
Log "contenedor nuevo: $newId12"

# ── 6. Health check (con rollback si no responde) ────────────────────────────
Log "health check en $healthUrl (máx ${healthTimeoutSec}s)"
$healthy = $false
for ($i = 0; $i -lt $healthTimeoutSec; $i += 3) {
    Start-Sleep -Seconds 3
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch { }
}
if (-not $healthy) {
    Log 'health FALLÓ → rollback al contenedor anterior'
    docker rm -f admon | Out-Null
    docker rename admon_old admon | Out-Null
    docker start admon | Out-Null
    Fail 'health check falló; restaurado el contenedor anterior'
}
Log "health OK (bundle $bundle en producción)"

# ── 7. Limpieza (solo el contenedor anterior; nada de prune global) ──────────
Run-Native { docker rm -f admon_old 2>&1 } | ForEach-Object { Log "  $_" }

Log "imagen activa: ${image}:latest ($newId) | rollback: $oldLatest"
Log "commit desplegado: $commit"
Add-Content -Path $log -Value ("FIN rc=0")
exit 0
