$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$artifactRoot = Join-Path $projectRoot "submission_artifacts"
$stage = Join-Path $artifactRoot "source_package_staging"
$zip = Join-Path $artifactRoot "agri_source_package.zip"

New-Item -ItemType Directory -Force $stage | Out-Null

# Rebuild from a clean, workspace-local staging directory so excluded training data
# from an interrupted package build cannot leak into the final archive.
if (Test-Path -LiteralPath $stage) {
  Remove-Item -LiteralPath $stage -Recurse -Force
  New-Item -ItemType Directory -Force $stage | Out-Null
}

$rootFiles = @(
  "README.md", "LICENSE", "Makefile", "docker-compose.yml", "docker-compose.server.yml", ".env.example", "pytest.ini"
)
$rootDirs = @(
  "backend", "frontend", "data", "batch_jobs", "knowledge_base", "scripts", "docs", "presentation"
)
$excludedDirs = @(
  "node_modules", ".next", ".venv", "__pycache__", ".pytest_cache", "artifacts", "submission_artifacts",
  "ip102", "ip102_yolo", "ip102_yolo_runs", "plantdoc", "plantdoc_tar", "plantdoc_yolo", "plantdoc_yolo_runs", "yolo_runs"
)
$excludedFiles = @(
  ".env", ".env.local", "*.log", "*.pyc", "*.zip", "*.tar", "*.tar.gz"
)

foreach ($name in $rootFiles) {
  $source = Join-Path $projectRoot $name
  if (Test-Path -LiteralPath $source) {
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage $name) -Force
  }
}

foreach ($dirName in $rootDirs) {
  $sourceDir = Join-Path $projectRoot $dirName
  if (-not (Test-Path -LiteralPath $sourceDir)) { continue }
  Get-ChildItem -LiteralPath $sourceDir -Recurse -File -Force | ForEach-Object {
    $relative = $_.FullName.Substring($projectRoot.Length).TrimStart("\\")
    $parts = $relative -split "\\"
    if ($parts | Where-Object { $excludedDirs -contains $_ }) { return }
    $fileName = $_.Name
    if ($excludedFiles | Where-Object { $fileName -like $_ }) { return }
    $destination = Join-Path $stage $relative
    New-Item -ItemType Directory -Force (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
  }
}

if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
# Use the .NET ZIP implementation so the archive path and Chinese filenames
# remain intact on Windows PowerShell.
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($stage, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $false)
Remove-Item -LiteralPath $stage -Recurse -Force
Write-Output $zip
