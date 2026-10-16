@echo off
chcp 65001 >nul
echo ========================================================
echo   KICH HOAT XAC THUC GOOGLE DRIVE VA GMAIL CHO ANTIGRAVITY
echo ========================================================
echo.

echo [1/2] Dang mo trinh duyet de xac thuc Google Drive...
set "GDRIVE_OAUTH_PATH=C:\Users\BANG\.gemini\credentials\gcp-oauth.keys.json"
set "GDRIVE_CREDENTIALS_PATH=C:\Users\BANG\.gemini\credentials\gdrive-token.json"
call npx -y @modelcontextprotocol/server-gdrive auth

echo.
echo ========================================================
echo [2/2] Dang mo trinh duyet de xac thuc Gmail...
call npx -y @gongrzhe/server-gmail-autoauth-mcp auth

echo.
echo ========================================================
echo   HOAN TAT XAC THUC! ANTIGRAVITY DA KET NOI VOI DRIVE & GMAIL!
echo ========================================================
pause
