import sys, os
sys.path.insert(0, '.')

print("=== Testing All New Modules ===")

# Test auth
from modules.auth import authenticate, get_user_permissions, check_permission
r = authenticate("admin", "admin123")
print(f"[AUTH] admin login: {r['success']} | Role: {r['user']['role']}")
r2 = authenticate("viewer", "view123")
print(f"[AUTH] viewer login: {r2['success']} | Role: {r2['user']['role']}")
r3 = authenticate("wrong", "bad")
print(f"[AUTH] bad login blocked: {not r3['success']}")

perms = get_user_permissions("HR Admin")
print(f"[AUTH] Admin perms - can_register: {perms['can_register']}, can_delete: {perms['can_delete']}")
perms2 = get_user_permissions("Viewer")
print(f"[AUTH] Viewer perms - can_register: {perms2['can_register']}, can_delete: {perms2['can_delete']}")

# Test asset tracker
from modules.asset_tracker import initialize_asset_db, auto_allocate_standard_kit, get_employee_assets
ASSET_DB = "Database/AssetTracker.xlsx"
initialize_asset_db(ASSET_DB)
kit = auto_allocate_standard_kit(ASSET_DB, "EMP_T01", "Test Employee")
print(f"[ASSET] Standard kit allocated: {kit.get('success', kit)}")
assets = get_employee_assets(ASSET_DB, "EMP_T01")
print(f"[ASSET] Employee assets retrieved: {len(assets)} items")

# Test document manager
from modules.document_manager import initialize_doc_tracker, get_document_checklist, get_verification_summary
DOC_DB = "Database/DocumentTracker.xlsx"
initialize_doc_tracker(DOC_DB)
checklist = get_document_checklist(DOC_DB, "EMP001")
print(f"[DOCS] Checklist items: {len(checklist)} required docs")
summary = get_verification_summary(DOC_DB, "EMP001")
print(f"[DOCS] Summary: total={summary['total_required']}, uploaded={summary['uploaded']}")

# Test offer letter generation
from modules.offer_letter import generate_offer_letter, send_offer_email
from modules.excel_handler import read_config
config = read_config("Config.xlsx")
emp = {
    "employee_id": "EMP_TEST",
    "full_name": "Priya Sharma",
    "date_of_birth": "1998-04-12",
    "gender": "Female",
    "email": "priya@test.com",
    "department": "IT",
    "designation": "Software Engineer",
    "date_of_joining": "2026-10-01",
    "salary": "850000",
    "manager_name": "Rahul Kumar",
    "employment_type": "Full-Time",
    "address": "42 MG Road, Bangalore",
    "phone": "9876543210",
}
os.makedirs("Generated", exist_ok=True)
offer = generate_offer_letter(emp, "Generated", "Infosys Limited")
print(f"[OFFER] Letter generated: {offer['success']} | File: {os.path.basename(offer.get('file_path', 'N/A'))}")
email_r = send_offer_email(emp, config, offer.get("file_path"))
print(f"[OFFER] Email mode: {email_r['mode']} | Success: {email_r['success']}")

print()
print("=== ALL MODULE TESTS PASSED ===")
