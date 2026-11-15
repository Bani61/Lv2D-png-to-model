# Lv2D-png-to-model smoke test.
# Usage:
#   powershell -ExecutionPolicy Bypass -File tests\smoke.ps1
#   powershell -ExecutionPolicy Bypass -File tests\smoke.ps1 -Full -Psd path\to\model.psd
# Exit code: 0 when no FAIL (SKIP is acceptable), 1 otherwise.

param(
    [switch]$Full,
    [string]$Psd = "",
    [string]$Psd2LiveExe = "D:\Live2D-Fullbody\tools\PSD2Live-3.6.7\PSD2Live.exe",
    [string]$CubismExe = "D:\Live2D Cubism 5.3\CubismEditor5.exe"
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$results = New-Object System.Collections.ArrayList

function Add-Result([string]$id, [string]$name, [string]$status, [string]$detail) {
    [void]$results.Add([pscustomobject]@{ id = $id; name = $name; status = $status; detail = $detail })
    $color = switch ($status) { "PASS" { "Green" } "FAIL" { "Red" } default { "Yellow" } }
    Write-Host ("[{0}] {1} - {2}" -f $status, $id, $name) -ForegroundColor $color
    if ($detail) { Write-Host ("        " + $detail) -ForegroundColor DarkGray }
}

function Invoke-Python([string[]]$pyArgs) {
    $out = Join-Path $env:TEMP ("smoke-py-" + [guid]::NewGuid().ToString("N") + ".out")
    $err = Join-Path $env:TEMP ("smoke-py-" + [guid]::NewGuid().ToString("N") + ".err")
    $p = Start-Process -FilePath "python" -ArgumentList $pyArgs -NoNewWindow -Wait -PassThru `
        -RedirectStandardOutput $out -RedirectStandardError $err
    $text = ""
    if (Test-Path $out) { $text = Get-Content $out -Raw -Encoding UTF8; Remove-Item $out -Force }
    if (Test-Path $err) { Remove-Item $err -Force }
    return [pscustomobject]@{ code = $p.ExitCode; text = $text }
}

# S1 python
$py = Invoke-Python @("-c", "import sys;print(sys.version.split()[0])")
if ($py.code -eq 0) { Add-Result "S1" "python" "PASS" ($py.text.Trim()) }
else { Add-Result "S1" "python" "FAIL" "python not runnable" }

# S2 required modules
$mods = "numpy, cv2, PIL, psd_tools"
$py = Invoke-Python @("-c", "import importlib,sys;mods='$mods'.split(',');bad=[m for m in mods if importlib.util.find_spec(m.strip()) is None];print('missing:'+','.join(bad) if bad else 'all ok')")
$text = $py.text.Trim()
if ($text -eq "all ok") { Add-Result "S2" "required modules" "PASS" "numpy, cv2, PIL, psd_tools" }
else { Add-Result "S2" "required modules" "FAIL" $text }

# S3 psd2live_mcp.py loads
$script = Join-Path $root "scripts\psd2live_mcp.py"
if (Test-Path $script) {
    $py = Invoke-Python @($script, "list")
    if ($py.text -match "无法获取 PSD2Live 令牌|401|Connection|refused|timed out|TimeoutError") {
        Add-Result "S3" "psd2live_mcp.py" "PASS" "script runs (server not reachable, expected when app is closed)"
    } elseif ($py.code -eq 0) {
        Add-Result "S3" "psd2live_mcp.py" "PASS" "connected to PSD2Live MCP"
    } else {
        Add-Result "S3" "psd2live_mcp.py" "FAIL" "script failed to start; is 'mcp' installed?"
    }
} else { Add-Result "S3" "psd2live_mcp.py" "FAIL" "scripts/psd2live_mcp.py missing" }

# S4 PSD2Live presence
if (Test-Path $Psd2LiveExe) {
    $size = [math]::Round((Get-Item $Psd2LiveExe).Length / 1MB, 1)
    Add-Result "S4" "PSD2Live" "PASS" "$Psd2LiveExe ($size MB)"
} else { Add-Result "S4" "PSD2Live" "SKIP" "not found at $Psd2LiveExe (CLI export unavailable)" }

# S5 Cubism + external API
if (Test-Path $CubismExe) {
    $port = $null
    try {
        $port = Test-NetConnection -ComputerName 127.0.0.1 -Port 22033 -InformationLevel Quiet -WarningAction SilentlyContinue
    } catch { $port = $false }
    if ($port) { Add-Result "S5" "Cubism external API" "PASS" "port 22033 open" }
    else { Add-Result "S5" "Cubism external API" "SKIP" "Cubism present but port 22033 closed (needs 5.4 alpha+ with 集成 API enabled)" }
} else { Add-Result "S5" "Cubism external API" "SKIP" "Cubism not installed" }

# S6 package integrity
$required = @(
    "SKILL.md", "AI_README.md", "README.md", "check_env.py", "install.py",
    "config\pipeline.json", "workflows\psd2live-mcp.md", "workflows\skill-routing.md",
    "references\psd2live-ops.md", "references\model-defects.md", "scripts\psd2live_mcp.py"
)
$missing = @()
foreach ($rel in $required) { if (-not (Test-Path (Join-Path $root $rel))) { $missing += $rel } }
if ($missing.Count -eq 0) { Add-Result "S6" "package files" "PASS" ("{0} files present" -f $required.Count) }
else { Add-Result "S6" "package files" "FAIL" ("missing: " + ($missing -join ", ")) }

# S7 full export through PSD2Live CLI
if ($Full) {
    if ($Psd -and (Test-Path $Psd) -and (Test-Path $Psd2LiveExe)) {
        $outDir = Join-Path $env:TEMP ("smoke-export-" + [guid]::NewGuid().ToString("N"))
        $o = Join-Path $env:TEMP "smoke-exp.out"; $e = Join-Path $env:TEMP "smoke-exp.err"
        $p = Start-Process -FilePath $Psd2LiveExe -ArgumentList @("--input", $Psd, "--output", $outDir, "--lang", "zh") `
            -NoNewWindow -Wait -PassThru -RedirectStandardOutput $o -RedirectStandardError $e
        $moc = Get-ChildItem $outDir -Filter *.moc3 -ErrorAction SilentlyContinue
        if ($moc) { Add-Result "S7" "PSD2Live export" "PASS" ("moc3 " + $moc[0].Length + " B") }
        else { Add-Result "S7" "PSD2Live export" "FAIL" "no moc3 produced (see $e)" }
    } else { Add-Result "S7" "PSD2Live export" "SKIP" "-Full needs -Psd <existing .psd> and PSD2Live.exe" }
} else { Add-Result "S7" "PSD2Live export" "SKIP" "use -Full -Psd <file.psd>" }

# summary + log
$fail = @($results | Where-Object { $_.status -eq "FAIL" }).Count
$skip = @($results | Where-Object { $_.status -eq "SKIP" }).Count
$pass = @($results | Where-Object { $_.status -eq "PASS" }).Count
Write-Host ""
Write-Host ("summary: {0} pass / {1} fail / {2} skip" -f $pass, $fail, $skip)

$logDir = $env:DSH_LOG_DIR
if (-not $logDir) { $logDir = Join-Path $env:TEMP "live2d-smoke" }
try { New-Item -ItemType Directory -Force -Path $logDir | Out-Null } catch { $logDir = $env:TEMP }
$logPath = Join-Path $logDir ("smoke-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".json")
$payload = [pscustomobject]@{
    root = $root; full = [bool]$Full; psd = $Psd
    pass = $pass; fail = $fail; skip = $skip; results = $results
}
try {
    $payload | ConvertTo-Json -Depth 5 | Set-Content $logPath -Encoding UTF8
    Write-Host ("log: " + $logPath)
} catch { Write-Host "log write skipped" -ForegroundColor DarkYellow }

if ($fail -gt 0) { exit 1 } else { exit 0 }
