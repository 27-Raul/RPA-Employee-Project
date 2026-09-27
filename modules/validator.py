"""
validator.py
============
RPA Module: Employee Data Validation
Validates all incoming employee data before processing.
"""

import re
from datetime import datetime


# ─────────────────────────────────────────────
#  Validation rules
# ─────────────────────────────────────────────

VALID_DEPARTMENTS = [
    "IT", "HR", "Finance", "Marketing", "Operations",
    "Sales", "Legal", "Administration", "Engineering", "R&D"
]

VALID_EMPLOYMENT_TYPES = ["Full-Time", "Part-Time", "Contract", "Intern"]

VALID_GENDERS = ["Male", "Female", "Other", "Prefer not to say"]


def validate_employee_data(data: dict) -> dict:
    """
    Validates a dictionary of employee data.

    Returns:
        {
          "is_valid": True/False,
          "errors": ["Error message 1", ...],
          "warnings": ["Warning 1", ...]
        }
    """
    errors = []
    warnings = []

    # ── Full Name ──────────────────────────────────────────────
    name = data.get("full_name", "").strip()
    if not name:
        errors.append("Full Name is required.")
    elif len(name) < 2:
        errors.append("Full Name must be at least 2 characters.")
    elif not re.match(r"^[A-Za-z\s\.\-']+$", name):
        errors.append("Full Name must contain only letters, spaces, dots, hyphens, or apostrophes.")

    # ── Date of Birth ──────────────────────────────────────────
    dob_str = data.get("date_of_birth", "").strip()
    if not dob_str:
        errors.append("Date of Birth is required.")
    else:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d")
            age = (datetime.now() - dob).days // 365
            if age < 18:
                errors.append("Employee must be at least 18 years old.")
            elif age > 70:
                warnings.append("Employee age appears unusually high. Please verify.")
        except ValueError:
            errors.append("Date of Birth must be in YYYY-MM-DD format.")

    # ── Gender ─────────────────────────────────────────────────
    gender = data.get("gender", "").strip()
    if not gender:
        errors.append("Gender is required.")
    elif gender not in VALID_GENDERS:
        errors.append(f"Gender must be one of: {', '.join(VALID_GENDERS)}.")

    # ── Email ──────────────────────────────────────────────────
    email = data.get("email", "").strip()
    if not email:
        errors.append("Email is required.")
    elif not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        errors.append("Email address is not valid.")

    # ── Phone ──────────────────────────────────────────────────
    phone = data.get("phone", "").strip()
    if not phone:
        errors.append("Phone Number is required.")
    else:
        digits_only = re.sub(r"[\s\-\(\)\+]", "", phone)
        if not digits_only.isdigit():
            errors.append("Phone Number must contain only digits (spaces, dashes, and parentheses allowed).")
        elif len(digits_only) < 7 or len(digits_only) > 15:
            errors.append("Phone Number must be between 7 and 15 digits.")

    # ── Address ────────────────────────────────────────────────
    address = data.get("address", "").strip()
    if not address:
        warnings.append("Address is empty. It is recommended to provide a full address.")

    # ── Department ─────────────────────────────────────────────
    department = data.get("department", "").strip()
    if not department:
        errors.append("Department is required.")

    # ── Designation ────────────────────────────────────────────
    designation = data.get("designation", "").strip()
    if not designation:
        errors.append("Designation is required.")

    # ── Date of Joining ────────────────────────────────────────
    doj_str = data.get("date_of_joining", "").strip()
    if not doj_str:
        errors.append("Date of Joining is required.")
    else:
        try:
            datetime.strptime(doj_str, "%Y-%m-%d")
        except ValueError:
            errors.append("Date of Joining must be in YYYY-MM-DD format.")

    # ── Salary ─────────────────────────────────────────────────
    salary = data.get("salary", "")
    try:
        salary_val = float(str(salary).replace(",", ""))
        if salary_val <= 0:
            errors.append("Salary must be a positive number.")
        elif salary_val < 5000:
            warnings.append("Salary is below ₹5,000. Please confirm this is correct.")
    except (ValueError, TypeError):
        errors.append("Salary must be a valid number.")

    # ── Manager Name ───────────────────────────────────────────
    manager = data.get("manager_name", "").strip()
    if not manager:
        warnings.append("Manager Name is empty. Recommended for proper record keeping.")

    # ── Employment Type ────────────────────────────────────────
    emp_type = data.get("employment_type", "").strip()
    if not emp_type:
        errors.append("Employment Type is required.")
    elif emp_type not in VALID_EMPLOYMENT_TYPES:
        errors.append(f"Employment Type must be one of: {', '.join(VALID_EMPLOYMENT_TYPES)}.")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }


def format_validation_report(result: dict, employee_name: str = "Employee") -> str:
    """Returns a human-readable validation report string."""
    lines = [f"=== Validation Report for {employee_name} ==="]
    if result["is_valid"]:
        lines.append("✅ All validations passed.")
    else:
        lines.append("❌ Validation FAILED.")
        for e in result["errors"]:
            lines.append(f"   ERROR: {e}")
    for w in result["warnings"]:
        lines.append(f"   WARNING: {w}")
    return "\n".join(lines)
