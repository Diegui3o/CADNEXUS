param(
    [Parameter(Mandatory)] [string] $CarpetaPlanos,
    [Parameter(Mandatory)] [string] $CarpetaFirmas,
    [Parameter(Mandatory)] [string] $CarpetaSalida,
    [Parameter(Mandatory)] [string] $Python
)

$env:PYTHONDONTWRITEBYTECODE = '1'
& $Python (Join-Path $PSScriptRoot 'piloto.py') --planos $CarpetaPlanos --firmas $CarpetaFirmas --salida $CarpetaSalida
if ($LASTEXITCODE -ne 0) {
    throw "El piloto termino con codigo $LASTEXITCODE."
}
