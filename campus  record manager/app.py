"""
Campus Record Manager - Flask Web Application Server.
Provides RESTful APIs for searching, adding, uploading, viewing, and deleting student records.
Hosts the web application on 0.0.0.0:5000.
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from manager import RecordManager

app = Flask(__name__)
# Set maximum upload size to 64 Megabytes
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

# Enable CORS for all incoming requests (supports VS Code Live Server on port 5500, etc.)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

# Handle pre-flight OPTIONS requests for CORS
@app.route("/api/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    return "", 200

# Initialize RecordManager holding data structures and file manager
manager = RecordManager(data_dir="data")

# Serve the single-page frontend application
@app.route("/")
def index():
    return render_template("index.html")

# Search students by exact ID or name prefix, or return all sorted students
@app.route("/api/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    result = manager.search(query)
    return jsonify(result)

# Retrieve full details and attached files for a single student by ID
@app.route("/api/students/<student_id>", methods=["GET"])
def get_student(student_id):
    student = manager.get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404
    return jsonify({"success": True, "student": student})

# Add a new record (Student, Staff, or Employee) with optional file attachments
@app.route("/api/students", methods=["POST"])
def add_student():
    student_id = request.form.get("id", "").strip()
    name = request.form.get("name", "").strip()
    department = request.form.get("department", "").strip()
    email = request.form.get("email", "").strip()
    designation = request.form.get("designation", "").strip()
    record_type = request.form.get("type", "").strip()
    phone = request.form.get("phone", "").strip()
    files = request.files.getlist("files")

    details = {}
    if phone:
        details["Phone"] = phone

    result = manager.add_student(
        student_id=student_id,
        name=name,
        department=department,
        email=email,
        designation=designation,
        record_type=record_type,
        details=details,
        uploaded_files=files
    )

    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

# Upload additional attached files for an existing student
@app.route("/api/students/<student_id>/files", methods=["POST"])
def upload_student_files(student_id):
    student = manager.get_student(student_id)
    if not student:
        return jsonify({"success": False, "message": "Student not found."}), 404

    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"success": False, "message": "No files selected."}), 400

    saved_files = []
    for f in files:
        if f and f.filename:
            fn = manager.save_attachment(student_id, f)
            if fn:
                saved_files.append(fn)

    updated_files = manager.get_student_files(student_id)
    return jsonify({
        "success": True,
        "message": f"Successfully attached {len(saved_files)} file(s).",
        "files": updated_files
    })

# Download or view an attached file for a student
@app.route("/api/students/<student_id>/files/<filename>", methods=["GET"])
def download_student_file(student_id, filename):
    folder = manager.get_student_files_dir(student_id)
    file_path = os.path.join(folder, filename)
    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found."}), 404
    return send_from_directory(folder, filename, as_attachment=True)

# Delete an individual attached file from a student
@app.route("/api/students/<student_id>/files/<filename>", methods=["DELETE"])
def delete_student_file(student_id, filename):
    success = manager.delete_attachment(student_id, filename)
    if success:
        return jsonify({"success": True, "message": "File deleted successfully."})
    return jsonify({"success": False, "message": "File could not be found or deleted."}), 404

# Delete a student record and all their attached files
@app.route("/api/students/<student_id>", methods=["DELETE"])
def delete_student(student_id):
    result = manager.delete_student(student_id)
    status_code = 200 if result.get("success") else 404
    return jsonify(result), status_code

# Upload any file (CSV, Excel, PDF, Image, Word) and parse or attach it
# Automatically replaces previous records permanently when a new records file is uploaded
@app.route("/api/upload", methods=["POST"])
def bulk_upload():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    file = request.files["file"]
    roll_no = request.form.get("roll_no", "").strip()
    replace_raw = request.form.get("replace", "true").strip().lower()
    replace_existing = replace_raw in ["true", "1", "yes"]

    result = manager.bulk_upload(file, explicit_roll_no=roll_no, replace_existing=replace_existing)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code

# Permanently clear all records from the system
@app.route("/api/records/clear", methods=["POST", "DELETE"])
def clear_records():
    manager.clear_all_records()
    return jsonify({
        "success": True,
        "message": "All previous records and files have been permanently deleted."
    })

# Return system statistics for the dashboard
@app.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(manager.get_stats())

# Download sample template in CSV or Excel format
@app.route("/api/sample/<fmt>", methods=["GET"])
def download_sample(fmt):
    if fmt == "staff":
        sample_path = os.path.join("sample_data", "sample_staff.csv")
        return send_file(sample_path, as_attachment=True, download_name="sample_staff.csv")
    elif fmt == "employees":
        sample_path = os.path.join("sample_data", "sample_employees.csv")
        return send_file(sample_path, as_attachment=True, download_name="sample_employees.csv")
    elif fmt == "csv":
        sample_path = os.path.join("sample_data", "sample_students.csv")
        return send_file(sample_path, as_attachment=True, download_name="sample_students.csv")
    elif fmt == "xlsx":
        sample_path = os.path.join("sample_data", "sample_students.xlsx")
        return send_file(sample_path, as_attachment=True, download_name="sample_students.xlsx")
    return jsonify({"success": False, "message": "Invalid format requested."}), 400

# Start Flask server on 0.0.0.0:5000
if __name__ == "__main__":
    print("=================================================================")
    print(" Campus Record Manager is starting...")
    print(" Running locally on: http://localhost:5000")
    print(" Running on Wi-Fi network: http://0.0.0.0:5000")
    print("=================================================================")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
