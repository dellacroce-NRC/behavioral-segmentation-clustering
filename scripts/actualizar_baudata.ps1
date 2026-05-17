[CmdletBinding()]
param(
    [switch]$SkipPostHog,
    [switch]$CompareModels,
    [string]$StartDate,
    [string]$EndDate,
    [string]$LegacyScript = ".\scripts\posthog.py"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "outputs\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "actualizacion_baudata_$Stamp.log"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Python = if (Test-Path $VenvPython) { $VenvPython } else { "python" }

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Invoke-PipelineCommand {
    param(
        [string]$StepName,
        [string[]]$Command
    )

    Write-Log ""
    Write-Log "=== $StepName ==="
    Write-Log ("Comando: " + ($Command -join " "))

    $exe = $Command[0]
    $args = @()
    if ($Command.Count -gt 1) {
        $args = $Command[1..($Command.Count - 1)]
    }

    & $exe @args 2>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo el paso '$StepName' con codigo $LASTEXITCODE. Revisa el log: $LogPath"
    }
}

function Assert-ProjectFile {
    param([string]$RelativePath)
    $path = Join-Path $ProjectRoot $RelativePath
    if (-not (Test-Path $path)) {
        throw "No se encontro el archivo requerido: $path"
    }
}

Push-Location $ProjectRoot
try {
    Write-Log "Iniciando actualizacion BauData"
    Write-Log "Proyecto: $ProjectRoot"
    Write-Log "Python: $Python"
    Write-Log "Log: $LogPath"

    Assert-ProjectFile "scripts\modeloml_baudata_local.py"
    Assert-ProjectFile "scripts\crear_analisis_empresas.py"

    if ($StartDate -and -not $EndDate) {
        throw "Si usas -StartDate tambien debes usar -EndDate."
    }
    if ($EndDate -and -not $StartDate) {
        throw "Si usas -EndDate tambien debes usar -StartDate."
    }

    if (-not $SkipPostHog) {
        Assert-ProjectFile "scripts\posthog_historico_local.py"
        $posthogArgs = @($Python, ".\scripts\posthog_historico_local.py")

        $legacyPath = Join-Path $ProjectRoot $LegacyScript
        $hasEnvCreds = $env:POSTHOG_PROJECT_ID -and $env:POSTHOG_API_KEY
        if (-not $hasEnvCreds -and (Test-Path $legacyPath)) {
            $posthogArgs += @("--legacy-script", $LegacyScript)
        }

        if ($StartDate -and $EndDate) {
            $posthogArgs += @("--start", $StartDate, "--end", $EndDate)
        }

        Invoke-PipelineCommand "1. Descargar datos de PostHog" $posthogArgs
    }
    else {
        Write-Log "1. Descargar datos de PostHog: omitido por -SkipPostHog"
    }

    Invoke-PipelineCommand "2. Regenerar clustering K3" @(
        $Python,
        ".\scripts\modeloml_baudata_local.py",
        "--clusters", "3",
        "--output-dir", ".\outputs\kmeans_k3"
    )

    Invoke-PipelineCommand "3. Regenerar capa B2B para Power BI" @(
        $Python,
        ".\scripts\crear_analisis_empresas.py"
    )

    if ($CompareModels) {
        Assert-ProjectFile "scripts\comparar_modelos_clustering.py"
        Invoke-PipelineCommand "4. Comparar modelos de clustering" @(
            $Python,
            ".\scripts\comparar_modelos_clustering.py"
        )
    }
    else {
        Write-Log "4. Comparar modelos: omitido. Usa -CompareModels si quieres correrlo."
    }

    Write-Log ""
    Write-Log "Actualizacion local terminada correctamente."
    Write-Log "Archivos clave para Power BI:"
    Write-Log "- outputs\kmeans_k3\resultados_clustering_posthog.csv"
    Write-Log "- outputs\company_analysis\empresas_powerbi.csv"
    Write-Log "- outputs\company_analysis\usuarios_empresas_powerbi.csv"
    Write-Log "Siguiente paso: abre Power BI Desktop y presiona Inicio > Actualizar."
    Write-Host ""
    Write-Host "LISTO. Ahora en Power BI presiona Inicio > Actualizar." -ForegroundColor Green
    Write-Host "Log guardado en: $LogPath"
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "La actualizacion fallo. Revisa el log:" -ForegroundColor Red
    Write-Host $LogPath
    exit 1
}
finally {
    Pop-Location
}
