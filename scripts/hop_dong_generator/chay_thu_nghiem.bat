@echo off
chcp 65001 > nul
echo ====================================================================
echo   ĐANG CHẠY THỬ NGHIỆM ĐIỀN HỢP ĐỒNG JINXUN (HONG MING GLOBAL)
echo ====================================================================

python "%~dp0generate_jinxun_mes_contract.py" --template "%~dp0..\..\Bieu Mau\Hợp đồng.docx" --output "%~dp0outputs\final\Hop_Dong_JINXUN_MES_Lite_DA_SUA_V2.docx"

echo.
echo Hoàn tất! Nhấn phím bất kỳ để thoát.
pause > nul
