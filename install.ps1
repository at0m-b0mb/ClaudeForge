# =============================================================================
# Claude Code Universal Setup — Windows PowerShell Bootstrap Script
# =============================================================================
# Run from PowerShell:
#   Set-ExecutionPolicy RemoteSigned -Scope CurrentUser  # one-time
#   iwr -useb https://raw.githubusercontent.com/at0m-b0mb/claude-code-setup/main/install.ps1 | iex
#
# Or clone and run locally:
#   git clone https://github.com/at0m-b0mb/claude-code-setup.git
#   cd claude-code-setup; .\install.ps1
# =============================================================================

$ErrorActionPreference = "Stop"
$REPO_URL = "https://github.com/at0m-b0mb/claude-code-setup"
$MIN_PYTHON_MAJOR = 3
$MIN_PYTHON_MINOR = 8

function Write-Header  { param($msg) Write-Host "`n$msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn    { param($msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Write-Err     { param($msg) Write-Host "  [X]  $msg" -ForegroundColor Red }
function Write-Info    { param($msg) Write-Host "  >    $msg" -ForegroundColor White }

# ── Banner ────────────────────────────────────────────────────────────────────
function Show-Banner {
    Write-Host ""
    Write-Host "   ____  _                    _         ____          _     " -ForegroundColor Cyan
    Write-Host "  / ___|| |__   ___  _ __ ___| |_ ___  / ___|___   __| | ___" -ForegroundColor Cyan
    Write-Host " | |    | '_ \ / _ \| '__/ __| __/ _ \| |   / _ \ / _  |/ _ \" -ForegroundColor Cyan
    Write-Host " | |___ | | | | (_) | |  \__ \ ||  __/| |__| (_) | (_| |  __/" -ForegroundColor Cyan
    Write-Host "  \____||_| |_|\___/|_|  |___/\__\___| \____\___/ \__,_|\___|" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "       Universal Installer & Hardware Recommender" -ForegroundColor White
    Write-Host ""
}

# ── Python Check ──────────────────────────────────────────────────────────────
function Find-Python {
    Write-Header "Checking Python..."
    $candidates = @("python", "python3", "py")
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge $MIN_PYTHON_MAJOR -and $minor -ge $MIN_PYTHON_MINOR) {
                    Write-Success "Found $cmd ($ver)"
                    return $cmd
                } else {
                    Write-Warn "$cmd $ver is too old (need >= $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR)"
                }
            }
        } catch { }
    }
    Write-Err "Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+ not found."
    Write-Host ""
    Write-Host "Install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Or use winget:  winget install Python.Python.3.12" -ForegroundColor Yellow
    exit 1
}

# ── Repo ──────────────────────────────────────────────────────────────────────
function Ensure-Repo {
    Write-Header "Getting the setup scripts..."

    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    if (Test-Path (Join-Path $scriptDir "main.py")) {
        Write-Info "Running from local clone: $scriptDir"
        return $scriptDir
    }

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Info "Cloning repository..."
        git clone --depth=1 $REPO_URL "$env:TEMP\claude-code-setup" 2>$null
        Write-Success "Cloned to $env:TEMP\claude-code-setup"
        return "$env:TEMP\claude-code-setup"
    }

    Write-Err "git not found and not running from a local clone."
    Write-Host "Download from: $REPO_URL" -ForegroundColor Yellow
    exit 1
}

# ── Deps ──────────────────────────────────────────────────────────────────────
function Install-PythonDeps {
    param($python, $repoDir)
    Write-Header "Installing Python dependencies..."
    & $python -m pip install --quiet --upgrade pip
    & $python -m pip install --quiet -r (Join-Path $repoDir "requirements.txt")
    Write-Success "Python dependencies installed"
}

# ── Run ───────────────────────────────────────────────────────────────────────
function Start-Setup {
    param($python, $repoDir)
    Write-Header "Launching Claude Code Setup..."
    Set-Location $repoDir
    & $python main.py @args
}

# ── Main ──────────────────────────────────────────────────────────────────────
Show-Banner
$python  = Find-Python
$repoDir = Ensure-Repo
Install-PythonDeps $python $repoDir
Start-Setup $python $repoDir
