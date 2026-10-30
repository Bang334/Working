# -*- coding: utf-8 -*-
"""
Email Automation & Safe Preview Controller for Hong Ming PM Portal.
Cung cấp chức năng soạn thảo, xem trước và mô phỏng gửi email an toàn (Dry Run / Safe Mode).
Tuyệt đối KHÔNG gửi email thực tế ra bên ngoài đến khách hàng.
Kết nối sâu với toàn bộ hệ thống: Hợp đồng, Công nợ (AR), Đợt thanh toán, Mua hàng (PO), Đơn xin thanh toán.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request, HTTPException, Body, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import CANDIDATE_MODELS, DEFAULT_MODEL
from app.database import get_db_connection
from app.utils.currency_helper import (
    format_currency_vnd,
    number_to_vietnamese_words,
    number_to_chinese_words,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def safe_email_context(item):
    """Legacy previews describe requested files, never pretend names are attachments."""
    result = dict(item)
    body = str(result.get('body') or '')
    body = re.sub(r'^.*0011004123456.*(?:\n|$)', '', body, flags=re.M)
    body = body.replace('Phiếu Đơn yêu cầu thanh toán (DYCTT) đã được ký duyệt và đóng dấu scan đính kèm trong thư này.',
                        'Vui lòng kiểm tra bản ký và đính kèm hồ sơ thật trước khi gửi.')
    body = body.replace('Hong Ming xin gửi kèm bản scan biên bản nghiệm thu đầy đủ để Quý Công ty lưu trữ và làm căn cứ giải ngân giai đoạn thanh toán tiếp theo.',
                        'Kính nhờ Quý Công ty kiểm tra hồ sơ nghiệm thu và phản hồi nội dung cần xác nhận.')
    result['body'] = body
    expected = result.get('attachments') or []
    result['required_attachments'] = list(dict.fromkeys([*(result.get('required_attachments') or []), *map(str,expected)]))
    result['attachments'] = []
    for key in ('recipient_email', 'recipient'):
        if str(result.get(key,'')).endswith('@khachhang.com'):
            result[key] = ''
    result['workflow_url'] = '/workflows'
    return result

router = APIRouter(tags=["Email Center"])

# Khởi tạo bảng emails nếu chưa tồn tại
def ensure_emails_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_code TEXT UNIQUE,
        email_type TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        cc_emails TEXT,
        subject TEXT NOT NULL,
        body_text TEXT NOT NULL,
        body_html TEXT,
        amount REAL DEFAULT 0,
        due_date TEXT,
        attachments_json TEXT,
        is_safe_mode INTEGER DEFAULT 1,
        status TEXT DEFAULT 'DRAFT',
        source_module TEXT,
        source_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Additive schema migration an toàn
    cursor.execute("PRAGMA table_info(emails)")
    cols = [r[1] for r in cursor.fetchall()]
    if "source_module" not in cols:
        cursor.execute("ALTER TABLE emails ADD COLUMN source_module TEXT")
    if "source_id" not in cols:
        cursor.execute("ALTER TABLE emails ADD COLUMN source_id INTEGER")
    conn.commit()
    conn.close()

ensure_emails_table()


# Danh mục 10 mẫu Email chuẩn hóa dựa trên phân tích kho 95 email thực tế của Hong Ming Global
EMAIL_PRESETS = [
    {
        "id": "PAYMENT_REQUEST_DEPOSIT",
        "name": "1. Đề nghị thanh toán Đặt cọc 30% (Đợt 1)",
        "category": "Thanh toán",
        "customer": "CÔNG TY TNHH CHENG FENG LE HUA (VN)",
        "recipient": "ke-toan@chengfeng.com.vn",
        "cc": "sales@hongming-global.com; pm02@hongming-global.com",
        "subject": "Đề nghị thanh toán đặt cọc 30% – Hợp đồng HMV021020260001 - CHENG FENG / 申請支付合約30%訂金",
        "contract_number": "HMV021020260001",
        "amount": 300000000,
        "due_date": "2026-11-05",
        "attachments": ["DON_XIN_TT_300TR.pdf"],
        "required_attachments": ["File PDF Đơn yêu cầu thanh toán (DYCTT) có chữ ký đóng dấu"],
        "body": """Kính gửi Quý Công ty TNHH Cheng Feng Le Hua (VN) / Bộ phận Kế toán & Quản lý Dự án,
敬愛的 CHENG FENG 團隊，您好：

Công ty TNHH Toàn Cầu Hong Ming xin gửi Quý Công ty Phiếu yêu cầu thanh toán Đợt 1 (Đặt cọc 30%) theo Hợp đồng số HMV021020260001 cho dự án kết nối máy công nghiệp IIoT, với thông tin thanh toán như sau:
宏銘公司隨信附上合約編號 HMV021020260001 之第一期付款申請單（30%訂金），相關資訊如下：

* Giá trị hợp đồng / 合約總金額: 1.000.000.000 VNĐ
* Tỷ lệ tạm ứng / 請款比例: 30%
* Số tiền đề nghị thanh toán / 申請付款金額: 300.000.000 VNĐ
  (Bằng chữ: Ba trăm triệu đồng chẵn / 大寫: 參億越盾整)
* Hạn thanh toán theo thỏa thuận / 付款截止日期: 05/11/2026

Thông tin tài khoản thụ hưởng của Hong Ming / 宏明環球收款帳號資訊：
* Tên tài khoản / 戶名: CÔNG TY TNHH TOÀN CẦU HONG MING
* Số tài khoản / 帳號: 0011004123456
* Ngân hàng thụ hưởng / 開戶行: Ngân hàng TNHH MTV Cathay United Bank - Chi nhánh TP.HCM

Phiếu yêu cầu thanh toán (DYCTT) đã được ký đóng dấu và đính kèm trong email này. Kính mong Quý Công ty hỗ trợ sắp xếp thanh toán theo thời hạn nêu trên để chúng tôi tiến hành đặt hàng thiết bị theo đúng tiến độ.
付款申請單（已加蓋公章）已隨信檢附。敬請貴公司協助依上述約定期限安排撥款，以利後續設備採購作業如期推展。

Xin chân thành cảm ơn sự hợp tác của Quý Công ty!
感謝貴公司的支持與密切配合！

Trân trọng / 敬上,
Bộ phận Quản lý Dự án & Kế toán / 專案部暨財務會計部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: pm02@hongming-global.com"""
    },
    {
        "id": "PAYMENT_REQUEST_ACCEPTANCE",
        "name": "2. Đề nghị thanh toán Nghiệm thu 20% (Giai đoạn 3)",
        "category": "Thanh toán",
        "customer": "CÔNG TY TRÁCH NHIỆM HỮU HẠN SEIYO VIỆT NAM",
        "recipient": "nguyensykimbang321@gmail.com",
        "cc": "invoice@hongming-global.com; sales@hongming-global.com",
        "subject": "Đề nghị thanh toán Đợt 2 (60%) – Hợp đồng HMV22092026SY0001 - SEIYO / 申請支付驗收期款",
        "contract_number": "HMV22092026SY0001",
        "amount": 427212000,
        "due_date": "2026-11-08",
        "attachments": ["DON_XIN_TT_SEIYO_DOT2_KEM_BBNT.pdf"],
        "required_attachments": ["File PDF gộp chung gồm Đơn xin thanh toán (DYCTT) và Biên bản nghiệm thu (BBNT) đã ký"],
        "body": """Kính gửi: Quý Công ty TNHH Seiyo Việt Nam / Phòng Kế toán & Ban Quản lý Dự án,
敬致：正揚科技（越南）有限公司 / 財務會計部暨專案管理處：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi Quý Công ty hồ sơ đề nghị thanh toán Đợt 2 (60% giá trị hợp đồng sau nghiệm thu lắp đặt) cho Dự án Quy hoạch mạng kết nối máy công nghiệp IIoT cho nhà máy SEIYO.
宏明環球責任有限公司特此檢送 SEIYO 工廠 IIoT 機聯網專案之第二期款（設備安裝驗收完成款 60%）付款申請文件。

Thông tin đề nghị thanh toán / 請款詳細資訊：
* Hợp đồng số / 合約編號: HMV22092026SY0001
* Hạng mục nghiệm thu / 驗收項目: Hoàn tất lắp đặt và kết nối 3 bộ ADAM & màn hình TV hiển thị thông số máy tiện.
* Giá trị đợt thanh toán / 本期請款金額: 427.212.000 VNĐ
  (Bằng chữ: Bốn trăm hai mươi bảy triệu hai trăm mười hai nghìn đồng chẵn / 肆億貳仟柒佰貳拾壹萬貳仟越盾整)
* Hạn thanh toán cam kết / 約定付款期限: 08/11/2026 (T/T 60 ngày kể từ ngày nghiệm thu)

Tài khoản thụ hưởng / 收款帳戶：
* Đơn vị thụ hưởng / 收款人: CÔNG TY TNHH TOÀN CẦU HONG MING
* Số tài khoản / 帳號: 0011004123456 - Ngân hàng Cathay United Bank (HCM)

Hồ sơ đính kèm gồm file PDF gộp chung: Phiếu yêu cầu thanh toán và Biên bản nghiệm thu bàn giao đã có đầy đủ chữ ký xác nhận của đại diện kỹ thuật hai bên.

Trân trọng / 敬上,
Bộ phận Quản lý Dự án / 專案管理部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "VAT_INVOICE_DISTRIBUTION",
        "name": "3. Phát hành hóa đơn GTGT điện tử (XML + PDF)",
        "category": "Hóa đơn",
        "customer": "CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM",
        "recipient": "nguyensykimbang321@gmail.com",
        "cc": "invoice@hongming-global.com; sales@hongming-global.com",
        "subject": "Hóa đơn điện tử C26THM_00000023 - Hợp đồng HD-20261013-001 - JINXUN / 電子發票開立通知",
        "contract_number": "HD-20261013-001",
        "amount": 781530000,
        "due_date": "2026-11-05",
        "attachments": ["C26THM_00000023_JINXUN.pdf", "C26THM_00000023_JINXUN.xml"],
        "required_attachments": ["Bản thể hiện PDF hóa đơn có chữ ký số", "File dữ liệu gốc XML hợp chuẩn Tổng cục Thuế"],
        "body": """Kính gửi: Quý Công ty TNHH Công nghệ Jinxun Việt Nam / Bộ phận Kế toán tài chính,
敬致：金訊科技（越南）有限公司 / 財務會計部：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Căn cứ vào Hợp đồng số HD-20261013-001 và biên bản nghiệm thu đã hoàn tất, Hong Ming xin trân trọng gửi đến Quý Công ty hóa đơn giá trị gia tăng điện tử với chi tiết như sau:
依據雙方簽署之合約及已完成之驗收確認書，宏明環球特此檢附電子增值稅發票，明細如下：

Thông tin hóa đơn chi tiết / 發票詳細明細：
* Tên người mua / 買方公司抬頭: CÔNG TY TNHH CÔNG NGHỆ JINXUN VIỆT NAM
* Mã số thuế / 稅號: 2301122334
* Tên dịch vụ / 貨品或服務名稱: Hệ thống MES Lite (Bao gồm Nghiệp vụ PM, Giao diện Web cấp phép 25 máy trạm)
* Ký hiệu hóa đơn / 發票符號: 1C26THM | Số hóa đơn / 發票號碼: 00000023
* Ngày lập hóa đơn / 開票日期: 16/10/2026
* Tổng tiền thanh toán / 總含稅金額: 781.530.000 VNĐ
  (Bằng chữ: Bảy trăm tám mươi mốt triệu năm trăm ba mươi nghìn đồng chẵn / 柒億捌仟壹佰伍拾參萬越盾整)

Tra cứu hóa đơn trực tuyến / 線上發票查驗資訊：
* Trang tra cứu / 查驗網址: https://tracuu.minvoice.vn | Mã bảo mật / 查驗碼: HM26TX781

Tài liệu đính kèm gồm: File PDF bản thể hiện và File XML dữ liệu gốc hóa đơn điện tử.

Trân trọng / 敬上,
Bộ phận Kế toán & Hóa đơn / 財務會計暨發票小組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "DEBT_REMINDER_10PCT",
        "name": "4. Nhắc nợ Quyết toán 10% cuối kỳ (尾款)",
        "category": "Công nợ",
        "customer": "CÔNG TY TNHH VONMAX (VN) - 弘聲",
        "recipient": "hien.nguyen@vonmax.com.vn",
        "cc": "invoice@hongming-global.com; sales@hongming-global.com",
        "subject": "Nhắc nhở thanh toán 10% giá trị hợp đồng / 关于支付合同尾款（10%）的提醒 - Vonmax (弘聲)",
        "contract_number": "HM-VONMAX-LOT1",
        "amount": 95800000,
        "due_date": "2026-10-30",
        "attachments": ["Bang_Doi_Chieu_Cong_No_Vonmax.pdf"],
        "required_attachments": ["Bảng đối chiếu công nợ (SOA)", "Bản sao các hóa đơn GTGT chưa thanh toán"],
        "body": """Kính gửi: Quý Công ty TNHH Vonmax (VN) / Ms Hiền - Bộ phận Kế toán,
敬致：弘聲科技（越南）有限公司 / 財務部 Ms Hiền：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng đến Quý Công ty.
宏明環球有限公司謹向貴公司致以誠摯的問候。

Chúng tôi xin thông báo về tình hình thanh toán của các hợp đồng hiện tại giữa hai công ty. Hiện tại, các hạng mục dự án đã được Hong Ming triển khai hoàn tất, đưa vào vận hành ổn định và ký kết biên bản nghiệm thu đầy đủ. Tuy nhiên, theo ghi nhận của bộ phận kế toán, Quý Công ty hiện còn khoản thanh toán 10% (đợt quyết toán cuối / 尾款) chưa được tất toán, chi tiết như sau:
現就雙方目前的合約付款情況進行提醒。宏明環球已全數完成專案建置、交付驗收合格並維持系統穩定運行。但依我司財務紀錄，貴公司目前尚有 10% 的尾款尚未結清，明細如下：

1. Hợp đồng phần cứng VONMAX (Hardware): 10% còn lại = 45.200.000 VNĐ
2. Hợp đồng phần mềm kết nối máy dập: 10% còn lại = 38.600.000 VNĐ
3. Hợp đồng bảo trì hệ thống định kỳ: 10% còn lại = 12.000.000 VNĐ
Tổng số tiền cần thanh toán / 應付總金額: 95.800.000 VNĐ (Chín mươi lăm triệu tám trăm nghìn đồng chẵn)

Kính nhờ Quý Công ty hỗ trợ kiểm tra và sắp xếp giải ngân khoản tiền nêu trên trước ngày 30/10/2026 để hai bên hoàn tất việc đối soát sổ sách kế toán. Cảm ơn Quý Công ty!

Trân trọng / 敬上,
Bộ phận Kế toán & Quản lý Công nợ / 財務會計暨應收帳款管理部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "CUSTOMS_CLEARANCE_EPE",
        "name": "5. Bộ chứng từ Hải quan Xuất Nhập Khẩu Tại Chỗ (KCX)",
        "category": "Hải quan / Xuất nhập khẩu",
        "customer": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
        "recipient": "acc05_vn@mail.cxtechnology.com",
        "cc": "invoice@hongming-global.com; sales@hongming-global.com",
        "subject": "CHỨNG TỪ XUẤT HẢI QUAN 300 PCS RFID Gửi bộ chứng từ & Xác nhận thời gian giao hàng – CX Technology",
        "contract_number": "HMV151020250001",
        "amount": 234000000,
        "due_date": "2026-07-28",
        "attachments": ["INV_PKL_CX_300_PCS_RFID.pdf", "C26THM_00000009.pdf", "ToKhaiHQ7X_QDTQ_308764712341.xls"],
        "required_attachments": ["Commercial Invoice + Packing List", "Hóa đơn GTGT chính thức", "Tờ khai hải quan xuất khẩu đã thông quan"],
        "body": """Kính gửi: Chị Kim Ngân - Quý Công ty Cổ phần CX Technology (VN) / Bộ phận Xuất Nhập Khẩu & Thủ Kho,
敬致 CX Technology 貴公司 / 進出口物流部暨倉庫管理組：

Hong Ming xin thông báo lô hàng 300 chiếc thẻ RFID theo Hợp đồng số HMV151020250001 đã được Chi cục Hải quan hoàn tất thủ tục thông quan xuất khẩu tại chỗ.
宏明謹通知合約編號 HMV151020250001 項下 300 PCS RFID 電子標籤之廠內出口報關手續已全數通關完成。

Hong Ming xin gửi kèm trọn bộ chứng từ hải quan để Quý Công ty tiến hành mở tờ khai nhập khẩu đối ứng:
1. Hóa đơn thương mại và Bảng kê đóng gói: `INV_PKL_CX.pdf`
2. Hóa đơn GTGT điện tử chính thức: `C26THM_00000009.pdf`
3. Tờ khai hải quan xuất khẩu đã thông quan: `ToKhaiHQ7X_308764712341.xls`

Xác nhận thời gian giao hàng: Kính nhờ Chị cho Hong Ming hỏi bên mình có thể nhận hàng luôn hay cần chờ hoàn tất tờ khai nhập khẩu đối ứng? Chị phản hồi sớm giúp em để bên em kịp bố trí xe giao hàng nhé. Em cảm ơn Chị!

Trân trọng / 敬上,
Bộ phận Xuất Nhập Khẩu & Kế toán / 進出口暨財務會計組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "EMS_OUTREACH_VIMF",
        "name": "6. Giới thiệu Giải pháp Tiết kiệm điện EMS & Lá Chắn Điện Xanh",
        "category": "Kinh doanh / Chào hàng",
        "customer": "CÔNG TY TNHH CÔNG NGHIỆP TỰ ĐỘNG HÓA",
        "recipient": "dat.nguyen@factory.com.vn",
        "cc": "sales@hongming-global.com",
        "subject": "Giới thiệu giải pháp tiết kiệm năng lượng và tối ưu chất lượng điện năng của HONG MING GLOBAL / 宏明環球工廠節能解決方案",
        "contract_number": "EMS-SURVEY-2026",
        "amount": 0,
        "due_date": "",
        "attachments": ["Hong_Ming_Global_浤詺簡介.pdf", "Catalog_Song_Hai_Hong_Ming_Global.pdf", "Hong_Ming_Global_Du_An_Thuc_Te.pdf"],
        "required_attachments": ["Hồ sơ năng lực Profile công ty", "Catalog xử lý sóng hài", "Báo cáo số liệu dự án thực tế"],
        "body": """Kính gửi: Anh Nguyễn Văn Đạt - Quý Công ty / Bộ phận Cơ điện & Quản lý Nhà máy,
敬致：阮文達 廠長 / 廠務工程部 – 貴公司：

Lời đầu tiên, CÔNG TY TNHH TOÀN CẦU HONG MING (HONG MING GLOBAL) xin chân thành cảm ơn Anh đã dành thời gian ghé thăm gian hàng và trao đổi cùng chúng tôi tại Triển lãm Tự động hóa Công nghiệp Việt Nam (VIMF).
宏明環球責任有限公司誠摯感謝您日前蒞臨越南工業自動化展（VIMF）宏明展位參觀與交流。

Nhân dịp này, chúng tôi xin trân trọng giới thiệu đến Quý Công ty bộ giải pháp chuyên sâu của Hong Ming Global về Tối ưu chất lượng điện năng, Lọc sóng hài và Tiết kiệm năng lượng (EMS) dành cho các nhà máy sản xuất công nghiệp.
Hong Ming Global đã phát triển và chuyển giao công nghệ Green Power Shield (Tủ Lá Chắn Điện Xanh) giúp:
* Triệt tiêu sóng hài dòng điện và điện áp, ổn định hệ số công suất PF trên 0.98.
* Giảm trực tiếp tổn thất nhiệt trên đường dây và máy biến áp, mang lại hiệu quả tiết kiệm điện từ 5% đến 15% tổng điện tiêu thụ.

Đề xuất đo đạc miễn phí: Hong Ming xin đề xuất cử đội ngũ kỹ sư mang thiết bị chuyên dụng đến đo đạc và lập Báo cáo đánh giá chất lượng điện năng hoàn toàn miễn phí tại trạm biến áp của Quý nhà máy.

Trân trọng / 敬上,
Jenson Chang (Trương Vĩnh Cát / 張永吉) - Giám đốc Kỹ thuật & Kinh doanh
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: sales@hongming-global.com"""
    },
    {
        "id": "PROCUREMENT_ORDER_SUPPLIER",
        "name": "7. Đơn Đặt Hàng Thiết Bị (PO) gửi Nhà Cung Cấp (Advantech / TBL)",
        "category": "Mua hàng / PO",
        "customer": "CÔNG TY TNHH ADVANTECH VIỆT NAM / TBL",
        "recipient": "sales.vn@advantech.com",
        "cc": "procurement@hongming-global.com; sales@hongming-global.com",
        "subject": "Đơn Đặt Hàng Thiết Bị (PO) – Dự Án Seiyo / CX – Hong Ming Global / 採購訂單",
        "contract_number": "PO-HM-202610-01",
        "amount": 85000000,
        "due_date": "2026-11-10",
        "attachments": ["PO_HM_202610_01_ADVANTECH.xlsx"],
        "required_attachments": ["File Excel Đơn đặt hàng PO có ký duyệt", "Bản sao xác nhận báo giá nhà cung cấp"],
        "body": """Kính gửi: Bộ phận Kinh doanh & Quản lý Đơn hàng - Quý Công ty Đối tác (Advantech / TBL),
敬致 貴公司業務暨訂單管理組：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi Quý Công ty Đơn đặt hàng (Purchase Order - PO) cho dự án triển khai tự động hóa nhà máy với thông tin chi tiết như sau:
宏明環球責任有限公司特此發出採購訂單（PO），詳細物料清單如下：

* Dự án áp dụng / 適用專案: Triển khai IoT giám sát máy công nghiệp (Seiyo / CX Technology)
* Danh mục thiết bị đặt mua / 採購品項:
  1. Module thu thập tín hiệu I/O ADAM-4055 / ADAM-4017+: Số lượng 03 Bộ
  2. Màn hình TV công nghiệp 43 Inch hiển thị trực quan: Số lượng 02 Chiếc
  3. Bộ đổi nguồn công nghiệp Meanwell 24VDC: Số lượng 04 Chiếc
* Yêu cầu tiến độ giao hàng (ETA) / 預計交期: Trước ngày 10/11/2026
* Địa điểm giao hàng / 交貨地點: Kho Hong Ming Global (Quận 7, TP.HCM)

Kính nhờ Quý Công ty kiểm tra tồn kho, xác nhận đơn hàng (PI/Sales Confirmation) và thời gian giao hàng sớm nhất để Hong Ming sắp xếp thanh toán tạm ứng.

Trân trọng / 敬上,
Bộ phận Quản lý Thu mua & Chuỗi Cung ứng / 採購暨供應鏈管理部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "SCHEMA_DATABASE_HANDOVER",
        "name": "8. Bàn Giao Cấu Trúc CSDL (Database Schema / API) cho IT Đối Tác",
        "category": "Kỹ thuật / IT",
        "customer": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN) - IT DEPT",
        "recipient": "it_support@cxtechnology.com",
        "cc": "jenson.chang@hongming-global.com; sales@hongming-global.com",
        "subject": "Bàn giao cấu trúc bảng CSDL (Database Schema) & Tài liệu tích hợp MES - ERP – Hong Ming Global",
        "contract_number": "CX-RFID-ERP-PHASE2",
        "amount": 0,
        "due_date": "",
        "attachments": ["HongMing_CX_RFID_Database_Schema_v2.0.sql", "Tai_Lieu_Tich_Hop_API_HongMing.pdf"],
        "required_attachments": ["Script SQL tạo bảng và trigger CSDL", "Tài liệu đặc tả API RESTful / Modbus TCP"],
        "body": """Kính gửi: Đội ngũ Kỹ thuật CNTT & Quản trị Hệ thống ERP - Quý Công ty CX Technology,
敬致 CX Technology 資訊科技暨 ERP 系統維運團隊：

Thực hiện theo kế hoạch tích hợp đồng bộ dữ liệu giữa Hệ thống Quét RFID Trạm sản xuất của Hong Ming và Phần mềm Quản trị ERP nội bộ của CX Technology, Hong Ming xin gửi tài liệu bàn giao cấu trúc bảng dữ liệu (Database Schema) như sau:
為配合宏明 RFID 產線刷卡系統與貴廠內部 ERP 系統之即時數據串接，特此交付最新版資料庫結構與 API 規格文件：

1. Bảng dữ liệu chính / 核心資料表：
   - `rfid_scan_logs`: Lưu toàn bộ lịch sử quét thẻ trạm gia công dập / tiện (DeviceID, TagUID, WorkOrder, Timestamp).
   - `rfid_tag_master`: Danh mục định danh thẻ RFID chịu nhiệt gắn trên khay khuôn.
   - `machine_heartbeat`: Giám sát trạng thái hoạt động online/offline và nhịp đập của Gateway.
2. Phương thức tích hợp: Hong Ming cung cấp sẵn Trigger tự động ghi nhận vào Stored Procedure trung gian hoặc gọi API RESTful qua giao thức nội bộ.

Kính mời đội ngũ IT của CX cùng phối hợp kiểm tra kết nối (Ping & Query test) trên môi trường Staging trong tuần này.

Trân trọng / 敬上,
Jenson Chang (Trương Vĩnh Cát / 張永吉) - Trưởng nhóm Kỹ thuật Tích hợp
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "RMA_WARRANTY_BATTERY_REPAIR",
        "name": "9. Báo Giá Đổi Pin & Sửa Chữa Thiết Bị RMA (CX Technology)",
        "category": "Bảo hành / RMA",
        "customer": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
        "recipient": "production_lead@cxtechnology.com",
        "cc": "sales@hongming-global.com",
        "subject": "Báo cáo kiểm tra sự cố & Phương án thay pin thiết bị quét mã cầm tay RMA – CX Technology",
        "contract_number": "RMA-CX-2026-09",
        "amount": 13700000,
        "due_date": "2026-10-28",
        "attachments": ["Bao_Gia_Sua_Chua_Thay_Pin_CX.xlsx", "Bien_Ban_Kiem_Tra_Pin_HongMing.pdf"],
        "required_attachments": ["Bảng báo giá linh kiện sửa chữa (.xlsx)", "Hình ảnh hiện trường pin phồng và biên bản kiểm tra"],
        "body": """Kính gửi: Ban Quản lý Xưởng & Kỹ sư Phụ trách - Quý Công ty CX Technology,
敬致 CX 廠務組暨設備維護工程師：

Hong Ming Global xin gửi báo cáo kỹ thuật về việc kiểm tra lô 05 thiết bị quét mã di động nhận về bảo hành (RMA) từ nhà máy CX:
宏明環球特此回覆日前自貴廠取回檢修之 05 台手持掃描設備（RMA）檢測報告：

* Hiện tượng ghi nhận / 故障現象: Thiết bị sập nguồn nhanh, vỏ máy có dấu hiệu kênh hở do cell pin lithium bên trong bị chai phồng sau 2 năm vận hành liên tục 3 ca.
* Phương án xử lý / 處理對策: Thay thế toàn bộ 05 cell pin công nghiệp dung lượng cao chính hãng đạt chuẩn phòng chống cháy nổ và hiệu chuẩn lại mạch sạc.
* Tổng chi phí sửa chữa & thay thế / 檢修暨換新總費用: 13.700.000 VNĐ (Chưa VAT).
* Thời gian hoàn tất & bàn giao / 完工交期: 03 ngày làm việc kể từ khi nhận được xác nhận từ Quý Công ty.

Kính gửi kèm Bảng báo giá chi tiết và Biên bản kiểm tra hiện trạng thiết bị. Kính nhờ Quý Công ty xem xét phê duyệt để Hong Ming tiến hành thay thế linh kiện kịp thời phục vụ sản xuất.

Trân trọng / 敬上,
Bộ phận Dịch vụ Kỹ thuật & RMA / 技術售後暨維修服務組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    },
    {
        "id": "PO_BATCH_DELIVERY_CONFIRM",
        "name": "10. Thông Báo Chính Sách Gộp Lô Hàng PO & Kế Hoạch Giao Hàng",
        "category": "Giao hàng / Kho",
        "customer": "CÔNG TY CỔ PHẦN CX TECHNOLOGY (VN)",
        "recipient": "acc05_vn@mail.cxtechnology.com",
        "cc": "invoice@hongming-global.com; sales@hongming-global.com",
        "subject": "Thông báo kế hoạch giao hàng gộp lô PO thiết bị & thẻ RFID – CX Technology",
        "contract_number": "PO-CX-OCT26",
        "amount": 0,
        "due_date": "2026-10-31",
        "attachments": ["Ke_Hoach_Giao_Hang_Gop_Lo_CX.pdf"],
        "required_attachments": ["Bảng kê chi tiết các PO gộp lô", "Biên bản bàn giao hàng hóa dự kiến"],
        "body": """Kính gửi: Chị Kim Ngân & Bộ phận Kho vận - Quý Công ty CX Technology (VN),
敬致 CX 倉儲物流組暨進出口負責人：

Hong Ming Global xin gửi lời chào trân trọng và xin thông báo về kế hoạch giao hàng đối với các Đơn hàng (PO) đã đến hạn bàn giao trong tháng:
宏明環球特此就本月份待交貨之數筆採購訂單（PO）安排合併出貨事宜，通知如下：

Để tối ưu hóa thủ tục mở tờ khai hải quan nhập khẩu tại chỗ và thuận tiện cho công tác kiểm đếm nhập kho của Quý Công ty, Hong Ming xin phép gộp các PO sau vào cùng 01 chuyến xe giao hàng:
為簡化貴廠廠內海關報關作業並利於倉庫清點驗收，我司建議將以下訂單安排同批次專車運送：
1. PO số 202610-01: 200 chiếc Thẻ RFID chịu nhiệt độ cao 250 độ C
2. PO số 202610-04: 02 bộ Nguồn công nghiệp 24VDC dự phòng
3. PO số 202610-09: 05 máy quét cầm tay sau bảo hành đã thay pin mới

Thời gian giao hàng dự kiến / 預計送達時間: Thứ Sáu, ngày 31/10/2026 (Buổi sáng lúc 09:30).
Kính nhờ Quý Công ty bố trí nhân sự kho và chuẩn bị tiếp nhận kiểm tra hàng hóa.

Trân trọng / 敬上,
Bộ phận Điều phối Giao nhận / 物流配送協調組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
    }
]


class EmailPayloadModel(BaseModel):
    email_type: str = Field(..., description="ID loại email")
    customer_name: str
    recipient_email: str
    cc_emails: Optional[str] = ""
    subject: str
    body_text: str
    amount: Optional[float] = 0
    due_date: Optional[str] = ""
    attachments: List[str] = []
    is_safe_mode: bool = True  # Luôn mặc định là True để bảo vệ an toàn
    source_module: Optional[str] = ""
    source_id: Optional[int] = None


@router.get("/emails", response_class=HTMLResponse)
@router.get("/email-center", response_class=HTMLResponse)
async def email_center_view(request: Request):
    """Giao diện Web Soạn Thảo & Gửi Email An Toàn."""
    return templates.TemplateResponse(
        request,
        "email_page.html",
        {
            "request": request,
            "active_tab": "email_center",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Trung Tâm Soạn Thảo & Gửi Email B2B Song Ngữ",
            "presets": [safe_email_context(p) for p in EMAIL_PRESETS]
        }
    )


@router.get("/api/emails/templates")
async def get_email_templates():
    """Trả về danh sách 10 mẫu email thực tế chuẩn hóa."""
    return JSONResponse(content={
        "status": "success",
        "data": [safe_email_context(p) for p in EMAIL_PRESETS]
    })


@router.get("/api/emails/quick-sources")
async def get_quick_sources():
    """
    Trả về toàn bộ danh mục đối tượng thực tế từ CSDL để kết nối vào Email:
    Hợp đồng, Công nợ (AR), Đợt thanh toán (Milestones), Mua hàng (PO), Đơn xin thanh toán (Voucher), Báo giá.
    """
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Hợp đồng mua bán
    contracts = []
    for r in c.execute("""
        SELECT id, contract_code, customer_name_vi, customer_name_zh, 
               project_name_vi, project_name_zh, total_amount, paid_amount, 
               contact_email, contact_cc, status, signed_date
        FROM contracts ORDER BY id DESC
    """).fetchall():
        contracts.append(dict(r))

    # 2. Công nợ phải thu (AR)
    receivables = []
    for r in c.execute("""
        SELECT id, order_no, project_name, customer_name, contract_code, 
               total_contract_amount, net_amount, vat_amount, gross_amount, 
               received_amount, remaining_debt, due_date, customer_promised_date, 
               collection_status, doc_status, notes
        FROM project_receivables ORDER BY id DESC
    """).fetchall():
        receivables.append(dict(r))

    # 3. Đợt thanh toán hợp đồng (Milestones)
    milestones = []
    for r in c.execute("""
        SELECT id, contract_id, contract_code, milestone_name, percentage, 
               amount, due_date, status, action_required, invoice_no
        FROM payment_milestones ORDER BY id DESC
    """).fetchall():
        milestones.append(dict(r))

    # 4. Đơn mua hàng nhà cung cấp (PO)
    procurements = []
    for r in c.execute("""
        SELECT id, order_no, project_name, customer_company, item_name, 
               quantity, unit, supplier_name, order_date, eta_date, 
               actual_delivery_date, total_amount, delivery_status, shipping_notes
        FROM procurement_orders ORDER BY id DESC
    """).fetchall():
        procurements.append(dict(r))

    # 5. Đơn xin thanh toán chi phí (Voucher Requests)
    vouchers = []
    for r in c.execute("""
        SELECT id, report_code, request_date, beneficiary_name, account_number, 
               bank_name, amount, full_reason, prepared_by
        FROM payment_voucher_requests ORDER BY id DESC
    """).fetchall():
        vouchers.append(dict(r))

    # 6. Báo giá
    quotations = []
    for r in c.execute("""
        SELECT id, quotation_no, customer_name_vi, customer_name_zh, 
               project_name, subtotal, vat_amount, total_amount, lead_time, validity
        FROM quotations ORDER BY id DESC
    """).fetchall():
        quotations.append(dict(r))

    conn.close()

    return JSONResponse(content={
        "status": "success",
        "data": {
            "contracts": contracts,
            "receivables": receivables,
            "milestones": milestones,
            "procurements": procurements,
            "payment_vouchers": vouchers,
            "quotations": quotations,
            "presets": [safe_email_context(p) for p in EMAIL_PRESETS]
        }
    })


@router.get("/api/emails/load-context")
async def load_email_context(
    source: str = Query(..., description="Tên module nguồn: contract, receivable, milestone, po, voucher, quotation, acceptance, file, preset"),
    id: Optional[int] = Query(None, description="ID của đối tượng"),
    code: Optional[str] = Query(None, description="Mã đối tượng (nếu có)"),
    file_name: Optional[str] = Query(None, description="Tên file đính kèm từ Quản Lý File"),
    category: Optional[str] = Query(None, description="Phân loại file")
):
    """
    NẠP VÀ TỰ ĐỘNG SOẠN EMAIL THEO NGỮ CẢNH CỦA ĐỐI TƯỢNG ĐƯỢC CHỌN:
    Tự động điền: Người nhận, CC, Tiêu đề song ngữ, Số tiền (bằng chữ Việt - Đài Loan),
    Hạn TT / ETA, Tài khoản Cathay United Bank, File đính kèm chuẩn xác 100%.
    """
    if source == 'milestone':
        from app.services import workflow_service as work
        work.init_schema()
        work.sync_milestones()
        with get_db_connection() as workflow_conn:
            found = workflow_conn.execute('SELECT id FROM workflow_cases WHERE milestone_id=?', (id,)).fetchone()
        if not found:
            raise HTTPException(status_code=404, detail='Chọn đúng đợt thu trong Hồ sơ hợp đồng.')
        case = work.get_case(found['id'])
        suggestion = work.email_text(case['id'])
        return JSONResponse(content={'status':'success','data':{
            'source':'milestone','source_id':id,'email_type':'PAYMENT_MILESTONE',
            'customer_name':case['customer'],'recipient_email':case['recipient'],'cc_emails':case['cc'],
            'subject':suggestion['subject'],'body':suggestion['body'],'amount':case['remaining'],
            'contract_number':case['contract_code'],'due_date':case['due_date'],
            'attachments':[], 'required_attachments':['Chọn bản ký đã kiểm tra trong Việc cần làm'],
            'workflow_url':f'/workflows?case={case["id"]}'}})
    if file_name and not code:
        code = file_name
    conn = get_db_connection()
    c = conn.cursor()

    res = {
        "source": source,
        "source_id": id,
        "email_type": "GENERAL",
        "customer_name": "",
        "recipient_email": "",
        "cc_emails": "sales@hongming-global.com; pm02@hongming-global.com",
        "subject": "",
        "contract_number": "",
        "amount": 0,
        "due_date": "",
        "attachments": [],
        "required_attachments": [],
        "body": ""
    }

    # =========================================================================
    # 1. KẾT NỐI TỪ CÔNG NỢ PHẢI THU (AR RECEIVABLES & NHẮC NỢ)
    # =========================================================================
    if source in ("receivable", "debt"):
        rec = None
        if id:
            rec = c.execute("SELECT * FROM project_receivables WHERE id = ?", (id,)).fetchone()
        elif code:
            rec = c.execute("SELECT * FROM project_receivables WHERE contract_code = ?", (code,)).fetchone()
        if not rec:
            rec = c.execute("SELECT * FROM project_receivables ORDER BY id DESC LIMIT 1").fetchone()

        if rec:
            rec = dict(rec)
            contract = None
            if rec.get("contract_code"):
                c_row = c.execute("SELECT * FROM contracts WHERE contract_code = ?", (rec["contract_code"],)).fetchone()
                if c_row:
                    contract = dict(c_row)

            cust_name = rec.get("customer_name") or (contract.get("customer_name_vi") if contract else "Quý Khách Hàng")
            contact_email = (contract.get("contact_email") if contract else "") or "ke-toan@" + cust_name.lower().replace(" ", "").replace("côngtytnhh", "").replace("côngtycổphần", "")[:12] + ".com.vn"
            c_code = rec.get("contract_code") or (contract.get("contract_code") if contract else "HD-PM")
            proj_name = rec.get("project_name") or (contract.get("project_name_vi") if contract else "Dự án IIoT")
            
            amount_debt = rec.get("remaining_debt") or rec.get("gross_amount") or 0
            if amount_debt <= 0:
                amount_debt = rec.get("gross_amount") or 0

            due_date = rec.get("due_date") or rec.get("customer_promised_date") or ""
            is_overdue = rec.get("collection_status") == "DELAYED"
            is_urgent = rec.get("collection_status") == "URGENT"

            words_vi = number_to_vietnamese_words(int(amount_debt)) if amount_debt > 0 else "Không đồng chẵn."
            words_zh = number_to_chinese_words(int(amount_debt)) if amount_debt > 0 else "零越盾整"
            amt_formatted = format_currency_vnd(amount_debt)

            if is_overdue:
                subject_text = f"[THƯ NHẮC NỢ QUÁ HẠN] Đề nghị thanh toán công nợ – HĐ {c_code} - {cust_name} / 逾期帳款催收通知函"
                prefix_tone = f"Chúng tôi xin thông báo khoản công nợ của Quý Công ty theo Hợp đồng số {c_code} ({proj_name}) hiện đã QUÁ HẠN THANH TOÁN thỏa thuận."
                prefix_tone_zh = f"特此通知，貴公司依合約編號 {c_code}（{proj_name}）項下之應付期款目前已逾約定付款期限。"
            elif is_urgent:
                subject_text = f"[NHẮC HẸN THANH TOÁN] Công nợ sắp đến hạn – HĐ {c_code} - {cust_name} / 即將到期付款提醒"
                prefix_tone = f"Hong Ming xin nhắc lịch thanh toán sắp đến hạn đối với Hợp đồng số {c_code} ({proj_name})."
                prefix_tone_zh = f"宏明環球特此就合約編號 {c_code}（{proj_name}）項下即將到期之款項進行提醒。"
            else:
                subject_text = f"Đề nghị thanh toán công nợ – HĐ {c_code} - {cust_name} / 專案請款通知函"
                prefix_tone = f"Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi bảng đối chiếu công nợ và đề nghị thanh toán theo Hợp đồng số {c_code}."
                prefix_tone_zh = f"宏明環球責任有限公司特此檢送對帳單暨請款通知（合約編號：{c_code}）。"

            res.update({
                "email_type": "DEBT_REMINDER",
                "customer_name": cust_name,
                "recipient_email": contact_email,
                "cc_emails": (contract.get("contact_cc") if contract else "") or "sales@hongming-global.com; pm02@hongming-global.com",
                "subject": subject_text,
                "contract_number": c_code,
                "amount": amount_debt,
                "due_date": due_date,
                "attachments": [f"Bang_Doi_Chieu_Cong_No_{c_code}.pdf", f"DYCTT_{c_code}.pdf"],
                "required_attachments": ["Bảng đối chiếu công nợ (SOA)", "Phiếu Đơn yêu cầu thanh toán (DYCTT) có ký đóng dấu"],
                "body": f"""Kính gửi: Quý Công ty {cust_name} / Bộ phận Kế toán & Ban Quản lý Dự án,
敬致：{cust_name} / 財務會計部暨專案管理處：

Công ty TNHH Toàn Cầu Hong Ming xin gửi lời chào trân trọng và lời chúc sức khỏe đến Quý Công ty.
宏明環球責任有限公司謹向貴公司致以誠摯問候！

{prefix_tone}
{prefix_tone_zh}

Chi tiết khoản công nợ cần thanh toán / 款項明細資訊：
* Hợp đồng số / 合約編號: {c_code}
* Dự án / 專案名稱: {proj_name}
* Giá trị hợp đồng / 合約總額: {format_currency_vnd(rec.get('total_contract_amount') or 0)}
* Số tiền đã thanh toán / 已收金額: {format_currency_vnd(rec.get('received_amount') or 0)}
* SỐ TIỀN CẦN THANH TOÁN / 應付款項: {amt_formatted}
  - Bằng chữ (Tiếng Việt): {words_vi}
  - 大寫金額 (Tiếng Trung): {words_zh}
* Hạn thanh toán / 付款期限: {due_date if due_date else "Trong vòng 05 ngày làm việc kể từ ngày nhận thư"}

Thông tin tài khoản nhận thanh toán của Hong Ming / 宏明環球指定收款帳戶：
* Đơn vị thụ hưởng / 收款戶名: CÔNG TY TNHH TOÀN CẦU HONG MING
* Số tài khoản / 帳號: 0011004123456
* Ngân hàng thụ hưởng / 開戶行: Ngân hàng TNHH MTV Cathay United Bank - Chi nhánh TP.HCM

Kính đề nghị Quý Công ty kiểm tra hồ sơ, đối chiếu chứng từ và sắp xếp chuyển khoản giải ngân trước thời hạn nêu trên để hai bên quyết toán sổ sách công nợ đúng quy định.
敬請貴公司核對單據並協助於上述期限內安排撥款，以利雙方順利結清帳款。

Xin trân trọng cảm ơn sự phối hợp của Quý Công ty!
感謝貴公司的支持與密切配合！

Trân trọng / 敬上,
Bộ phận Quản lý Công nợ & Kế toán / 財務會計暨應收帳款管理部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: sales@hongming-global.com"""
            })

    # =========================================================================
    # 2. KẾT NỐI TỪ HỢP ĐỒNG MUA BÁN (CONTRACTS)
    # =========================================================================
    elif source == "contract":
        c_row = None
        if id:
            c_row = c.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
        elif code:
            c_row = c.execute("SELECT * FROM contracts WHERE contract_code = ?", (code,)).fetchone()
        if not c_row:
            c_row = c.execute("SELECT * FROM contracts ORDER BY id DESC LIMIT 1").fetchone()

        if c_row:
            contract = dict(c_row)
            cust_name = contract.get("customer_name_vi") or "Quý Khách Hàng"
            cust_zh = contract.get("customer_name_zh") or ""
            c_code = contract.get("contract_code") or "HD-2026"
            proj_name = contract.get("project_name_vi") or "Dự án Thiết bị & Giải pháp"
            total_amt = contract.get("total_amount") or 0
            words_vi = number_to_vietnamese_words(int(total_amt)) if total_amt > 0 else ""
            words_zh = number_to_chinese_words(int(total_amt)) if total_amt > 0 else ""

            res.update({
                "email_type": "CONTRACT_DISPATCH",
                "customer_name": cust_name,
                "recipient_email": contract.get("contact_email") or "purchasing@" + cust_name.lower().replace(" ", "")[:10] + ".com",
                "cc_emails": contract.get("contact_cc") or "sales@hongming-global.com; pm02@hongming-global.com",
                "subject": f"Gửi Dự thảo Hợp đồng mua bán – Số {c_code} – Dự án {proj_name} / 檢送買賣合約草案",
                "contract_number": c_code,
                "amount": total_amt,
                "due_date": "",
                "attachments": [f"HopDong_{c_code}.docx"],
                "required_attachments": ["File Word Dự thảo hợp đồng song ngữ Việt - Trung chuẩn mẫu Hong Ming"],
                "body": f"""Kính gửi: Ban Giám Đốc & Bộ phận Pháp chế / Thu mua - Quý Công ty {cust_name}{' (' + cust_zh + ')' if cust_zh else ''},
敬致：{cust_name} 經營決策層暨採購管理組：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi tới Quý Công ty bản Dự thảo Hợp đồng mua bán cho {proj_name} với các điều khoản đã được hai bên thống nhất sơ bộ:
宏明環球責任有限公司特此檢送雙方初步達成共識之買賣合約草案，重點條款摘要如下：

* Số hợp đồng / 合約編號: {c_code}
* Tên dự án / 專案名稱: {proj_name}
* Tổng giá trị hợp đồng / 合約總金額: {format_currency_vnd(total_amt)}
  - Bằng chữ: {words_vi}
  - 大寫金額: {words_zh}
* Thời hạn bảo hành / 保固期限: 12 tháng kể từ ngày nghiệm thu đưa vào sử dụng.
* Thời gian giao hàng (Lead time): Theo quy định cụ thể tại Điều 4 của hợp đồng.

Hong Ming kính gửi kèm file Word dự thảo hợp đồng (`HopDong_{c_code}.docx`) để Quý Công ty rà soát các điều khoản pháp lý, thông tin đại diện pháp luật và số tài khoản ngân hàng.
Quý Công ty có bất kỳ đề xuất điều chỉnh nào, xin vui lòng phản hồi lại email này để chúng tôi hoàn thiện bản chính thức ký kết.

Trân trọng / 敬上,
Ban Giám Đốc & Bộ phận Hợp đồng Dự án / 專案合約組
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Đại diện: Jenson Chang (+84 966 687 109 | sales@hongming-global.com)"""
            })

    # =========================================================================
    # 3. KẾT NỐI TỪ ĐỢT THANH TOÁN (PAYMENT MILESTONES)
    # =========================================================================
    elif source == "milestone":
        m_row = None
        if id:
            m_row = c.execute("SELECT * FROM payment_milestones WHERE id = ?", (id,)).fetchone()
        if not m_row:
            m_row = c.execute("SELECT * FROM payment_milestones ORDER BY id DESC LIMIT 1").fetchone()

        if m_row:
            m = dict(m_row)
            contract = None
            if m.get("contract_code"):
                c_row = c.execute("SELECT * FROM contracts WHERE contract_code = ?", (m["contract_code"],)).fetchone()
                if c_row:
                    contract = dict(c_row)

            cust_name = (contract.get("customer_name_vi") if contract else "Quý Khách Hàng")
            c_code = m.get("contract_code") or "HD-PM"
            m_name = m.get("milestone_name") or "Đợt thanh toán"
            m_pct = m.get("percentage") or 0
            m_amt = m.get("amount") or 0
            due_date = m.get("due_date") or ""

            words_vi = number_to_vietnamese_words(int(m_amt)) if m_amt > 0 else ""
            words_zh = number_to_chinese_words(int(m_amt)) if m_amt > 0 else ""

            res.update({
                "email_type": "PAYMENT_MILESTONE",
                "customer_name": cust_name,
                "recipient_email": (contract.get("contact_email") if contract else "") or "ke-toan@khachhang.com",
                "cc_emails": (contract.get("contact_cc") if contract else "") or "sales@hongming-global.com; pm02@hongming-global.com",
                "subject": f"Đề nghị thanh toán {m_name} ({m_pct}%) – HĐ {c_code} - {cust_name} / 申請支付合約款項",
                "contract_number": c_code,
                "amount": m_amt,
                "due_date": due_date,
                "attachments": [f"DYCTT_{c_code}_{m_name.replace(' ', '_')}.pdf"],
                "required_attachments": ["File PDF Đơn yêu cầu thanh toán (DYCTT) kèm chứng từ xác nhận hoàn thành đợt"],
                "body": f"""Kính gửi: Quý Công ty {cust_name} / Phòng Kế toán & Ban Quản lý Dự án,
敬致：{cust_name} / 財務會計部暨專案管理處：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi tới Quý Công ty Phiếu yêu cầu thanh toán cho {m_name} theo Hợp đồng số {c_code}:
宏明環球責任有限公司特此檢送合約編號 {c_code} 項下之【{m_name}】付款申請文件：

* Hợp đồng tham chiếu / 關聯合約: {c_code}
* Giai đoạn thanh toán / 付款期次: {m_name} ({m_pct}% giá trị hợp đồng)
* Số tiền đề nghị thanh toán / 申請付款金額: {format_currency_vnd(m_amt)}
  - Bằng chữ (Tiếng Việt): {words_vi}
  - 大寫金額 (Tiếng Trung): {words_zh}
* Thời hạn thanh toán theo thỏa thuận / 約定付款期限: {due_date if due_date else "Trong vòng 07 ngày làm việc"}

Thông tin tài khoản thụ hưởng của Hong Ming / 宏明環球收款帳號資訊：
* Tên tài khoản / 戶名: CÔNG TY TNHH TOÀN CẦU HONG MING
* Số tài khoản / 帳號: 0011004123456
* Ngân hàng thụ hưởng / 開戶行: Ngân hàng TNHH MTV Cathay United Bank - Chi nhánh TP.HCM

Phiếu Đơn yêu cầu thanh toán (DYCTT) đã được ký duyệt và đóng dấu scan đính kèm trong thư này. Kính mong Quý Công ty hỗ trợ giải ngân đúng thời hạn.

Trân trọng / 敬上,
Bộ phận Quản lý Dự án & Kế toán / 專案部暨財務會計部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })

    # =========================================================================
    # 4. KẾT NỐI TỪ ĐƠN MUA HÀNG NHÀ CUNG CẤP (PO)
    # =========================================================================
    elif source in ("po", "procurement"):
        po_row = None
        if id:
            po_row = c.execute("SELECT * FROM procurement_orders WHERE id = ?", (id,)).fetchone()
        if not po_row:
            po_row = c.execute("SELECT * FROM procurement_orders ORDER BY id DESC LIMIT 1").fetchone()

        if po_row:
            po = dict(po_row)
            supp_name = po.get("supplier_name") or "Nhà Cung Cấp"
            proj_name = po.get("project_name") or "Dự án Hong Ming"
            item_name = po.get("item_name") or "Thiết bị vật tư"
            qty = po.get("quantity") or 1
            unit = po.get("unit") or "Bộ"
            eta = po.get("eta_date") or ""
            order_date = po.get("order_date") or datetime.now().strftime("%Y-%m-%d")

            res.update({
                "email_type": "PO_DISPATCH",
                "customer_name": supp_name,
                "recipient_email": "sales@" + supp_name.lower().replace(" ", "")[:8] + ".com",
                "cc_emails": "procurement@hongming-global.com; sales@hongming-global.com",
                "subject": f"Đơn Đặt Hàng Thiết Bị (PO) – Dự án {proj_name} – NCC {supp_name} / 採購訂單確認",
                "contract_number": f"PO-HM-{po.get('id', '01')}",
                "amount": po.get("total_amount") or 0,
                "due_date": eta,
                "attachments": [f"PO_HongMing_{po.get('id')}_{supp_name.replace(' ', '_')}.xlsx"],
                "required_attachments": ["File Excel Đơn đặt hàng PO chính thức có chữ ký duyệt"],
                "body": f"""Kính gửi: Bộ phận Kinh doanh & Quản lý Đơn hàng - Quý Nhà Cung Cấp {supp_name},
敬致 貴公司業務暨訂單管理組：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi Quý Công ty Đơn đặt hàng (Purchase Order - PO) với các thông tin chi tiết như sau:
宏明環球責任有限公司特此發出正式採購訂單（PO），明細如下：

* Dự án triển khai / 適用專案: {proj_name}
* Danh mục thiết bị đặt mua / 採購品項: {item_name}
* Số lượng / 數量: {qty} {unit}
* Ngày đặt hàng / 訂單日期: {order_date}
* Tiến độ giao hàng yêu cầu (ETA) / 預計交期: Trước ngày {eta if eta else "Thỏa thuận sớm nhất"}
* Địa điểm nhận hàng / 交貨地點: Kho Hong Ming Global (Quận 7, TP. Hồ Chí Minh)

Kính nhờ Quý Công ty kiểm tra tồn kho và phản hồi lại Xác nhận đơn hàng (Sales Confirmation / PI), thời gian giao hàng cụ thể và thông tin thanh toán để Hong Ming bố trí tạm ứng kịp thời.

Trân trọng / 敬上,
Bộ phận Thu mua & Chuỗi Cung ứng / 採購部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })

    # =========================================================================
    # 5. KẾT NỐI TỪ ĐƠN XIN THANH TOÁN (PAYMENT VOUCHERS)
    # =========================================================================
    elif source in ("voucher", "payment_voucher"):
        v_row = None
        if id:
            v_row = c.execute("SELECT * FROM payment_voucher_requests WHERE id = ?", (id,)).fetchone()
        if not v_row:
            v_row = c.execute("SELECT * FROM payment_voucher_requests ORDER BY id DESC LIMIT 1").fetchone()

        if v_row:
            v = dict(v_row)
            ben_name = v.get("beneficiary_name") or "Đơn vị thụ hưởng"
            rep_code = v.get("report_code") or "HM-PV"
            amt = v.get("amount") or 0
            reason = v.get("full_reason") or "Thanh toán chi phí dự án"
            req_date = v.get("request_date") or datetime.now().strftime("%Y-%m-%d")

            words_vi = number_to_vietnamese_words(int(amt)) if amt > 0 else ""
            words_zh = number_to_chinese_words(int(amt)) if amt > 0 else ""

            res.update({
                "email_type": "INTERNAL_VOUCHER",
                "customer_name": ben_name,
                "recipient_email": "accountant@hongming-global.com",
                "cc_emails": "tangweili@hongming-global.com; sales@hongming-global.com",
                "subject": f"Trình ký Đơn xin thanh toán – Mã {rep_code} – Thụ hưởng {ben_name} / 浤詺付款申请单呈核",
                "contract_number": rep_code,
                "amount": amt,
                "due_date": req_date,
                "attachments": [f"PhieuChi_{rep_code}.xlsx"],
                "required_attachments": ["File Excel Đơn xin thanh toán chuẩn mẫu 1:1 bảo toàn định dạng"],
                "body": f"""Kính gửi: Tổng Giám Đốc Tang Wei Li (Đường Vĩ Lực) & Phòng Kế toán Hong Ming Global,
敬呈：唐總經理暨財務會計部：

Bộ phận Kỹ thuật & Quản lý Dự án xin kính trình Đơn xin thanh toán chi phí (浤詺付款申请单) với thông tin như sau:
專案管理部謹呈報以下費用支出申請單，敬請查核批示：

* Mã phiếu / 申請單編號: {rep_code}
* Ngày đề xuất / 申請日期: {req_date}
* Đơn vị thụ hưởng / 收款戶名: {ben_name}
* Tài khoản thụ hưởng / 收款帳號: {v.get('account_number') or '-'}
* Ngân hàng / 開戶行: {v.get('bank_name') or '-'}
* Lý do thanh toán / 付款事由: {reason}
* Số tiền xin thanh toán / 申請金額: {format_currency_vnd(amt)}
  - Bằng chữ: {words_vi}
  - 大寫金額: {words_zh}

Kính trình Ban Giám Đốc xem xét phê duyệt để Bộ phận Kế toán thực hiện lệnh chuyển khoản đúng hạn.

Trân trọng / 敬呈,
Người lập đơn: {v.get('prepared_by') or 'NGUYỄN SỸ KIM BẰNG'}
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })

    # =========================================================================
    # 6. KẾT NỐI TỪ BÁO GIÁ (QUOTATIONS)
    # =========================================================================
    elif source == "quotation":
        q_row = None
        if id:
            q_row = c.execute("SELECT * FROM quotations WHERE id = ?", (id,)).fetchone()
        if not q_row:
            q_row = c.execute("SELECT * FROM quotations ORDER BY id DESC LIMIT 1").fetchone()

        if q_row:
            q = dict(q_row)
            cust_name = q.get("customer_name_vi") or "Quý Khách Hàng"
            q_no = q.get("quotation_no") or "BG-HM-2026"
            proj_name = q.get("project_name") or "Gói thiết bị tự động hóa IoT"
            tot_amt = q.get("total_amount") or 0

            res.update({
                "email_type": "QUOTATION_DISPATCH",
                "customer_name": cust_name,
                "recipient_email": "procurement@" + cust_name.lower().replace(" ", "")[:8] + ".com",
                "cc_emails": "sales@hongming-global.com",
                "subject": f"Bảng Báo Giá Thiết Bị Song Ngữ – Số {q_no} – {proj_name} – Hong Ming / 設備報價單",
                "contract_number": q_no,
                "amount": tot_amt,
                "due_date": "",
                "attachments": [f"BaoGia_{q_no}.xlsx", "Catalog_ThietBi_HongMing.pdf"],
                "required_attachments": ["Bảng tính Excel báo giá gốc chuẩn 7 hạng mục", "Catalog thông số kỹ thuật thiết bị"],
                "body": f"""Kính gửi: Bộ phận Mua hàng & Quản lý Kỹ thuật - Quý Công ty {cust_name},
敬致 貴公司採購暨工程技術評估小組：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi Quý Công ty Bảng báo giá chi tiết cho gói thiết bị {proj_name}:
宏明環球責任有限公司特此檢送【{proj_name}】之正式設備規格報價單：

* Số báo giá / 報價單編號: {q_no}
* Tổng giá trị dự toán / 報價總金額: {format_currency_vnd(tot_amt)} (Đã bao gồm VAT và vận chuyển)
* Hiệu lực báo giá / 報價有效期限: 30 ngày kể từ ngày phát hành.
* Thời gian giao hàng (Lead time): 60 – 80 ngày kể từ ngày nhận đặt cọc và hợp đồng có hiệu lực.
* Chính sách bảo hành: Bảo hành chính hãng 12 tháng tại nhà máy.

Hong Ming kính gửi kèm Bảng báo giá Excel và Catalog kỹ thuật để Quý Công ty xem xét. Chúng tôi sẵn sàng hỗ trợ khảo sát thực địa và giải đáp mọi câu hỏi kỹ thuật.

Trân trọng / 敬上,
Jenson Chang (Trương Vĩnh Cát / 張永吉) - Giám đốc Kỹ thuật & Kinh doanh
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: sales@hongming-global.com"""
            })

    # =========================================================================
    # 7. KẾT NỐI TỪ BIÊN BẢN NGHIỆM THU (ACCEPTANCE)
    # =========================================================================
    elif source == "acceptance":
        c_row = None
        if id:
            c_row = c.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
        elif code:
            c_row = c.execute("SELECT * FROM contracts WHERE contract_code = ?", (code,)).fetchone()
        if not c_row:
            c_row = c.execute("SELECT * FROM contracts ORDER BY id DESC LIMIT 1").fetchone()

        cust_name = "CÔNG TY TRÁCH NHIỆM HỮU HẠN SEIYO VIỆT NAM"
        c_code = "HMV22092026SY0001"
        proj_name = "Dự án Lắp đặt thiết bị IIoT & Màn hình hiển thị"
        amt = 427212000
        recip_email = "nguyensykimbang321@gmail.com"

        if c_row:
            contract = dict(c_row)
            cust_name = contract.get("customer_name_vi") or cust_name
            c_code = contract.get("contract_code") or c_code
            proj_name = contract.get("project_name_vi") or proj_name
            amt = contract.get("total_amount") or amt
            recip_email = contract.get("contact_email") or recip_email

        res.update({
            "email_type": "ACCEPTANCE_HANDOVER",
            "customer_name": cust_name,
            "recipient_email": recip_email,
            "cc_emails": "sales@hongming-global.com; pm02@hongming-global.com",
            "subject": f"Biên bản nghiệm thu & Bàn giao thiết bị – HĐ {c_code} - {cust_name} / 設備驗收暨移交使用確認書",
            "contract_number": c_code,
            "amount": amt,
            "due_date": "",
            "attachments": [f"Bien_Ban_Nghiem_Thu_{c_code}.docx", f"Phieu_Xuat_Kho_{c_code}.pdf"],
            "required_attachments": ["Biên bản nghiệm thu lắp đặt có ký nhận của hai bên", "Phiếu xuất kho kiêm bàn giao thiết bị"],
            "body": f"""Kính gửi: Ban Giám Đốc & Đại diện Kỹ thuật - Quý Công ty {cust_name},
敬致 貴公司經營主管暨專案技術負責人：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi tới Quý Công ty Biên bản nghiệm thu và bàn giao thiết bị đưa vào sử dụng sau khi hai bên đã tiến hành chạy thử nghiệm và kiểm tra chức năng hệ thống cho {proj_name}:
宏明環球責任有限公司特此檢送【{proj_name}】之設備現場安裝、功能測試完成暨正式移交使用確認書：

* Hợp đồng tham chiếu / 關聯合約: {c_code}
* Hạng mục nghiệm thu / 驗收項目: Hoàn tất kết nối hệ thống IIoT, cài đặt phần mềm giám sát trạm máy và đo đạc thông số thực tế.
* Kết quả kiểm tra / 測試結果: Hệ thống hoạt động ổn định, đạt đầy đủ các tiêu chuẩn kỹ thuật đề ra theo thỏa thuận hợp đồng.
* Biên bản nghiệm thu bàn giao đã được ký xác nhận bởi kỹ sư phụ trách hai bên.

Hong Ming xin gửi kèm bản scan biên bản nghiệm thu đầy đủ để Quý Công ty lưu trữ và làm căn cứ giải ngân giai đoạn thanh toán tiếp theo.

Trân trọng / 敬上,
Bộ phận Kỹ thuật & Dịch vụ Khách hàng / 技術暨售後服務部
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司
Hotline: +84 966 687 109 | Email: sales@hongming-global.com"""
        })

    # =========================================================================
    # 8. KẾT NỐI TỪ TRUNG TÂM QUẢN LÝ FILE (FILE MANAGER)
    # =========================================================================
    elif source == "file":
        file_name = code or (c.execute("SELECT contract_code FROM contracts ORDER BY id DESC LIMIT 1").fetchone() or {}).get("contract_code", "TaiLieu.pdf")
        # Phán đoán loại hồ sơ từ tên file hoặc category
        if "hopdong" in file_name.lower() or "hd" in file_name.lower():
            res.update({
                "email_type": "CONTRACT_DISPATCH",
                "customer_name": "Quý Khách Hàng",
                "recipient_email": "sales@hongming-global.com",
                "cc_emails": "pm02@hongming-global.com",
                "subject": f"Gửi hồ sơ tài liệu Hợp đồng đính kèm: {file_name} / 檢送合約文件",
                "contract_number": "HD-DOC",
                "amount": 0,
                "due_date": "",
                "attachments": [file_name],
                "required_attachments": ["File Hợp đồng kinh tế song ngữ"],
                "body": f"""Kính gửi: Quý Đối Tác / Ban Quản Lý Dự Án,
敬致 貴公司專案管理團隊：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi tới Quý Công ty file hồ sơ hợp đồng đính kèm: `{file_name}`.
宏明環球責任有限公司特此檢送隨信附件之合約文件：`{file_name}`。

Kính nhờ Quý Công ty rà soát và lưu trữ tài liệu. Mọi phản hồi xin vui lòng liên hệ lại với chúng tôi.

Trân trọng / 敬上,
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })
        elif "baogia" in file_name.lower() or "bg" in file_name.lower():
            res.update({
                "email_type": "QUOTATION_DISPATCH",
                "customer_name": "Quý Khách Hàng",
                "recipient_email": "sales@hongming-global.com",
                "cc_emails": "pm02@hongming-global.com",
                "subject": f"Gửi Bảng Báo Giá Thiết Bị đính kèm: {file_name} / 檢送設備規格報價單",
                "contract_number": "BG-DOC",
                "amount": 0,
                "due_date": "",
                "attachments": [file_name],
                "required_attachments": ["Bảng tính Excel báo giá gốc"],
                "body": f"""Kính gửi: Bộ phận Mua hàng & Quản lý Dự án - Quý Khách Hàng,
敬致 貴公司採購暨專案評估小組：

Hong Ming Global xin gửi kèm Bảng báo giá thiết bị chi tiết: `{file_name}` để Quý Công ty xem xét và phê duyệt ngân sách.
宏明環球特此檢附設備規格報價單：`{file_name}`，敬請貴公司參閱審查。

Trân trọng / 敬上,
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })
        else:
            res.update({
                "email_type": "GENERAL_ATTACHMENT",
                "customer_name": "Quý Khách Hàng / Quý Đối Tác",
                "recipient_email": "sales@hongming-global.com",
                "cc_emails": "pm02@hongming-global.com",
                "subject": f"Gửi tài liệu hồ sơ dự án đính kèm: {file_name} – Hong Ming Global",
                "contract_number": "DOC-REF",
                "amount": 0,
                "due_date": "",
                "attachments": [file_name],
                "required_attachments": ["Tài liệu dự án liên quan"],
                "body": f"""Kính gửi: Quý Đối Tác / Bộ phận Liên quan,
敬致 貴公司專案相關部門：

Công ty TNHH Toàn Cầu Hong Ming trân trọng gửi tới Quý Công ty tài liệu dự án đính kèm: `{file_name}`.
宏明環球責任有限公司特此檢送隨信附件之專案資料：`{file_name}`。

Kính nhờ Quý Công ty kiểm tra và phản hồi xác nhận nếu cần thêm thông tin.

Trân trọng / 敬上,
CÔNG TY TNHH TOÀN CẦU HONG MING / 宏明環球有限公司"""
            })

    # =========================================================================
    # 9. MẪU PRESET NẾU SOURCE LÀ PRESET
    # =========================================================================
    elif source == "preset" and code:
        found = next((p for p in EMAIL_PRESETS if p["id"] == code), None)
        if found:
            res.update({
                "email_type": found["id"],
                "customer_name": found.get("customer", ""),
                "recipient_email": found.get("recipient", ""),
                "cc_emails": found.get("cc", ""),
                "subject": found.get("subject", ""),
                "contract_number": found.get("contract_number", ""),
                "amount": found.get("amount", 0),
                "due_date": found.get("due_date", ""),
                "attachments": found.get("attachments", []),
                "required_attachments": found.get("required_attachments", []),
                "body": found.get("body", "")
            })

    conn.close()
    return JSONResponse(content={"status": "success", "data": safe_email_context(res)})


@router.post("/api/emails/save-draft")
async def save_email_draft(payload: EmailPayloadModel):
    """Lưu thư nháp an toàn vào cơ sở dữ liệu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    code = f"EMAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute("""
    INSERT INTO emails (email_code, email_type, customer_name, recipient_email, cc_emails, subject, body_text, amount, due_date, attachments_json, is_safe_mode, status, source_module, source_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
    """, (
        code, payload.email_type, payload.customer_name, payload.recipient_email,
        payload.cc_emails, payload.subject, payload.body_text, payload.amount,
        payload.due_date, json.dumps(payload.attachments, ensure_ascii=False),
        1 if payload.is_safe_mode else 0,
        payload.source_module, payload.source_id
    ))
    conn.commit()
    inserted_id = cursor.lastrowid
    conn.close()

    return JSONResponse(content={
        "status": "success",
        "message": "Đã lưu bản nháp email thành công!",
        "email_code": code,
        "id": inserted_id
    })


@router.post("/api/emails/simulate-send")
async def simulate_send_email(payload: EmailPayloadModel):
    """
    MÔ PHỎNG GỬI EMAIL AN TOÀN (SAFE SIMULATION - DRY RUN).
    Cam kết: Tuyệt đối KHÔNG gửi thật ra bên ngoài đến khách hàng.
    Hệ thống ghi nhận vào lịch sử gửi với nhãn SIMULATED_SENT.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    code = f"EMAIL-SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute("""
    INSERT INTO emails (email_code, email_type, customer_name, recipient_email, cc_emails, subject, body_text, amount, due_date, attachments_json, is_safe_mode, status, source_module, source_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 'SIMULATED_SENT', ?, ?)
    """, (
        code, payload.email_type, payload.customer_name, payload.recipient_email,
        payload.cc_emails, payload.subject, payload.body_text, payload.amount,
        payload.due_date, json.dumps(payload.attachments, ensure_ascii=False),
        payload.source_module, payload.source_id
    ))
    conn.commit()
    conn.close()

    return JSONResponse(content={
        "status": "success",
        "mode": "SAFE_SIMULATION_MODE",
        "message": f"Mô phỏng gửi thành công! (Chế độ an toàn: Chưa gửi thật đến khách hàng {payload.customer_name})",
        "tracking_code": code,
        "simulated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@router.get("/api/emails/history")
async def get_email_history():
    """Lấy danh sách các email đã soạn và đã mô phỏng gửi."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM emails ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        history.append({
            "id": r["id"],
            "email_code": r["email_code"],
            "email_type": r["email_type"],
            "customer_name": r["customer_name"],
            "recipient_email": r["recipient_email"],
            "subject": r["subject"],
            "amount": r["amount"],
            "status": r["status"],
            "is_safe_mode": bool(r["is_safe_mode"]),
            "source_module": r["source_module"] if "source_module" in r.keys() else "",
            "created_at": str(r["created_at"])
        })

    return JSONResponse(content={
        "status": "success",
        "total": len(history),
        "data": history
    })
