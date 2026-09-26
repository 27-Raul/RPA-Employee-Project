"""
test_uipath.py
==============
Test script for verifying UiPath project workflows, XAML validity, and execution.
"""

import os
import sys
import json
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UIPATH_DIR = os.path.join(BASE_DIR, "UiPath_Project")

def test_project_json():
    print("Test 1: Validating UiPath project.json ...")
    proj_path = os.path.join(UIPATH_DIR, "project.json")
    assert os.path.exists(proj_path), f"project.json missing at {proj_path}"
    with open(proj_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["main"] == "Main.xaml", "Main file should be Main.xaml"
    assert "UiPath.Excel.Activities" in data["dependencies"]
    print("✅ project.json is valid.")

def test_xaml_files():
    print("\nTest 2: Validating XAML XML structure and syntax ...")
    xaml_files = [
        "Main.xaml",
        "Workflows/Initialize_Config.xaml",
        "Workflows/Validate_Data.xaml",
        "Workflows/Generate_Employee_ID.xaml",
        "Workflows/Create_Employee_Folder.xaml",
        "Workflows/Generate_Welcome_Letter.xaml",
        "Workflows/Send_Email.xaml",
        "Workflows/Update_Excel_Database.xaml",
        "Workflows/Generate_Report.xaml"
    ]
    for xf in xaml_files:
        full_path = os.path.join(UIPATH_DIR, xf)
        assert os.path.exists(full_path), f"XAML file missing: {xf}"
        try:
            tree = ET.parse(full_path)
            root = tree.getroot()
            assert "Activity" in root.tag, f"Root element of {xf} must be Activity"
            print(f"  ✅ {xf} is well-formed XML.")
        except Exception as e:
            print(f"  ❌ Failed parsing {xf}: {e}")
            raise e

def test_runner_execution():
    print("\nTest 3: Testing UiPath Execution Pipeline ...")
    from UiPath_Project.run_uipath import execute_uipath_pipeline
    test_cand = {
        "full_name": "Kiran Kumar",
        "date_of_birth": "1994-08-12",
        "gender": "Female",
        "email": f"kiran.kumar.{os.urandom(3).hex()}@infosys.com",
        "phone": "9811223344",
        "address": "Electronic City, Bangalore",
        "department": "Engineering",
        "designation": "RPA Solution Architect",
        "date_of_joining": "2026-10-15",
        "salary": 950000,
        "manager_name": "Deepak Mehta",
        "employment_type": "Full-Time"
    }
    res = execute_uipath_pipeline(test_cand)
    print("  Pipeline Result Status:", res.get("status"))
    assert res.get("status") == "Success", f"Pipeline failed: {res.get('errors')}"
    assert res.get("employee_id") is not None, "Employee ID was not generated"
    assert res.get("folder_created") is True, "Folder was not created"
    assert res.get("letter_generated") is True, "Letter was not generated"
    assert res.get("db_updated") is True, "Database was not updated"
    print(f"✅ Onboarding successful! Generated Employee ID: {res.get('employee_id')}")

if __name__ == "__main__":
    print("============================================================")
    print("  UiPath Project & Automation Test Suite")
    print("============================================================")
    test_project_json()
    test_xaml_files()
    test_runner_execution()
    print("\n🎉 ALL UIPATH TESTS PASSED SUCCESSFULLY!")
