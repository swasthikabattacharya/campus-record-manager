/**
 * Campus Record Manager - Frontend Application Logic
 * Supports real-time search, flexible file uploads for Staff, Employees & Students,
 * dynamic personal details display, permanent deletion of previous records on new upload,
 * and instant synchronization with Hash Map & BST.
 */

// Base API URL: if opened via VS Code Live Server (port 5500) or file protocol, route API requests to port 5000.
// When accessed natively on port 5000, Wi-Fi (e.g. 192.168.x.x:5000), or public tunnel (Cloudflare), use relative paths ('').
const isDevServer = (window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost') && window.location.port && window.location.port !== '5000';
const isFileProtocol = window.location.protocol === 'file:';
const API_BASE = (isDevServer || isFileProtocol) ? 'http://localhost:5000' : '';

// Application state
const state = {
    searchQuery: "",
    selectedStudent: null,
    pendingDeleteStudent: null,
    searchDebounceTimer: null
};

// DOM Element references
const elements = {
    searchInput: document.getElementById("search-input"),
    clearSearchBtn: document.getElementById("clear-search-btn"),
    contentArea: document.getElementById("content-area"),
    
    // Stats
    statTotalStudents: document.getElementById("stat-total-students"),
    statRecordsBreakdown: document.getElementById("stat-records-breakdown"),
    statLoadFactor: document.getElementById("stat-load-factor"),
    statBstNodes: document.getElementById("stat-bst-nodes"),
    statFilesCount: document.getElementById("stat-files-count"),
    statStorageSize: document.getElementById("stat-storage-size"),

    // Modals
    addModal: document.getElementById("add-modal"),
    uploadModal: document.getElementById("upload-modal"),
    deleteModal: document.getElementById("delete-modal"),

    // Buttons & Inputs for Add
    btnOpenAdd: document.getElementById("btn-open-add"),
    btnCloseAdd: document.getElementById("close-add-modal"),
    btnCancelAdd: document.getElementById("cancel-add-btn"),
    addStudentForm: document.getElementById("add-student-form"),
    addErrorBanner: document.getElementById("add-error-banner"),
    newMemberType: document.getElementById("new-member-type"),
    newMemberDesig: document.getElementById("new-member-desig"),
    newMemberPhone: document.getElementById("new-member-phone"),
    addFilesInput: document.getElementById("new-student-files"),
    addSelectedFilesList: document.getElementById("add-selected-files-list"),

    // Buttons & Inputs for Upload
    btnOpenUpload: document.getElementById("btn-open-upload"),
    btnCloseUpload: document.getElementById("close-upload-modal"),
    btnCancelUpload: document.getElementById("cancel-upload-btn"),
    confirmUploadBtn: document.getElementById("confirm-upload-btn"),
    bulkFileInput: document.getElementById("bulk-file-input"),
    bulkReplaceCheckbox: document.getElementById("bulk-replace-records"),
    bulkRollNo: document.getElementById("bulk-roll-no"),
    bulkSelectedFileName: document.getElementById("bulk-selected-file-name"),
    uploadSummaryReport: document.getElementById("upload-summary-report"),
    summaryAdded: document.getElementById("summary-added"),
    summaryUpdated: document.getElementById("summary-updated"),
    summaryErrors: document.getElementById("summary-errors"),
    summaryDetailsBox: document.getElementById("summary-details-box"),
    btnWipeAll: document.getElementById("btn-wipe-all"),

    // Delete Modal elements
    btnCloseDelete: document.getElementById("close-delete-modal"),
    btnCancelDelete: document.getElementById("cancel-delete-btn"),
    confirmDeleteBtn: document.getElementById("confirm-delete-btn"),
    deleteStudentName: document.getElementById("delete-student-name"),
    deleteStudentId: document.getElementById("delete-student-id"),

    toastContainer: document.getElementById("toast-container")
};

// Initialize application on page load
document.addEventListener("DOMContentLoaded", () => {
    initEventListeners();
    fetchStats();
    executeSearch("");
});

// Set up UI and modal event listeners
function initEventListeners() {
    // Search input typing with debounce
    elements.searchInput.addEventListener("input", (e) => {
        const query = e.target.value;
        elements.clearSearchBtn.style.display = query ? "block" : "none";
        clearTimeout(state.searchDebounceTimer);
        state.searchDebounceTimer = setTimeout(() => {
            executeSearch(query);
        }, 150);
    });

    // Clear search button
    elements.clearSearchBtn.addEventListener("click", () => {
        elements.searchInput.value = "";
        elements.clearSearchBtn.style.display = "none";
        elements.searchInput.focus();
        executeSearch("");
    });

    // Add Member modal controls
    elements.btnOpenAdd.addEventListener("click", () => openAddModal());
    elements.btnCloseAdd.addEventListener("click", () => closeAddModal());
    elements.btnCancelAdd.addEventListener("click", () => closeAddModal());
    elements.addStudentForm.addEventListener("submit", handleAddStudentSubmit);

    // Add Member files picker preview
    elements.addFilesInput.addEventListener("change", (e) => {
        updateSelectedFilesPreview(e.target.files, elements.addSelectedFilesList);
    });

    // Bulk upload modal controls
    elements.btnOpenUpload.addEventListener("click", () => openUploadModal());
    elements.btnCloseUpload.addEventListener("click", () => closeUploadModal());
    elements.btnCancelUpload.addEventListener("click", () => closeUploadModal());
    elements.confirmUploadBtn.addEventListener("click", handleBulkUploadSubmit);

    elements.bulkFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            elements.bulkSelectedFileName.textContent = `Selected: ${e.target.files[0].name} (${formatBytes(e.target.files[0].size)})`;
        } else {
            elements.bulkSelectedFileName.textContent = "";
        }
    });

    // Permanently wipe all records button
    if (elements.btnWipeAll) {
        elements.btnWipeAll.addEventListener("click", handleWipeAllRecords);
    }

    // Delete modal controls
    elements.btnCloseDelete.addEventListener("click", () => closeDeleteModal());
    elements.btnCancelDelete.addEventListener("click", () => closeDeleteModal());
    elements.confirmDeleteBtn.addEventListener("click", handleConfirmDelete);

    // Close modals when tapping outside modal dialog
    [elements.addModal, elements.uploadModal, elements.deleteModal].forEach(modal => {
        if (modal) {
            modal.addEventListener("click", (e) => {
                if (e.target === modal) {
                    modal.style.display = "none";
                }
            });
        }
    });
}

// Fetch dashboard statistics from backend
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();
        elements.statTotalStudents.textContent = data.total_students;
        if (elements.statRecordsBreakdown) {
            elements.statRecordsBreakdown.textContent = `Staff: ${data.staff_count || 0} • Employees: ${data.employee_count || 0} • Students: ${data.student_count || 0}`;
        }
        elements.statLoadFactor.textContent = `Chaining • Load: ${data.load_factor} (Cap: ${data.capacity})`;
        elements.statBstNodes.textContent = `${data.bst_nodes} Nodes in BST`;
        elements.statFilesCount.textContent = `${data.total_files} Files`;
        elements.statStorageSize.textContent = `${data.total_storage} Used`;
    } catch (err) {
        console.error("Failed to load statistics:", err);
    }
}

// Execute search query against backend
async function executeSearch(query) {
    state.searchQuery = query.trim();
    try {
        const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(state.searchQuery)}`);
        const data = await res.json();

        if (data.type === "exact") {
            // Feature 1: An exact unique ID shows ONLY that one member's complete details
            renderExactStudentProfile(data.student);
        } else {
            // Feature 1: Otherwise list members whose name starts with typed text (or all if empty)
            renderStudentDirectory(data.students || [], state.searchQuery);
        }
    } catch (err) {
        console.error("Search failed:", err);
        showToast("Search failed. Please try again.", "error");
    }
}

// Render the detailed single member profile view (Staff, Employee, or Student)
function renderExactStudentProfile(student) {
    state.selectedStudent = student;
    const initial = (student.name || student.id || "M").charAt(0).toUpperCase();
    const memberType = student.type || "Member";

    let typeBadgeClass = "badge-student";
    if (memberType === "Staff") typeBadgeClass = "badge-staff";
    else if (memberType === "Employee") typeBadgeClass = "badge-emp";

    // Render any additional dynamic fields present for this person
    let extraDetailsHtml = "";
    if (student.details && typeof student.details === "object" && Object.keys(student.details).length > 0) {
        extraDetailsHtml = Object.entries(student.details).map(([key, val]) => `
            <div class="info-item">
                <span class="info-label">${escapeHtml(key)}</span>
                <span class="info-value">${escapeHtml(String(val))}</span>
            </div>
        `).join("");
    }

    let filesHtml = "";
    if (student.files && student.files.length > 0) {
        filesHtml = `
            <div class="files-grid">
                ${student.files.map(f => `
                    <div class="file-item-card">
                        <div class="file-info-group">
                            <div class="file-ext-icon ${escapeHtml(f.ext)}">${escapeHtml(f.ext)}</div>
                            <div class="file-details">
                                <div class="file-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
                                <div class="file-meta">${f.size_str} &bull; ${f.modified}</div>
                            </div>
                        </div>
                        <div class="file-actions">
                            <a href="${API_BASE}/api/students/${encodeURIComponent(student.id)}/files/${encodeURIComponent(f.name)}" 
                               class="btn btn-secondary btn-sm" download title="Download file">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                            </a>
                            <button class="btn btn-secondary btn-sm" 
                                    onclick="handleDeleteStudentFile('${escapeHtml(student.id)}', '${escapeHtml(f.name)}')" 
                                    title="Delete file">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                `).join("")}
            </div>
        `;
    } else {
        filesHtml = `
            <div class="empty-state" style="padding: 1.5rem 0;">
                <p>No documents attached for this ${escapeHtml(memberType.toLowerCase())} yet.</p>
            </div>
        `;
    }

    elements.contentArea.innerHTML = `
        <div class="student-details-container">
            <div class="back-bar">
                <button class="btn btn-secondary btn-sm" onclick="backToDirectory()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="19" y1="12" x2="5" y2="12"></line>
                        <polyline points="12 19 5 12 12 5"></polyline>
                    </svg>
                    <span>Back to Directory</span>
                </button>
                <button class="btn btn-danger btn-sm" onclick="openDeleteModal('${escapeHtml(student.id)}', '${escapeHtml(student.name)}')">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                    <span>Delete Record</span>
                </button>
            </div>

            <div class="profile-card">
                <div class="profile-card-header">
                    <div class="profile-identity">
                        <div class="profile-avatar">${initial}</div>
                        <div>
                            <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                                <h2 class="profile-name" style="margin: 0;">${escapeHtml(student.name)}</h2>
                                <span class="${typeBadgeClass}">${escapeHtml(memberType)}</span>
                            </div>
                            <span class="profile-id-chip" style="margin-top: 0.35rem; display: inline-block;">
                                ${escapeHtml(memberType)} ID: ${escapeHtml(student.id)}
                            </span>
                        </div>
                    </div>
                </div>

                <div class="profile-info-grid">
                    <div class="info-item">
                        <span class="info-label">${escapeHtml(memberType)} ID</span>
                        <span class="info-value">${escapeHtml(student.id)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Full Name</span>
                        <span class="info-value">${escapeHtml(student.name || student.id)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Category / Role</span>
                        <span class="info-value"><span class="${typeBadgeClass}">${escapeHtml(memberType)}</span></span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Department / Division</span>
                        <span class="info-value">${escapeHtml(student.department || '—')}</span>
                    </div>
                    ${student.designation && student.designation !== '—' ? `
                        <div class="info-item">
                            <span class="info-label">Designation</span>
                            <span class="info-value">${escapeHtml(student.designation)}</span>
                        </div>
                    ` : ''}
                    <div class="info-item">
                        <span class="info-label">Email Address</span>
                        <span class="info-value">
                            ${student.email && student.email !== '—' 
                                ? `<a href="mailto:${escapeHtml(student.email)}" style="color: var(--primary);">${escapeHtml(student.email)}</a>` 
                                : '—'}
                        </span>
                    </div>
                    ${extraDetailsHtml}
                </div>

                <div class="profile-files-section">
                    <div class="files-header">
                        <div class="files-title">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
                            <span>Attached Documents (${student.files ? student.files.length : 0})</span>
                        </div>
                        <div>
                            <label class="btn btn-secondary btn-sm" style="cursor: pointer; margin: 0;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="12" y1="5" x2="12" y2="19"></line>
                                    <line x1="5" y1="12" x2="19" y2="12"></line>
                                </svg>
                                <span>+ Attach New File</span>
                                <input type="file" multiple style="display: none;" onchange="handleAttachFilesDirectly('${escapeHtml(student.id)}', this.files)">
                            </label>
                        </div>
                    </div>

                    ${filesHtml}
                </div>
            </div>
        </div>
    `;
}

// Render the directory table view
function renderStudentDirectory(students, query) {
    state.selectedStudent = null;

    if (!students || students.length === 0) {
        if (!query) {
            elements.contentArea.innerHTML = `
                <div class="directory-card">
                    <div class="empty-state" style="padding: 4rem 1.5rem; text-align: center;">
                        <div class="empty-state-icon">
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                                <line x1="12" y1="18" x2="12" y2="12"></line>
                                <line x1="9" y1="15" x2="12" y2="12"></line>
                                <line x1="15" y1="15" x2="12" y2="12"></line>
                            </svg>
                        </div>
                        <h3 style="font-size: 1.35rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-color, #0f172a);">
                            Database is Empty
                        </h3>
                        <p style="margin-bottom: 1.75rem; max-width: 480px; margin-left: auto; margin-right: auto; color: var(--text-muted, #64748b); line-height: 1.6;">
                            No default or pre-loaded records are present. Upload your records file (<strong>PDF</strong>, <strong>Excel .xlsx/.xls</strong>, or <strong>CSV</strong>) or add a member to populate the system and enable instant search.
                        </p>
                        <div style="display: flex; justify-content: center;">
                            <button class="btn btn-primary" onclick="openUploadModal()" style="padding: 0.75rem 1.75rem; font-size: 0.95rem;">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="17 8 12 3 7 8"></polyline>
                                    <line x1="12" y1="3" x2="12" y2="15"></line>
                                </svg>
                                <span>Upload Records (PDF, Excel, CSV)</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        } else {
            elements.contentArea.innerHTML = `
                <div class="directory-card">
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            </svg>
                        </div>
                        <h3>No matching records found</h3>
                        <p>No member with ID '${escapeHtml(query)}' or name starting with '${escapeHtml(query)}'.</p>
                    </div>
                </div>
            `;
        }
        return;
    }

    const titleText = query ? `Prefix Search: "${escapeHtml(query)}"` : "All Campus Members";
    const subText = query ? `Matching names in BST` : `Sorted A-Z via BST In-Order Traversal`;

    elements.contentArea.innerHTML = `
        <div class="directory-card">
            <div class="directory-header">
                <div>
                    <h2 class="directory-title">${titleText}</h2>
                    <span style="font-size: 0.8rem; color: var(--text-muted);">${subText}</span>
                </div>
                <span class="directory-badge">${students.length} Record${students.length === 1 ? "" : "s"}</span>
            </div>
            <div class="table-responsive">
                <div class="mobile-table-hint">
                    <span>👈 Swipe horizontally to view full details & actions 👉</span>
                </div>
                <table class="student-table">
                    <thead>
                        <tr>
                            <th>Member ID</th>
                            <th>Name</th>
                            <th>Category / Dept</th>
                            <th>Email & Personal Details</th>
                            <th>Documents</th>
                            <th style="text-align: right;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${students.map(s => {
                            const mType = s.type || "Member";
                            let badgeClass = "badge-student";
                            if (mType === "Staff") badgeClass = "badge-staff";
                            else if (mType === "Employee") badgeClass = "badge-emp";

                            let extraPills = "";
                            if (s.details && typeof s.details === 'object') {
                                const entries = Object.entries(s.details);
                                if (entries.length > 0) {
                                    extraPills = `<div style="margin-top: 4px; display: flex; flex-wrap: wrap; gap: 4px;">` +
                                        entries.slice(0, 2).map(([k, v]) => `
                                            <span style="font-size: 0.7rem; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; color: #475569;">
                                                <strong>${escapeHtml(k)}:</strong> ${escapeHtml(String(v))}
                                            </span>
                                        `).join('') +
                                        (entries.length > 2 ? `<span style="font-size: 0.7rem; color: #64748b;">+${entries.length - 2} more</span>` : '') +
                                        `</div>`;
                                }
                            }
                            return `
                                <tr>
                                    <td>
                                        <div style="display: flex; align-items: center; gap: 0.35rem;">
                                            <span class="badge" style="cursor: pointer;" onclick="viewStudentDetails('${escapeHtml(s.id)}')">${escapeHtml(s.id)}</span>
                                            <span class="${badgeClass}">${escapeHtml(mType)}</span>
                                        </div>
                                    </td>
                                    <td><strong style="cursor: pointer; color: var(--primary);" onclick="viewStudentDetails('${escapeHtml(s.id)}')">${escapeHtml(s.name)}</strong></td>
                                    <td>
                                        <div>${escapeHtml(s.department || '—')}</div>
                                        ${s.designation && s.designation !== '—' ? `<small style="color: var(--text-muted);">${escapeHtml(s.designation)}</small>` : ''}
                                    </td>
                                    <td>
                                        <div>${escapeHtml(s.email || '—')}</div>
                                        ${extraPills}
                                    </td>
                                    <td>
                                        <span class="badge" style="background: ${s.files_count > 0 ? '#dbeafe' : '#f1f5f9'}; color: ${s.files_count > 0 ? '#1e40af' : '#64748b'};">
                                            📎 ${s.files_count || 0}
                                        </span>
                                    </td>
                                    <td style="text-align: right;">
                                        <button class="btn btn-secondary btn-sm" onclick="viewStudentDetails('${escapeHtml(s.id)}')">View Details</button>
                                    </td>
                                </tr>
                            `;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// Fetch and open member full details
async function viewStudentDetails(studentId) {
    try {
        const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}`);
        const data = await res.json();
        if (data.success && data.student) {
            renderExactStudentProfile(data.student);
            window.scrollTo({ top: 0, behavior: "smooth" });
        } else {
            showToast("Member details not found.", "error");
        }
    } catch (err) {
        showToast("Error retrieving member details.", "error");
    }
}

// Return from single profile view back to the full directory
function backToDirectory() {
    elements.searchInput.value = "";
    elements.clearSearchBtn.style.display = "none";
    executeSearch("");
}

// Open modal to add a new member
function openAddModal() {
    elements.addErrorBanner.style.display = "none";
    elements.addErrorBanner.textContent = "";
    elements.addStudentForm.reset();
    elements.addSelectedFilesList.innerHTML = "";
    elements.addModal.style.display = "flex";
    document.getElementById("new-student-id").focus();
}

// Close add modal
function closeAddModal() {
    elements.addModal.style.display = "none";
}

// Handle submission of new or updated member form
async function handleAddStudentSubmit(e) {
    e.preventDefault();
    elements.addErrorBanner.style.display = "none";

    const formData = new FormData(elements.addStudentForm);
    const saveBtn = document.getElementById("save-student-btn");
    saveBtn.disabled = true;
    saveBtn.textContent = "Saving...";

    try {
        const res = await fetch(`${API_BASE}/api/students`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok && data.success) {
            closeAddModal();
            showToast(data.message || "Record saved successfully!", "success");
            await fetchStats();
            if (data.student) {
                renderExactStudentProfile(data.student);
            } else {
                executeSearch(formData.get("id"));
            }
        } else {
            elements.addErrorBanner.textContent = data.message || "Failed to save record.";
            elements.addErrorBanner.style.display = "block";
        }
    } catch (err) {
        console.error("Add failed:", err);
        elements.addErrorBanner.textContent = "Network error. Please make sure the server is running.";
        elements.addErrorBanner.style.display = "block";
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = "Save / Update Record";
    }
}

// Open bulk upload modal
function openUploadModal() {
    elements.bulkFileInput.value = "";
    elements.bulkSelectedFileName.textContent = "";
    if (elements.bulkRollNo) elements.bulkRollNo.value = "";
    if (elements.bulkReplaceCheckbox) elements.bulkReplaceCheckbox.checked = true;
    elements.uploadSummaryReport.style.display = "none";
    elements.summaryDetailsBox.style.display = "none";
    elements.uploadModal.style.display = "flex";
}

// Close bulk upload modal
function closeUploadModal() {
    elements.uploadModal.style.display = "none";
}

// Handle bulk upload submission with automatic replacement
async function handleBulkUploadSubmit() {
    const file = elements.bulkFileInput.files[0];
    if (!file) {
        showToast("Please select a file to upload.", "error");
        return;
    }

    const rollNo = elements.bulkRollNo ? elements.bulkRollNo.value.trim() : "";
    const shouldReplace = elements.bulkReplaceCheckbox ? elements.bulkReplaceCheckbox.checked : true;

    elements.confirmUploadBtn.disabled = true;
    elements.confirmUploadBtn.textContent = "Uploading & Processing...";

    const formData = new FormData();
    formData.append("file", file);
    formData.append("replace", shouldReplace ? "true" : "false");
    if (rollNo) {
        formData.append("roll_no", rollNo);
    }

    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();

        if (res.ok && data.success) {
            elements.uploadSummaryReport.style.display = "block";
            elements.summaryAdded.textContent = data.added || 0;
            elements.summaryUpdated.textContent = data.updated || 0;
            elements.summaryErrors.textContent = data.errors || 0;

            if (data.details && data.details.length > 0) {
                elements.summaryDetailsBox.style.display = "block";
                elements.summaryDetailsBox.innerHTML = `<strong>Details Log:</strong><br>${data.details.map(d => `• ${escapeHtml(d)}`).join("<br>")}`;
            } else {
                elements.summaryDetailsBox.style.display = "none";
            }

            const replaceNote = shouldReplace ? " (Previous records permanently deleted)" : "";
            showToast(`Success! Recorded ${data.added || 0} members.${replaceNote}`, "success");
            await fetchStats();
            executeSearch("");
        } else {
            showToast(data.message || "Failed to process file.", "error");
        }
    } catch (err) {
        console.error("Upload error:", err);
        showToast("Error uploading file. Check connection.", "error");
    } finally {
        elements.confirmUploadBtn.disabled = false;
        elements.confirmUploadBtn.textContent = "Upload & Save File";
    }
}

// Permanently delete all records from the system
async function handleWipeAllRecords() {
    if (!confirm("⚠️ Are you sure you want to PERMANENTLY delete ALL current records, staff, employees, students, and attached files from disk? This cannot be undone.")) {
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/api/records/clear`, { method: "POST" });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast("All records have been permanently deleted.", "success");
            closeUploadModal();
            await fetchStats();
            executeSearch("");
        } else {
            showToast("Failed to delete records.", "error");
        }
    } catch (err) {
        showToast("Network error while deleting records.", "error");
    }
}

// Attach files directly to an existing member
async function handleAttachFilesDirectly(studentId, fileList) {
    if (!fileList || fileList.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < fileList.length; i++) {
        formData.append("files", fileList[i]);
    }

    try {
        showToast("Uploading attachments...", "info");
        const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}/files`, {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(data.message || "Files attached successfully!", "success");
            await fetchStats();
            viewStudentDetails(studentId);
        } else {
            showToast(data.message || "Failed to attach files.", "error");
        }
    } catch (err) {
        showToast("Network error while attaching files.", "error");
    }
}

// Delete an attached file from a member
async function handleDeleteStudentFile(studentId, filename) {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
        const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}/files/${encodeURIComponent(filename)}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast("File deleted successfully.", "success");
            await fetchStats();
            viewStudentDetails(studentId);
        } else {
            showToast(data.message || "Failed to delete file.", "error");
        }
    } catch (err) {
        showToast("Error deleting file.", "error");
    }
}

// Open modal to confirm deleting a member record
function openDeleteModal(studentId, studentName) {
    state.pendingDeleteStudent = { id: studentId, name: studentName };
    elements.deleteStudentId.textContent = studentId;
    elements.deleteStudentName.textContent = studentName || studentId;
    elements.deleteModal.style.display = "flex";
}

// Close delete modal
function closeDeleteModal() {
    state.pendingDeleteStudent = null;
    elements.deleteModal.style.display = "none";
}

// Confirm and execute record deletion
async function handleConfirmDelete() {
    if (!state.pendingDeleteStudent) return;
    const studentId = state.pendingDeleteStudent.id;

    elements.confirmDeleteBtn.disabled = true;
    elements.confirmDeleteBtn.textContent = "Deleting...";

    try {
        const res = await fetch(`${API_BASE}/api/students/${encodeURIComponent(studentId)}`, {
            method: "DELETE"
        });
        const data = await res.json();

        if (res.ok && data.success) {
            closeDeleteModal();
            showToast(data.message || "Record permanently deleted.", "success");
            await fetchStats();
            backToDirectory();
        } else {
            showToast(data.message || "Failed to delete record.", "error");
        }
    } catch (err) {
        showToast("Network error while deleting record.", "error");
    } finally {
        elements.confirmDeleteBtn.disabled = false;
        elements.confirmDeleteBtn.textContent = "Yes, Delete Record";
    }
}

// Update file previews in Add Member modal
function updateSelectedFilesPreview(files, container) {
    container.innerHTML = "";
    if (!files || files.length === 0) return;

    Array.from(files).forEach(f => {
        const tag = document.createElement("div");
        tag.className = "file-preview-item";
        tag.textContent = `📎 ${f.name} (${formatBytes(f.size)})`;
        container.appendChild(tag);
    });
}

// Display toast notifications
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(10px)";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Format bytes into human readable format
function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

// Escape HTML characters to prevent XSS
function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
