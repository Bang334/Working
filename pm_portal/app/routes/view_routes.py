"""View routes serving web UI pages."""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import CANDIDATE_MODELS, DEFAULT_MODEL

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["UI Views"])


@router.get("/", response_class=HTMLResponse)
async def index_view(request: Request):
    """Trang chủ hiển thị tổng quan danh mục dự án & dữ liệu vận hành."""
    return templates.TemplateResponse(
        "tracker_page.html",
        {
            "request": request,
            "active_tab": "dashboard",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Trang Chủ · Tổng Quan Dự Án Hong Ming"
        }
    )


@router.get("/contracts", response_class=HTMLResponse)
async def contracts_page(request: Request):
    """Main contract generator view."""
    from app.services.contract_service import get_all_contracts_list
    try:
        contracts = get_all_contracts_list()
        contract_count = len(contracts)
    except Exception:
        contract_count = 0

    return templates.TemplateResponse(
        "contract_page.html",
        {
            "request": request,
            "active_tab": "contracts",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Tạo Hợp Đồng Mua Bán Song Ngữ",
            "contract_count": contract_count
        }
    )


@router.get("/repair-contracts", response_class=HTMLResponse)
@router.get("/repair-contract", response_class=HTMLResponse)
async def repair_contracts_page(request: Request):
    """Main repair contract generator view."""
    from app.services.repair_contract_service import get_all_repair_contracts_list
    try:
        contracts = get_all_repair_contracts_list()
        contract_count = len(contracts)
    except Exception:
        contract_count = 0

    return templates.TemplateResponse(
        "repair_contract_page.html",
        {
            "request": request,
            "active_tab": "repair_contracts",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Tạo Hợp Đồng Sửa Chữa & Bảo Trì Song Ngữ",
            "contract_count": contract_count
        }
    )


@router.get("/quotation", response_class=HTMLResponse)
@router.get("/quotations", response_class=HTMLResponse)
async def quotations_page(request: Request):
    """Quotation generator view."""
    return templates.TemplateResponse(
        "quotation_page.html",
        {
            "request": request,
            "active_tab": "quotations",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Bảng Báo Giá Thiết Bị Song Ngữ (Quotation)"
        }
    )


@router.get("/eco-prime", response_class=HTMLResponse)
@router.get("/eco-prime-quotation", response_class=HTMLResponse)
@router.get("/eco-prime-quotations", response_class=HTMLResponse)
async def eco_prime_quotation_page(request: Request):
    """ECO PRIME AI Schematic & Quotation Generator Page."""
    return templates.TemplateResponse(
        "eco_prime_quotation_page.html",
        {
            "request": request,
            "active_tab": "eco_prime_quotations",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Báo Giá ECO PRIME · AI Phân Tích Sơ Đồ Nguyên Lý"
        }
    )



@router.get("/delivery", response_class=HTMLResponse)
async def delivery_page(request: Request):
    """Stock-out and equipment handover minutes view."""
    return templates.TemplateResponse(
        "delivery_page.html",
        {
            "request": request,
            "active_tab": "delivery",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Phiếu Xuất Kho Kiêm Bàn Giao Thiết Bị"
        }
    )


@router.get("/purchase-orders", response_class=HTMLResponse)
async def purchase_orders_page(request: Request):
    """Purchase order (PO) generator view."""
    return templates.TemplateResponse(
        "po_page.html",
        {
            "request": request,
            "active_tab": "po",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Đơn Đặt Mua Hàng Nhà Cung Cấp (PO)"
        }
    )


@router.get("/liquidation", response_class=HTMLResponse)
async def liquidation_page(request: Request):
    """Contract liquidation view."""
    return templates.TemplateResponse(
        "liquidation_page.html",
        {
            "request": request,
            "active_tab": "liquidation",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Biên Bản Thanh Lý Hợp Đồng"
        }
    )


@router.get("/tracker", response_class=HTMLResponse)
async def tracker_page(request: Request):
    """Project lifecycle tracker & dashboard view."""
    return templates.TemplateResponse(
        "tracker_page.html",
        {
            "request": request,
            "active_tab": "dashboard",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Trang Chủ · Tổng Quan Dự Án Hong Ming"
        }
    )


from app.services.font_service import get_active_font_setting, get_all_fonts


@router.get("/fonts", response_class=HTMLResponse)
async def fonts_showcase_page(request: Request):
    """Typography and 100 fonts showcase view with instant one-click switcher."""
    active_font = get_active_font_setting()
    fonts = get_all_fonts()
    return templates.TemplateResponse(
        "font_showcase.html",
        {
            "request": request,
            "active_tab": "fonts",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "active_font": active_font,
            "fonts": fonts,
            "page_title": "Kho 100 Kiểu Chữ & Đổi Font Toàn Web"
        }
    )


@router.get("/acceptance", response_class=HTMLResponse)
async def acceptance_page(request: Request):
    """Acceptance minutes & equipment inspection generator view."""
    return templates.TemplateResponse(
        "acceptance_page.html",
        {
            "request": request,
            "active_tab": "acceptance",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Tạo Biên Bản Nghiệm Thu Thiết Bị"
        },
    )


@router.get("/reminders", response_class=HTMLResponse)
async def reminders_page(request: Request):
    """Payment requests, customer AR reminders & Gmail/Drive integration view."""
    return templates.TemplateResponse(
        "reminder_page.html",
        {
            "request": request,
            "active_tab": "reminders",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Đề Nghị Thanh Toán & Nhắc Nợ Khách Hàng"
        }
    )


@router.get("/payment-reminders", response_class=HTMLResponse)
async def payment_reminders_alias():
    """Alias for /reminders."""
    return RedirectResponse(url="/reminders", status_code=302)


@router.get("/payment-requests", response_class=HTMLResponse)
@router.get("/payment-request", response_class=HTMLResponse)
@router.get("/don-xin-thanh-toan", response_class=HTMLResponse)
async def payment_requests_page(request: Request):
    """Trang lập Đơn Xin Thanh Toán (浤詺付款申请单) và quản lý tài khoản thụ hưởng."""
    from app.services.beneficiary_service import list_beneficiaries
    from app.services.payment_voucher_excel_service import list_voucher_history

    try:
        beneficiaries = list_beneficiaries(limit=100)
    except Exception:
        beneficiaries = []

    try:
        history = list_voucher_history(limit=20)
    except Exception:
        history = []

    return templates.TemplateResponse(
        "payment_request_page.html",
        {
            "request": request,
            "active_tab": "payment_requests",
            "models": CANDIDATE_MODELS,
            "default_model": DEFAULT_MODEL,
            "page_title": "Đơn Xin Thanh Toán · 浤詺付款申请单",
            "beneficiaries": beneficiaries,
            "history": history
        }
    )

