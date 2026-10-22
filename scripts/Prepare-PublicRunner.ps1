$ErrorActionPreference = 'Stop'
$SourceRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$TargetRoot = 'D:\AI-Video-Factory\AI-Broskyee-AutoFactory-Public'
$D = Get-PSDrive -Name D
$FreeGB = [math]::Round($D.Free / 1GB, 2)
if ($FreeGB -lt 15) { throw "STOP: D: has only $FreeGB GB free; minimum required is 15 GB." }
if (Test-Path -LiteralPath $TargetRoot) { throw "STOP: $TargetRoot already exists. Nothing overwritten." }
$Forbidden = @('.git','__pycache__','test_output','work','output')
New-Item -ItemType Directory -Path $TargetRoot | Out-Null
try {
    Get-ChildItem -LiteralPath $SourceRoot -Force | Where-Object { $_.Name -notin $Forbidden } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $TargetRoot -Recurse -Force
    }
    # Do not copy any locally downloaded model or credential file.
    $Voice = Join-Path $TargetRoot 'assets\voice'
    if (Test-Path -LiteralPath $Voice) {
        Get-ChildItem -LiteralPath $Voice -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Extension -in @('.onnx','.json') } |
            Remove-Item -Force
    }
    $Bad = Get-ChildItem -LiteralPath $TargetRoot -Recurse -Force -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '(^\.env$|client_secret|credentials\.json|token\.json|\.pem$|\.key$)' }
    if ($Bad) { throw "STOP: Possible credential file detected in staging. Review $TargetRoot before uploading." }
    git -C $TargetRoot init -b main | Out-Null
    Write-Host "SAFE STAGING COPY CREATED: $TargetRoot"
    Write-Host 'No files in your existing AI-Video-Factory project were modified.'
    Write-Host 'Next create a NEW public GitHub repository for this folder only; this exposes only the AutoFactory source files, not your existing private renderer or credentials.'
} catch {
    Write-Warning "Staging stopped: $($_.Exception.Message)"
    throw
}
