# -*- coding: utf-8 -*-
"""
Script kiểm thử toàn diện kết nối phần Email với các module trong Hong Ming PM Portal.
"""
import sys
from pathlib import Path

# Đảm bảo đường dẫn import
portal_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(portal_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_routes():
    print("=== 1. KIỂM TRA TRANG GIAO DIỆN /emails ===")
    res = client.get("/emails")
    assert res.status_code == 200, f"Lỗi /emails: status {res.status_code}"
    assert "Trung Tâm Soạn Thảo" in res.text
    assert "Nguồn Dữ Liệu Kết Nối Tự Động" in res.text
    print("✓ /emails: OK (200)")

    print("\n=== 2. KIỂM TRA API /api/emails/quick-sources ===")
    res = client.get("/api/emails/quick-sources")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    sources = data["data"]
    print(f"✓ Quick sources: {len(sources.get('contracts', []))} hợp đồng, {len(sources.get('receivables', []))} công nợ, {len(sources.get('procurements', []))} PO, {len(sources.get('payment_vouchers', []))} phiếu thanh toán, {len(sources.get('quotations', []))} báo giá.")

    print("\n=== 3. KIỂM TRA LOAD CONTEXT TỪ CÁC MODULE ===")
    test_cases = [
        ("receivable", "Công nợ AR"),
        ("contract", "Hợp đồng"),
        ("po", "Đơn mua hàng PO"),
        ("voucher", "Đơn xin thanh toán"),
        ("quotation", "Báo giá"),
        ("acceptance", "Nghiệm thu"),
        ("file", "Quản lý File", {"code": "HopDong_HMV02102026.docx"}),
        ("preset", "Mẫu Preset", {"code": "PAYMENT_REQUEST_DEPOSIT"})
    ]

    for item in test_cases:
        src = item[0]
        desc = item[1]
        extra = item[2] if len(item) > 2 else {}
        params = {"source": src}
        params.update(extra)

        r = client.get("/api/emails/load-context", params=params)
        assert r.status_code == 200, f"Lỗi context {src}: {r.text}"
        ctx = r.json()
        assert ctx["status"] == "success"
        d = ctx["data"]
        print(f"✓ Load context [{desc}]: Subject = '{d.get('subject')[:50]}...', Số tiền = {d.get('amount')}, Người nhận = {d.get('recipient_email')}")

    print("\n=== 4. KIỂM TRA LƯU NHÁP & MÔ PHỎNG GỬI ===")
    draft_payload = {
        "email_type": "TEST_CONNECT",
        "customer_name": "Công Ty Test Đối Tác",
        "recipient_email": "test@doitac.com",
        "cc_emails": "sales@hongming-global.com",
        "subject": "Thư thử nghiệm kết nối hệ thống / 系統串接測試信",
        "body_text": "Kính gửi đối tác, đây là thư thử nghiệm kết nối.",
        "amount": 10000000,
        "due_date": "2026-11-01",
        "attachments": ["Test_HopDong.pdf"],
        "is_safe_mode": True,
        "source_module": "receivable",
        "source_id": 1
    }
    r_draft = client.post("/api/emails/save-draft", json=draft_payload)
    assert r_draft.status_code == 200
    res_draft_data = r_draft.json()
    assert res_draft_data["status"] == "success"
    print(f"✓ Lưu nháp thành công: Mã = {res_draft_data.get('email_code')}")

    r_sim = client.post("/api/emails/simulate-send", json=draft_payload)
    assert r_sim.status_code == 200
    res_sim_data = r_sim.json()
    assert res_sim_data["status"] == "success"
    print(f"✓ Mô phỏng gửi an toàn: Mã = {res_sim_data.get('tracking_code')}")

    print("\n=== 5. KIỂM TRA CÁC TRANG LIÊN QUAN ===")
    pages = [
        ("/", "Trang chủ Dashboard"),
        ("/contracts", "Hợp đồng"),
        ("/purchase-orders", "Mua hàng PO"),
        ("/receivables", "Công nợ AR"),
        ("/payment-requests", "Đơn xin thanh toán"),
        ("/quotations", "Báo giá"),
        ("/acceptance", "Nghiệm thu"),
        ("/files", "Quản lý File"),
        ("/reminders", "Nhắc nợ")
    ]
    for url, title in pages:
        res_page = client.get(url)
        assert res_page.status_code == 200, f"Lỗi trang {url}: status {res_page.status_code}"
        print(f"✓ Trang {title} ({url}): OK (200)")

    print("\n🎉 TẤT CẢ CÁC BÀI TEST ĐÃ HOÀN TẤT THÀNH CÔNG 100%!")

if __name__ == "__main__":
    test_routes()
