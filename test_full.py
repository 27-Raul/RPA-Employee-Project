"""
test_full.py
============
Comprehensive End-to-End Test Suite for Infosys HR Onboarding System.
Tests Authentication, RBAC, Onboarding RPA Pipeline, Offer Letter Generation,
Email Dispatch, Hardware Asset Provisioning, Document Matrix, Reports, and Audit Trail.

Run with:
    python -X utf8 test_full.py
"""

import sys
import os
import json
import urllib.request
import urllib.error
import time
import http.cookiejar

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, '.')

BASE_URL = "http://localhost:5000/api"

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def post_json(path, body=None):
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        resp = opener.open(req)
        return json.loads(resp.read().decode("utf-8")), resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": str(e)}, e.code


def get_json(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    try:
        resp = opener.open(req)
        return json.loads(resp.read().decode("utf-8")), resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": str(e)}, e.code


def delete_json(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="DELETE")
    try:
        resp = opener.open(req)
        return json.loads(resp.read().decode("utf-8")), resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:
            return {"error": str(e)}, e.code


test_results = []


def assert_test(name, condition, extra=""):
    status = "PASS" if condition else "FAIL"
    test_results.append((name, status, extra))
    msg = f"  [{status}] {name}"
    if extra:
        msg += f" — {extra}"
    print(msg)
    return condition


def run_all_tests():
    print("\n" + "=" * 65)
    print("  INFOSYS HR ONBOARDING SYSTEM — E2E TEST SUITE")
    print("=" * 65)

    # -------------------------------------------------------------
    # 1. AUTHENTICATION & SESSION
    # -------------------------------------------------------------
    print("\n[1] Authentication & Access Control (RBAC)")

    res, code = post_json("/login", {"username": "admin", "password": "wrongpassword"})
    assert_test("Reject invalid credentials", code == 401 and not res.get("success"))

    res, code = post_json("/login", {"username": "admin", "password": "admin123"})
    assert_test("Admin login successful", code == 200 and res.get("success"), f"Role: {res.get('user', {}).get('role')}")

    me, code = get_json("/me")
    assert_test("Session persistence (/me)", code == 200 and me.get("logged_in"), f"User: {me.get('username')}")

    # -------------------------------------------------------------
    # 2. DASHBOARD METRICS
    # -------------------------------------------------------------
    print("\n[2] Dashboard Executive Metrics")
    stats, code = get_json("/dashboard-stats")
    assert_test("Dashboard statistics returned", code == 200 and "total" in stats, f"Total records: {stats.get('total')}")
    assert_test("Monthly trend analytics", "monthly_trend" in stats and isinstance(stats["monthly_trend"], dict))
    assert_test("Department distribution", "departments" in stats and isinstance(stats["departments"], dict))

    # -------------------------------------------------------------
    # 3. RPA ONBOARDING PIPELINE & OFFER DISPATCH
    # -------------------------------------------------------------
    print("\n[3] Robotic Process Automation: Onboarding & Offer Generation")
    unique_suffix = int(time.time())
    candidate_name = "Ananya Rao"
    candidate_email = f"ananya.rao.{unique_suffix}@example.com"

    candidate_payload = {
        "full_name": candidate_name,
        "date_of_birth": "1997-08-20",
        "gender": "Female",
        "email": candidate_email,
        "phone": "9876501234",
        "address": "Infosys Electronic City Campus, Hosur Road, Bangalore",
        "department": "IT",
        "designation": "Senior Systems Engineer",
        "date_of_joining": "2026-11-15",
        "salary": "950000",
        "location": "Bangalore",
        "manager_name": "Deepak Mehta",
        "employment_type": "Full-Time",
        "send_offer": True
    }

    onboard_res, code = post_json("/onboard", candidate_payload)
    assert_test("Onboarding pipeline executed", code == 200 and onboard_res.get("status") == "Success", f"Status: {onboard_res.get('status')}")

    emp_id = onboard_res.get("employee_id", "")
    assert_test("Employee ID auto-generated", bool(emp_id), f"ID: {emp_id}")
    assert_test("Candidate folder created", onboard_res.get("folder_created", False))
    assert_test("Welcome Letter PDF generated", onboard_res.get("letter_generated", False))
    assert_test("Offer Letter PDF generated", onboard_res.get("offer_letter_generated", False))
    assert_test("Offer email dispatched", onboard_res.get("offer_email_sent", False))
    assert_test("Welcome email dispatched", onboard_res.get("email_sent", False))
    assert_test("Hardware kit auto-provisioned", onboard_res.get("assets_allocated", False))

    # -------------------------------------------------------------
    # 4. STANDALONE OFFER EMAIL DISPATCH
    # -------------------------------------------------------------
    print("\n[4] Standalone Offer Email Dispatch (/api/send-offer)")
    if emp_id:
        offer_res, code = post_json("/send-offer", {"employee_id": emp_id})
        assert_test("Standalone offer email API", code == 200 and offer_res.get("success"), f"Mode: {offer_res.get('mode')}")
    else:
        assert_test("Standalone offer email API", False, "Skipped: emp_id missing")

    # -------------------------------------------------------------
    # 5. MASTER EMPLOYEE DIRECTORY
    # -------------------------------------------------------------
    print("\n[5] Master Employee Directory")
    emp_dir, code = get_json("/employees")
    assert_test("Directory fetch", code == 200 and "employees" in emp_dir, f"Count: {emp_dir.get('count', 0)}")
    found = any(e.get("Employee ID") == emp_id for e in emp_dir.get("employees", []))
    assert_test("New candidate listed in directory", found, f"Target: {emp_id}")

    # -------------------------------------------------------------
    # 6. IT ASSET TRACKER
    # -------------------------------------------------------------
    print("\n[6] IT Asset Allocation & Inventory")
    if emp_id:
        emp_assets, code = get_json(f"/employees/{emp_id}/assets")
        assert_test("Employee asset kit loaded", code == 200 and isinstance(emp_assets, list), f"Assets allocated: {len(emp_assets)}")
    else:
        assert_test("Employee asset kit loaded", False, "Skipped: emp_id missing")

    all_assets, code = get_json("/assets")
    assert_test("Global asset inventory", code == 200 and "assets" in all_assets, f"Total assets: {all_assets.get('count', 0)}")

    # -------------------------------------------------------------
    # 7. DOCUMENT MANAGEMENT & VERIFICATION
    # -------------------------------------------------------------
    print("\n[7] Document Management & Verification Matrix")
    if emp_id:
        doc_data, code = get_json(f"/employees/{emp_id}/documents")
        assert_test("Document checklist retrieved", code == 200 and "checklist" in doc_data, f"Required: {len(doc_data.get('checklist', []))}")
        summary = doc_data.get("summary", {})
        assert_test("Verification summary scorecard", "total_required" in summary, f"Required: {summary.get('total_required')}")
    else:
        assert_test("Document checklist retrieved", False, "Skipped: emp_id missing")

    # -------------------------------------------------------------
    # 8. COMPLIANCE & EXECUTIVE REPORTS
    # -------------------------------------------------------------
    print("\n[8] Compliance Reports & Audit Exports")
    rpt_gen, code = post_json("/generate-report")
    assert_test("Excel report generation", code == 200 and rpt_gen.get("success"), f"Path: {os.path.basename(rpt_gen.get('file_path', ''))}")

    rpt_list, code = get_json("/reports")
    reports = rpt_list.get("reports", [])
    assert_test("Reports catalog retrieved", code == 200 and len(reports) > 0, f"Available reports: {len(reports)}")

    if reports:
        latest_report = reports[0]["name"]
        # Test delete endpoint
        del_res, code = delete_json(f"/reports/{latest_report}")
        assert_test("Delete report capability", code == 200 and del_res.get("success"), f"Deleted: {latest_report}")

    # -------------------------------------------------------------
    # 9. SYSTEM AUDIT TRAIL
    # -------------------------------------------------------------
    print("\n[9] System Audit Trail Log")
    audit, code = get_json("/audit-log")
    assert_test("Audit trail log accessible", code == 200 and "entries" in audit, f"Events logged: {len(audit.get('entries', []))}")

    # -------------------------------------------------------------
    # 10. EXCEL DATA HUB & BATCH ONBOARDING
    # -------------------------------------------------------------
    print("\n[10] Excel Data Hub (Template, Export, Batch Onboarding)")
    req_tpl = urllib.request.Request(f"{BASE_URL}/download-template")
    try:
        resp_tpl = opener.open(req_tpl)
        assert_test("Download Excel template", resp_tpl.getcode() == 200 and len(resp_tpl.read()) > 1000)
    except Exception as e:
        assert_test("Download Excel template", False, str(e))

    req_exp = urllib.request.Request(f"{BASE_URL}/export-employees-excel")
    try:
        resp_exp = opener.open(req_exp)
        assert_test("Export Master Database Excel", resp_exp.getcode() == 200 and len(resp_exp.read()) > 1000)
    except Exception as e:
        assert_test("Export Master Database Excel", False, str(e))

    # Test Batch Onboarding API
    batch_suffix = int(time.time())
    sample_batch_candidates = [
        {
            "full_name": f"Aditya Nair",
            "date_of_birth": "1995-03-10",
            "gender": "Male",
            "email": f"aditya.nair.{batch_suffix}@example.com",
            "phone": "9876543211",
            "address": "Electronic City, Bangalore",
            "department": "Engineering",
            "designation": "Software Engineer",
            "salary": "800000",
            "date_of_joining": "2026-11-20",
            "location": "Bangalore",
            "manager_name": "Deepak Mehta",
            "employment_type": "Full-Time",
            "send_offer": True
        },
        {
            "full_name": f"Meera Iyer",
            "date_of_birth": "1997-07-15",
            "gender": "Female",
            "email": f"meera.iyer.{batch_suffix}@example.com",
            "phone": "9876543212",
            "address": "Hitec City, Hyderabad",
            "department": "HR",
            "designation": "HR Specialist",
            "salary": "750000",
            "date_of_joining": "2026-11-25",
            "location": "Hyderabad",
            "manager_name": "Pooja Hegde",
            "employment_type": "Full-Time",
            "send_offer": True
        }
    ]

    batch_res, code = post_json("/batch-onboard", {"candidates": sample_batch_candidates})
    assert_test("Batch RPA onboarding execution", code == 200 and batch_res.get("success") and batch_res.get("success_count") == 2, f"Processed: {batch_res.get('success_count')}/{batch_res.get('total')}")

    # -------------------------------------------------------------
    # 11. RBAC SALARY MASKING (VIEWER & MANAGER)
    # -------------------------------------------------------------
    print("\n[11] RBAC Salary Masking Verification")
    post_json("/logout")
    post_json("/login", {"username": "viewer", "password": "view123"})
    viewer_dir, code = get_json("/employees")
    if viewer_dir.get("employees"):
        first_emp = viewer_dir["employees"][0]
        assert_test("Viewer salary masking enforced", first_emp.get("Salary") == "Confidential", f"Salary value: {first_emp.get('Salary')}")

    # Re-login as admin for clean logout
    post_json("/login", {"username": "admin", "password": "admin123"})

    # -------------------------------------------------------------
    # 12. SESSION TERMINATION
    # -------------------------------------------------------------
    print("\n[12] Session Termination & Logout")
    logout_res, code = post_json("/logout")
    assert_test("Logout successful", code == 200 and logout_res.get("success"))
    me_after, _ = get_json("/me")
    assert_test("Session terminated cleanly", not me_after.get("logged_in"))

    # -------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------
    print("\n" + "=" * 65)
    passed = sum(1 for _, status, _ in test_results if status == "PASS")
    total = len(test_results)
    print(f"  TOTAL TESTS: {total} | PASSED: {passed} | FAILED: {total - passed}")
    if passed == total:
        print("  🎉 ALL ENTERPRISE TEST CASES PASSED SUCCESSFULLY!")
    else:
        print("  ⚠️ SOME TESTS FAILED. CHECK LOGS ABOVE.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_all_tests()

