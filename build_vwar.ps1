# VWAR v3.0.0 Build Script with Enhanced Features
# Build Date: November 2, 2025
# Includes: Adaptive validation (5-60s), Auto-renew real-time sync, YARA auto-update, 24h offline grace

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VWAR v3.0.0 Build Script" -ForegroundColor Cyan  
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Clean previous builds
Write-Host "[1/5] Cleaning previous builds..." -ForegroundColor Yellow

# Clean build folder
if (Test-Path ".\build") { 
    try {
        Remove-Item -Recurse -Force ".\build" -ErrorAction Stop
    }
    catch {
        Write-Host "[WARNING] Could not remove build folder (in use)" -ForegroundColor Yellow
    }
}

# Clean dist folder with retry logic
if (Test-Path ".\dist") { 
    try {
        # Try to remove VWAR.exe first
        if (Test-Path ".\dist\VWAR.exe") {
            Remove-Item -Force ".\dist\VWAR.exe" -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
        }
        Remove-Item -Recurse -Force ".\dist" -ErrorAction Stop
    }
    catch {
        Write-Host "[WARNING] Could not fully remove dist folder (in use)" -ForegroundColor Yellow
        Write-Host "         Trying to clean contents only..." -ForegroundColor Gray
        # Try to clean contents instead
        Get-ChildItem ".\dist" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
    }
}

# Clean spec file
if (Test-Path ".\VWAR.spec") { 
    Remove-Item -Force ".\VWAR.spec" -ErrorAction SilentlyContinue
}

Write-Host "[OK] Cleaned" -ForegroundColor Green
Write-Host ""

# Run PyInstaller
Write-Host "[2/5] Building VWAR.exe with PyInstaller..." -ForegroundColor Yellow
Write-Host "This may take 2-5 minutes..." -ForegroundColor Gray
Write-Host ""

pyinstaller --noconfirm --onefile --windowed `
    --icon=assets/VWAR.ico `
    --manifest=vwar.manifest `
    --name=VWAR `
    --add-data "assets/VWAR.ico;assets" `
    --add-data "assets/yara;assets/yara" `
    --add-data "vwar_monitor;vwar_monitor" `
    --hidden-import=plyer.platforms.win.notification `
    --hidden-import=win10toast `
    --hidden-import=pywin32 `
    --hidden-import=win32api `
    --hidden-import=win32con `
    --hidden-import=win32gui `
    --hidden-import=win32gui_struct `
    --hidden-import=win32file `
    --hidden-import=pywintypes `
    --hidden-import=pystray `
    --hidden-import=PIL `
    --hidden-import=PIL.Image `
    --hidden-import=PIL.ImageDraw `
    --hidden-import=cryptography `
    --hidden-import=cryptography.fernet `
    --hidden-import=yara `
    --hidden-import=requests `
    --hidden-import=psutil `
    --hidden-import=threading `
    --hidden-import=concurrent.futures `
    --hidden-import=queue `
    --hidden-import=tkinter `
    --hidden-import=tkinter.ttk `
    --hidden-import=tkinter.scrolledtext `
    --hidden-import=tkinter.messagebox `
    --hidden-import=tkinter.filedialog `
    --hidden-import=subprocess `
    --hidden-import=ctypes `
    --hidden-import=hashlib `
    --hidden-import=base64 `
    --hidden-import=datetime `
    --hidden-import=json `
    --hidden-import=pathlib `
    --collect-all plyer `
    --collect-all win10toast `
    main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] Build completed" -ForegroundColor Green
Write-Host ""

# Create runtime directories
Write-Host "[3/5] Creating runtime directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path ".\dist\quarantine" | Out-Null
New-Item -ItemType Directory -Force -Path ".\dist\scanvault" | Out-Null
New-Item -ItemType Directory -Force -Path ".\dist\data" | Out-Null
Write-Host "[OK] Created quarantine, scanvault, data folders" -ForegroundColor Green
Write-Host ""

# Verify build
Write-Host "[4/5] Verifying build..." -ForegroundColor Yellow

if (Test-Path ".\dist\VWAR.exe") {
    $exe = Get-Item ".\dist\VWAR.exe"
    $sizeMB = [math]::Round($exe.Length / 1MB, 2)
    Write-Host "[OK] VWAR.exe created successfully" -ForegroundColor Green
    Write-Host "  File size: $sizeMB MB" -ForegroundColor Gray
    Write-Host "  Location: $($exe.FullName)" -ForegroundColor Gray
}
else {
    Write-Host "[ERROR] VWAR.exe not found!" -ForegroundColor Red
    exit 1
}

if (Test-Path ".\dist\vwar_monitor\vwar_monitor.exe") {
    Write-Host "[OK] C++ monitor included" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] C++ monitor not found" -ForegroundColor Yellow
}

if (Test-Path ".\dist\assets\yara") {
    $yaraCount = (Get-ChildItem ".\dist\assets\yara" -Recurse -Filter "*.yar").Count
    Write-Host "[OK] YARA rules included ($yaraCount files)" -ForegroundColor Green
}
else {
    Write-Host "[WARNING] YARA rules not found" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "[5/5] Build Summary" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Version: 3.0.0" -ForegroundColor White
Write-Host "Build Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor White
Write-Host ""
Write-Host "New Features in v3.0.0:" -ForegroundColor White
Write-Host "  [OK] Dynamic License Terms page (2-second refresh)" -ForegroundColor Green
Write-Host "  [OK] Prominent 'X Days Active' display (color-coded)" -ForegroundColor Green
Write-Host "  [OK] Force Server Check button removed" -ForegroundColor Green
Write-Host "  [OK] Offline grace extended to 24 hours" -ForegroundColor Green
Write-Host "  [OK] YARA rule auto-update (background)" -ForegroundColor Green
Write-Host "  [OK] Smart auto-renew warnings (<30 days)" -ForegroundColor Green
Write-Host "  [OK] Auto-renew real-time sync with database" -ForegroundColor Green
Write-Host "  [OK] 30-day validation for auto-renew enable" -ForegroundColor Green
Write-Host "  [OK] Adaptive validation intervals (5-60s)" -ForegroundColor Green
Write-Host "  [OK] Blinking animation for urgent expiry (<=7 days)" -ForegroundColor Green
Write-Host "  [OK] Yellow warning banner removed" -ForegroundColor Green
Write-Host ""
Write-Host "Previous Features:" -ForegroundColor White
Write-Host "  [OK] 2-device licensing support" -ForegroundColor Green
Write-Host "  [OK] All API endpoints authenticated" -ForegroundColor Green
Write-Host "  [OK] Installation mode exclusions" -ForegroundColor Green
Write-Host "  [OK] Enhanced error handling" -ForegroundColor Green
Write-Host ""
Write-Host "Location: .\dist\VWAR.exe" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Build complete!" -ForegroundColor Green
