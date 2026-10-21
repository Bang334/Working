# -*- coding: utf-8 -*-
"""
Installation Acceptance HTML preview service.
Renders high-fidelity live web preview of Installation Acceptance & Handover Minutes (.docx)
matching the Hong Ming corporate style: Table 0, Table 1, Table 2, Table 3, Table 4.
"""

import html
from typing import Any, Dict

from app.services.installation_acceptance_word_service import prepare_installation_acceptance_data


def generate_installation_acceptance_preview_html(raw_data: Dict[str, Any]) -> str:
    """Generate professional live preview HTML for Installation Acceptance Minutes."""
    data = prepare_installation_acceptance_data(raw_data)

    so_hd = html.escape(str(data.get("so_hop_dong", "")))
    so_bb = html.escape(str(data.get("so_bien_ban", "")))
    ngay_ky = html.escape(str(data.get("ngay_ky_hop_dong", "")))
    ngay_nt = html.escape(str(data.get("ngay_nghiem_thu", "")))
    gia_tri_hd = html.escape(str(data.get("gia_tri_hop_dong", "")))

    ben_a = data.get("ben_a", {})
    ben_b = data.get("ben_b", {})
    ten_a_vn = html.escape(str(ben_a.get("ten_cong_ty", "")))
    ten_a_tw = html.escape(str(ben_a.get("ten_tieng_trung", "")))
    ten_b_vn = html.escape(str(ben_b.get("ten_cong_ty", "CÔNG TY TNHH TOÀN CẦU HONG MING")))
    ten_b_tw = html.escape(str(ben_b.get("ten_tieng_trung", "宏明環球有限公司")))

    he_thong = html.escape(str(data.get("ten_he_thong", "")))
    he_thong_tw = html.escape(str(data.get("ten_he_thong_trung", "")))

    can_cu_pl = html.escape(str(data.get("can_cu_phu_luc", "")))
    can_cu_pl_tw = html.escape(str(data.get("can_cu_phu_luc_trung", "")))
    can_cu_kt = html.escape(str(data.get("can_cu_ky_thuat", "")))
    can_cu_kt_tw = html.escape(str(data.get("can_cu_ky_thuat_trung", "")))

    # Table 2: Items
    items = data.get("hang_muc", [])
    items_rows = []
    for idx, it in enumerate(items, start=1):
        if isinstance(it, dict):
            sp = (it.get("ten_san_pham") or "").strip()
            hm_text = it.get("hang_muc") or it.get("noi_dung") or sp or ""
        else:
            sp = ""
            hm_text = str(it)

        # Ensure index prefix
        import re
        if not re.match(r'^\d+\.', hm_text.strip()):
            hm_text = f"{idx}. {hm_text.strip()}"

        escaped_hm = html.escape(hm_text).replace("\n", "<br>")
        if sp and sp not in hm_text:
            col0_html = f"<strong>{html.escape(sp)}</strong><br>{escaped_hm}"
        else:
            col0_html = escaped_hm

        items_rows.append(f"""
        <tr>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; text-align: left; vertical-align: top; font-size: 0.82rem; line-height: 1.4;">
            {col0_html}
          </td>
          <td style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: center; vertical-align: middle; font-size: 0.72rem; font-weight: 700; color: #1E7B34; line-height: 1.35; background: #f8fafc;">
            Xác nhận thiết bị đã được đưa vào sử dụng.<br><span style="font-size: 0.68rem; font-weight: 700; color: #1E7B34;">確認已投入使用</span>
          </td>
          <td style="padding: 6px 8px; border: 1px solid #cbd5e1; text-align: center; vertical-align: middle; font-size: 0.72rem; font-weight: 700; color: #1E7B34; line-height: 1.35; background: #f8fafc;">
            Đã nghiệm thu, xác nhận đạt yêu cầu.<br><span style="font-size: 0.68rem; font-weight: 700; color: #1E7B34;">驗收合格，確認符合需求</span>
          </td>
        </tr>
        """)

    table2_html = "".join(items_rows) if items_rows else "<tr><td colspan='3' style='text-align: center; padding: 20px; color: #94a3b8;'>Chưa có hạng mục nghiệm thu lắp đặt nào.</td></tr>"

    # Table 3: Payment stages (selected stages + gold total row)
    selected_stages = data.get("selected_stages", [])
    stages_rows = []
    zh_nums_map = {1: "第一期", 2: "第二期", 3: "第三期", 4: "第四期", 5: "第五期"}

    for stg in selected_stages:
        stage_name = html.escape(str(stg.get("stage", ""))).replace("\n", "<br>")
        cond = html.escape(str(stg.get("condition", ""))).replace("\n", "<br>")
        rate = html.escape(str(stg.get("rate", "")))
        amt = html.escape(str(stg.get("amount", "")))

        stages_rows.append(f"""
        <tr style="background: #ffffff; color: #0f172a;">
          <td style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center; vertical-align: middle; font-size: 0.85rem; font-weight: 600;">{stage_name}</td>
          <td style="padding: 8px 12px; border: 1px solid #cbd5e1; text-align: left; vertical-align: middle; font-size: 0.85rem;">{cond}</td>
          <td style="padding: 8px 10px; border: 1px solid #cbd5e1; text-align: center; vertical-align: middle; font-size: 0.85rem;">{rate}</td>
          <td style="padding: 8px 12px; border: 1px solid #cbd5e1; text-align: right; vertical-align: middle; font-size: 0.88rem; font-weight: 600;">{amt}</td>
        </tr>
        """)

    # Gold Total Row
    total_rate = html.escape(str(data.get("total_rate_str", "20%")))
    total_amt = html.escape(str(data.get("total_amount_str", "46.800.000 VND")))
    stages_rows.append(f"""
    <tr style="background-color: #FFC000; font-weight: 800; color: #000000;">
      <td style="padding: 8px 10px; border: 1px solid #b45309; text-align: center; vertical-align: middle; font-size: 0.88rem;">TỔNG CỘNG<br><span style="font-size: 0.75rem;">合計</span></td>
      <td style="padding: 8px 12px; border: 1px solid #b45309; text-align: left; vertical-align: middle;"></td>
      <td style="padding: 8px 10px; border: 1px solid #b45309; text-align: center; vertical-align: middle; font-size: 0.88rem;">{total_rate}</td>
      <td style="padding: 8px 12px; border: 1px solid #b45309; text-align: right; vertical-align: middle; font-size: 0.92rem; font-weight: 800;">{total_amt}</td>
    </tr>
    """)

    table3_html = "".join(stages_rows)

    # Words paragraphs
    words_paragraphs = []
    for stg in selected_stages:
        s_num = stg.get("stage_num", 1)
        st_zh = zh_nums_map.get(s_num, f"第{s_num}期")
        w_vn = html.escape(str(stg.get("words_vn", "")))
        w_tw = html.escape(str(stg.get("words_tw", "")))
        words_paragraphs.append(f'<p style="margin: 0 0 3px 0;"><strong>Giai đoạn {s_num} / {st_zh}:</strong> {w_vn} {w_tw}。</p>')

    tot_vn = html.escape(str(data.get("total_words_vn", "")))
    tot_tw = html.escape(str(data.get("total_words_tw", "")))
    words_paragraphs.append(f'<p style="margin: 0 0 3px 0;"><strong>Tổng cộng / 合計:</strong> {tot_vn} {tot_tw}。</p>')
    words_paragraphs_html = "".join(words_paragraphs)

    section_v_title = html.escape(str(data.get("section_v_title", "V. ĐỀ NGHỊ THANH TOÁN / 款項付款申請")))
    conclusion_vn = html.escape(str(data.get("conclusion_vn", "")))
    conclusion_tw = html.escape(str(data.get("conclusion_tw", "")))

    preview_html = f"""
    <div class="installation-preview-paper" style="font-family: 'Times New Roman', '微軟正黑體', Times, serif; color: #1e293b; line-height: 1.5; padding: 32px 36px; background: #ffffff; box-shadow: 0 4px 20px rgba(0,0,0,0.12); border-radius: 6px; max-width: 900px; margin: 0 auto; border: 1px solid #e2e8f0;">
      
      <!-- Document Header & Title -->
      <div style="text-align: center; margin-bottom: 1.25rem;">
        <h1 style="font-size: 1.25rem; font-weight: 800; color: #1F4E79; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">
          BIÊN BẢN TIẾN ĐỘ LẮP ĐẶT VÀ NGHIỆM THU LẮP ĐẶT
        </h1>
        <div style="font-size: 1.05rem; font-weight: 750; color: #1F4E79; margin-top: 4px;">
          安裝進度及安裝驗收確認書
        </div>
        <div style="font-size: 0.85rem; font-style: italic; color: #64748b;">
          Installation Acceptance Confirmation
        </div>
      </div>

      <!-- Table 0: Metadata Bar -->
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 1rem; border: 1px solid #cbd5e1; background: #f8fafc;">
        <tr>
          <td style="padding: 6px 12px; font-size: 0.82rem; font-weight: 600; color: #334155; border-right: 1px solid #cbd5e1; width: 50%;">
            Số biên bản / 文件編號: <strong style="color: #0f172a;">{so_bb}</strong>
          </td>
          <td style="padding: 6px 12px; font-size: 0.82rem; font-weight: 600; color: #334155; width: 50%;">
            Liên quan HĐ / 合約編號: <strong style="color: #1e40af;">{so_hd}</strong>
          </td>
        </tr>
      </table>

      <!-- Section I: THÔNG TIN HỢP ĐỒNG -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        I. THÔNG TIN HỢP ĐỒNG / 合約資訊
      </div>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 1.25rem; border: 1px solid #cbd5e1; font-size: 0.83rem;">
        <tr>
          <td style="width: 32%; padding: 7px 10px; background: #f8fafc; font-weight: 700; border: 1px solid #cbd5e1;">Bên A (Bên Mua) / 買方<br><span style="font-weight: 500; color: #64748b;">{ten_a_tw}</span></td>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; font-weight: 700; color: #0f172a;">{ten_a_vn}</td>
        </tr>
        <tr>
          <td style="padding: 7px 10px; background: #f8fafc; font-weight: 700; border: 1px solid #cbd5e1;">Bên B (Bên Bán) / 賣方<br><span style="font-weight: 500; color: #64748b;">{ten_b_tw}</span></td>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; font-weight: 700; color: #0f172a;">{ten_b_vn}</td>
        </tr>
        <tr>
          <td style="padding: 7px 10px; background: #f8fafc; font-weight: 700; border: 1px solid #cbd5e1;">Hệ thống / 系統<br><span style="font-weight: 500; color: #64748b;">{he_thong_tw}</span></td>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; font-weight: 600;">{he_thong}</td>
        </tr>
        <tr>
          <td style="padding: 7px 10px; background: #f8fafc; font-weight: 700; border: 1px solid #cbd5e1;">Ngày ký HĐ / 合約日期</td>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; font-weight: 600;">{ngay_ky}</td>
        </tr>
        <tr>
          <td style="padding: 7px 10px; background: #f8fafc; font-weight: 700; border: 1px solid #cbd5e1;">Giá trị HĐ / 合約金額</td>
          <td style="padding: 7px 10px; border: 1px solid #cbd5e1; font-weight: 800; color: #1e3a8a;">{gia_tri_hd}</td>
        </tr>
      </table>

      <!-- Section II: CĂN CỨ & NGUYÊN TẮC NGHIỆM THU -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        II. CĂN CỨ & NGUYÊN TẮC NGHIỆM THU / 驗收依據與原則
      </div>
      <div style="font-size: 0.83rem; line-height: 1.5; color: #334155; margin-bottom: 1.25rem;">
        <p style="margin: 0 0 4px 0;">1. Căn cứ Hợp đồng mua bán số {so_hd} ký ngày {ngay_ky} giữa {ten_a_vn} và {ten_b_vn}; {can_cu_pl}; và {can_cu_kt}</p>
        <p style="margin: 0 0 6px 0; color: #64748b; font-size: 0.8rem;">1. 依據 {ten_a_vn} 與 {ten_b_vn} 於 {ngay_ky} 簽訂之第 {so_hd} 號買賣合約書及{can_cu_pl_tw}；並{can_cu_kt_tw}</p>
        <p style="margin: 0 0 4px 0;">2. Bên Bán phối hợp với Bên Mua thực hiện lắp đặt, điều chỉnh, kiểm tra và nghiệm thu; tiêu chuẩn nghiệm thu thực hiện theo thông số kỹ thuật trong tài liệu phân tích hệ thống do hai bên xác nhận.</p>
        <p style="margin: 0; color: #64748b; font-size: 0.8rem;">2. 乙方配合甲方進行安裝、調整、測試及驗收；驗收標準依雙方確認之系統分析文件與技術規格執行。</p>
      </div>

      <!-- Section III: HẠNG MỤC LẮP ĐẶT & NGHIỆM THU -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        III. HẠNG MỤC LẮP ĐẶT & NGHIỆM THU / 安裝與驗收項目
      </div>
      <p style="font-size: 0.82rem; margin: 0 0 8px 0; color: #475569;">
        Hai bên tiến hành đối chiếu các hạng mục theo hợp đồng/phụ lục và xác nhận kết quả như sau: 雙方依合約／附件逐項核對並確認如下：
      </p>
      <div style="overflow-x: auto; margin-bottom: 1.25rem;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.83rem; border: 1px solid #cbd5e1;">
          <thead>
            <tr style="background-color: #1F4E79; color: #ffffff; text-align: center;">
              <th style="padding: 8px 10px; border: 1px solid #1e3a8a; text-align: left;">Hạng mục / 項目</th>
              <th style="width: 125px; padding: 8px 6px; border: 1px solid #1e3a8a;">XÁC NHẬN LẮP ĐẶT<br><span style="font-size: 0.72rem; font-weight: normal;">安裝確認</span></th>
              <th style="width: 145px; padding: 8px 6px; border: 1px solid #1e3a8a;">XÁC NHẬN NGHIỆM THU<br><span style="font-size: 0.72rem; font-weight: normal;">驗收確認</span></th>
            </tr>
          </thead>
          <tbody>
            {table2_html}
          </tbody>
        </table>
      </div>

      <!-- Section IV: KẾT QUẢ NGHIỆM THU -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        IV. KẾT QUẢ NGHIỆM THU / 驗收結果
      </div>
      <div style="font-size: 0.83rem; line-height: 1.5; color: #334155; margin-bottom: 1.25rem; background: #f0fdf4; border-left: 3px solid #16a34a; padding: 8px 12px; border-radius: 0 4px 4px 0;">
        <p style="margin: 0 0 3px 0;">Qua kiểm tra và đối chiếu, hai bên xác nhận các hạng mục nêu tại Mục III đã được Bên B hoàn thành lắp đặt, triển khai, điều chỉnh và kiểm tra. <strong style="color: #166534;">Kết quả nghiệm thu: ĐẠT YÊU CẦU.</strong></p>
        <p style="margin: 0; color: #15803d; font-size: 0.8rem;">經檢查與逐項核對，雙方確認乙方已完成第三項所列內容之安裝、部署、調整及測試。<strong style="color: #166534;">驗收結果：合格。</strong></p>
      </div>

      <!-- Section V: ĐỀ NGHỊ THANH TOÁN -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        {section_v_title}
      </div>
      <div style="font-size: 0.83rem; line-height: 1.5; color: #334155; margin-bottom: 8px;">
        <p style="margin: 0 0 3px 0;">Căn cứ điều khoản thanh toán của Hợp đồng {so_hd} và kết quả nghiệm thu nêu trên, Bên B đề nghị Bên A thanh toán các khoản sau:</p>
        <p style="margin: 0 0 8px 0; color: #64748b; font-size: 0.8rem;">依據 {so_hd} 合約付款條款及上述驗收結果，乙方請求甲方支付下列款項：</p>
      </div>
      <div style="overflow-x: auto; margin-bottom: 10px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 0.83rem; border: 1px solid #cbd5e1;">
          <thead>
            <tr style="background-color: #1F4E79; color: #ffffff; text-align: center;">
              <th style="width: 25%; padding: 7px 8px; border: 1px solid #1e3a8a;">Giai đoạn / 期別</th>
              <th style="padding: 7px 10px; border: 1px solid #1e3a8a;">Điều kiện thanh toán / 付款條件</th>
              <th style="width: 12%; padding: 7px 8px; border: 1px solid #1e3a8a;">Tỷ lệ / 比例</th>
              <th style="width: 25%; padding: 7px 10px; border: 1px solid #1e3a8a;">Số tiền / 金額</th>
            </tr>
          </thead>
          <tbody>
            {table3_html}
          </tbody>
        </table>
      </div>
      <div style="font-size: 0.83rem; line-height: 1.5; color: #334155; margin-bottom: 1.25rem;">
        {words_paragraphs_html}
        <p style="margin: 0; color: #64748b; font-size: 0.8rem;">Thuế VAT / 增值稅: Theo quy định tại thời điểm xuất hóa đơn / 依發票開立時之規定另計。</p>
      </div>

      <!-- Section VI: KẾT LUẬN & XÁC NHẬN -->
      <div style="font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 6px;">
        VI. KẾT LUẬN & XÁC NHẬN / 結論與確認
      </div>
      <div style="font-size: 0.83rem; line-height: 1.5; color: #334155; margin-bottom: 1.25rem;">
        <p style="margin: 0 0 3px 0;">{conclusion_vn}</p>
        <p style="margin: 0; color: #64748b; font-size: 0.8rem;">{conclusion_tw}</p>
      </div>

      <!-- Section VII: CHỮ KÝ XÁC NHẬN -->
      <div style="text-align: center; font-weight: 800; color: #1F4E79; font-size: 0.95rem; margin-bottom: 8px;">
        CHỮ KÝ XÁC NHẬN / 簽署確認
      </div>
      <table style="width: 100%; border-collapse: collapse; margin-bottom: 1rem; border: 1px solid #cbd5e1; background: #f8fafc;">
        <tr>
          <td style="width: 50%; padding: 14px 16px; text-align: center; vertical-align: top; border-right: 1px solid #cbd5e1;">
            <div style="font-weight: 750; color: #1F4E79; font-size: 0.95rem;">BÊN A (BÊN MUA) / 買方</div>
            <div style="font-weight: 700; font-size: 0.88rem; color: #000000; margin-top: 3px;">{ten_a_vn}</div>
            <div style="font-size: 0.82rem; color: #000000; margin-top: 4px;">Ký tên & Đóng dấu / 簽名蓋章</div>
            <div style="height: 65px;"></div>
            <div style="width: 65%; margin: 0 auto; border-top: 1px solid #000000; padding-top: 4px; font-size: 0.82rem; color: #000000;">
              Ngày / 日期: _____ / _____ / 2026
            </div>
          </td>
          <td style="width: 50%; padding: 14px 16px; text-align: center; vertical-align: top;">
            <div style="font-weight: 750; color: #1F4E79; font-size: 0.95rem;">BÊN B (BÊN BÁN) / 賣方</div>
            <div style="font-weight: 700; font-size: 0.88rem; color: #000000; margin-top: 3px;">{ten_b_vn}</div>
            <div style="font-size: 0.82rem; color: #666666; margin-top: 1px;">{ten_b_tw}</div>
            <div style="font-size: 0.82rem; color: #000000; margin-top: 4px;">Ký tên & Đóng dấu / 簽名蓋章</div>
            <div style="height: 65px;"></div>
            <div style="width: 65%; margin: 0 auto; border-top: 1px solid #000000; padding-top: 4px; font-size: 0.82rem; color: #000000;">
              Ngày / 日期: _____ / _____ / 2026
            </div>
          </td>
        </tr>
      </table>

      <!-- Note footer -->
      <div style="font-size: 0.75rem; color: #808080; line-height: 1.4; padding-top: 4px;">
        Biên bản này là một phần không tách rời của Hợp đồng {so_hd} / 本確認書為 {so_hd} 合約不可分割之一部分，<br>
        <span style="color: #000000; font-weight: 700;">Bên dưới là hình ảnh trong {he_thong}.下面是 {he_thong_tw} 中的畫面。</span>
      </div>

    </div>
    """
    return preview_html
