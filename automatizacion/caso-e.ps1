param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Pasos
)

$ErrorActionPreference = "Stop"
$Aqui = $PSScriptRoot
$Api = "http://127.0.0.1:3080/v2/version"
if (-not $Pasos -or $Pasos.Count -eq 0) {
    $Pasos = @("construir", "iniciar", "licenciar")
}

function Paso($texto) { Write-Host "`n==> $texto" }
function Falla($texto) { Write-Host "error: $texto" -ForegroundColor Red; exit 1 }

function Invoke-Gns3ctl([string[]]$argumentos) {
    Push-Location $Aqui
    try {
        & uv run gns3ctl.py @argumentos
        if ($LASTEXITCODE -ne 0) { Falla "gns3ctl.py $($argumentos -join ' ') termino con error" }
    }
    finally { Pop-Location }
}

function Api-Responde {
    try {
        Invoke-WebRequest -Uri $Api -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    }
    catch { return $false }
}

function Env-Listo {
    $archivo = Join-Path $Aqui ".env"
    if (-not (Test-Path $archivo)) { return $false }
    $lineas = Get-Content $archivo
    $correo = ($lineas | Where-Object { $_ -match "^FORTICLOUD_CORREO=(.+)$" } | ForEach-Object { $Matches[1] }) -join ""
    $clave = ($lineas | Where-Object { $_ -match "^FORTICLOUD_CLAVE=(.+)$" } | ForEach-Object { $Matches[1] }) -join ""
    return ($correo -like "*@*") -and ($clave.Length -gt 0)
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Falla "falta uv. Instalalo con: winget install --id astral-sh.uv -e"
}
if ($Pasos -contains "destruir") {
    Falla "destruir borra el FortiGate y con el la licencia. Hazlo a mano si de verdad quieres."
}
if (($Pasos -contains "licenciar") -and -not (Env-Listo)) {
    Falla "llena FORTICLOUD_CORREO y FORTICLOUD_CLAVE en $Aqui\.env"
}
if (-not (Api-Responde)) {
    Falla "la VM de GNS3 no responde en $Api. Enciendela en VirtualBox y espera a que termine de arrancar."
}

$iniciado = $false
foreach ($p in $Pasos) {
    Paso $p
    switch ($p) {
        "iniciar" {
            Invoke-Gns3ctl @("iniciar")
            $iniciado = $true
        }
        "licenciar" {
            if ($iniciado) {
                Write-Host "esperando el arranque del FortiGate (3 minutos)"
                Start-Sleep -Seconds 180
            }
            Invoke-Gns3ctl @("licenciar")
        }
        default { Invoke-Gns3ctl @($p) }
    }
}

Paso "listo. No corras destruir: la licencia queda ligada a esta instancia del FortiGate."
