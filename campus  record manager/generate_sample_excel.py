"""Generate sample students Excel file."""
import os
import openpyxl

def generate_excel():
    os.makedirs("sample_data", exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"

    # Headers
    headers = ["Roll No", "Student Name", "Department", "Email"]
    ws.append(headers)

    # Sample rows
    students = [
        ["25RBAID0201", "Kiran Verma", "Artificial Intelligence & Data Science", "kiran.v@campus.edu"],
        ["25RBAID0202", "Lavanya Sundaram", "Artificial Intelligence & Data Science", "lavanya.s@campus.edu"],
        ["25RBCSE0203", "Manish Malhotra", "Computer Science & Engineering", "manish.m@campus.edu"],
        ["25RBCSE0204", "Nandini Das", "Computer Science & Engineering", "nandini.d@campus.edu"],
        ["25RBECE0205", "Omkar Deshmukh", "Electronics & Communication", "omkar.d@campus.edu"],
        ["25RBME0206", "Priya Bhatt", "Mechanical Engineering", "priya.b@campus.edu"],
        ["25RBCIV0207", "Qasim Sheikh", "Civil Engineering", "qasim.s@campus.edu"],
        ["25RBAID0208", "Ritu Agarwal", "Artificial Intelligence & Data Science", "ritu.a@campus.edu"],
    ]

    for s in students:
        ws.append(s)

    wb.save("sample_data/sample_students.xlsx")
    print("Generated sample_data/sample_students.xlsx")

if __name__ == "__main__":
    generate_excel()
