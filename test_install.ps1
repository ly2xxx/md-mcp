# Quick test script for md-mcp MVP
# Run this to verify everything works

Write-Host "=== md-mcp MVP Test Script ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "[1/5] Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Python found: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ERROR Python not found!" -ForegroundColor Red
    exit 1
}

# Step 2: Install package
Write-Host ""
Write-Host "[2/5] Installing md-mcp..." -ForegroundColor Yellow
pip install -e . --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Installed successfully" -ForegroundColor Green
} else {
    Write-Host "  ERROR Installation failed!" -ForegroundColor Red
    exit 1
}

# Step 3: Check CLI
Write-Host ""
Write-Host "[3/5] Testing CLI..." -ForegroundColor Yellow
$version = md-mcp --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK CLI works: $version" -ForegroundColor Green
} else {
    Write-Host "  ERROR CLI failed!" -ForegroundColor Red
    exit 1
}

# Step 4: Test scan
Write-Host ""
Write-Host "[4/5] Scanning test samples..." -ForegroundColor Yellow
$scanOutput = md-mcp --folder "$PSScriptRoot\test-samples" --scan 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Scanner works" -ForegroundColor Green
    Write-Host ""
    Write-Host $scanOutput
} else {
    Write-Host "  ERROR Scanner failed!" -ForegroundColor Red
    Write-Host $scanOutput
    exit 1
}

# Step 5: Check config path
Write-Host ""
Write-Host "[5/5] Checking Claude config..." -ForegroundColor Yellow
$configPath = "$env:APPDATA\Claude\claude_desktop_config.json"
if (Test-Path $configPath) {
    Write-Host "  OK Claude config found: $configPath" -ForegroundColor Green
} else {
    Write-Host "  NOTE Claude config not found (Claude Desktop not installed?)" -ForegroundColor Yellow
    Write-Host "    Expected: $configPath" -ForegroundColor Gray
}

# Summary
Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Add test server to Claude" -ForegroundColor Gray
Write-Host "  2. Restart Claude Desktop" -ForegroundColor Gray
Write-Host "  3. Ask Claude about your markdown files" -ForegroundColor Gray
Write-Host ""
Write-Host "For more info see QUICKSTART.md" -ForegroundColor White
Write-Host ""
