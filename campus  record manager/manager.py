"""
Campus Record Manager - Data Storage & Business Logic.
Integrates CustomHashMap and BST with file storage and CSV persistence.
Supports:
1. Staff members (Staff ID, designation, personal details)
2. Employee members (Employee ID, role, personal details)
3. Students (Student ID / Roll No, department, personal details)
4. Permanent deletion of previous records when uploading new files.
5. Flexible file uploads without requiring rigid headers.
"""

import os
import re
import csv
import json
import shutil
import random
import stat
from datetime import datetime
from werkzeug.utils import secure_filename
import openpyxl

from structures.hash_map import CustomHashMap
from structures.bst import BST

# Helper to remove read-only attribute on Windows during deletion
def _safe_remove_readonly(action, path, exc):
    try:
        os.chmod(path, stat.S_IWRITE)
        action(path)
    except Exception:
        pass

# Safely delete a directory tree even with Windows read-only flags
def safe_rmtree(path):
    if os.path.exists(path):
        try:
            shutil.rmtree(path, onexc=_safe_remove_readonly)
        except Exception:
            shutil.rmtree(path, ignore_errors=True)

# Format file byte size into human readable string
def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


class RecordManager:
    # Initialize the record manager, directories, and data structures
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.csv_path = os.path.join(data_dir, "students.csv")
        self.files_dir = os.path.join(data_dir, "files")
        self.uploads_dir = os.path.join(data_dir, "uploads")

        # Core custom data structures
        self.hash_map = CustomHashMap(initial_capacity=16, load_factor_threshold=0.75)
        self.bst = BST()

        # Ensure required directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.files_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

        # Load records from CSV if available
        self._load_records()

    # Permanently delete all records from memory, CSV, and disk
    def clear_all_records(self):
        """Permanently wipes all existing student, staff, and employee records and their files."""
        # 1. Clear in-memory hash map and binary search tree
        self.hash_map.clear()
        self.bst.clear()

        # 2. Delete all member file folders on disk
        if os.path.exists(self.files_dir):
            safe_rmtree(self.files_dir)
        os.makedirs(self.files_dir, exist_ok=True)

        # 3. Clean uploaded files cache
        if os.path.exists(self.uploads_dir):
            safe_rmtree(self.uploads_dir)
        os.makedirs(self.uploads_dir, exist_ok=True)

        # 4. Permanently overwrite CSV storage file with empty headers
        with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Department", "Email", "Details"])
        return True

    # Get the storage folder path for a member's attached files
    def get_student_files_dir(self, student_id):
        clean_id = student_id.strip().upper()
        student_folder = os.path.join(self.files_dir, clean_id)
        os.makedirs(student_folder, exist_ok=True)
        return student_folder

    # Read and list all attached files for a member from disk
    def get_student_files(self, student_id):
        clean_id = student_id.strip().upper()
        folder = os.path.join(self.files_dir, clean_id)
        if not os.path.exists(folder):
            return []

        file_list = []
        for filename in sorted(os.listdir(folder)):
            file_path = os.path.join(folder, filename)
            if os.path.isfile(file_path):
                stat_info = os.stat(file_path)
                ext = os.path.splitext(filename)[1].lower().lstrip(".")
                file_list.append({
                    "name": filename,
                    "size": stat_info.st_size,
                    "size_str": format_file_size(stat_info.st_size),
                    "ext": ext or "file",
                    "modified": datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M")
                })
        return file_list

    # Save an uploaded file attachment preserving the original filename
    def save_attachment(self, student_id, file_storage):
        clean_id = student_id.strip().upper()
        if not file_storage or not file_storage.filename:
            return None

        # Clean filename while preserving its exact identity
        original_name = os.path.basename(file_storage.filename)
        safe_name = re.sub(r'[^A-Za-z0-9_.\- ]', '_', original_name).strip()
        if not safe_name:
            safe_name = f"attachment_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        folder = self.get_student_files_dir(clean_id)
        target_path = os.path.join(folder, safe_name)

        # Also preserve in global uploads archive
        archive_path = os.path.join(self.uploads_dir, safe_name)
        file_storage.seek(0)
        file_storage.save(archive_path)

        # Copy to member folder
        shutil.copy2(archive_path, target_path)
        return safe_name

    # Delete an individual attached file of a member
    def delete_attachment(self, student_id, filename):
        clean_id = student_id.strip().upper()
        safe_name = os.path.basename(filename)
        folder = os.path.join(self.files_dir, clean_id)
        file_path = os.path.join(folder, safe_name)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False

    # Save all current records to the CSV file
    def _save_to_csv(self):
        records = self.hash_map.values()
        temp_csv = self.csv_path + ".tmp"
        
        with open(temp_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Department", "Email", "Details"])
            for rec in records:
                details_payload = dict(rec.get("details", {}))
                # Persist type and designation into Details JSON
                details_payload["_type"] = rec.get("type", "Student")
                details_payload["_designation"] = rec.get("designation", "—")
                details_json = json.dumps(details_payload)

                writer.writerow([
                    rec.get("id", ""),
                    rec.get("name", ""),
                    rec.get("department", ""),
                    rec.get("email", ""),
                    details_json
                ])

        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        os.rename(temp_csv, self.csv_path)

    # Load records from CSV, shuffle them to keep BST balanced, and populate structures
    def _load_records(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Department", "Email", "Details"])
            return

        records = []
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers:
                for row in reader:
                    if row and row[0].strip():
                        details = {}
                        if len(row) >= 5 and row[4].strip():
                            try:
                                details = json.loads(row[4])
                            except Exception:
                                details = {}

                        rec_type = details.pop("_type", None)
                        rec_desig = details.pop("_designation", "—")

                        sid = row[0].strip().upper()
                        # Infer record type if not stored
                        if not rec_type:
                            if sid.startswith(("STF", "STAFF", "FAC")):
                                rec_type = "Staff"
                            elif sid.startswith(("EMP", "EID")):
                                rec_type = "Employee"
                            else:
                                rec_type = "Student"

                        records.append({
                            "id": sid,
                            "name": row[1].strip() if len(row) > 1 and row[1].strip() else sid,
                            "department": row[2].strip() if len(row) > 2 and row[2].strip() else "—",
                            "email": row[3].strip() if len(row) > 3 and row[3].strip() else "—",
                            "type": rec_type or "Student",
                            "designation": rec_desig or "—",
                            "details": details
                        })

        # Shuffle loaded records so sorted CSV does not degenerate BST into a line
        random.shuffle(records)

        for rec in records:
            clean_id = rec["id"]
            name = rec["name"]
            self.hash_map.put(clean_id, rec)
            self.bst.insert(name, clean_id)

    # Add or update a member record (Student, Staff, or Employee)
    def add_student(self, student_id, name=None, department=None, email=None, designation=None, record_type=None, details=None, uploaded_files=None):
        clean_id = (student_id or "").strip().upper()
        if not clean_id:
            return {"success": False, "message": "ID / Roll Number cannot be empty."}

        clean_name = (name or "").strip() or clean_id
        clean_dept = (department or "").strip() or "—"
        clean_email = (email or "").strip() or "—"
        clean_desig = (designation or "").strip() or "—"
        member_details = details if isinstance(details, dict) else {}

        # Determine record type (Staff, Employee, Student)
        clean_type = (record_type or "").strip().capitalize()
        if not clean_type or clean_type not in ["Staff", "Employee", "Student"]:
            if clean_id.startswith(("STF", "STAFF", "FAC")):
                clean_type = "Staff"
            elif clean_id.startswith(("EMP", "EID")):
                clean_type = "Employee"
            elif clean_desig and any(w in clean_desig.lower() for w in ["professor", "lecturer", "teacher", "dean", "hod", "faculty", "instructor"]):
                clean_type = "Staff"
            elif clean_desig and any(w in clean_desig.lower() for w in ["manager", "clerk", "engineer", "officer", "admin", "accountant", "security", "assistant"]):
                clean_type = "Employee"
            else:
                clean_type = "Student"

        # If record already exists, update details
        is_update = self.hash_map.contains(clean_id)
        if is_update:
            existing_record = self.hash_map.get(clean_id)
            old_name = existing_record.get("name", "")
            
            # If name changed, update BST
            if old_name.lower() != clean_name.lower():
                self.bst.delete(old_name, clean_id)
                self.bst.insert(clean_name, clean_id)

            # Preserve existing details and merge new ones
            merged_details = dict(existing_record.get("details", {}))
            merged_details.update(member_details)

            existing_record["name"] = clean_name
            existing_record["department"] = clean_dept
            existing_record["email"] = clean_email
            existing_record["type"] = clean_type
            existing_record["designation"] = clean_desig if clean_desig != "—" else existing_record.get("designation", "—")
            existing_record["details"] = merged_details

            self.hash_map.put(clean_id, existing_record)
            record = existing_record
        else:
            record = {
                "id": clean_id,
                "name": clean_name,
                "department": clean_dept,
                "email": clean_email,
                "type": clean_type,
                "designation": clean_desig,
                "details": member_details
            }
            self.hash_map.put(clean_id, record)
            self.bst.insert(clean_name, clean_id)

        # Handle file attachments if provided
        if uploaded_files:
            for file_item in uploaded_files:
                if file_item and file_item.filename:
                    self.save_attachment(clean_id, file_item)

        # Persist update to CSV
        self._save_to_csv()

        record_copy = dict(record)
        record_copy["files"] = self.get_student_files(clean_id)
        action_word = "updated" if is_update else "added"
        return {
            "success": True,
            "updated": is_update,
            "student": record_copy,
            "message": f"{clean_type} {clean_id} {action_word} successfully."
        }

    # Delete a member record, attached files folder, and update data structures and CSV
    def delete_student(self, student_id):
        clean_id = (student_id or "").strip().upper()
        record = self.hash_map.get(clean_id)

        if not record:
            return {"success": False, "message": f"Record with ID '{clean_id}' not found."}

        record_name = record["name"]
        record_type = record.get("type", "Record")

        # Remove from HashMap and BST
        self.hash_map.remove(clean_id)
        self.bst.delete(record_name, clean_id)

        # Remove member files directory on disk safely
        folder = os.path.join(self.files_dir, clean_id)
        safe_rmtree(folder)

        # Persist changes to CSV
        self._save_to_csv()
        return {"success": True, "message": f"{record_type} {clean_id} ({record_name}) deleted permanently."}

    # Retrieve full member details including attached files by ID
    def get_student(self, student_id):
        clean_id = (student_id or "").strip().upper()
        record = self.hash_map.get(clean_id)
        if not record:
            return None
        res = dict(record)
        res["files"] = self.get_student_files(clean_id)
        return res

    # Search members: exact ID returns single record; prefix returns matching names; empty returns all
    def search(self, query):
        clean_query = (query or "").strip()

        # Case 1: Empty search - return all members in alphabetical order via BST in-order traversal
        if not clean_query:
            inorder_list = self.bst.inorder()
            students = []
            for name, sid in inorder_list:
                rec = self.hash_map.get(sid)
                if rec:
                    item = dict(rec)
                    item["files_count"] = len(self.get_student_files(sid))
                    students.append(item)
            return {"type": "list", "students": students, "total": len(students)}

        # Case 2: Check if query matches exact ID (Staff ID, Employee ID, or Student ID) via Hash Map O(1)
        exact_record = self.hash_map.get(clean_query.upper())
        if exact_record:
            full_record = dict(exact_record)
            full_record["files"] = self.get_student_files(exact_record["id"])
            return {"type": "exact", "student": full_record}

        # Case 3: Name prefix search via BST
        matches = self.bst.search_prefix(clean_query)
        students = []
        for name, sid in matches:
            rec = self.hash_map.get(sid)
            if rec:
                item = dict(rec)
                item["files_count"] = len(self.get_student_files(sid))
                students.append(item)

        return {"type": "list", "students": students, "total": len(students)}

    # Parse and import any uploaded file, extracting IDs and personal details
    # When replace_existing is True (default), permanently deletes previous records!
    def bulk_upload(self, file_storage, explicit_roll_no=None, replace_existing=True):
        if not file_storage or not file_storage.filename:
            return {"success": False, "message": "No file uploaded."}

        original_filename = os.path.basename(file_storage.filename)
        safe_filename = re.sub(r'[^A-Za-z0-9_.\- ]', '_', original_filename).strip()
        
        # Save copy of the uploaded file with its filename
        archive_path = os.path.join(self.uploads_dir, safe_filename)
        file_storage.seek(0)
        file_storage.save(archive_path)

        lower_ext = os.path.splitext(original_filename)[1].lower()

        # Check if file is a spreadsheet or text table
        if lower_ext in [".csv", ".tsv", ".txt", ".xlsx", ".xls"]:
            return self._parse_and_import_tabular(archive_path, original_filename, replace_existing=replace_existing)
        elif lower_ext == ".pdf":
            return self._parse_and_import_pdf(file_storage, archive_path, safe_filename, original_filename, explicit_roll_no=explicit_roll_no, replace_existing=replace_existing)
        else:
            # File is a document (Word, image, etc.)
            return self._handle_document_upload(file_storage, archive_path, safe_filename, explicit_roll_no=explicit_roll_no, replace_existing=replace_existing)

    # Process and import tabular data for staff, employees, or students
    def _parse_and_import_tabular(self, file_path, original_filename, replace_existing=True):
        lower_ext = os.path.splitext(file_path)[1].lower()
        rows_data = []

        if lower_ext in [".csv", ".tsv", ".txt"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)
                delimiter = ","
                if "\t" in sample and sample.count("\t") > sample.count(","):
                    delimiter = "\t"
                elif ";" in sample and sample.count(";") > sample.count(","):
                    delimiter = ";"
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    if row and any(cell.strip() for cell in row):
                        rows_data.append([c.strip() for c in row])
        elif lower_ext in [".xlsx", ".xls"]:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            sheet = wb.active
            for row in sheet.iter_rows(values_only=True):
                str_row = [str(val).strip() if val is not None else "" for val in row]
                if any(str_row):
                    rows_data.append(str_row)

        if not rows_data:
            return {"success": False, "message": "Uploaded file is empty."}

        return self._import_rows_data(rows_data, original_filename, replace_existing=replace_existing)

    # Extract records from PDF files (handles table layout and student profile forms)
    def _parse_and_import_pdf(self, file_storage, archive_path, safe_filename, original_filename, explicit_roll_no=None, replace_existing=True):
        rows_data = []
        try:
            import pypdf
            reader = pypdf.PdfReader(archive_path)
            for page in reader.pages:
                text = ""
                try:
                    text = page.extract_text(extraction_mode="layout") or ""
                except Exception:
                    text = page.extract_text() or ""

                for line in text.splitlines():
                    clean_line = line.strip()
                    if not clean_line:
                        continue
                    cols = [c.strip() for c in re.split(r'\t+|\s{2,}|\|', clean_line) if c.strip()]
                    if len(cols) >= 2:
                        rows_data.append(cols)
        except Exception:
            rows_data = []

        # If table-like rows were extracted, attempt structured import
        if rows_data:
            res = self._import_rows_data(rows_data, original_filename, replace_existing=replace_existing)
            if res.get("success") and (res.get("added", 0) > 0 or res.get("updated", 0) > 0):
                return res

        # Check for Key-Value student profiles (e.g., Roll No: ..., Name: ...)
        kv_records = self._extract_key_value_records_from_pdf(archive_path)
        if kv_records:
            if replace_existing:
                self.clear_all_records()
            added = 0
            for r in kv_records:
                sid = r.get("id") or explicit_roll_no
                if sid:
                    self.add_student(
                        student_id=sid,
                        name=r.get("name", sid),
                        department=r.get("department", "—"),
                        email=r.get("email", "—"),
                        designation=r.get("designation", "—"),
                        record_type=r.get("type", "Student"),
                        details=r.get("details", {})
                    )
                    added += 1
            if added > 0:
                self._save_to_csv()
                delete_msg = " Previous records permanently deleted." if replace_existing else ""
                return {
                    "success": True,
                    "added": added,
                    "updated": 0,
                    "skipped": 0,
                    "errors": 0,
                    "replaced": replace_existing,
                    "details": [],
                    "message": f"Successfully extracted {added} record(s) from PDF '{original_filename}'.{delete_msg}"
                }

        # If no multi-student records found, fall back to single document attachment
        return self._handle_document_upload(file_storage, archive_path, safe_filename, explicit_roll_no=explicit_roll_no, replace_existing=replace_existing)

    # Extract key-value student profiles from PDF text
    def _extract_key_value_records_from_pdf(self, file_path):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                full_text += (page.extract_text() or "") + "\n"
        except Exception:
            return []

        lines = full_text.splitlines()
        current_record = {}
        records = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^([A-Za-z0-9\s/_\-]{2,30})[:\-=]\s*(.+)$', line)
            if m:
                k = m.group(1).strip()
                v = m.group(2).strip()
                k_lower = k.lower()

                is_id = any(term in k_lower for term in ['roll', 'id', 'regno', 'usn', 'htno', 'memberid'])
                if is_id and ('id' in current_record):
                    records.append(current_record)
                    current_record = {}

                if is_id:
                    current_record['id'] = v.upper()
                elif 'name' in k_lower:
                    current_record['name'] = v
                elif any(d in k_lower for d in ['dept', 'department', 'branch']):
                    current_record['department'] = v
                elif 'email' in k_lower:
                    current_record['email'] = v
                elif any(d in k_lower for d in ['desig', 'designation', 'role']):
                    current_record['designation'] = v
                else:
                    if 'details' not in current_record:
                        current_record['details'] = {}
                    current_record['details'][k] = v

        if current_record and ('id' in current_record or 'name' in current_record):
            records.append(current_record)

        return records

    # Parse and record rows extracted from spreadsheet, CSV, or PDF
    def _import_rows_data(self, rows_data, original_filename, replace_existing=True):

        # Search the first 5 rows for the table header row
        header_idx = -1
        for i, r in enumerate(rows_data[:5]):
            non_empty = [c for c in r if c]
            if len(non_empty) < 2:
                continue
            has_id = any(re.search(r'\b(staff\s*id|staffid|staff_id|faculty\s*id|employee\s*id|employeeid|empid|emp_id|empno|roll|rollno|regno|usn|htno|studentid|student_id|memberid|id)\b', c, re.I) for c in non_empty)
            has_name = any(re.search(r'\b(name|student|staff|employee|faculty|person|candidate)\b', c, re.I) for c in non_empty)
            if has_id and has_name:
                header_idx = i
                break
            elif has_id and len(non_empty) >= 3:
                header_idx = i
                break

        # Match columns by header names (case-insensitive)
        id_col = -1
        name_col = -1
        dept_col = -1
        email_col = -1
        desig_col = -1
        type_col = -1
        phone_col = -1
        extra_headers = {}

        if header_idx != -1:
            headers = rows_data[header_idx]
            data_rows = rows_data[header_idx + 1:]
            for idx, h in enumerate(headers):
                if not h:
                    continue
                # ID column
                if re.search(r'\b(staff\s*id|staffid|staff_id|faculty\s*id|employee\s*id|employeeid|empid|emp_id|empno|roll|rollno|regno|usn|htno|studentid|student_id|memberid)\b', h, re.I) and id_col == -1:
                    id_col = idx
                elif re.search(r'\b(name|staff\s*name|employee\s*name|student\s*name|full\s*name|faculty\s*name)\b', h, re.I) and name_col == -1:
                    name_col = idx
                elif re.search(r'\b(dept|department|division|branch|course|stream|faculty|school|unit)\b', h, re.I) and dept_col == -1:
                    dept_col = idx
                elif re.search(r'\b(designation|role|post|position|title|job\s*title|rank)\b', h, re.I) and desig_col == -1:
                    desig_col = idx
                elif re.search(r'\b(type|member\s*type|record\s*type|person\s*type|emp_type)\b', h, re.I) and type_col == -1:
                    type_col = idx
                elif re.search(r'\b(email|mail|e_mail|email_id)\b', h, re.I) and email_col == -1:
                    email_col = idx
                elif re.search(r'\b(phone|mobile|contact|cell|tel|phone_no|mobile_no)\b', h, re.I) and phone_col == -1:
                    phone_col = idx
                else:
                    extra_headers[idx] = h
            
            # If id_col was not matched with strict regex, check for 'id'
            if id_col == -1:
                for idx, h in enumerate(headers):
                    if re.search(r'\bid\b', h, re.I):
                        id_col = idx
                        break
        else:
            # No header row found: treat all rows as data
            data_rows = rows_data
            if len(rows_data[0]) > 1:
                col0_is_serial = all(r[0].isdigit() and len(r[0]) <= 3 for r in rows_data[:5] if r and r[0])
                col1_has_alphanum = any(re.search(r'\d', r[1]) and re.search(r'[a-zA-Z]', r[1]) for r in rows_data[:5] if len(r) > 1 and r[1])
                if col0_is_serial and col1_has_alphanum:
                    id_col = 1
                    name_col = 2 if len(rows_data[0]) > 2 else -1
                else:
                    id_col = 0
                    name_col = 1 if len(rows_data[0]) > 1 else -1
            else:
                id_col = 0
                name_col = -1

            dept_col = 2 if len(rows_data[0]) > 2 and name_col != 2 else -1
            email_col = 3 if len(rows_data[0]) > 3 else -1

        if id_col == -1:
            id_col = 0

        # CRITICAL USER REQUIREMENT:
        # "after i upload new files the previous record should delete permently"
        if replace_existing:
            self.clear_all_records()

        # Infer default category from file name or headers
        file_lower = original_filename.lower()
        default_category = None
        if "staff" in file_lower or "faculty" in file_lower:
            default_category = "Staff"
        elif "employee" in file_lower or "emp" in file_lower:
            default_category = "Employee"
        elif "student" in file_lower or "roll" in file_lower:
            default_category = "Student"

        added = 0
        updated = 0
        error_rows = 0
        details_log = []

        for row_idx, row in enumerate(data_rows, start=1):
            if not row or not any(row):
                continue

            # Extract ID candidate
            member_id = row[id_col].strip().upper() if id_col < len(row) else ""
            
            # Skip rows that are banners or repeated headers
            if re.search(r'\b(roll|sl\.?\s*no|serial|student\s*name|staff\s*name|employee\s*name|staff\s*id|employee\s*id|details|id)\b', member_id, re.I):
                continue
            if len(member_id) > 50:
                continue

            if not member_id:
                # Search row for any cell that looks like an ID
                for cell in row:
                    clean_c = cell.strip()
                    if clean_c and 3 <= len(clean_c) <= 25 and not ("@" in clean_c) and not ("," in clean_c):
                        member_id = clean_c.upper()
                        break

            if not member_id:
                error_rows += 1
                details_log.append(f"Row {row_idx}: Could not find a valid ID.")
                continue

            # Extract name
            name = row[name_col].strip() if name_col != -1 and name_col < len(row) and row[name_col].strip() else member_id
            if re.search(r'\b(student\s*name|staff\s*name|employee\s*name|name)\b', name, re.I):
                name = member_id

            # Extract department
            dept = row[dept_col].strip() if dept_col != -1 and dept_col < len(row) and row[dept_col].strip() else "—"
            
            # Extract email
            email = row[email_col].strip() if email_col != -1 and email_col < len(row) and row[email_col].strip() else "—"
            if email == "—":
                for cell in row:
                    if "@" in cell and "." in cell:
                        email = cell.strip()
                        break

            # Extract designation
            designation = row[desig_col].strip() if desig_col != -1 and desig_col < len(row) and row[desig_col].strip() else "—"
            
            # Extract phone
            phone = row[phone_col].strip() if phone_col != -1 and phone_col < len(row) and row[phone_col].strip() else ""

            # Determine member type (Staff, Employee, Student)
            row_type = row[type_col].strip().capitalize() if type_col != -1 and type_col < len(row) and row[type_col].strip() else ""
            if not row_type or row_type not in ["Staff", "Employee", "Student"]:
                if member_id.startswith(("EMP", "EID")):
                    row_type = "Employee"
                elif member_id.startswith(("STF", "STAFF", "FAC")):
                    row_type = "Staff"
                elif designation and any(w in designation.lower() for w in ["professor", "lecturer", "teacher", "dean", "hod", "faculty", "instructor"]):
                    row_type = "Staff"
                elif designation and any(w in designation.lower() for w in ["manager", "clerk", "engineer", "officer", "admin", "accountant", "security", "administrator", "developer"]):
                    row_type = "Employee"
                elif default_category:
                    row_type = default_category
                else:
                    row_type = "Student" if any(c.isdigit() for c in member_id) else "Member"

            # Collect all other columns as personal details
            extra_details = {}
            if phone:
                extra_details["Phone"] = phone
            if designation and designation != "—":
                extra_details["Designation"] = designation

            for col_i, val in enumerate(row):
                if col_i not in [id_col, name_col, dept_col, email_col, desig_col, type_col, phone_col] and val.strip():
                    h_name = extra_headers.get(col_i, f"Detail {col_i + 1}")
                    clean_h_name = re.sub(r'\s+', ' ', h_name).strip()
                    extra_details[clean_h_name] = val.strip()

            result = self.add_student(
                student_id=member_id,
                name=name,
                department=dept,
                email=email,
                designation=designation,
                record_type=row_type,
                details=extra_details
            )

            if result["success"]:
                if result.get("updated"):
                    updated += 1
                else:
                    added += 1

        self._save_to_csv()

        delete_msg = " Previous records permanently deleted." if replace_existing else ""
        return {
            "success": True,
            "added": added,
            "updated": updated,
            "skipped": 0,
            "errors": error_rows,
            "replaced": replace_existing,
            "details": details_log[:20],
            "message": f"Successfully processed '{original_filename}': {added} record(s) recorded.{delete_msg}"
        }

    # Handle document upload (single document, Word, image, etc.) and link to member
    def _handle_document_upload(self, file_storage, archive_path, safe_filename, explicit_roll_no=None, replace_existing=False):
        if replace_existing:
            self.clear_all_records()

        roll_no = (explicit_roll_no or "").strip().upper()

        # If not provided explicitly, look for ID in the filename
        if not roll_no:
            base = os.path.splitext(safe_filename)[0]
            # Check against existing IDs
            for existing_id in self.hash_map.keys():
                if existing_id in base.upper():
                    roll_no = existing_id
                    break

            if not roll_no:
                tokens = re.findall(r'[A-Za-z0-9_-]+', base)
                for t in tokens:
                    if len(t) >= 3 and any(c.isdigit() for c in t):
                        roll_no = t.upper()
                        break

        # If still no ID found, use base filename as ID
        if not roll_no:
            roll_no = re.sub(r'[^A-Za-z0-9]', '', os.path.splitext(safe_filename)[0]).upper()
            if not roll_no:
                roll_no = f"MEMBER_{datetime.now().strftime('%M%S')}"

        # Copy file into member's directory
        folder = self.get_student_files_dir(roll_no)
        dest_path = os.path.join(folder, safe_filename)
        shutil.copy2(archive_path, dest_path)

        # Create or update member record
        is_existing = self.hash_map.contains(roll_no)
        if not is_existing:
            self.add_student(student_id=roll_no, name=roll_no)

        action = "attached to existing record" if is_existing else "created new record with attachment"
        return {
            "success": True,
            "added": 0 if is_existing else 1,
            "updated": 1 if is_existing else 0,
            "student_id": roll_no,
            "filename": safe_filename,
            "message": f"File '{safe_filename}' saved and {action} ({roll_no})."
        }

    # Return system statistics including total records, staff, employees, and students
    def get_stats(self):
        total_records = len(self.hash_map)
        staff_count = sum(1 for r in self.hash_map.values() if r.get("type") == "Staff")
        employee_count = sum(1 for r in self.hash_map.values() if r.get("type") == "Employee")
        student_count = sum(1 for r in self.hash_map.values() if r.get("type") == "Student" or not r.get("type"))
        total_files = 0
        total_size = 0

        for sid in self.hash_map.keys():
            folder = os.path.join(self.files_dir, sid)
            if os.path.exists(folder):
                for f in os.listdir(folder):
                    fp = os.path.join(folder, f)
                    if os.path.isfile(fp):
                        total_files += 1
                        total_size += os.stat(fp).st_size

        return {
            "total_students": total_records,
            "total_records": total_records,
            "staff_count": staff_count,
            "employee_count": employee_count,
            "student_count": student_count,
            "capacity": self.hash_map.capacity,
            "load_factor": round(total_records / self.hash_map.capacity, 2) if self.hash_map.capacity else 0,
            "bst_nodes": self.bst.count(),
            "total_files": total_files,
            "total_storage": format_file_size(total_size)
        }
