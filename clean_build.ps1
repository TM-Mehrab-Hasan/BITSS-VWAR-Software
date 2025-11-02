# Clean Build Folders - Force cleanup utility
# Use this if build_vwar.ps1 cannot clean folders

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VWAR Build Cleanup Utility" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[INFO] Checking for running processes..." -ForegroundColor Yellow
$vwarProcs = Get-Process -Name "VWAR" -ErrorAction SilentlyContinue
if ($vwarProcs) {
    Write-Host "[WARNING] Found running VWAR.exe processes!" -ForegroundColor Yellow
    Write-Host "         Attempting to close them..." -ForegroundColor Gray
    $vwarProcs | Stop-Process -Force
    Start-Sleep -Seconds 2
}

Write-Host "[INFO] Cleaning build artifacts..." -ForegroundColor Yellow
Write-Host ""

# Function to force delete with retry
function Force-Delete {
    param($Path, $Name)
    
    if (Test-Path $Path) {
        Write-Host "  Cleaning $Name..." -ForegroundColor Gray
        $attempts = 3
        $success = $false
        
        for ($i = 1; $i -le $attempts; $i++) {
            try {
                Remove-Item -Recurse -Force $Path -ErrorAction Stop
                Write-Host "  [OK] $Name removed" -ForegroundColor Green
                $success = $true
                break
            }
            catch {
                if ($i -lt $attempts) {
                    Write-Host "  [RETRY $i/$attempts] Waiting..." -ForegroundColor Yellow
                    Start-Sleep -Seconds 2
                }
                else {
                    Write-Host "  [FAILED] Could not remove $Name" -ForegroundColor Red
                    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
                    
                    # Try to delete contents
                    Write-Host "  [ATTEMPT] Removing contents only..." -ForegroundColor Yellow
                    Get-ChildItem $Path -Recurse -ErrorAction SilentlyContinue | 
                    Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
                }
            }
        }
        
        return $success
    }
    else {
        Write-Host "  [SKIP] $Name does not exist" -ForegroundColor Gray
        return $true
    }
}

# Clean folders
$cleaned = @()
$cleaned += Force-Delete ".\build" "build folder"
$cleaned += Force-Delete ".\dist" "dist folder"

# Clean files
if (Test-Path ".\VWAR.spec") {
    Remove-Item -Force ".\VWAR.spec" -ErrorAction SilentlyContinue
    Write-Host "  [OK] VWAR.spec removed" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($cleaned -notcontains $false) {
    Write-Host "Cleanup completed successfully!" -ForegroundColor Green
}
else {
    Write-Host "Cleanup completed with warnings." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "If folders still exist:" -ForegroundColor Yellow
    Write-Host "  1. Close Windows Explorer windows viewing these folders" -ForegroundColor White
    Write-Host "  2. Close any terminals with CWD in dist/build" -ForegroundColor White
    Write-Host "  3. Temporarily disable antivirus" -ForegroundColor White
    Write-Host "  4. Restart PowerShell and try again" -ForegroundColor White
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
