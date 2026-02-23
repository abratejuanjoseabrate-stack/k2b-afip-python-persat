# Script para configurar el remoto de git
Set-Location $PSScriptRoot

Write-Host "Configurando remoto de git..." -ForegroundColor Green

# Verificar si es un repositorio git
if (-not (Test-Path .git)) {
    Write-Host "Inicializando repositorio git..." -ForegroundColor Yellow
    git init
}

# Verificar remotos existentes
Write-Host "`nRemotos actuales:" -ForegroundColor Cyan
git remote -v

# Nuevo remoto
$newRemote = "https://gbk.kaizen2b.net/git/ddelias/pyAfipWs_fastapi_arca.git"

# Verificar si ya existe un remoto llamado 'origin'
$existingRemote = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nRemoto 'origin' ya existe: $existingRemote" -ForegroundColor Yellow
    Write-Host "¿Deseas cambiarlo? (S/N)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -eq "S" -or $response -eq "s" -or $response -eq "Y" -or $response -eq "y") {
        git remote set-url origin $newRemote
        Write-Host "Remoto 'origin' actualizado a: $newRemote" -ForegroundColor Green
    } else {
        Write-Host "Remoto no modificado." -ForegroundColor Yellow
    }
} else {
    Write-Host "`nAgregando remoto 'origin'..." -ForegroundColor Cyan
    git remote add origin $newRemote
    Write-Host "Remoto 'origin' agregado: $newRemote" -ForegroundColor Green
}

# Verificar rama actual
$currentBranch = git branch --show-current
if (-not $currentBranch) {
    Write-Host "`nNo hay rama actual. Creando rama 'main'..." -ForegroundColor Yellow
    git checkout -b main
    $currentBranch = "main"
} else {
    Write-Host "`nRama actual: $currentBranch" -ForegroundColor Cyan
}

# Mostrar estado final
Write-Host "`n=== Configuración final ===" -ForegroundColor Green
Write-Host "Remoto configurado:" -ForegroundColor Cyan
git remote -v
Write-Host "`nRama actual: $currentBranch" -ForegroundColor Cyan
Write-Host "`nPara hacer push:" -ForegroundColor Yellow
Write-Host "  git push -u origin $currentBranch" -ForegroundColor White
