#Requires -Version 5.1
<#
.SYNOPSIS
    米游社工具箱 (miHoYo ToolKit) 构建脚本

.DESCRIPTION
    v2.1.0 构建脚本。支持依赖安装、测试、lint、类型检查、EXE 打包（PyInstaller）、
    Docker 构建与缓存清理。版本号从 version_info.txt 解析（单一数据源），
    解析失败时回退到 pyproject.toml。

.PARAMETER Command
    要执行的构建命令：
      deps        - 安装依赖（含 dev/pinyin/excel/icon extras）+ Playwright 浏览器
      test        - 运行单元测试与覆盖率
      lint        - ruff check + ruff format --check
      type        - mypy 类型检查
      exe         - 打包 EXE（默认 onefile）
      exe-onefile - 打包单文件 EXE
      exe-onedir  - 打包文件夹模式（推荐，启动更快）
      docker      - 构建 Docker 镜像
      clean       - 清理缓存（需输入 YES 确认）
      all         - deps + lint + type + test + exe-onedir
      help        - 显示帮助

.EXAMPLE
    .\build.ps1 deps
    .\build.ps1 exe-onedir
    .\build.ps1 clean
#>

param(
    [Parameter(Position = 0)]
    [ValidateSet("deps", "test", "lint", "type", "exe", "exe-onefile", "exe-onedir", "docker", "clean", "all", "help")]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

# ============================================================
#  版本号（version_info.txt 优先，回退 pyproject.toml）
# ============================================================
function Get-ProjectVersion {
    if (Test-Path "version_info.txt") {
        $content = Get-Content "version_info.txt" -Raw
        $match = [regex]::Match($content, "ProductVersion', u'([\d.]+)'")
        if ($match.Success) { return $match.Groups[1].Value }
    }
    if (Test-Path "pyproject.toml") {
        $content = Get-Content "pyproject.toml" -Raw
        $match = [regex]::Match($content, '(?m)^version\s*=\s*"([^"]+)"')
        if ($match.Success) { return $match.Groups[1].Value }
    }
    return "0.0.0"
}
$VERSION = Get-ProjectVersion

# ============================================================
#  Python 探测（优先 .venv）
# ============================================================
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
    Write-Host "  miHoYo ToolKit Build Script v$VERSION"
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "  Usage: .\build.ps1 <command>"
    Write-Host ""
    Write-Host "  Commands:"
    Write-Host "    deps           Install dependencies + Playwright chromium"
    Write-Host "    test           Run pytest with coverage"
    Write-Host "    lint           Run ruff check + ruff format --check"
    Write-Host "    type           Run mypy type check"
    Write-Host "    exe            Build single-file EXE (default onefile)"
    Write-Host "    exe-onefile    Build single-file EXE"
    Write-Host "    exe-onedir     Build directory mode"
    Write-Host "    docker         Build Docker image"
    Write-Host "    clean          Clean temp files (type YES to confirm)"
    Write-Host "    all            Run deps + lint + type + test + exe-onedir"
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
    Write-Host "[INFO] Installing dependencies (editable, with extras)..."
    & $py.Pip install -e ".[dev,pinyin,excel,icon]"
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed" }
    Write-Host "[INFO] Installing Playwright chromium browser..."
    & $py.Python -m playwright install chromium
    if ($LASTEXITCODE -ne 0) { throw "Playwright browser installation failed" }
    Write-Host "[OK] Dependencies installed"
}

# ============================================================
#  test
# ============================================================
function Invoke-Test {
    Write-Host "[INFO] Running tests with coverage..."
    & $py.Python -m pytest --cov --cov-report=term-missing
    if ($LASTEXITCODE -ne 0) { throw "Some tests failed" }
    Write-Host "[OK] All tests passed"
}

# ============================================================
#  lint
# ============================================================
function Invoke-Lint {
    Write-Host "[INFO] Running ruff check..."
    & $py.Python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "ruff check failed" }
    Write-Host "[INFO] Running ruff format --check..."
    & $py.Python -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { throw "ruff format check failed" }
    Write-Host "[OK] Lint check passed"
}

# ============================================================
#  type
# ============================================================
function Invoke-Type {
    Write-Host "[INFO] Running mypy..."
    & $py.Python -m mypy
    if ($LASTEXITCODE -ne 0) { throw "mypy check failed" }
    Write-Host "[OK] Type check passed"
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

    # EXE 不打包浏览器，运行时由用户手动安装
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
    docker build -t mihoyo-toolkit:$VERSION -t mihoyo-toolkit:latest .
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
    Write-Host "[OK] Docker image built: mihoyo-toolkit:$VERSION"
}

# ============================================================
#  clean
# ============================================================
function Invoke-Clean {
    Write-Host "[INFO] Will clean:"
    Write-Host "  - __pycache__ dirs and *.pyc / *.pyo files"
    Write-Host "  - logs/*.log files"
    Write-Host "  - build/ and dist/ temp dirs"
    Write-Host "  - .pytest_cache / .ruff_cache / .mypy_cache"
    Write-Host "  - .coverage / htmlcov"
    Write-Host "  (skips .venv / .git / browser / data / har / resources)"
    Write-Host ""

    $confirm = Read-Host "Confirm? Type YES to continue"
    if ($confirm -ne "YES") {
        Write-Host "[INFO] Clean cancelled"
        return
    }

    Write-Host ""
    Write-Host "[INFO] Cleaning..."
    $count = 0
    $skip = '\\\.venv\\|\\\.git\\|\\browser\\|\\data\\|\\har\\|\\resources\\'

    # __pycache__ dirs
    Get-ChildItem -Path $ProjectDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $skip } |
        ForEach-Object {
            Write-Host "  Removing: $($_.FullName.Substring($ProjectDir.Length + 1))"
            Remove-Item $_.FullName -Recurse -Force
            $count++
        }

    # *.pyc / *.pyo files
    Get-ChildItem -Path $ProjectDir -Recurse -File -Include "*.pyc", "*.pyo" -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $skip } |
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

    # build/ dist/ .pytest_cache/ .ruff_cache/ .mypy_cache/ htmlcov/
    foreach ($d in @("build", "dist", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov")) {
        $dir = Join-Path $ProjectDir $d
        if (Test-Path $dir) {
            Write-Host "  Removing: $d\"
            Remove-Item $dir -Recurse -Force
            $count++
        }
    }

    # .coverage
    $coverage = Join-Path $ProjectDir ".coverage"
    if (Test-Path $coverage) {
        Write-Host "  Removing: .coverage"
        Remove-Item $coverage -Force
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
    "lint"        { Invoke-Lint }
    "type"        { Invoke-Type }
    "exe"         { Invoke-Exe -Mode "onefile" }
    "exe-onefile" { Invoke-Exe -Mode "onefile" }
    "exe-onedir"  { Invoke-Exe -Mode "onedir" }
    "docker"      { Invoke-Docker }
    "clean"       { Invoke-Clean }
    "all"         { Invoke-Deps; Invoke-Lint; Invoke-Type; Invoke-Test; Invoke-Exe -Mode "onedir" }
    default       { Show-Help }
}
