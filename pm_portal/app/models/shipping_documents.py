"""Reviewed shipping data shared by AI extraction, UI and both Excel exports."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def vietnam_today():
    return datetime.now(timezone(timedelta(hours=7))).date()


class ShippingItem(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    name_vi: str = Field(default='', max_length=500)
    name_zh: str = Field(default='', max_length=500)
    description: str = Field(default='', max_length=3000)
    model: str = Field(default='', max_length=200)
    group: str = Field(default='', max_length=300)
    origin: str = Field(default='', max_length=150)
    quantity: Decimal | None = Field(default=None, gt=0, le=1000000000)
    unit: str = Field(default='', max_length=100)
    unit_price: Decimal | None = Field(default=None, ge=0, le=1000000000000000)
    unit_weight_kg: Decimal | None = Field(default=None, ge=0, le=1000000000)
    total_weight_kg: Decimal | None = Field(default=None, ge=0, le=1000000000)
    kind: Literal['goods', 'service'] = 'goods'
    include_in_packing: bool = True
    source: str = Field(default='', max_length=1500)

    @field_validator('quantity', 'unit_price', 'unit_weight_kg', 'total_weight_kg', mode='before')
    @classmethod
    def blank_number(cls, value):
        return None if value == '' else value

    @model_validator(mode='after')
    def exclude_services(self):
        if self.kind == 'service':
            self.include_in_packing = False
        return self


class ShippingDocument(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    issue_date: date = Field(default_factory=vietnam_today)
    invoice_no: str = Field(default='', max_length=120)
    packing_no: str = Field(default='', max_length=120)
    contract_no: str = Field(default='', max_length=120)
    seller_name: str = Field(default='CÔNG TY TNHH TOÀN CẦU HONG MING', max_length=500)
    seller_address: str = Field(default='Lầu 2, số 68 Nguyễn Huệ, Phường Sài Gòn, Thành phố Hồ Chí Minh, Việt Nam', max_length=1000)
    seller_phone: str = Field(default='+84966687109', max_length=120)
    seller_email: str = Field(default='sales@hongming-global.com', max_length=150)
    seller_representative: str = Field(default='TANG, WEI-LI (General Director)', max_length=200)
    buyer_name: str = Field(default='', max_length=500)
    buyer_address: str = Field(default='', max_length=1000)
    buyer_phone: str = Field(default='', max_length=120)
    buyer_email: str = Field(default='', max_length=150)
    payment_term: str = Field(default='', max_length=1000)
    shipment_term: str = Field(default='', max_length=500)
    incoterm: str = Field(default='', max_length=120)
    departure: str = Field(default='', max_length=200)
    destination: str = Field(default='', max_length=200)
    on_board_date: str = Field(default='', max_length=100)
    package_count: str = Field(default='', max_length=100)
    lc_no: str = Field(default='', max_length=100)
    currency: str = Field(default='VND', pattern=r'^[A-Z]{3}$')
    reported_total: Decimal | None = Field(default=None, ge=0, le=1000000000000000000)
    notes: str = Field(default='', max_length=5000)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    items: list[ShippingItem] = Field(default_factory=list, max_length=300)

    @field_validator('notes', mode='before')
    @classmethod
    def notes_as_text(cls, value):
        if isinstance(value,list) and all(isinstance(x,str) for x in value):
            return '\n'.join(value)
        return value or ''

    @field_validator('issue_date', mode='before')
    @classmethod
    def default_date(cls, value):
        return value or vietnam_today()


def review_document(data: ShippingDocument) -> dict:
    """Observe missing facts; never infer weight, legal identity or money."""
    warnings = list(data.warnings)
    if not data.buyer_name:
        warnings.append('Chưa có tên người mua.')
    if not data.invoice_no:
        warnings.append('Chưa có số Invoice.')
    if not data.packing_no:
        warnings.append('Chưa có số Packing List.')
    complete = bool(data.items) and all(i.quantity is not None and i.unit_price is not None for i in data.items)
    total = sum((i.quantity * i.unit_price for i in data.items), Decimal(0)) if complete else None
    if total is not None and data.reported_total is not None and abs(total-data.reported_total) > Decimal('0.01'):
        warnings.append(f'Tổng chi tiết {total:,.2f} {data.currency} khác tổng tài liệu {data.reported_total:,.2f} {data.currency}; cần đối chiếu.')
    for n, item in enumerate(data.items, 1):
        missing = [label for key, label in [('quantity','số lượng'), ('unit_price','đơn giá')] if getattr(item,key) is None]
        if missing:
            warnings.append(f'Dòng {n}: thiếu {", ".join(missing)}.')
        if item.quantity is not None and item.unit_weight_kg is not None and item.total_weight_kg is not None and abs(item.quantity*item.unit_weight_kg-item.total_weight_kg)>Decimal('0.001'):
            warnings.append(f'Dòng {n}: kg/đơn vị × số lượng khác tổng kg đã nhập; Packing List sẽ tính theo kg/đơn vị.')
    packed = [i for i in data.items if i.include_in_packing and i.kind=='goods']
    if any(i.unit_weight_kg is None and i.total_weight_kg is None for i in packed):
        warnings.append('Cân nặng chưa đủ; ô chưa có số liệu và tổng trọng lượng sẽ để trống.')
    return dict(warnings=list(dict.fromkeys(warnings)), total=float(total) if total is not None else None,
                invoice_count=len(data.items), packing_count=len(packed))
