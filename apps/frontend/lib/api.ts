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

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
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
