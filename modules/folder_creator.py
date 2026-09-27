"""
folder_creator.py
=================
RPA Module: Employee Folder Creator
Creates the standard folder structure for each new employee.
"""

import os
import logging

logger = logging.getLogger("RPA_Onboarding")

# Sub-folders created inside each employee's root folder
EMPLOYEE_SUBFOLDERS = [
    "Personal_Documents",
    "Employment_Documents",
    "Generated_Documents",
    "Generated_Documents/Welcome_Letter",
    "Generated_Documents/ID_Card",
]


def sanitize_name(name: str) -> str:
    """Removes characters that are invalid in folder names on Windows/Linux."""
    invalid_chars = r'\/:*?"<>|'
    for ch in invalid_chars:
        name = name.replace(ch, "")
    return name.strip().replace(" ", "_")


def create_employee_folder(employee_root: str, employee_id: str, full_name: str) -> dict:
    """
    Creates the full folder structure for a new employee.

    Example structure:
        Employees/
          EMP001_John_Doe/
            Personal_Documents/
            Employment_Documents/
            Generated_Documents/
              Welcome_Letter/
              ID_Card/

    Args:
        employee_root: Root folder where all employee folders live (e.g. "Employees")
        employee_id:   e.g. "EMP001"
        full_name:     e.g. "John Doe"

    Returns:
        {
          "success": True/False,
          "folder_path": "...",
          "sub_folders": [...],
          "error": "..."
        }
    """
    try:
        safe_name   = sanitize_name(full_name)
        folder_name = f"{employee_id}_{safe_name}"
        folder_path = os.path.abspath(os.path.join(employee_root, folder_name))

        if os.path.exists(folder_path):
            logger.warning(f"Employee folder already exists: {folder_path}")
            return {
                "success": True,
                "folder_path": folder_path,
                "sub_folders": [],
                "error": None
            }

        os.makedirs(folder_path, exist_ok=True)
        logger.info(f"Created employee root folder: {folder_path}")

        created_subs = []
        for sub in EMPLOYEE_SUBFOLDERS:
            sub_path = os.path.join(folder_path, sub)
            os.makedirs(sub_path, exist_ok=True)
            created_subs.append(sub_path)

        logger.info(f"Created {len(created_subs)} sub-folders for {employee_id}")

        return {
            "success": True,
            "folder_path": folder_path,
            "sub_folders": created_subs,
            "error": None
        }

    except PermissionError as e:
        msg = f"Permission denied while creating folder for {employee_id}: {e}"
        logger.error(msg)
        return {"success": False, "folder_path": "", "sub_folders": [], "error": msg}

    except Exception as e:
        msg = f"Unexpected error creating folder for {employee_id}: {e}"
        logger.error(msg)
        return {"success": False, "folder_path": "", "sub_folders": [], "error": msg}


def get_employee_folder_path(employee_root: str, employee_id: str, full_name: str) -> str:
    """Returns the expected folder path for an employee (without creating it)."""
    safe_name   = sanitize_name(full_name)
    folder_name = f"{employee_id}_{safe_name}"
    return os.path.abspath(os.path.join(employee_root, folder_name))


def get_generated_docs_path(employee_folder: str) -> str:
    return os.path.join(employee_folder, "Generated_Documents")


def get_welcome_letter_path(employee_folder: str) -> str:
    return os.path.join(employee_folder, "Generated_Documents", "Welcome_Letter")


def get_id_card_path(employee_folder: str) -> str:
    return os.path.join(employee_folder, "Generated_Documents", "ID_Card")
