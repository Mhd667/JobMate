# JobMate - installation (une seule fois, puis apres chaque "git pull" qui ajoute des dependances)
# Usage : clic droit > Executer avec PowerShell, ou :  powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "1/3 Dependances du backend (Python)..." -ForegroundColor Cyan
py -m pip install -r backend\requirements.txt

Write-Host "2/3 Dependances du site (Node)..." -ForegroundColor Cyan
npm --prefix web install

Write-Host "3/3 Configuration..." -ForegroundColor Cyan
$webEnv = Join-Path $root "web\.env.local"
if (-not (Test-Path $webEnv)) {
  # Valeurs publiques uniquement (URL du projet et cle publishable). Aucun secret ici.
  @"
NEXT_PUBLIC_SUPABASE_URL=https://mdiucfqnqavplfflzbfv.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_mA0e5QwJUcdLmGqkgGrW3A_zlAgkynV
NEXT_PUBLIC_API_URL=/api
"@ | Set-Content -Encoding ascii $webEnv
  Write-Host "   web\.env.local cree." -ForegroundColor Green
} else {
  Write-Host "   web\.env.local existe deja." -ForegroundColor Green
}
if (-not (Test-Path (Join-Path $root "backend\.env"))) {
  Write-Host "   ATTENTION : backend\.env est absent. Copiez backend\.env.example en backend\.env et remplissez-le." -ForegroundColor Yellow
}
Write-Host "Installation terminee. Lancez JobMate avec start.bat (ou .\start.ps1)." -ForegroundColor Green
