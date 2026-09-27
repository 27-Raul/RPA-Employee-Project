"""
employee_id_gen.py
==================
RPA Module: Automatic Employee ID Generator
Reads existing EmployeeDatabase.xlsx and generates the next sequential EMP ID.
"""

import os
import re
import logging

logger = logging.getLogger("RPA_Onboarding")


def generate_employee_id(database_path: str) -> str:
    """
    Reads the EmployeeDatabase.xlsx and returns the next available Employee ID.
    Format: EMP001, EMP002, ... EMP999

    Args:
        database_path: Full path to EmployeeDatabase.xlsx

    Returns:
        New unique Employee ID string (e.g. "EMP004")
    """
    try:
        import openpyxl
        if not os.path.exists(database_path):
            logger.info("Database not found. Starting with EMP001.")
            return "EMP001"

        wb = openpyxl.load_workbook(database_path)
        ws = wb.active

        existing_ids = []
        # Skip header row (row 1), read Employee ID column (column A)
        for row in ws.iter_rows(min_row=2, values_only=True):
            emp_id = row[0]
            if emp_id and isinstance(emp_id, str):
                match = re.match(r"EMP(\d+)", emp_id.strip().upper())
                if match:
                    existing_ids.append(int(match.group(1)))

        if not existing_ids:
            return "EMP001"

        next_num = max(existing_ids) + 1
        return f"EMP{next_num:03d}"

    except Exception as e:
        logger.error(f"Error generating Employee ID: {e}")
        # Fallback: use timestamp-based ID
        import time
        fallback = f"EMP{int(time.time()) % 10000:04d}"
        logger.warning(f"Using fallback Employee ID: {fallback}")
        return fallback


def is_duplicate_employee(database_path: str, email: str, full_name: str = "") -> dict:
    """
    Checks if an employee with the same email already exists.
    NOTE: Name is NOT used for duplicate detection — multiple employees can
    share the same name in a large company. Email is the unique identifier.

    Returns:
        {"is_duplicate": True/False, "reason": "..."}
    """
    try:
        import openpyxl
        if not os.path.exists(database_path):
            return {"is_duplicate": False, "reason": ""}

        wb = openpyxl.load_workbook(database_path)
        ws = wb.active

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            # row[4] = Email column
            row_email = str(row[4]).strip().lower() if row[4] else ""
            if row_email and row_email == email.strip().lower():
                return {
                    "is_duplicate": True,
                    "reason": f"An employee with email '{email}' already exists (ID: {row[0]})."
                }

        return {"is_duplicate": False, "reason": ""}

    except Exception as e:
        logger.error(f"Error checking for duplicate employee: {e}")
        return {"is_duplicate": False, "reason": ""}
