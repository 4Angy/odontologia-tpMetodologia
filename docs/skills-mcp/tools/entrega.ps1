# Empaqueta la entrega del TP en un unico .zip.
#
#   powershell -ExecutionPolicy Bypass -File docs/skills-mcp/tools/entrega.ps1 -Apellidos "Apellido1-Apellido2-Apellido3"
#
# El .zip queda en la raiz del repositorio con el nombre
# TP-Skills-MCP-<Apellidos>.zip y contiene la ficha, el informe, los PDFs,
# ENTREGA.md, las evidencias y las instrucciones de reproduccion.

param(
    [Parameter(Mandatory = $true)]
    [string]$Apellidos
)

$ErrorActionPreference = "Stop"

$raiz = Resolve-Path (Join-Path $PSScriptRoot "..\..\..")
$nombre = "TP-Skills-MCP-$Apellidos"
$destino = Join-Path $raiz "$nombre.zip"

if (Test-Path $destino) {
    Write-Host "Existe $destino; se reemplaza."
    Remove-Item $destino -Force
}

$incluidos = @(
    "ENTREGA.md",
    "README.md",
    "AGENTS.md",
    "CHANGES.md",
    "docs/skills-mcp/investigacion.md",
    "docs/skills-mcp/aplicacion.md",
    "docs/skills-mcp/preparacion.md",
    "docs/skills-mcp/revision-critica.md",
    "docs/skills-mcp/revision-critica-punto-8.md",
    "docs/skills-mcp/revision-critica-punto-8-c02.md",
    "docs/skills-mcp/mcp-configuracion.md",
    "docs/skills-mcp/informe-cumplimiento.md",
    "docs/skills-mcp/TP-investigacion-puntos-1-a-4.pdf",
    "docs/skills-mcp/TP-aplicacion-puntos-5-a-6.pdf",
    "docs/skills-mcp/TP-preparacion-puntos-7.pdf",
    "docs/skills-mcp/TP-revision-critica-puntos-8.pdf",
    "docs/skills-mcp/TP-informe-cumplimiento.pdf",
    "docs/skills-mcp/tools",
    ".atl/skill-registry.md",
    ".opencode/skills",
    "skills"
)

$stage = Join-Path $env:TEMP "entrega-$([guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
try {
    foreach ($item in $incluidos) {
        $origen = Join-Path $raiz $item
        if (-not (Test-Path $origen)) {
            Write-Warning "No existe (se omite): $item"
            continue
        }
        $destinoItem = Join-Path $stage $item
        $padre = Split-Path $destinoItem -Parent
        New-Item -ItemType Directory -Force -Path $padre | Out-Null
        if ((Get-Item $origen).PSIsContainer) {
            Copy-Item $origen $destinoItem -Recurse -Force
        } else {
            Copy-Item $origen $destinoItem -Force
        }
    }

    # Evidencias completas (registros de invocaciones y verificaciones).
    $evOrigen = Join-Path $raiz "docs/skills-mcp/evidencias"
    if (Test-Path $evOrigen) {
        Copy-Item $evOrigen (Join-Path $stage "docs/skills-mcp/evidencias") -Recurse -Force
    }

    # Nada de caches de Python dentro de la entrega.
    Get-ChildItem $stage -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $destino -Force
    $tam = [math]::Round((Get-Item $destino).Length / 1KB, 1)
    Write-Host "Entrega generada: $destino ($tam KB)"
}
finally {
    Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
}
