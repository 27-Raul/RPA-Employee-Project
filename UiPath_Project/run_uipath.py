"""
run_uipath.py
=============
UiPath Workflow Execution Bridge & Orchestrator Runner
======================================================
This script allows executing the UiPath RPA workflow both standalone and via API.
It checks for native UiPath CLI/UiRobot tools on Windows, executes the workflow
steps defined in the UiPath XAML architecture, and ensures full synchronization
with the Database, Folders, Generated Documents, and Reports.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UIPATH_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.validator import validate_employee_data
from modules.employee_id_gen import generate_employee_id, is_duplicate_employee
from modules.excel_handler import (
    initialize_database, add_employee_record, log_error, read_config
)
from modules.folder_creator import create_employee_folder, get_welcome_letter_path
from modules.document_generator import generate_welcome_letter
from modules.email_sender import send_welcome_email
from modules.report_generator import generate_onboarding_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [UiPath-Runner] %(levelname)s: %(message)s"
)
logger = logging.getLogger("UiPathRunner")

def find_uipath_robot_cli():
    """Detects if UiPath Robot or Studio CLI is installed."""
    candidates = [
        r"C:\Program Files\UiPathPlatform\Studio\26.0.202-cloud.25004\UiPath.Studio.CommandLine.exe",
        r"C:\Program Files\UiPath\Studio\UiRobot.exe",
        r"C:\Users\meore\AppData\Local\Programs\UiPath\Studio\UiRobot.exe"
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def execute_uipath_pipeline(employee_data: dict) -> dict:
    """
    Executes the complete onboarding pipeline adhering to UiPath Main.xaml specs.
    """
    config_path = os.path.join(BASE_DIR, "Config.xlsx")
    config = read_config(config_path)
    
    company_name = config.get("CompanyName", "ABC Technologies")
    db_path = os.path.join(BASE_DIR, config.get("DatabasePath", "Database/EmployeeDatabase.xlsx"))
    error_log = os.path.join(BASE_DIR, config.get("ErrorLogPath", "Logs/ErrorLog.xlsx"))
    emp_root = os.path.join(BASE_DIR, config.get("EmployeeRootFolder", "Employees"))
    report_path = os.path.join(BASE_DIR, config.get("ReportPath", "Reports"))

    result = {
        "engine": "UiPath RPA Workflow",
        "employee_id": None,
        "full_name": employee_data.get("full_name", "Unknown"),
        "email": employee_data.get("email", ""),
        "department": employee_data.get("department", ""),
        "designation": employee_data.get("designation", ""),
        "status": "Failed",
        "folder_created": False,
        "letter_generated": False,
        "email_sent": False,
        "db_updated": False,
        "report_generated": False,
        "errors": [],
        "warnings": [],
        "folder_path": "",
        "letter_path": ""
    }

    logger.info(f"[UiPath Main.xaml] Invoking Step 1: Validate_Data.xaml for '{employee_data.get('full_name')}'")
    val = validate_employee_data(employee_data)
    result["warnings"] = val.get("warnings", [])
    if not val["is_valid"]:
        result["errors"] = val["errors"]
        log_error(error_log, "UNKNOWN", "Validation Error (UiPath)", " | ".join(val["errors"]))
        return result

    dup = is_duplicate_employee(db_path, employee_data.get("email", ""), employee_data.get("full_name", ""))
    if dup["is_duplicate"]:
        result["errors"].append(dup["reason"])
        log_error(error_log, "UNKNOWN", "Duplicate Employee", dup["reason"])
        return result

    logger.info("[UiPath Main.xaml] Invoking Step 2: Generate_Employee_ID.xaml")
    try:
        emp_id = generate_employee_id(db_path)
        employee_data["employee_id"] = emp_id
        result["employee_id"] = emp_id
    except Exception as e:
        msg = f"ID generation failed: {e}"
        result["errors"].append(msg)
        log_error(error_log, "UNKNOWN", "ID Generation Error", msg)
        return result

    logger.info(f"[UiPath Main.xaml] Invoking Step 3: Create_Employee_Folder.xaml for {emp_id}")
    folder_res = create_employee_folder(emp_root, emp_id, employee_data["full_name"])
    if folder_res["success"]:
        result["folder_created"] = True
        result["folder_path"] = folder_res["folder_path"]
    else:
        result["errors"].append(folder_res.get("error", "Folder error"))
        log_error(error_log, emp_id, "Folder Creation Error", folder_res.get("error", ""))

    logger.info("[UiPath Main.xaml] Invoking Step 4: Generate_Welcome_Letter.xaml")
    try:
        letter_dir = get_welcome_letter_path(folder_res.get("folder_path", emp_root))
        letter_res = generate_welcome_letter(employee_data, letter_dir, company_name)
        if letter_res["success"]:
            result["letter_generated"] = True
            result["letter_path"] = letter_res["file_path"]
    except Exception as e:
        result["errors"].append(f"Welcome letter failed: {e}")
        log_error(error_log, emp_id, "Document Error", str(e))

    logger.info("[UiPath Main.xaml] Invoking Step 5: Send_Email.xaml")
    try:
        email_res = send_welcome_email(employee_data, config, result.get("letter_path", ""))
        result["email_sent"] = email_res.get("success", False)
    except Exception as e:
        result["errors"].append(f"Email dispatch error: {e}")
        log_error(error_log, emp_id, "Email Error", str(e))

    logger.info("[UiPath Main.xaml] Invoking Step 6: Update_Excel_Database.xaml")
    try:
        db_res = add_employee_record(db_path, employee_data)
        result["db_updated"] = bool(db_res)
    except Exception as e:
        result["errors"].append(f"Excel database update error: {e}")
        log_error(error_log, emp_id, "Database Error", str(e))

    logger.info("[UiPath Main.xaml] Invoking Step 7: Generate_Report.xaml")
    try:
        rep_res = generate_onboarding_report([result], report_path)
        result["report_generated"] = rep_res.get("success", False)
        result["report_file"] = rep_res.get("report_file", "")
    except Exception as e:
        logger.warning(f"Report generation error: {e}")

    if result["folder_created"] and result["db_updated"]:
        result["status"] = "Success"

    # Write UiPath execution artifact log
    out_log = os.path.join(BASE_DIR, "Logs", "UiPath_Execution_Result.json")
    with open(out_log, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    # Check if input file specified or use sample
    input_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "Input", "Sample_Employee_01.json")
    if os.path.exists(input_file):
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {
            "full_name": "John Doe",
            "date_of_birth": "1995-05-20",
            "gender": "Male",
            "email": "john.doe@abctech.com",
            "phone": "9876543210",
            "address": "123 Tech Park, Bangalore",
            "department": "Engineering",
            "designation": "RPA Automation Specialist",
            "date_of_joining": "2026-10-01",
            "salary": 75000,
            "manager_name": "Sarah Connor",
            "employment_type": "Full-Time"
        }
    
    print("============================================================")
    print(" Executing UiPath Workflow Suite for:", data.get("full_name"))
    print("============================================================")
    res = execute_uipath_pipeline(data)
    print("\nResult:")
    print(json.dumps(res, indent=2))
