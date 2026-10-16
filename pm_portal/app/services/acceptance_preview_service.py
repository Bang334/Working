"""Acceptance HTML preview service rendering live paper view and rich text."""

import html
from typing import Any, Dict

from app.services.acceptance_excel_service import prepare_acceptance_data


def generate_acceptance_preview_html(raw_data: Dict[str, Any]) -> str:
    """Generate high-fidelity HTML reproducing the physical A4 acceptance document."""
    data = prepare_acceptance_data(raw_data)

    items = data.get("hang_muc") or []
    items_html = []
    for idx, it in enumerate(items, start=1):
        stt = it.get("stt") or idx
        sn = html.escape(str(it.get("serial_number") or ""))
        loi = html.escape(str(it.get("loi_ban_dau") or "")).replace("\n", "<br>")
        bp = html.escape(str(it.get("bo_phan") or "CNC")).replace("\n", "<br>")
        hm = html.escape(str(it.get("hang_muc_kiem_tra") or "")).replace("\n", "<br>")
        kq = html.escape(str(it.get("ket_qua") or "Đạt / 合格"))
        sheet_anh = html.escape(str(it.get("sheet_anh") or "Đã kiểm tra / 已檢驗"))

        items_html.append(f"""
        <tr>
          <td style="text-align: center; font-weight: 600; padding: 8px 6px; border: 1px solid #b0c4de;">{stt}</td>
          <td style="text-align: center; font-weight: 700; color: #1e293b; padding: 8px 6px; border: 1px solid #b0c4de; font-family: monospace; font-size: 0.9rem;">{sn}</td>
          <td style="text-align: left; padding: 8px 10px; border: 1px solid #b0c4de; line-height: 1.4;">{loi}</td>
          <td style="text-align: center; padding: 8px 6px; border: 1px solid #b0c4de; font-weight: 500;">{bp}</td>
          <td style="text-align: left; padding: 8px 10px; border: 1px solid #b0c4de; line-height: 1.4;">{hm}</td>
          <td style="text-align: center; font-weight: 600; color: #047857; padding: 8px 6px; border: 1px solid #b0c4de;">{kq}</td>
          <td style="text-align: center; color: #1f4e79; font-weight: 500; padding: 8px 6px; border: 1px solid #b0c4de; font-size: 0.85rem;">{sheet_anh}</td>
        </tr>
        """)

    table_rows = "".join(items_html) if items_html else """
      <tr>
        <td colspan="7" style="text-align: center; padding: 20px; color: #64748b; font-style: italic;">
          Chưa có thiết bị nào trong danh mục nghiệm thu.
        </td>
      </tr>
    """

    actual_note = data.get("ghi_chu") or data.get("ghi_chu_1") or ""
    notes_html = html.escape(str(actual_note).strip()).replace("\n", "<br>")

    preview_html = f"""
    <div class="contract-paper" style="font-family: 'Times New Roman', Times, serif; color: #000; line-height: 1.5; padding: 30px 40px; background: #fff; box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-radius: 4px; max-width: 900px; margin: 0 auto;">
      
      <!-- Main Title -->
      <div style="background-color: #1F4E79; color: #ffffff; text-align: center; padding: 10px 15px; border-radius: 4px 4px 0 0;">
        <h1 style="font-size: 15pt; font-weight: bold; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">
          {html.escape(data['tieu_de_viet'])}
        </h1>
        <h2 style="font-size: 13pt; font-weight: bold; margin: 4px 0 0 0;">
          {html.escape(data['tieu_de_trung'])}
        </h2>
      </div>

      <!-- Reference Bar -->
      <div style="display: flex; justify-content: space-between; background-color: #D6E4F0; color: #1F4E79; padding: 8px 15px; font-weight: bold; font-size: 11pt; border-bottom: 1px solid #b0c4de;">
        <div>Số HĐ / 合約編號: <span style="color: #0f172a;">{html.escape(data['so_hop_dong'])}</span></div>
        <div>Ngày / 日期: <span style="color: #0f172a;">{html.escape(data['ngay_nghiem_thu'])}</span> &nbsp;&nbsp;&nbsp;&nbsp; Số BB: <span style="color: #0f172a;">{html.escape(data['so_bien_ban'])}</span></div>
      </div>

      <!-- Parties Bar -->
      <div style="display: flex; justify-content: space-between; background-color: #F2F2F2; color: #000000; padding: 10px 15px; font-size: 11.5pt; border-bottom: 2px solid #2E75B6;">
        <div style="flex: 1; padding-right: 15px;">
          <strong>Bên A / 甲方:</strong> {html.escape(data['ben_a']['ten_cong_ty'])}
        </div>
        <div style="flex: 1; padding-left: 15px; border-left: 1px solid #cbd5e1;">
          <strong>Bên B / 乙方:</strong> {html.escape(data['ben_b']['ten_cong_ty'])}
        </div>
      </div>

      <!-- Equipment Table -->
      <div style="margin-top: 15px; overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; font-size: 10.5pt;">
          <thead>
            <tr style="background-color: #2E75B6; color: #ffffff; text-align: center;">
              <th style="width: 5%; padding: 8px 4px; border: 1px solid #1f4e79;">STT<br><span style="font-size: 9pt;">序號</span></th>
              <th style="width: 22%; padding: 8px 6px; border: 1px solid #1f4e79;">Serial Number<br><span style="font-size: 9pt;">產品序號</span></th>
              <th style="width: 23%; padding: 8px 8px; border: 1px solid #1f4e79;">Lỗi ban đầu<br><span style="font-size: 9pt;">故障說明</span></th>
              <th style="width: 10%; padding: 8px 4px; border: 1px solid #1f4e79;">Bộ phận<br><span style="font-size: 9pt;">部門</span></th>
              <th style="width: 23%; padding: 8px 8px; border: 1px solid #1f4e79;">Hạng mục kiểm tra<br><span style="font-size: 9pt;">檢查項目</span></th>
              <th style="width: 9%; padding: 8px 4px; border: 1px solid #1f4e79;">Kết quả<br><span style="font-size: 9pt;">結果</span></th>
              <th style="width: 8%; padding: 8px 4px; border: 1px solid #1f4e79;">Ghi chú<br><span style="font-size: 9pt;">備註</span></th>
            </tr>
          </thead>
          <tbody>
            {table_rows}
          </tbody>
        </table>
      </div>

      <!-- Notes Section -->
      <div style="margin-top: 20px; font-size: 11pt;">
        <div style="font-size: 12.5pt; font-weight: bold; color: #1F4E79; margin-bottom: 6px;">
          GHI CHÚ / 備註:
        </div>
        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 12px 16px; line-height: 1.6; min-height: 40px;">
          {notes_html if notes_html else '<span style="color: #94a3b8; font-style: italic;">(Không có ghi chú phát sinh / 無特別備註)</span>'}
        </div>
      </div>

      <!-- Signature Section -->
      <div style="margin-top: 35px; display: flex; justify-content: space-between; font-size: 11.5pt;">
        <div style="width: 45%; text-align: center;">
          <div style="font-weight: bold; color: #1F4E79; line-height: 1.3;">
            ĐẠI DIỆN BÊN A / 甲方代表<br>
            <span style="font-size: 10pt; font-weight: normal; color: #475569;">(Ký xác nhận / 簽字確認)</span>
          </div>
          <div style="height: 80px;"></div>
          <div style="font-weight: bold; color: #0f172a; border-top: 1px dashed #cbd5e1; padding-top: 6px;">
            {html.escape(data['ben_a']['ten_cong_ty'])}
          </div>
        </div>

        <div style="width: 45%; text-align: center;">
          <div style="font-weight: bold; color: #1F4E79; line-height: 1.3;">
            ĐẠI DIỆN BÊN B / 乙方代表<br>
            <span style="font-size: 10pt; font-weight: normal; color: #475569;">(Ký tên, đóng dấu / 簽字蓋章)</span>
          </div>
          <div style="height: 80px;"></div>
          <div style="font-weight: bold; color: #0f172a; border-top: 1px dashed #cbd5e1; padding-top: 6px;">
            {html.escape(data['ben_b']['ten_cong_ty'])}
          </div>
        </div>
      </div>

    </div>
    """
    return preview_html
