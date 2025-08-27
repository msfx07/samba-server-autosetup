# Windows SMB Client Configuration Commands
# Run these in PowerShell AS ADMINISTRATOR on your Windows Guest OS

# Configuration - modify these as needed
$ServerIP = "10.10.55.1"
$ShareName = "shared"

Write-Host "SMB Client Configuration for Server: $ServerIP" -ForegroundColor Green
Write-Host "Target Share: \\$ServerIP\$ShareName" -ForegroundColor Green
Write-Host ""

# 1. Enable SMB1 Client (if disabled)
Write-Host "1. Enabling SMB1 Client..." -ForegroundColor Yellow
Enable-WindowsOptionalFeature -Online -FeatureName SMB1Protocol-Client

# 2. Check SMB configuration
Write-Host "2. Current SMB Client Configuration:" -ForegroundColor Yellow
Get-SmbClientConfiguration

# 3. Enable insecure guest logons (for anonymous shares)
Write-Host "3. Configuring SMB for anonymous shares..." -ForegroundColor Yellow
Set-SmbClientConfiguration -RequireSecuritySignature $false -Force
Set-SmbClientConfiguration -EnableSecuritySignature $false -Force

# 4. Test network connectivity
Write-Host "4. Testing network connectivity..." -ForegroundColor Yellow
ping $ServerIP
telnet $ServerIP 445

# 5. Try to connect
Write-Host "5. Attempting to map drive..." -ForegroundColor Yellow
net use Z: "\\$ServerIP\$ShareName"

# Alternative: Map drive with credentials
Write-Host "Alternative command (if above fails):" -ForegroundColor Cyan
Write-Host "net use Z: \\$ServerIP\$ShareName /user:guest `"`"" -ForegroundColor White
