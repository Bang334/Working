import pytest
from fastapi.testclient import TestClient
from app.main import app
import json

client = TestClient(app)

def test_import_existing_contract_api():
    contract_data = {
        "so_hop_dong": "HD-TEST-IMPORT-999",
        "khach_hang_vi": "CÔNG TY TNHH CÔNG NGHỆ BẮC NINH",
        "khach_hang_zh": "北寧科技有限公司",
        "ten_du_an_vi": "Dự Án Lắp Đặt IoT Máy Dập",
        "ten_du_an_zh": "沖壓機IoT安裝專案",
        "ngay_ky": "2026-10-17",
        "tong_gia_tri": 213606000,
        "milestones": [
            {
                "dot": 1,
                "ten_dot": "Đợt 1",
                "phan_tram": 30.0,
                "so_tien": 64081800,
                "dieu_kien_vi": "Thanh toán ngay sau khi hai bên ký kết hợp đồng",
                "thoi_han_tt_ngay": 10
            },
            {
                "dot": 2,
                "ten_dot": "Đợt 2",
                "phan_tram": 70.0,
                "so_tien": 149524200,
                "dieu_kien_vi": "Sau khi bàn giao và nghiệm thu",
                "thoi_han_tt_ngay": 30
            }
        ]
    }
    
    response = client.post(
        "/api/v1/contracts/import-existing",
        data={"contract_data": json.dumps(contract_data)},
        files={"file": ("hop_dong_mau.docx", b"dummy content", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "success"
    assert res["contract_code"] == "HD-TEST-IMPORT-999"
    assert res["milestones_count"] == 2
    
    # Kiểm tra đợt 1 có thời hạn 10 ngày
    ms_res = client.get("/api/v1/dossier/contracts")
    assert ms_res.status_code == 200
    dossier = ms_res.json()
    target_c = next((c for c in dossier["contracts"] if c["contract_code"] == "HD-TEST-IMPORT-999"), None)
    assert target_c is not None
    m1 = target_c["milestones"][0]
    assert m1["payment_term_days"] == 10
    assert m1["milestone_name"] == "Đợt 1"
