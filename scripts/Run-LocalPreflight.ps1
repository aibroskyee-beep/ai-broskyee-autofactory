$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$FactoryRoot = 'D:\AI-Video-Factory'
Write-Host "AutoFactory package: $Root"
if (-not (Test-Path -LiteralPath $FactoryRoot -PathType Container)) {
    throw "Expected project root not found: $FactoryRoot"
}
$drive = Get-PSDrive -Name D
$freeGB = [math]::Round($drive.Free / 1GB, 2)
$projectBytes = (Get-ChildItem -LiteralPath $FactoryRoot -Force -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
$projectGB = [math]::Round(($projectBytes / 1GB), 3)
Write-Host "D: free: $freeGB GB"
Write-Host "AI-Broskyee workspace: $projectGB GB"
if ($projectGB -ge 9) { throw "STOP: workspace reached the 9 GB soft limit." }
if ($freeGB -lt 15) { throw "STOP: D: has less than 15 GB free." }
Write-Host "Storage guard passed. No renderer, network API or publisher was started."
