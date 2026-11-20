# Campus Record Manager
### Fast Student Search & Interactive File Manager Using Data Structures

A lightweight, high-performance web application engineered for instant student directory search, profile management, and document storage using custom **Data Structures & Algorithms (DSA)**.

Built for the **school/university**.
Built by - Swasthika battacharya 
- **Mentor:** Dr. R. Kiran Kumar
- **Team Members:**
  - Swasthika (25RBAID0002)
  - Saritha (25RBAID0001)
  - Abdul Rahman (25RBAID0017)
  - K. Srujana (25RBAIM0065)

---......

## 🌟 Key Features

1. **Dual-Mode Instant Search:**
   - **Exact Student ID Match:** Typing an exact unique Student ID (e.g., `25RBAID0002`) immediately retrieves and displays **ONLY** that student's comprehensive profile and document files.
   - **Prefix Name Search:** Typing letters (e.g., `Sw` or `A`) performs a prefix search on the Binary Search Tree, returning all students whose names begin with that query.
   - **Empty Query:** Shows all campus students sorted in alphabetical order ($A \to Z$) via BST in-order traversal.

2. **Add Student Record (`+ Add`):**
   - Modal form supporting Student ID / Roll No, Full Name, Department, Email, and optional document attachments (PDF, Word `.docx`, Images, etc.).
   - Rejects empty IDs or duplicate IDs with clear error alerts.

3. **Bulk CSV & Excel Upload:**
   - Upload `.csv` or `.xlsx` files with multiple student records.
   - Automatically maps column headers regardless of case or format (`ID / Roll No`, `Name / Student Name`, `Department / Dept`, `Email / Email ID`).
   - Detailed summary modal showing: **Added**, **Skipped (Duplicates)**, and **Error Rows**.

4. **Multi-Format Document File Management:**
   - Attach any document file type (PDF, Word, JPEG/PNG, spreadsheets) to a student.
   - One-click file download and file deletion directly from the student's profile.
   - Upload additional files to any existing student anytime.

5. **Safe Deletion with Confirmation:**
   - "Delete" button with a confirmation modal.
   - Atomically deletes the student from the Hash Map, the BST, removes `data/files/<ID>/` from disk, and updates `data/students.csv`.

6. **Persistence Across Restarts:**
   - Records survive server restarts via `data/students.csv`.
   - Attached files are saved in `data/files/<ID>/<filename>`.
   - On startup, records are shuffled before insertion into the BST so pre-sorted CSV files never degrade the tree into a linked list chain.

---

## 🧠 Data Structures & Algorithms (DSA) Architecture

This project deliberately avoids using Python's built-in `dict` as the hash map storage, implementing both core structures from scratch:

```
                            [ USER REQUEST ]
                                   │
                                   ▼
                         [ Flask Controller ]
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
     ┌───────────────────┐                   ┌───────────────────┐
     │  Custom Hash Map  │                   │    Custom BST     │
     │ ───────────────── │                   │ ───────────────── │
     │ • Chaining        │                   │ • Sorted Names    │
     │ • Resize at 0.75  │                   │ • In-Order Walk   │
     │ • Strip & Upper   │                   │ • Prefix Pruning  │
     │ • O(1) ID Lookup  │                   │ • O(log n) Search │
     └─────────┬─────────┘                   └─────────┬─────────┘
               │                                       │
               └───────────────────┬───────────────────┘
                                   │
                                   ▼
                        [ Storage & CSV Layer ]
                        data/students.csv
                        data/files/<ID>/
```

### 1. Custom Chained Hash Map (`structures/hash_map.py`)
- **Key Normalization:** `key.strip().upper()`.
- **Hash Function:** Polynomial rolling hash $\sum (c_i \times 31^i) \pmod{\text{capacity}}$ distributing keys uniformly.
- **Collision Resolution:** Separate Chaining with custom linked list `HashNode` objects.
- **Dynamic Resizing:** When load factor $\frac{\text{size} + 1}{\text{capacity}} \ge 0.75$, the table doubles capacity and rehashes all elements in $O(n)$ amortized time.
- **Lookup Complexity:** $O(1)$ average time.

### 2. Custom Binary Search Tree (`structures/bst.py`)
- **Key:** Student Name (case-insensitive ordering).
- **Value:** Student ID (points directly to the record in the Hash Map).
- **In-Order Traversal:** Recursively visits `left -> root -> right` to yield students in sorted alphabetical order ($A \to Z$) in $O(n)$ time.
- **Prefix Search Pruning:**
  - If node name starts with prefix: visits left subtree, records match, visits right subtree.
  - If node name $<$ prefix: skips left subtree entirely and prunes search to right subtree.
  - If node name $>$ prefix: skips right subtree entirely and prunes search to left subtree.
- **Balanced Load:** Shuffles records on startup with `random.shuffle()` to guarantee an average tree height of $O(\log n)$.

### 3. Complexity Comparison Table

| Operation | Linear Scan (Folder) | Custom Hash Map | BST (Balanced) | Sorted Array |
| :--- | :---: | :---: | :---: | :---: |
| **Search by Exact ID** | $O(n)$ | **$O(1)$ average** | $O(\log n)$ | $O(\log n)$ |
| **Insert New Record** | $O(1)$ | **$O(1)$ average** | $O(\log n)$ | $O(n)$ |
| **Delete Record** | $O(n)$ | **$O(1)$ average** | $O(\log n)$ | $O(n)$ |
| **Sorted Directory Listing** | $O(n \log n)$ | Not supported | **$O(n)$** | $O(n)$ |
| **Prefix / Letter Search** | $O(n)$ | Not supported | **$O(\log n + k)$** | $O(\log n + k)$ |

---

## 🚀 Quick Start Guide

### Step 1: Clone or Navigate to Project Directory
```powershell
cd "c:\Users\swasthika\OneDrive\Desktop\New folder (2)"
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Application
```powershell
python app.py
```

### Step 4: Open in Web Browser
- **On this computer:** Open [http://localhost:5000](http://localhost:5000)
- **On Wi-Fi Network (Same router / hotspot):** Open `http://<your-ip-address>:5000` (e.g., `http://192.168.31.206:5000`).
- **Over the Internet (Share with anyone anywhere):**
  - Run `share.bat` or run:
    ```powershell
    ssh -R 80:127.0.0.1:5000 nokey@localhost.run
    ```
  - It generates a live public HTTPS link (e.g. `https://xxxx.lhr.life`) that you can send to anyone over WhatsApp, email, etc.

---

## 📁 Project Structure

```
Campus-Record-Manager/
│
├── app.py                      # Flask web server & REST API endpoints (0.0.0.0:5000)
├── manager.py                  # Storage layer, CSV sync & file operations
├── requirements.txt            # Python dependencies (flask, openpyxl)
├── README.md                   # Complete documentation & project guide
│
├── structures/                 # Core Data Structure Implementations (No dict!)
│   ├── __init__.py             # Package initializer
│   ├── hash_map.py             # Custom chained Hash Map with 0.75 load factor resize
│   └── bst.py                  # Custom Binary Search Tree with in-order & prefix search
│
├── templates/
│   └── index.html              # Responsive single-page application UI
│
├── static/
│   ├── css/
│   │   └── style.css           # Modern clean styling, card layouts, modals & badges
│   └── js/
│       └── app.js              # Real-time search, profile view, upload & delete handlers
│
├── data/                       # Persistent data directory
│   ├── students.csv            # Permanent CSV database of students
│   └── files/                  # Student documents organized by ID (data/files/<ID>/)
│
├── sample_data/                # Ready-to-use sample templates
│   ├── sample_students.csv     # Sample CSV import file
│   └── sample_students.xlsx    # Sample Excel import file
│
├── test_structures.py          # Unit tests for CustomHashMap & BST
└── test_app.py                 # 14 End-to-end integration tests for Flask APIs
```

---

## 🧪 Testing

Run the automated test suites anytime:

1. **Test Core Data Structures:**
   ```powershell
   python test_structures.py
   ```
2. **Run All 14 End-to-End Flask Integration Tests:**
   ```powershell
   python test_app.py
   ```

---

## 🎓 Viva / Presentation Guide

- **Q: Why do we use both a Hash Map and a BST together?**
  - **A:** A Hash Map provides instant $O(1)$ lookup for unique Student IDs, but has no concept of order. A BST maintains students in alphabetical order, enabling $O(n)$ sorted listing and $O(\log n)$ prefix search. Working together, they provide the best features of both data structures.
- **Q: Why are records shuffled when loading from CSV?**
  - **A:** If a CSV is already sorted alphabetically from A to Z, inserting items in order into an unbalanced BST produces a degenerate linked list with height $O(n)$. Shuffling the records beforehand produces a balanced tree with expected height $O(\log n)$.
- **Q: How does the Hash Map handle collisions?**
  - **A:** It uses separate chaining. Each bucket holds a linked list of `HashNode` items. When a collision occurs, the new node is prepended to that bucket's chain. When the load factor reaches 0.75, capacity is doubled and all keys are rehashed.
