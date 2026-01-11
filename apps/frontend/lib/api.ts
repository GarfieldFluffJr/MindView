const API_BASE_URL = "http://localhost:8000";

export interface UploadResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface StatusResponse {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  mesh_url: string | null;
  error: string | null;
}

export interface RegionInfo {
  name: string;
  label: string;
  labelId: number;
  color: [number, number, number];
  category: string;
  opacity: number;
  defaultVisible: boolean;
  vertexCount?: number;
  faceCount?: number;
}

export interface MeshMetadata {
  regions: RegionInfo[];
  has_tumor: boolean;
  total_regions: number;
  segmentation_method: string;
}

export async function uploadFile(
  file: File,
  patientId: number,
  caseId: number,
  scanDate?: string
): Promise<UploadResponse> {

  const formData = new FormData();
  formData.append("file", file);

  let url = `${API_BASE_URL}/api/upload?patient_id=${patientId}&case_id=${caseId}`;
  if (scanDate) {
    url += `&scan_date=${encodeURIComponent(scanDate)}`;
  }

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Upload failed");
  }

  return response.json();
}

export async function getStatus(jobId: string): Promise<StatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get status");
  }

  return response.json();
}

export function getMeshUrl(jobId: string): string {
  return `${API_BASE_URL}/api/mesh/${jobId}`;
}

export async function getMetadata(jobId: string): Promise<MeshMetadata> {
  const response = await fetch(`${API_BASE_URL}/api/mesh/${jobId}/metadata`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get metadata");
export interface PatientResponse {
  patient_id: number;
  first_name: string | null;
  last_name: string | null;
  date_of_birth: string | null;
  gender: string | null;
  medical_record_number: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
}

export async function createPatient(): Promise<PatientResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create patient");
  }

  return response.json();
}

export async function getPatient(patientId: number): Promise<PatientResponse> {
  const response = await fetch(`${API_BASE_URL}/api/patients/${patientId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Patient ${patientId} not found`);
    }
    const error = await response.json();
    throw new Error(error.detail || "Failed to get patient");
  }

  return response.json();
}

export interface PatientWithStats extends PatientResponse {
  case_count: number;
  file_count: number;
}

export async function getPatientsWithStats(): Promise<PatientWithStats[]> {
  const response = await fetch(`${API_BASE_URL}/api/patients/stats/all`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get patients with stats");
  }

  return response.json();
}

export async function deletePatient(patientId: number, force: boolean = false): Promise<void> {
  const url = `${API_BASE_URL}/api/patients/${patientId}${force ? "?force=true" : ""}`;
  const response = await fetch(url, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete patient");
  }
}

export interface MedicalCaseResponse {
  case_id: number;
  patient_id: number;
  case_name: string;
  diagnosis: string | null;
  doctor_notes: string | null;
  created_by: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  file_count: number;
}

export async function getCasesForPatient(patientId: number): Promise<MedicalCaseResponse[]> {
  const response = await fetch(`${API_BASE_URL}/api/cases/?patient_id=${patientId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get cases");
  }

  return response.json();
}

export interface CreateCaseRequest {
  patient_id: number;
  case_name: string;
  diagnosis?: string;
  doctor_notes?: string;
}

export async function createCase(caseData: CreateCaseRequest): Promise<MedicalCaseResponse> {
  const response = await fetch(`${API_BASE_URL}/api/cases/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(caseData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to create case");
  }

  return response.json();
}

export async function deleteCase(
  patientId: number,
  caseId: number,
  force: boolean = false
): Promise<void> {
  const url = `${API_BASE_URL}/api/cases/${patientId}/${caseId}${force ? "?force=true" : ""}`;
  const response = await fetch(url, {
    method: "DELETE",
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete case");
  }
}

export interface ScanFileResponse {
  job_id: string;
  file_id: string;
  case_id: number;
  patient_id: number;
  original_filename: string;
  status: string;
  progress: number;
  mesh_url: string | null;
  original_url: string | null;
  error: string | null;
  uploaded_at: string;
  scan_timestamp: string;
  doctor_notes: string | null;
  metadata: Record<string, unknown>;
}

export async function getFilesForCase(
  patientId: number,
  caseId: number
): Promise<ScanFileResponse[]> {
  const response = await fetch(`${API_BASE_URL}/api/files/${patientId}/${caseId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get files");
  }

  return response.json();
}

export async function deleteFile(
  patientId: number,
  caseId: number,
  jobId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/files/${patientId}/${caseId}/${jobId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete file");
  }
}
