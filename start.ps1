# JobMate - lance le backend (port 8000) et le site (port 3000), puis ouvre le navigateur.
# Usage : double-clic sur start.bat, ou :  powershell -ExecutionPolicy Bypass -File .\start.ps1
# Le site tourne en mode production (plus leger en memoire que "npm run dev").
# Il est recompile automatiquement apres un "git pull".
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# --- verifications (aucune valeur secrete n'est affichee)
$backendEnv = Join-Path $root "backend\.env"
if (-not (Test-Path $backendEnv)) {
  Write-Host "backend\.env est absent : copiez backend\.env.example en backend\.env et remplissez-le." -ForegroundColor Red
  exit 1
}
foreach ($key in @("DATABASE_URL", "GROQ_API_KEY")) {
  if (-not (Select-String -Path $backendEnv -Pattern "^\s*$key\s*=\s*\S" -Quiet)) {
    Write-Host "backend\.env : la ligne $key est vide ou absente." -ForegroundColor Red
    exit 1
  }
}
if (-not (Test-Path (Join-Path $root "web\node_modules"))) {
  Write-Host "Dependances absentes : lancez d'abord setup.ps1." -ForegroundColor Red
  exit 1
}

# --- backend
Write-Host "Demarrage du backend sur http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='JobMate backend'; Set-Location '$root\backend'; py -m uvicorn app.main:app --port 8000"

# --- site : recompile si le code a change depuis la derniere compilation
$commit = (git -C $root rev-parse HEAD 2>$null)
$stamp = Join-Path $root "web\.next\jobmate-commit.txt"
$built = if (Test-Path $stamp) { Get-Content $stamp -Raw } else { "" }
if (-not (Test-Path (Join-Path $root "web\.next\BUILD_ID")) -or ("$built".Trim() -ne "$commit".Trim())) {
  Write-Host "Compilation du site (1 a 2 minutes, seulement apres une mise a jour)..." -ForegroundColor Cyan
  npm --prefix web run build
  if ($LASTEXITCODE -ne 0) { Write-Host "La compilation du site a echoue (voir ci-dessus)." -ForegroundColor Red; exit 1 }
  Set-Content -Encoding ascii -Path $stamp -Value $commit
}
Write-Host "Demarrage du site sur http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='JobMate site'; Set-Location '$root\web'; npm run start"

# --- attendre que tout reponde, puis ouvrir le navigateur
function Wait-Url($url, $label) {
  for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $url | Out-Null; return $true } catch { Start-Sleep -Seconds 2 }
  }
  Write-Host "$label ne repond pas encore : regardez sa fenetre pour l'erreur." -ForegroundColor Yellow
  return $false
}
if (Wait-Url "http://localhost:8000/health" "Le backend") {
  $health = Invoke-RestMethod http://localhost:8000/health
  Write-Host ("Backend : status={0}, base={1}, IA={2}" -f $health.status, $health.database, $health.intelligence) -ForegroundColor Green
}
if (Wait-Url "http://localhost:3000/login" "Le site") {
  Start-Process "http://localhost:3000"
  Write-Host "JobMate est lance. Pour l'arreter, fermez les deux fenetres 'JobMate backend' et 'JobMate site'." -ForegroundColor Green
}
