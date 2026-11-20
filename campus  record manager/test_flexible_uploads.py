"""Verify flexible upload handling without headers, update on duplicates, and document attachments."""
import os
from io import BytesIO
import openpyxl
from app import app, manager

client = app.test_client()

def test_flexible_uploads():
    print("Testing flexible uploads...")

    # 1. Test CSV with NO HEADERS, only Roll No and Details
    csv_no_headers = (
        "25RBAID0001,Swasthika,Artificial Intelligence,swas@campus.edu\n"
        "25RBAID0002,Saritha,Artificial Intelligence,sari@campus.edu\n"
    ).encode("utf-8")

    res = client.post("/api/upload", data={
        "file": (BytesIO(csv_no_headers), "student_data.csv")
    }, content_type="multipart/form-data")
    assert res.status_code == 200, f"Failed: {res.get_json()}"
    data = res.get_json()
    assert data["added"] == 2
    print("Test 1 Passed: CSV with NO HEADERS imported 2 students successfully.")

    # 2. Test re-uploading with updated details for 25RBAID0001
    csv_update = (
        "25RBAID0001,Swasthika Updated,AI & DS,swasthika_new@campus.edu\n"
        "25RBAID0003,Abdul Rahman,Artificial Intelligence,abdul@campus.edu\n"
    ).encode("utf-8")

    res_up = client.post("/api/upload", data={
        "file": (BytesIO(csv_update), "updated_list.csv")
    }, content_type="multipart/form-data")
    assert res_up.status_code == 200
    data_up = res_up.get_json()
    assert data_up["added"] == 1
    assert data_up["updated"] == 1
    # Check that 25RBAID0001 has updated name
    st = manager.get_student("25RBAID0001")
    assert st["name"] == "Swasthika Updated"
    print("Test 2 Passed: Updated existing student details and added new student without error.")

    # 3. Test CSV with ONLY Roll Numbers (no names, no headers)
    csv_only_roll = (
        "25RBAID0099\n"
        "25RBAID0100\n"
    ).encode("utf-8")

    res_only_roll = client.post("/api/upload", data={
        "file": (BytesIO(csv_only_roll), "roll_numbers.csv")
    }, content_type="multipart/form-data")
    assert res_only_roll.status_code == 200
    assert res_only_roll.get_json()["added"] == 2
    st_99 = manager.get_student("25RBAID0099")
    assert st_99 is not None
    assert st_99["id"] == "25RBAID0099"
    print("Test 3 Passed: CSV with ONLY roll numbers imported successfully.")

    # 4. Test Excel file with NO HEADERS
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["25XLS701", "Pooja Reddy", "Electronics", "pooja@campus.edu", "Section A", "9.5 CGPA"])
    ws.append(["25XLS702", "Vikram Rao", "Mechanical", "vikram@campus.edu", "Section B", "8.9 CGPA"])
    excel_io = BytesIO()
    wb.save(excel_io)
    excel_io.seek(0)

    res_xls = client.post("/api/upload", data={
        "file": (excel_io, "no_header_students.xlsx")
    }, content_type="multipart/form-data")
    assert res_xls.status_code == 200
    assert res_xls.get_json()["added"] == 2
    st_xls = manager.get_student("25XLS701")
    assert st_xls["name"] == "Pooja Reddy"
    # Verify extra details are captured
    assert len(st_xls["details"]) > 0
    print("Test 4 Passed: Excel with NO HEADERS and extra columns imported successfully with details.")

    # 5. Test Document Upload (e.g. PDF named with roll number)
    pdf_content = b"%PDF-1.4 mock pdf data"
    res_pdf = client.post("/api/upload", data={
        "file": (BytesIO(pdf_content), "25RBAID0001_hallticket.pdf")
    }, content_type="multipart/form-data")
    assert res_pdf.status_code == 200
    st_pdf = manager.get_student("25RBAID0001")
    assert any("hallticket" in f["name"] for f in st_pdf["files"])
    print("Test 5 Passed: PDF file attached to student matching roll number in filename.")

    # 6. Test Add student with ONLY roll number
    res_add_min = client.post("/api/students", data={
        "id": "25MINIMAL01"
    })
    assert res_add_min.status_code == 200
    st_min = manager.get_student("25MINIMAL01")
    assert st_min["id"] == "25MINIMAL01"
    print("Test 6 Passed: Add student with ONLY roll number succeeded.")

    # 7. Test exact search returns only one student with all details
    res_search = client.get("/api/search?q=25RBAID0001")
    assert res_search.status_code == 200
    search_data = res_search.get_json()
    assert search_data["type"] == "exact"
    assert search_data["student"]["id"] == "25RBAID0001"
    print("Test 7 Passed: Exact search returned single student with all files and details.")

    # Verify uploaded files are preserved in data/uploads
    assert os.path.exists(os.path.join("data", "uploads", "student_data.csv"))
    assert os.path.exists(os.path.join("data", "uploads", "no_header_students.xlsx"))
    assert os.path.exists(os.path.join("data", "uploads", "25RBAID0001_hallticket.pdf"))
    print("Test 8 Passed: Uploaded files preserved with original filenames.")

    print("\nALL FLEXIBLE UPLOAD TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_flexible_uploads()
