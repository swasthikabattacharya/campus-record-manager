"""Integration and End-to-End tests for the Campus Record Manager Flask App."""
import os
import shutil
from io import BytesIO
import openpyxl
import app as app_module
from app import app
from manager import RecordManager

def run_integration_tests():
    print("Starting integration test suite with isolated test database...")
    test_data_dir = "test_run_data"
    from manager import safe_rmtree
    safe_rmtree(test_data_dir)

    # Use a fresh RecordManager instance pointing to test_data_dir
    test_manager = RecordManager(data_dir=test_data_dir)
    app_module.manager = test_manager

    client = app.test_client()

    # 1. Test homepage renders
    res = client.get("/")
    assert res.status_code == 200
    assert b"Campus Record Manager" in res.data
    print("Test 1 Passed: Homepage rendered successfully.")

    # 2. Test empty search (returns all sorted via BST)
    res = client.get("/api/search?q=")
    assert res.status_code == 200
    data = res.get_json()
    assert data["type"] == "list"
    assert data["total"] == 12
    # Verify alphabetical order
    names = [s["name"].lower() for s in data["students"]]
    assert names == sorted(names), "Names should be sorted alphabetically via BST in-order"
    print(f"Test 2 Passed: Empty search returned {data['total']} sorted students.")

    # 3. Test exact Student ID search
    res = client.get("/api/search?q=25RBAID0002")
    assert res.status_code == 200
    data = res.get_json()
    assert data["type"] == "exact"
    assert data["student"]["name"] == "Swasthika"
    assert "files" in data["student"]
    print("Test 3 Passed: Exact ID search returned single student profile.")

    # 4. Test prefix search
    res = client.get("/api/search?q=Sw")
    assert res.status_code == 200
    data = res.get_json()
    assert data["type"] == "list"
    found = [s["name"] for s in data["students"]]
    assert "Swasthika" in found
    print(f"Test 4 Passed: Prefix search 'Sw' found {found}.")

    # 5. Test Add Student with file attachment
    file_content = b"PDF mock document content for Swasthika project"
    res = client.post("/api/students", data={
        "id": "25TEST001",
        "name": "Tanvi Sharma",
        "department": "Artificial Intelligence",
        "email": "tanvi.s@campus.edu",
        "files": (BytesIO(file_content), "project_report.pdf")
    }, content_type="multipart/form-data")

    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["student"]["id"] == "25TEST001"
    assert len(data["student"]["files"]) == 1
    assert data["student"]["files"][0]["name"].startswith("project_report")
    print("Test 5 Passed: Student added with attached PDF document.")

    # 6. Test reject duplicate ID
    res_dup = client.post("/api/students", data={
        "id": "25TEST001",
        "name": "Duplicate Student",
        "department": "AI",
        "email": "dup@campus.edu"
    })
    assert res_dup.status_code == 400
    data_dup = res_dup.get_json()
    assert data_dup["success"] is False
    assert "already exists" in data_dup["message"]
    print("Test 6 Passed: Duplicate ID rejected with clear message.")

    # 7. Test reject empty ID
    res_empty_id = client.post("/api/students", data={
        "id": "   ",
        "name": "No ID Student",
        "department": "AI",
        "email": "no@campus.edu"
    })
    assert res_empty_id.status_code == 400
    data_empty_id = res_empty_id.get_json()
    assert data_empty_id["success"] is False
    assert "cannot be empty" in data_empty_id["message"]
    print("Test 7 Passed: Empty ID rejected with clear message.")

    # 8. Test attaching additional file to existing student
    res_add_file = client.post("/api/students/25TEST001/files", data={
        "files": (BytesIO(b"Word document resume bytes"), "resume.docx")
    }, content_type="multipart/form-data")
    assert res_add_file.status_code == 200
    assert len(res_add_file.get_json()["files"]) == 2
    print("Test 8 Passed: Added second attachment (Word doc) to student.")

    # 9. Test downloading attached file
    files = test_manager.get_student_files("25TEST001")
    filename = files[0]["name"]
    res_download = client.get(f"/api/students/25TEST001/files/{filename}")
    assert res_download.status_code == 200
    assert len(res_download.data) > 0
    res_download.close()
    print("Test 9 Passed: Downloaded student file successfully.")

    # 10. Test bulk upload CSV
    csv_bytes = (
        "Roll No,Student Name,Department,Email\n"
        "25BULK001,Amitabh Bachchan,AI & Data Science,amitabh@campus.edu\n"
        "25TEST001,Duplicate Person,AI,dup@campus.edu\n"  # duplicate
        ",Nameless,Mech,none@campus.edu\n"  # missing id error
    ).encode("utf-8")

    res_csv = client.post("/api/upload", data={
        "file": (BytesIO(csv_bytes), "upload.csv")
    }, content_type="multipart/form-data")
    assert res_csv.status_code == 200
    data_csv = res_csv.get_json()
    assert data_csv["added"] == 1
    assert data_csv["skipped"] == 1
    assert data_csv["errors"] == 1
    print("Test 10 Passed: CSV bulk upload handled added, skipped duplicates, and errors correctly.")

    # 11. Test bulk upload Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Name", "Department", "Email"])
    ws.append("25XLS001, Excel Student, Electronics, excel@campus.edu".split(", "))
    ws.append("25BULK001, Duplicate Excel, AI, dup@campus.edu".split(", "))  # duplicate
    excel_io = BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)

    res_xls = client.post("/api/upload", data={
        "file": (excel_io, "upload.xlsx")
    }, content_type="multipart/form-data")
    assert res_xls.status_code == 200
    data_xls = res_xls.get_json()
    assert data_xls["added"] == 1
    assert data_xls["skipped"] == 1
    print("Test 11 Passed: Excel bulk upload handled correctly.")

    # 12. Test deleting student and attached files
    student_folder = test_manager.get_student_files_dir("25TEST001")
    assert os.path.exists(student_folder)
    res_del = client.delete("/api/students/25TEST001")
    assert res_del.status_code == 200
    assert not os.path.exists(student_folder), "Student files directory should be completely removed on delete"
    assert test_manager.get_student("25TEST001") is None
    print("Test 12 Passed: Student and files deleted completely.")

    # 13. Test stats API
    res_stats = client.get("/api/stats")
    assert res_stats.status_code == 200
    stats = res_stats.get_json()
    assert stats["total_students"] >= 12
    print("Test 13 Passed: Stats API returned system details:", stats)

    # 14. Test persistence: simulate server restart by reloading RecordManager on test_data_dir
    restart_manager = RecordManager(data_dir=test_data_dir)
    assert len(restart_manager.hash_map) == stats["total_students"]
    print("Test 14 Passed: Persistence verified. Data survived restart reload!")

    # Cleanup test folder
    shutil.rmtree(test_data_dir)

    # Restore main app manager
    app_module.manager = RecordManager(data_dir="data")

    print("\n=======================================================")
    print(" ALL 14 END-TO-END INTEGRATION TESTS PASSED SUCCESSFULLY! ")
    print("=======================================================")

if __name__ == "__main__":
    run_integration_tests()
