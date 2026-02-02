$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Py = Join-Path $Root ".venv/Scripts/python.exe"
& "$Root/.venv/Scripts/Activate.ps1"

# Load .env if present (for OPENAI_API_KEY, etc.)
$envPath = Join-Path $Root ".env"
if (Test-Path $envPath) {
  Get-Content $envPath | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $parts = $_.Split('=',2)
    if ($parts.Length -eq 2) {
      $name = $parts[0].Trim()
      $value = $parts[1].Trim()
      if ($name) { Set-Item -Path "Env:$name" -Value $value }
    }
  }
}

try {
  & $Py "$Root/jarvis/cli.py" send "ping" | Out-Null
} catch {
  & $Py "$Root/jarvis/cli.py" serve --daemon | Out-Null
  Start-Sleep -Seconds 1
}

& $Py "$Root/jarvis/cli.py" ui --open
