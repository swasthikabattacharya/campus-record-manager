"""Test script for RecordManager business logic and file persistence."""
import os
import shutil
from io import BytesIO
import openpyxl
from werkzeug.datastructures import FileStorage
from manager import RecordManager

def run_tests():
    test_dir = "test_data_dir"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    manager = RecordManager(data_dir=test_dir)

    # 1. Test Seeded records
    stats = manager.get_stats()
    print("Initial stats:", stats)
    assert stats["total_students"] == 12

    # 2. Test exact search
    res = manager.search("25RBAID0002")
    assert res["type"] == "exact"
    assert res["student"]["name"] == "Swasthika"

    # 3. Test prefix search
    res_prefix = manager.search("Sw")
    assert res_prefix["type"] == "list"
    assert any(s["id"] == "25RBAID0002" for s in res_prefix["students"])

    # 4. Test empty search returns all sorted
    res_empty = manager.search("")
    assert res_empty["type"] == "list"
    assert res_empty["total"] == 12
    # Verify alphabetical sorting
    names = [s["name"].lower() for s in res_empty["students"]]
    assert names == sorted(names)

    # 5. Test adding duplicate student
    dup_res = manager.add_student("25RBAID0002", "Clone", "AI", "test@campus.edu")
    assert dup_res["success"] is False
    assert "already exists" in dup_res["message"]

    # 6. Test adding valid new student
    new_res = manager.add_student("TEST001", "Zara Williams", "Biotech", "zara@campus.edu")
    assert new_res["success"] is True

    # Check that Zara is now in list
    res_zara = manager.search("TEST001")
    assert res_zara["type"] == "exact"
    assert res_zara["student"]["name"] == "Zara Williams"

    # 7. Test file attachment
    fake_file = FileStorage(
        stream=BytesIO(b"Hello Student Document"),
        filename="notes.txt",
        content_type="text/plain"
    )
    saved_fn = manager.save_attachment("TEST001", fake_file)
    assert saved_fn.startswith("notes")
    files = manager.get_student_files("TEST001")
    assert len(files) == 1
    assert files[0]["name"] == saved_fn

    # 8. Test deleting student
    del_res = manager.delete_student("TEST001")
    assert del_res["success"] is True
    assert manager.get_student("TEST001") is None
    # Folder should be deleted
    assert not os.path.exists(os.path.join(test_dir, "files", "TEST001"))

    # 9. Test Excel bulk upload
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Roll No", "Student Name", "Department", "Email"])
    ws.append(["EXCEL101", "Kavya Rao", "Computer Science", "kavya@campus.edu"])
    ws.append(["25RBAID0002", "Duplicate Swasthika", "AI", "swas@campus.edu"])  # duplicate
    ws.append(["", "Missing ID", "Civil", "missing@campus.edu"])  # error row
    ws.append(["EXCEL102", "Rohan Mehta", "Information Technology", "rohan@campus.edu"])

    excel_io = BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)

    upload_file = FileStorage(
        stream=excel_io,
        filename="students.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    bulk_res = manager.bulk_upload(upload_file)
    print("Bulk upload result:", bulk_res)
    assert bulk_res["success"] is True
    assert bulk_res["added"] == 2
    assert bulk_res["skipped"] == 1
    assert bulk_res["errors"] == 1

    # Cleanup test dir
    shutil.rmtree(test_dir)
    print("All RecordManager tests passed successfully!")

if __name__ == "__main__":
    run_tests()
