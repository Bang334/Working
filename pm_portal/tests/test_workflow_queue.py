"""Historical source state must not be counted as unfinished business."""
import pytest
from app.services.workflow_service import queue_state


def row(**values):
    return dict(current={'title':'Nhận và kiểm tra hàng'},kind='procurement',source_type='po',source_status='',source_date='',events=[],business_confirmations=[],owner='',followup_date='',**values)


def test_delivered_source_is_review_not_outstanding_delivery():
    d=row();d.update(source_status='DELIVERED',source_date='2026-10-07')
    result=queue_state(d)
    assert result['queue_group']=='review' and 'đã giao đủ' in result['queue_reason']
    assert 'không yêu cầu' in result['queue_reason']


@pytest.mark.parametrize('source',['po','contract','document','quotation'])
def test_unconfirmed_imports_need_review(source):
    d=row();d['source_type']=source
    assert queue_state(d)['queue_group']=='review'


def test_scheduled_work_is_active_but_delivered_import_remains_review():
    d=row();d['owner']='PM'
    assert queue_state(d)['queue_group']=='active'
    d['source_status']='DELIVERED'
    assert queue_state(d)['queue_group']=='review'


def test_payment_waits_for_actual_trigger():
    d=row();d.update(kind='payment',source_type='',milestone={'triggered':0})
    assert queue_state(d)['queue_group']=='waiting'
    d['milestone']['triggered']=1
    assert queue_state(d)['queue_group']=='active'


def test_completed_case_stays_closed_regardless_of_missing_history():
    d=row();d.update(current=None,source_status='DELIVERED')
    assert queue_state(d)['queue_group']=='closed'


def test_confirmed_work_can_be_managed_as_active():
    d=row();d.update(source_status='DELIVERED',business_confirmations=[{'action':'supplier_received'}])
    assert queue_state(d)['queue_group']=='active'
