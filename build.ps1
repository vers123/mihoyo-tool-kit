#Requires -Version 5.1
<#
.SYNOPSIS
    miHoYo ToolKit Build Script v1.3.0

.DESCRIPTION
    Build script for miHoYo ToolKit. Supports dependency installation,
    testing, EXE packaging (PyInstaller), Docker build, and cache cleanup.

.PARAMETER Command
    The build command to execute:
      deps        - Install dependencies (incl. PyInstaller)
      test        - Run unit tests
      exe         - Build EXE (default: onefile)
      exe-onefile - Build single-file EXE
      exe-onedir  - Build directory mode
      docker      - Build Docker image
      clean       - Clean temp files (with confirmation)
      all         - Run deps + test + exe-onefile
      help        - Show this help

.EXAMPLE
    .\build.ps1 deps
    .\build.ps1 exe-onedir
    .\build.ps1 clean
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("deps", "test", "exe", "exe-onefile", "exe-onedir", "docker", "clean", "all", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

# Detect Python
function Get-Python {
    if (Test-Path ".venv\Scripts\python.exe") {
        Write-Host "[INFO] Using venv: .venv"
        return @{
            Python = ".venv\Scripts\python.exe"
            Pip    = ".venv\Scripts\pip.exe"
        }
    }
    Write-Host "[INFO] Using system Python"
    return @{
        Python = "python"
        Pip    = "pip"
    }
}

$py = Get-Python

# ============================================================
#  Help
# ============================================================
function Show-Help {
    Write-Host "============================================================"
    Write-Host "  miHoYo ToolKit Build Script v1.3.0"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  Usage: .\build.ps1 <command>"
    Write-Host ""
    Write-Host "  Commands:"
    Write-Host "    deps           Install dependencies (incl. PyInstaller)"
    Write-Host "    test           Run unit tests"
    Write-Host "    exe            Build single-file EXE (default onefile)"
    Write-Host "    exe-onefile    Build single-file EXE"
    Write-Host "    exe-onedir     Build directory mode"
    Write-Host "    docker         Build Docker image"
    Write-Host "    clean          Clean temp files (type YES to confirm)"
    Write-Host "    all            Run deps + test + exe-onefile"
    Write-Host "    help           Show this help"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\build.ps1 deps"
    Write-Host "    .\build.ps1 exe-onedir"
    Write-Host "    .\build.ps1 clean"
    Write-Host ""
}

# ============================================================
#  deps
# ============================================================
function Invoke-Deps {
    Write-Host "[INFO] Installing dependencies..."
    & $py.Pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
    Write-Host "[INFO] Installing PyInstaller..."
    & $py.Pip install pyinstaller
    Write-Host "[OK] Dependencies installed"
}

# ============================================================
#  test
# ============================================================
function Invoke-Test {
    Write-Host "[INFO] Running unit tests..."
    & $py.Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Some tests failed" }
    Write-Host "[OK] All tests passed"
}

# ============================================================
#  exe
# ============================================================
function Invoke-Exe {
    param([string]$Mode = "onefile")

    Write-Host "[INFO] Building EXE ($Mode)..."

    # Ensure PyInstaller
    & $py.Python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[INFO] Installing PyInstaller..."
        & $py.Pip install pyinstaller
    }

    # Build (EXE 不打包浏览器，运行时由用户手动安装)
    $env:PYI_MODE = $Mode
    & $py.Python -m PyInstaller app.spec --noconfirm --clean
    if ($LASTEXITCODE -ne 0) { throw "Build failed" }

    Write-Host ""
    Write-Host "[OK] Build complete!"
    if ($Mode -eq "onefile") {
        Write-Host "     Output: dist\米游社工具箱.exe"
    } else {
        Write-Host "     Output: dist\米游社工具箱\"
    }
}

# ============================================================
#  docker
# ============================================================
function Invoke-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker not found"
    }
    Write-Host "[INFO] Building Docker image..."
    docker build -t mihoyo-toolkit:1.3.0 -t mihoyo-toolkit:latest .
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
    Write-Host "[OK] Docker image built: mihoyo-toolkit:1.3.0"
}

# ============================================================
#  clean
# ============================================================
function Invoke-Clean {
    Write-Host "[INFO] Will clean:"
    Write-Host "  - __pycache__ dirs and *.pyc files"
    Write-Host "  - logs/*.log files"
    Write-Host "  - build/ and dist/ temp dirs"
    Write-Host "  - .pytest_cache"
    Write-Host ""

    $confirm = Read-Host "Confirm? Type YES to continue"
    if ($confirm -ne "YES") {
        Write-Host "[INFO] Clean cancelled"
        return
    }

    Write-Host ""
    Write-Host "[INFO] Cleaning..."
    $count = 0

    # __pycache__ dirs
    Get-ChildItem -Path $ProjectDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "\\\.venv\\|\\\.git\\|\\browser\\|\\data\\|\\logs\\|\\har\\" } |
        ForEach-Object {
            Write-Host "  Removing: $($_.FullName.Substring($ProjectDir.Length + 1))"
            Remove-Item $_.FullName -Recurse -Force
            $count++
        }

    # *.pyc files
    Get-ChildItem -Path $ProjectDir -Recurse -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch "\\\.venv\\|\\\.git\\|\\browser\\|\\data\\|\\logs\\|\\har\\" } |
        ForEach-Object {
            Write-Host "  Removing: $($_.FullName.Substring($ProjectDir.Length + 1))"
            Remove-Item $_.FullName -Force
            $count++
        }

    # logs/*.log
    $logsDir = Join-Path $ProjectDir "logs"
    if (Test-Path $logsDir) {
        Get-ChildItem -Path $logsDir -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "  Removing: logs\$($_.Name)"
            Remove-Item $_.FullName -Force
            $count++
        }
    }

    # build/ dist/
    foreach ($d in @("build", "dist")) {
        $dir = Join-Path $ProjectDir $d
        if (Test-Path $dir) {
            Write-Host "  Removing: $d\"
            Remove-Item $dir -Recurse -Force
            $count++
        }
    }

    # .pytest_cache
    $pytestCache = Join-Path $ProjectDir ".pytest_cache"
    if (Test-Path $pytestCache) {
        Write-Host "  Removing: .pytest_cache\"
        Remove-Item $pytestCache -Recurse -Force
        $count++
    }

    Write-Host ""
    Write-Host "[OK] Clean complete, removed $count items"
}

# ============================================================
#  Dispatch
# ============================================================
switch ($Command) {
    "help"        { Show-Help }
    "deps"        { Invoke-Deps }
    "test"        { Invoke-Test }
    "exe"         { Invoke-Exe -Mode "onefile" }
    "exe-onefile" { Invoke-Exe -Mode "onefile" }
    "exe-onedir"  { Invoke-Exe -Mode "onedir" }
    "docker"      { Invoke-Docker }
    "clean"       { Invoke-Clean }
    "all"         { Invoke-Deps; Invoke-Test; Invoke-Exe -Mode "onefile" }
    default       { Show-Help }
}
