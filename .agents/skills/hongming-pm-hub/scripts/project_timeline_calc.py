# -*- coding: utf-8 -*-
"""
Hong Ming Global - Project Milestone & Timeline Calculator
Script tính toán các mốc thời gian và hạn chót thanh toán cho PM.
"""

from datetime import datetime, timedelta
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def calculate_project_milestones(
    contract_sign_date_str,
    deposit_date_str,
    lead_time_days=80,
    trial_run_days=14,
    payment_terms_days=30,
    warranty_months=12
):
    date_format = "%d/%m/%Y"
    sign_date = datetime.strptime(contract_sign_date_str, date_format)
    deposit_date = datetime.strptime(deposit_date_str, date_format)
    
    delivery_deadline = deposit_date + timedelta(days=lead_time_days)
    trial_run_end = delivery_deadline + timedelta(days=trial_run_days)
    payment_due_date = trial_run_end + timedelta(days=payment_terms_days)
    
    # Calculate warranty (approx 365 days)
    warranty_end = trial_run_end + timedelta(days=int(warranty_months * 30.4375))
    
    today = datetime.now()
    days_to_delivery = (delivery_deadline - today).days
    days_to_payment = (payment_due_date - today).days
    
    print("\n" + "="*60)
    print(" HONG MING GLOBAL - PROJECT TIMELINE & MILESTONE REPORT ")
    print("="*60)
    print(f"1. Ngày ký hợp đồng (簽約日期): {sign_date.strftime(date_format)}")
    print(f"2. Ngày nhận tiền cọc (收到定金日期): {deposit_date.strftime(date_format)}")
    print(f"3. Hạn giao hàng & thi công ({lead_time_days} ngày kể từ cọc): {delivery_deadline.strftime(date_format)}")
    if days_to_delivery >= 0:
        print(f"   -> Còn {days_to_delivery} ngày nữa đến hạn bàn giao.")
    else:
        print(f"   -> [CẢNH BÁO] ĐÃ QUÁ HẠN GIAO HÀNG {abs(days_to_delivery)} NGÀY!")
        
    print(f"4. Dự kiến chạy thử xong & ký nghiệm thu ({trial_run_days} ngày trial): {trial_run_end.strftime(date_format)}")
    print(f"5. Hạn chót thanh toán đợt tiếp theo (T/T {payment_terms_days} ngày): {payment_due_date.strftime(date_format)}")
    if days_to_payment >= 0:
        print(f"   -> Còn {days_to_payment} ngày nữa đến hạn thanh toán.")
    else:
        print(f"   -> [CẢNH BÁO] CÔNG NỢ ĐÃ QUÁ HẠN {abs(days_to_payment)} NGÀY! Cần gửi thư nhắc nợ.")
        
    print(f"6. Hạn bảo hành hệ thống ({warranty_months} tháng kể từ nghiệm thu): {warranty_end.strftime(date_format)}")
    print("="*60 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        c_date = sys.argv[1]
        d_date = sys.argv[2]
        calculate_project_milestones(c_date, d_date)
    else:
        # Example calculation for Cheng Feng project
        print("Demo: Tính toán mốc cho dự án Cheng Feng:")
        calculate_project_milestones("02/10/2026", "05/10/2026", lead_time_days=80, payment_terms_days=30)
