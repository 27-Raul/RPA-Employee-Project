"""
main.py
=======
RPA Employee Onboarding System — Master Orchestrator + Flask API
================================================================
This is the central Python script that:
  1. Exposes a REST API for the HTML dashboard
  2. Orchestrates the full RPA workflow for each new employee

Run with:
    python main.py
"""

import os
import sys
import json
import logging
from datetime import datetime
from functools import wraps

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from flask import Flask, request, jsonify, send_from_directory, session, send_file
from flask_cors import CORS

# ── Add project root to sys.path ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.validator       import validate_employee_data
from modules.employee_id_gen import generate_employee_id, is_duplicate_employee
from modules.excel_handler   import (
    initialize_database, initialize_error_log,
    add_employee_record, update_employee_record,
    log_error, read_config, get_all_employees,
    create_employee_template, parse_employee_excel
)
from modules.folder_creator    import (
    create_employee_folder, get_welcome_letter_path, get_id_card_path
)
from modules.document_generator import generate_welcome_letter, generate_id_card
from modules.email_sender        import send_welcome_email
from modules.report_generator    import generate_onboarding_report

# New imports
from modules.offer_letter import generate_offer_letter, send_offer_email
from modules.auth import authenticate, get_user_permissions, check_permission
from modules.asset_tracker import initialize_asset_db, auto_allocate_standard_kit, get_employee_assets, get_all_assets
from modules.document_manager import initialize_doc_tracker, save_uploaded_document, add_document_record, get_employee_documents, get_document_checklist, verify_document, get_verification_summary

# ═══════════════════════════════════════════════════════════════════════════════
#  Logging Setup
# ═══════════════════════════════════════════════════════════════════════════════
os.makedirs(os.path.join(BASE_DIR, "Logs"), exist_ok=True)
log_file = os.path.join(BASE_DIR, "Logs", f"onboarding_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RPA_Onboarding")

# ═══════════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════════
CONFIG_PATH   = os.path.join(BASE_DIR, "Config.xlsx")
config        = read_config(CONFIG_PATH)

COMPANY_NAME  = config.get("CompanyName",        "Infosys Limited")
DB_PATH       = os.path.join(BASE_DIR,  config.get("DatabasePath",   "Database/EmployeeDatabase.xlsx"))
ERROR_LOG     = os.path.join(BASE_DIR,  config.get("ErrorLogPath",   "Logs/ErrorLog.xlsx"))
EMP_ROOT      = os.path.join(BASE_DIR,  config.get("EmployeeRootFolder", "Employees"))
REPORT_PATH   = os.path.join(BASE_DIR,  config.get("ReportPath",     "Reports"))
AUDIT_LOG     = os.path.join(BASE_DIR,  "Logs", "audit_trail.log")
ASSET_DB      = os.path.join(BASE_DIR, 'Database/AssetTracker.xlsx')
DOC_TRACKER   = os.path.join(BASE_DIR, 'Database/DocumentTracker.xlsx')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'Templates', 'Employee_Onboarding_Template.xlsx')

# ═══════════════════════════════════════════════════════════════════════════════
#  Flask App
# ═══════════════════════════════════════════════════════════════════════════════
app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "Dashboard"))
app.secret_key = 'infosys-rpa-2026'
CORS(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized', 'logged_in': False}), 401
        return f(*args, **kwargs)
    return decorated_function

# Serve the dashboard at /
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(app.static_folder, filename)


# ── Audit Trail Writer ─────────────────────────────────────────────────────────
def _write_audit_log(action: str, detail: str, employee_id: str = "SYSTEM"):
    """Appends a structured entry to the audit trail log file."""
    try:
        os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] | {employee_id} | {action} | {detail}\n"
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # Audit log failure should never crash main workflow

# ═══════════════════════════════════════════════════════════════════════════════
#  Core RPA Workflow
# ═══════════════════════════════════════════════════════════════════════════════
def run_onboarding_workflow(employee_data: dict) -> dict:
    """
    Executes the full RPA onboarding pipeline for ONE employee.
    """
    result = {
        "employee_id":       None,
        "full_name":         employee_data.get("full_name", "Unknown"),
        "email":             employee_data.get("email", ""),
        "department":        employee_data.get("department", ""),
        "designation":       employee_data.get("designation", ""),
        "status":            "Failed",
        "folder_created":    False,
        "letter_generated":  False,
        "id_card_generated": False,
        "email_sent":        False,
        "db_updated":        False,
        "offer_letter_generated": False,
        "offer_email_sent": False,
        "assets_allocated": False,
        "errors":            [],
        "warnings":          [],
        "folder_path":       "",
        "letter_path":       "",
    }

    logger.info(f"═══ Starting onboarding for: {employee_data.get('full_name')} ═══")

    # ── Step 1: Validate ───────────────────────────────────────────────────────
    validation = validate_employee_data(employee_data)
    result["warnings"] = validation.get("warnings", [])

    if not validation["is_valid"]:
        result["errors"] = validation["errors"]
        log_error(ERROR_LOG, "UNKNOWN", "Validation Error",
                  " | ".join(validation["errors"]))
        logger.warning(f"Validation failed for {employee_data.get('full_name')}")
        return result

    logger.info("✅ Step 1: Validation passed")

    # ── Step 2: Duplicate Check ────────────────────────────────────────────────
    dup = is_duplicate_employee(DB_PATH, employee_data["email"], employee_data["full_name"])
    if dup["is_duplicate"]:
        result["errors"].append(dup["reason"])
        log_error(ERROR_LOG, "UNKNOWN", "Duplicate Employee", dup["reason"])
        logger.warning(dup["reason"])
        return result

    logger.info("✅ Step 2: No duplicate found")

    # ── Step 3: Generate Employee ID ──────────────────────────────────────────
    try:
        emp_id = generate_employee_id(DB_PATH)
        employee_data["employee_id"] = emp_id
        result["employee_id"] = emp_id
        logger.info(f"✅ Step 3: Employee ID generated → {emp_id}")
    except Exception as e:
        msg = f"Employee ID generation failed: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, "UNKNOWN", "ID Generation Error", msg)
        return result

    # ── Step 4: Add to Excel ───────────────────────────────────────────────────
    try:
        ok = add_employee_record(DB_PATH, employee_data)
        if ok:
            result["db_updated"] = True
            logger.info(f"✅ Step 4: Employee record added to database")
        else:
            raise Exception("add_employee_record returned False")
    except Exception as e:
        msg = f"Database record creation failed: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "Database Error", msg)

    # ── Step 5: Create Folder ─────────────────────────────────────────────────
    folder_result = create_employee_folder(EMP_ROOT, emp_id, employee_data["full_name"])
    if folder_result["success"]:
        result["folder_created"] = True
        result["folder_path"]    = folder_result["folder_path"]
        logger.info(f"✅ Step 5: Employee folder created → {folder_result['folder_path']}")
    else:
        result["errors"].append(folder_result["error"])
        log_error(ERROR_LOG, emp_id, "Folder Creation Error", folder_result["error"])
        
    # ── Step 5.5: Auto Allocate Standard Kit ─────────────────────────────────
    if result["folder_created"]:
        try:
            kit_res = auto_allocate_standard_kit(ASSET_DB, emp_id, employee_data["full_name"])
            if kit_res:
                result["assets_allocated"] = True
                logger.info(f"✅ Step 5.5: Assets allocated automatically")
        except Exception as e:
            msg = f"Asset allocation failed: {e}"
            result["errors"].append(msg)
            log_error(ERROR_LOG, emp_id, "Asset Error", msg)

    # ── Step 6: Generate Welcome Letter ───────────────────────────────────────
    try:
        letter_folder = get_welcome_letter_path(folder_result.get("folder_path", EMP_ROOT))
        letter_result = generate_welcome_letter(employee_data, letter_folder, COMPANY_NAME)
        if letter_result["success"]:
            result["letter_generated"] = True
            result["letter_path"]      = letter_result["file_path"]
            logger.info(f"✅ Step 6: Welcome Letter generated → {letter_result['file_path']}")
        else:
            result["errors"].append(letter_result["error"])
            log_error(ERROR_LOG, emp_id, "Document Error", letter_result["error"])
    except Exception as e:
        msg = f"Welcome letter generation exception: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "Document Error", msg)
        
    # ── Step 6.5: Generate Offer Letter ───────────────────────────────────────
    offer_letter_path = None
    try:
        offer_folder = os.path.join(folder_result.get("folder_path", EMP_ROOT), "Offer_Letter")
        os.makedirs(offer_folder, exist_ok=True)
        offer_result = generate_offer_letter(employee_data, offer_folder, COMPANY_NAME)
        if offer_result["success"]:
            result["offer_letter_generated"] = True
            offer_letter_path = offer_result["file_path"]
            logger.info(f"✅ Step 6.5: Offer Letter generated → {offer_letter_path}")
        else:
            result["errors"].append(offer_result.get("error", "Unknown error generating offer letter"))
            log_error(ERROR_LOG, emp_id, "Document Error", offer_result.get("error", "Error"))
    except Exception as e:
        msg = f"Offer letter generation exception: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "Document Error", msg)

    # ── Step 6.6: Send Offer Email ────────────────────────────────────────────
    if result["offer_letter_generated"]:
        try:
            offer_email_result = send_offer_email(employee_data, config, offer_letter_path)
            if offer_email_result["success"]:
                result["offer_email_sent"] = True
                logger.info("✅ Step 6.6: Offer email sent successfully")
            else:
                result["errors"].append(offer_email_result.get("error", "Unknown error sending offer email"))
                log_error(ERROR_LOG, emp_id, "Email Error", offer_email_result.get("error", "Error"))
        except Exception as e:
            msg = f"Offer email sending exception: {e}"
            result["errors"].append(msg)
            log_error(ERROR_LOG, emp_id, "Email Error", msg)

    # ── Step 7: Generate ID Card ──────────────────────────────────────────────
    try:
        id_card_folder = get_id_card_path(folder_result.get("folder_path", EMP_ROOT))
        id_result = generate_id_card(employee_data, id_card_folder, COMPANY_NAME)
        if id_result["success"]:
            result["id_card_generated"] = True
            logger.info(f"✅ Step 7: ID Card generated → {id_result['file_path']}")
        else:
            result["errors"].append(id_result["error"])
            log_error(ERROR_LOG, emp_id, "ID Card Error", id_result["error"])
    except Exception as e:
        msg = f"ID card generation exception: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "ID Card Error", msg)

    # ── Step 8: Send Email ────────────────────────────────────────────────────
    try:
        attachment = result["letter_path"] if result["letter_generated"] else None
        email_result = send_welcome_email(employee_data, config, attachment)
        if email_result["success"]:
            result["email_sent"] = True
            logger.info(f"✅ Step 8: Welcome email sent (mode={email_result['mode']})")
        else:
            result["errors"].append(email_result["error"])
            log_error(ERROR_LOG, emp_id, "Email Error", email_result["error"])
    except Exception as e:
        msg = f"Email sending exception: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "Email Error", msg)

    # ── Step 9: Update Excel (finalize) ──────────────────────────────────────
    try:
        updates = {
            "Status":               "Onboarding Completed",
            "Onboarding Date":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Employee Folder Path": result["folder_path"],
            "Welcome Letter Path":  result["letter_path"],
            "Email Status":         "Sent" if result["email_sent"] else "Failed",
        }
        update_employee_record(DB_PATH, emp_id, updates)
        logger.info(f"✅ Step 9: Employee record updated to 'Onboarding Completed'")
    except Exception as e:
        msg = f"Final DB update failed: {e}"
        result["errors"].append(msg)
        log_error(ERROR_LOG, emp_id, "Database Update Error", msg)

    # ── Final status ──────────────────────────────────────────────────────────
    critical_failures = [e for e in result["errors"] if "validation" in e.lower() or "duplicate" in e.lower()]
    if not critical_failures:
        result["status"] = "Success"

    # Write to audit trail
    _write_audit_log(
        action=f"ONBOARD_{result['status'].upper()}",
        detail=f"Name: {result['full_name']} | Dept: {result['department']} | Email: {result['email']}",
        employee_id=emp_id
    )

    logger.info(f"═══ Onboarding complete for {emp_id}: {result['status']} ═══\n")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  API Routes
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/login", methods=["POST"])
def api_login():
    """POST /api/login — authenticate user and create session."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        username = data.get("username", "")
        password = data.get("password", "")

        result = authenticate(username, password)
        if result.get("success"):
            user = result["user"]   # {'role': ..., 'name': ...}
            session["logged_in"] = True
            session["username"]  = username
            session["role"]      = user.get("role", "Viewer")
            session["name"]      = user.get("name", username)

            perms = get_user_permissions(session["role"])
            return jsonify({
                "success": True,
                "user": {
                    "username":    username,
                    "name":        session["name"],
                    "role":        session["role"],
                    "permissions": perms
                }
            })
        else:
            return jsonify({"success": False, "error": result.get("error", "Invalid credentials")}), 401
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/logout", methods=["POST"])
def api_logout():
    """POST /api/logout"""
    session.clear()
    return jsonify({"success": True})

@app.route("/api/me", methods=["GET"])
def api_me():
    """GET /api/me"""
    if session.get("logged_in"):
        return jsonify({
            "logged_in": True,
            "username": session.get("username"),
            "role": session.get("role"),
            "name": session.get("name"),
            "permissions": get_user_permissions(session.get("role"))
        })
    else:
        return jsonify({"logged_in": False})

@app.route("/api/onboard", methods=["POST"])
@login_required
def api_onboard():
    """POST /api/onboard — Onboard a single employee."""
    try:
        if not check_permission(session.get("role"), "can_register"):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        engine = data.get("engine", "python").lower()
        logger.info(f"API: Received onboarding request for '{data.get('full_name', 'Unknown')}' using engine '{engine}'")

        if engine == "uipath":
            from UiPath_Project.run_uipath import execute_uipath_pipeline
            result = execute_uipath_pipeline(data)
        else:
            result = run_onboarding_workflow(data)

        # Save submitted form to Input/ folder for audit & UiPath pickup
        input_dir = os.path.join(BASE_DIR, "Input")
        os.makedirs(input_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"Employee_{result.get('employee_id', 'UNKNOWN')}_{ts}.json"
        with open(os.path.join(input_dir, fname), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        # Also write to New_Employee.json for direct UiPath robot pickup
        with open(os.path.join(input_dir, "New_Employee.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        status_code = 200 if result["status"] == "Success" else 422
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"API /onboard unhandled exception: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/uipath/run", methods=["POST"])
@login_required
def api_uipath_run():
    """POST /api/uipath/run — Direct UiPath workflow execution endpoint."""
    try:
        if not check_permission(session.get("role"), "can_register"):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json() or {}
        from UiPath_Project.run_uipath import execute_uipath_pipeline
        result = execute_uipath_pipeline(data)
        return jsonify(result), 200 if result.get("status") == "Success" else 422
    except Exception as e:
        logger.error(f"API /uipath/run error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500



@app.route("/api/employees", methods=["GET"])
@login_required
def api_employees():
    """GET /api/employees — Return all employees from the database."""
    try:
        employees = get_all_employees(DB_PATH)
        role = session.get("role", "Viewer")
        can_view_salary = check_permission(role, "can_view_salary")
        if not can_view_salary:
            for emp in employees:
                if "Salary" in emp:
                    emp["Salary"] = "Confidential"
        return jsonify({"employees": employees, "count": len(employees)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download-template", methods=["GET"])
@login_required
def api_download_template():
    """GET /api/download-template — Download sample Excel onboarding template."""
    try:
        if not os.path.exists(TEMPLATE_PATH):
            create_employee_template(TEMPLATE_PATH)
        return send_file(
            TEMPLATE_PATH,
            as_attachment=True,
            download_name="Employee_Onboarding_Template.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Failed to send template: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/export-employees-excel", methods=["GET"])
@login_required
def api_export_employees_excel():
    """GET /api/export-employees-excel — Download current EmployeeDatabase.xlsx."""
    try:
        initialize_database(DB_PATH)
        _write_audit_log("EXPORT_DATABASE", f"Employee database exported to Excel by {session.get('name')}")
        return send_file(
            DB_PATH,
            as_attachment=True,
            download_name=f"EmployeeDatabase_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Failed to export employee database: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload-excel-preview", methods=["POST"])
@login_required
def api_upload_excel_preview():
    """POST /api/upload-excel-preview — Upload an Excel file and parse/validate rows for preview."""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            return jsonify({"error": "Only Excel spreadsheets (.xlsx, .xls) are supported."}), 400

        candidates = parse_employee_excel(file)
        if not candidates:
            return jsonify({"error": "No valid candidate rows found in the uploaded Excel spreadsheet."}), 400

        preview_data = []
        valid_count = 0
        error_count = 0

        for cand in candidates:
            validation = validate_employee_data(cand)
            dup_check = is_duplicate_employee(DB_PATH, cand.get("email", ""), cand.get("full_name", ""))

            row_errors = list(validation.get("errors", []))
            if dup_check.get("is_duplicate"):
                row_errors.append(dup_check.get("reason"))

            is_valid = len(row_errors) == 0
            if is_valid:
                valid_count += 1
            else:
                error_count += 1

            preview_data.append({
                "candidate": cand,
                "is_valid": is_valid,
                "errors": row_errors,
                "warnings": validation.get("warnings", [])
            })

        return jsonify({
            "success": True,
            "filename": file.filename,
            "total_rows": len(preview_data),
            "valid_count": valid_count,
            "error_count": error_count,
            "candidates": preview_data
        })
    except Exception as e:
        logger.error(f"Excel preview parsing failed: {e}", exc_info=True)
        return jsonify({"error": f"Failed to parse Excel file: {str(e)}"}), 500


@app.route("/api/batch-onboard", methods=["POST"])
@login_required
def api_batch_onboard():
    """POST /api/batch-onboard — Execute RPA onboarding for a batch of candidate records."""
    try:
        if not check_permission(session.get("role"), "can_register"):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json(force=True, silent=True) or {}
        candidates = data.get("candidates", [])
        if not candidates:
            return jsonify({"error": "No candidates provided for batch onboarding."}), 400

        batch_results = []
        success_count = 0
        failed_count = 0

        logger.info(f"Starting batch RPA onboarding for {len(candidates)} candidates...")
        _write_audit_log("BATCH_ONBOARD_START", f"Starting batch onboarding for {len(candidates)} candidates by {session.get('name')}")

        for cand in candidates:
            cand_data = cand.get("candidate") if (isinstance(cand, dict) and "candidate" in cand) else cand
            result = run_onboarding_workflow(cand_data)
            if result.get("status") == "Success":
                success_count += 1
            else:
                failed_count += 1
            batch_results.append(result)

        _write_audit_log("BATCH_ONBOARD_COMPLETE", f"Batch complete: {success_count} succeeded, {failed_count} failed")
        return jsonify({
            "success": True,
            "total": len(candidates),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": batch_results
        })
    except Exception as e:
        logger.error(f"Batch onboarding failed: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
@login_required
def api_stats():
    """GET /api/stats — Dashboard statistics."""
    try:
        employees = get_all_employees(DB_PATH)
        total = len(employees)
        completed = sum(1 for e in employees if "Completed" in str(e.get("Status", "")))
        onboarding = sum(1 for e in employees if e.get("Status") == "Onboarding")
        emails_sent = sum(1 for e in employees if e.get("Email Status") == "Sent")

        dept_counts = {}
        for e in employees:
            dept = e.get("Department", "Unknown")
            dept_counts[dept] = dept_counts.get(dept, 0) + 1

        return jsonify({
            "total":      total,
            "completed":  completed,
            "onboarding": onboarding,
            "emails_sent": emails_sent,
            "departments": dept_counts,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/dashboard-stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    """GET /api/dashboard-stats — Enhanced Dashboard statistics."""
    try:
        employees = get_all_employees(DB_PATH)
        total = len(employees)
        completed = sum(1 for e in employees if "Completed" in str(e.get("Status", "")))
        onboarding = sum(1 for e in employees if e.get("Status") == "Onboarding")
        emails_sent = sum(1 for e in employees if e.get("Email Status") == "Sent")
        # In a real scenario, offer_letters_sent might be tracked in DB. We will mock or count by some heuristic if missing
        offer_letters_sent = sum(1 for e in employees if e.get("Email Status") in ["Sent", "Offer Sent"])
        
        dept_counts = {}
        monthly_trend_counts = {}
        
        for e in employees:
            dept = e.get("Department", "Unknown")
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
            
            doj = e.get("Date of Joining", "")
            if doj:
                try:
                    # Assumes YYYY-MM-DD or similar standard format; adjust if needed
                    month = doj[:7]
                    monthly_trend_counts[month] = monthly_trend_counts.get(month, 0) + 1
                except:
                    pass

        return jsonify({
            "total":      total,
            "completed":  completed,
            "onboarding": onboarding,
            "emails_sent": emails_sent,
            "departments": dept_counts,
            "offer_letters_sent": offer_letters_sent,
            "monthly_trend": monthly_trend_counts,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/reports", methods=["GET"])
@login_required
def api_reports():
    """GET /api/reports — List all generated onboarding reports."""
    try:
        reports = []
        if os.path.exists(REPORT_PATH):
            for f in os.listdir(REPORT_PATH):
                if f.endswith(".xlsx"):
                    fpath = os.path.join(REPORT_PATH, f)
                    reports.append({
                        "name": f,
                        "path": fpath,
                        "size_kb": round(os.path.getsize(fpath) / 1024, 1),
                        "created": datetime.fromtimestamp(
                            os.path.getctime(fpath)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    })
        reports.sort(key=lambda x: x["created"], reverse=True)
        return jsonify({"reports": reports})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate-report", methods=["POST"])
@login_required
def api_generate_report():
    """POST /api/generate-report — Generate an onboarding report from the current database."""
    try:
        if not check_permission(session.get("role"), "can_generate_report"):
            return jsonify({"error": "Permission denied"}), 403

        employees = get_all_employees(DB_PATH)
        if not employees:
            return jsonify({"error": "No employees in database to report on."}), 400

        results = []
        for emp in employees:
            results.append({
                "employee_id":       emp.get("Employee ID", ""),
                "full_name":         emp.get("Full Name", ""),
                "email":             emp.get("Email", ""),
                "department":        emp.get("Department", ""),
                "designation":       emp.get("Designation", ""),
                "status":            "Success" if "Completed" in str(emp.get("Status", "")) else "Onboarding",
                "folder_created":    bool(emp.get("Employee Folder Path")),
                "letter_generated":  bool(emp.get("Welcome Letter Path")),
                "id_card_generated": bool(emp.get("Welcome Letter Path")),  # proxy
                "email_sent":        emp.get("Email Status") == "Sent",
                "db_updated":        True,
                "errors":            [],
            })

        report_result = generate_onboarding_report(results, REPORT_PATH, COMPANY_NAME)
        if report_result["success"]:
            return jsonify({
                "success":   True,
                "file_path": report_result["file_path"],
                "summary":   report_result["summary"]
            })
        else:
            return jsonify({"error": report_result.get("error")}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
@login_required
def api_config():
    """GET /api/config — Return non-sensitive config values."""
    safe_config = {k: v for k, v in config.items() if "password" not in k.lower()}
    return jsonify(safe_config)


@app.route("/api/reports/<filename>", methods=["DELETE"])
@login_required
def api_delete_report(filename):
    """DELETE /api/reports/<filename> — Permanently delete a specific report file."""
    try:
        if not check_permission(session.get("role"), "can_delete"):
            return jsonify({"error": "Permission denied"}), 403

        safe_filename = os.path.basename(filename)
        if not safe_filename.endswith(".xlsx"):
            return jsonify({"error": "Only .xlsx report files can be deleted."}), 400

        file_path = os.path.join(REPORT_PATH, safe_filename)
        if not os.path.exists(file_path):
            return jsonify({"error": f"Report '{safe_filename}' not found."}), 404

        os.remove(file_path)

        _write_audit_log("DELETE_REPORT", f"Report deleted: {safe_filename}")
        logger.info(f"Report deleted: {safe_filename}")
        return jsonify({"success": True, "message": f"Report '{safe_filename}' deleted successfully."})

    except PermissionError:
        return jsonify({"error": "Permission denied. The file may be open in Excel."}), 403
    except Exception as e:
        logger.error(f"Failed to delete report {filename}: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/audit-log", methods=["GET"])
@login_required
def api_audit_log():
    """GET /api/audit-log — Return last 50 audit trail entries."""
    try:
        if not os.path.exists(AUDIT_LOG):
            return jsonify({"entries": []})
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        entries = []
        for line in reversed(lines[-50:]):
            line = line.strip()
            if line:
                entries.append(line)
        return jsonify({"entries": entries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/send-offer", methods=["POST"])
@login_required
def api_send_offer():
    """POST /api/send-offer — Generate offer letter and send email to employee."""
    try:
        if not check_permission(session.get("role"), "can_register"):
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json(force=True, silent=True) or {}
        employee_id = data.get("employee_id", "").strip()

        # Fetch employee from database
        employees = get_all_employees(DB_PATH)
        db_row = next((e for e in employees if str(e.get("Employee ID", "")).strip() == employee_id), None)

        if not db_row:
            return jsonify({"error": f"Employee '{employee_id}' not found in database."}), 404

        # Normalize DB column keys → lowercase snake_case for the offer_letter module
        employee_data = {
            "employee_id":       db_row.get("Employee ID", ""),
            "full_name":         db_row.get("Full Name", ""),
            "email":             db_row.get("Email", ""),
            "phone":             db_row.get("Phone", ""),
            "address":           db_row.get("Address", ""),
            "department":        db_row.get("Department", ""),
            "designation":       db_row.get("Designation", ""),
            "date_of_joining":   str(db_row.get("Date of Joining", "")),
            "salary":            str(db_row.get("Salary", "")),
            "manager_name":      db_row.get("Manager Name", ""),
            "employment_type":   db_row.get("Employment Type", ""),
            "date_of_birth":     str(db_row.get("Date of Birth", "")),
            "gender":            db_row.get("Gender", ""),
        }

        if not employee_data["email"]:
            return jsonify({"error": "Employee email address is missing."}), 400

        # Determine offer folder path
        folder_path = db_row.get("Employee Folder Path", EMP_ROOT)
        if not folder_path or not os.path.exists(str(folder_path)):
            folder_path = os.path.join(EMP_ROOT, f"{employee_id}_{employee_data['full_name'].replace(' ', '_')}")
        offer_folder = os.path.join(str(folder_path), "Offer_Letter")
        os.makedirs(offer_folder, exist_ok=True)

        offer_result = generate_offer_letter(employee_data, offer_folder, COMPANY_NAME)
        if not offer_result.get("success"):
            return jsonify({"error": offer_result.get("error", "Error generating offer letter")}), 500

        email_result = send_offer_email(employee_data, config, offer_result.get("file_path"))
        _write_audit_log("SEND_OFFER_EMAIL",
                         f"Offer email sent to {employee_data['email']}",
                         employee_id=employee_id)

        return jsonify({
            "success": email_result.get("success", False),
            "mode":    email_result.get("mode", "mock"),
            "message": "Offer letter generated and email sent successfully.",
            "employee_id": employee_id,
            "employee_name": employee_data["full_name"]
        })

    except Exception as e:
        logger.error(f"send-offer error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/employees/<employee_id>/assets", methods=["GET"])
@login_required
def api_employee_assets(employee_id):
    """GET /api/employees/<employee_id>/assets — Return assets for one employee."""
    try:
        assets = get_employee_assets(ASSET_DB, employee_id)
        return jsonify(assets)   # plain list — simple for frontend
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/employees/<employee_id>/documents", methods=["GET"])
@login_required
def api_employee_documents(employee_id):
    """GET /api/employees/<employee_id>/documents — Return document checklist."""
    try:
        checklist = get_document_checklist(DOC_TRACKER, employee_id)
        summary   = get_verification_summary(DOC_TRACKER, employee_id)
        return jsonify({"checklist": checklist, "summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/employees/<employee_id>/documents", methods=["POST"])
@login_required
def api_upload_document(employee_id):
    """POST /api/employees/<employee_id>/documents — Upload a document for an employee."""
    try:
        if not check_permission(session.get("role"), "can_upload_docs"):
            return jsonify({"error": "Permission denied"}), 403

        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file     = request.files["file"]
        doc_type = request.form.get("doc_type", "Other")

        # Find the employee folder
        employees = get_all_employees(DB_PATH)
        db_row = next((e for e in employees if str(e.get("Employee ID","")).strip() == employee_id), None)
        emp_name = db_row.get("Full Name", employee_id) if db_row else employee_id

        result = save_uploaded_document(EMP_ROOT, employee_id, doc_type, file, file.filename)
        if not result.get("success"):
            return jsonify({"error": result.get("error", "Failed to save file")}), 500

        add_document_record(DOC_TRACKER, employee_id, emp_name, doc_type, file.filename, result["file_path"])
        _write_audit_log("UPLOAD_DOCUMENT", f"Doc uploaded: {doc_type} | {file.filename}", employee_id=employee_id)
        return jsonify({"success": True, "file_path": result["file_path"], "doc_type": doc_type})

    except Exception as e:
        logger.error(f"Document upload error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/employees/<employee_id>/documents/<doc_id>/verify", methods=["POST"])
@login_required
def api_verify_document(employee_id, doc_id):
    """POST /api/employees/<employee_id>/documents/<doc_id>/verify — Mark document as verified."""
    try:
        if not check_permission(session.get("role"), "can_approve"):
            return jsonify({"error": "Permission denied"}), 403
        verifier = session.get("name", "Unknown Verifier")
        result   = verify_document(DOC_TRACKER, doc_id, verifier)
        if result:
            _write_audit_log("VERIFY_DOCUMENT", f"Doc {doc_id} verified by {verifier}", employee_id=employee_id)
            return jsonify({"success": True, "message": "Document verified successfully."})
        return jsonify({"error": "Failed to verify document"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/assets", methods=["GET"])
@login_required
def api_assets():
    """GET /api/assets — Return all allocated assets."""
    try:
        assets = get_all_assets(ASSET_DB)
        return jsonify({"assets": assets, "count": len(assets)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════════════════
#  Startup
# ═══════════════════════════════════════════════════════════════════════════════
def startup():
    """Initialize database files and folders on startup."""
    logger.info("=" * 60)
    logger.info(f"  {COMPANY_NAME} — RPA Employee Onboarding System")
    logger.info("=" * 60)
    os.makedirs(EMP_ROOT,    exist_ok=True)
    os.makedirs(REPORT_PATH, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "Input"),   exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "Logs"),    exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "Database"), exist_ok=True)
    
    initialize_database(DB_PATH)
    initialize_error_log(ERROR_LOG)
    initialize_asset_db(ASSET_DB)
    initialize_doc_tracker(DOC_TRACKER)
    create_employee_template(TEMPLATE_PATH)
    
    logger.info("✅ All systems initialized. Server starting...")


if __name__ == "__main__":
    startup()
    print("\n" + "="*60)
    print("  🚀 RPA Employee Onboarding System is running!")
    print("  📊 Dashboard: http://localhost:5000")
    print("  📡 API Base:  http://localhost:5000/api")
    print("="*60 + "\n")
    app.run(debug=True, port=5000, host="0.0.0.0")
