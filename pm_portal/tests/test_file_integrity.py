import base64
from pathlib import Path

import pytest

from app import database
from app.services import file_manager_service as files


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(database, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(files, "WORKING_DIR", tmp_path)
    monkeypatch.setattr(files, "HO_SO_DIR", tmp_path / "Ho So Du An")
    monkeypatch.setattr(files, "BIEU_MAU_DIR", tmp_path / "Bieu Mau")
    monkeypatch.setattr(files, "OUTPUTS_DIR", tmp_path / "outputs")
    database.init_db()
    return tmp_path


def test_scan_preserves_explicit_links_and_never_guesses_generic_contract(workspace):
    folder = workspace / "Ho So Du An" / "Hop Dong"
    folder.mkdir(parents=True)
    generic = folder / "hop_dong_other.docx"
    generic.write_bytes(b"document")
    extra = workspace / "outside_index.docx"
    extra.write_bytes(b"linked")
    conn = database.get_db_connection()
    conn.execute("INSERT INTO contracts (contract_code, customer_name_vi) VALUES (?, ?)", ("HMV021020260001", "A"))
    conn.execute("INSERT INTO documents (contract_code, doc_type, doc_name, file_name, file_path) VALUES (?, ?, ?, ?, ?)", ("HMV021020260001", "OTHER", "Explicit", extra.name, str(extra)))
    database.scan_and_index_documents(conn)
    rows = conn.execute("SELECT contract_code, file_path FROM documents").fetchall()
    assert any(r["file_path"] == str(extra) and r["contract_code"] == "HMV021020260001" for r in rows)
    assert next(r for r in rows if r["file_path"] == str(generic))["contract_code"] is None
    database.scan_and_index_documents(conn)
    assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == 2
    conn.close()


def test_distinct_files_and_rename_stays_linked(workspace):
    a = files.HO_SO_DIR / "Hop Dong" / "same.pdf"
    b = files.HO_SO_DIR / "Bao Gia" / "same.pdf"
    for p in (a, b):
        p.parent.mkdir(parents=True)
        p.write_bytes(b"equal")
    database.index_single_document("C-1", "HOP_DONG", "Doc", a.name, str(a))
    assert len(files.list_all_files()["files"]) == 2
    result = files.rename_file(files.encode_file_id(a), "renamed.pdf")
    conn = database.get_db_connection()
    row = conn.execute("SELECT file_path, contract_code FROM documents").fetchone()
    assert row["file_path"] == str(a.with_name("renamed.pdf"))
    assert row["contract_code"] == "C-1"
    assert result["file"]["file_name"] == "renamed.pdf"
    conn.close()


def test_trash_and_upload_validation(workspace):
    with pytest.raises(ValueError):
        files.upload_file_to_category("hop_dong", "../escape.pdf", b"a")
    with pytest.raises(ValueError):
        files.upload_file_to_category("bieu_mau", "bad.pdf", b"a")
    saved = files.upload_file_to_category("hop_dong", "good.pdf", b"data")
    result = files.delete_file(saved["file"]["id"])
    assert Path(result["trash_path"]).read_bytes() == b"data"
    conn = database.get_db_connection()
    assert conn.execute("SELECT count(*) FROM documents").fetchone()[0] == 0
    conn.close()
    encoded = base64.urlsafe_b64encode(str(workspace / ".." / (workspace.name + "_other") / "file.pdf").encode()).decode()
    with pytest.raises(ValueError):
        files.decode_file_id(encoded)


def test_quotation_word_and_excel_share_name(workspace, monkeypatch):
    from app.services import quotation_word_service as word
    from app.services import quotation_excel_service as excel
    monkeypatch.setattr(word, "WORKING_DIR", workspace)
    monkeypatch.setattr(excel, "WORKING_DIR", workspace)
    data = {"customer_name_vi": "Cong ty CX", "quotation_no": "BG-001", "_file_timestamp": "20261028_120000_123456", "items": []}
    w = word.generate_quotation_word(data)
    x = excel.generate_quotation_excel(data)
    assert Path(w["file_name"]).stem == Path(x["file_name"]).stem
    assert Path(w["file_path"]).is_file() and Path(x["file_path"]).is_file()


def test_search_ignores_accents_and_uses_contract_and_template_labels(workspace):
    folder = files.HO_SO_DIR / "Nghiem Thu" / "Cong trinh"
    folder.mkdir(parents=True)
    doc = folder / "bien_ban_01.xlsx"
    doc.write_bytes(b"test")
    files.BIEU_MAU_DIR.mkdir()
    template = files.BIEU_MAU_DIR / "Mau_Goc_Hop_Dong_Mua_Ban.docx"
    template.write_bytes(b"template")
    conn = database.get_db_connection()
    cursor = conn.execute("INSERT INTO contracts (contract_code, customer_name_vi, project_name_vi) VALUES (?, ?, ?)", ("HMV-999", "Công ty CX", "Nhà máy Bắc Ninh"))
    contract_id = cursor.lastrowid
    conn.execute("INSERT INTO documents (contract_id, contract_code, doc_type, doc_name, file_name, file_path) VALUES (?, ?, ?, ?, ?, ?)", (contract_id, "HMV-999", "NGHIEM_THU", "Bien ban", doc.name, str(doc)))
    conn.commit()
    conn.close()
    assert [f["file_name"] for f in files.list_all_files(search="cx nghiem thu bac ninh")["files"]] == [doc.name]
    assert [f["file_name"] for f in files.list_all_files(search="mau hop dong")["files"]] == [template.name]
    assert [f["file_name"] for f in files.list_all_files(search="hmv-999")["files"]] == [doc.name]


def test_generated_filename_sanitizes_and_keeps_useful_information():
    from app.utils.file_helper import document_filename
    name = document_filename("Nghiem_Thu", "Công ty CX", "HM/123", "docx", "20261028_120000")
    assert name == "Nghiem_Thu_Công_ty_CX_HM_123_20261028_120000.docx"


def test_renamed_master_templates_are_available():
    from app import config
    from app.services import payment_request_excel_service as payment
    from app.services import payment_voucher_excel_service as voucher
    from app.services import installation_acceptance_word_service as installation
    from app.services.eco_prime import eco_prime_excel_service as eco
    for path in (config.TEMPLATE_DOCX, config.REPAIR_ACCEPTANCE_TEMPLATE,
                 payment.TEMPLATE_PATH, payment.WORD_TEMPLATE_PATH,
                 voucher.TEMPLATE_MASTER, voucher.FALLBACK_TEMPLATE,
                 installation.TEMPLATE_PATH, eco.ECO_PRIME_TEMPLATE_PATH):
        assert path.is_file(), str(path)


def test_installation_uses_renamed_template_in_temporary_directory(tmp_path, monkeypatch):
    from app.services import installation_acceptance_word_service as installation
    from app.controllers.acceptance_controller import get_installation_sample_data_controller
    monkeypatch.setattr(installation, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(installation, "DOSSIER_DIR", tmp_path / "documents")
    result = installation.generate_installation_acceptance_word(get_installation_sample_data_controller()["data"])
    assert Path(result["file_path"]).is_file()
    assert Path(result["file_path"]).parent == tmp_path / "documents"


def test_organized_files_and_signature_mapping():
    import ast
    from openpyxl import Workbook
    from app.config import WORKING_DIR
    from app.services import payment_voucher_excel_service as voucher
    script_dir = WORKING_DIR / "scripts" / "thiet_bi_dfv"
    expected = {
        "cap_nhat_anh_pin_dfv.py": ("EXCEL_PATH", "BAT_DIR"),
        "dien_phieu_sua_chua_dfv.py": ("SOURCE_PATH",),
    }
    for filename, names in expected.items():
        tree = ast.parse((script_dir / filename).read_text(encoding="utf-8"))
        constants = {node.targets[0].id: node.value.value for node in tree.body
                     if isinstance(node, ast.Assign) and len(node.targets) == 1
                     and isinstance(node.targets[0], ast.Name)
                     and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)}
        for name in names:
            assert Path(constants[name]).exists(), (filename, name)
    assert voucher.FALLBACK_TEMPLATE.is_file()
    ws = Workbook().active
    voucher._attach_signature(ws, "NGUYỄN SỸ KIM BẰNG")
    assert len(ws._images) == 1


def test_organized_categories_are_searchable(workspace):
    path = files.HO_SO_DIR / "Cong Ty" / "DFV_Darfon" / "Thiet Bi" / "Bang_ke.xlsx"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"test")
    results = files.list_all_files(category="thiet_bi", search="dfv bang ke")
    assert [item["file_name"] for item in results["files"]] == [path.name]


def test_company_upload_and_search(workspace):
    result = files.upload_file_to_category("thiet_bi", "Danhsach.xlsx", b"data", "DFV_Darfon")
    stored = workspace / "Ho So Du An" / "Cong Ty" / "DFV_Darfon" / "Thiet Bi" / "Danhsach.xlsx"
    assert stored.read_bytes() == b"data"
    assert result["file"]["category"] == "thiet_bi"
    assert [f["file_name"] for f in files.list_all_files(category="thiet_bi", search="dfv danhsach")["files"]] == [stored.name]
    with pytest.raises(ValueError):
        files.upload_file_to_category("hop_dong", "bad.docx", b"data", "../bad")


def test_company_contract_documents_are_indexed(workspace):
    folder = workspace / "Ho So Du An" / "Cong Ty" / "DFV_Darfon" / "Hop Dong"
    folder.mkdir(parents=True)
    doc = folder / "Hop_Dong_HMV-123.docx"
    doc.write_bytes(b"data")
    conn = database.get_db_connection()
    conn.execute("INSERT INTO contracts (contract_code, customer_name_vi) VALUES (?, ?)", ("HMV-123", "DFV Darfon"))
    database.scan_and_index_documents(conn)
    row = conn.execute("SELECT contract_code FROM documents WHERE file_path=?", (str(doc),)).fetchone()
    assert row["contract_code"] == "HMV-123"
    conn.close()


@pytest.mark.anyio
async def test_company_upload_endpoint(workspace):
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/files/upload", data={"category": "thiet_bi", "company": "DFV_Darfon"}, files={"file": ("bienban.pdf", b"data", "application/pdf")})
    assert response.status_code == 200
    assert (workspace / "Ho So Du An" / "Cong Ty" / "DFV_Darfon" / "Thiet Bi" / "bienban.pdf").is_file()
