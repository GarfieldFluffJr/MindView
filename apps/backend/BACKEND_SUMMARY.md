# MindView Backend Summary

## Current Functionality

### ✅ What Works

#### 1. MongoDB Database
- **Status**: Connected to MongoDB Atlas (cloud)
- **Database**: `mindview`
- **GridFS**: Configured for file storage (bucket: `scans`)
- **Collections**: `patients`, `medical_cases`, `scan_files`

#### 2. Patient Management (`/api/patients/`)
- Create patient
- List all patients (with search and pagination)
- Get single patient by ID
- Update patient information
- Delete patient (protected if has cases)

#### 3. Medical Case Management (`/api/cases/`)
- Create medical case (must have existing patient)
- List all cases (filter by patient, status, pagination)
- Get single case by ID
- Get all files for a case
- Update case information
- Delete case (protected if has files)

#### 4. File Upload & Processing (`/api/upload`)
- Upload NIfTI files (.nii, .nii.gz)
- Upload OBJ files (.obj)
- Process NIfTI → GLB (multi-layer colored mesh)
- Process OBJ → GLB
- Get processing status
- Download processed mesh

**⚠️ Limitation**: Files saved to local storage, NOT MongoDB

#### 5. GridFS Service (Ready but not integrated)
- Upload to GridFS
- Download from GridFS
- Stream from GridFS
- Delete from GridFS
- Get file metadata

---

### ❌ What Doesn't Work

1. **Upload not connected to MongoDB** - Files stored locally, not in database
2. **No file management routes** - Can't list/download files from GridFS
3. **No patient/case file links** - Uploaded files not linked to patients/cases
4. **No frontend** - No UI or 3D viewer yet

---

## Data Flow

### Current:
```
Create Patient → MongoDB
Create Case → MongoDB
Upload File → Local Storage → Process → Local Storage
```

### Should Be:
```
Create Patient → MongoDB
Create Case → MongoDB
Upload File + patient_id + case_id → GridFS → Process → GridFS → MongoDB Record
```

---

## Test Data in Database

- **1 Patient**: P-001 (John Doe)
- **1 Case**: CASE-001 (linked to P-001)
- **0 Files**: None yet

---

## Next Steps

1. **Connect upload to MongoDB** (2-3 hours)
   - Accept patient_id and case_id in upload
   - Save files to GridFS
   - Create scan_file records

2. **File management routes** (2-3 hours)
   - List files
   - Download from GridFS
   - Delete files

3. **Build frontend** (8-12 hours)
   - Three.js 3D viewer
   - Patient/case UI
   - File upload interface

---

## Running the Server

```bash
cd /Users/louie/Desktop/Coding\ stuff/projects/MindView/apps/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

Visit: `http://localhost:8000/`

---

**Last Updated**: January 10, 2026
