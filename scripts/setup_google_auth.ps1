Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  KÍCH HOẠT XÁC THỰC GOOGLE DRIVE VÀ GMAIL CHO ANTIGRAVITY" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Đang mở trình duyệt để xác thực Google Drive..." -ForegroundColor Yellow
$env:GDRIVE_OAUTH_PATH = "C:\Users\BANG\.gemini\credentials\gcp-oauth.keys.json"
$env:GDRIVE_CREDENTIALS_PATH = "C:\Users\BANG\.gemini\credentials\gdrive-token.json"
npx -y @modelcontextprotocol/server-gdrive auth

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "[2/2] Đang mở trình duyệt để xác thực Gmail..." -ForegroundColor Yellow
npx -y @gongrzhe/server-gmail-autoauth-mcp auth

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  HOÀN TẤT XÁC THỰC! ANTIGRAVITY ĐÃ KẾT NỐI VỚI DRIVE & GMAIL!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
