export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export interface MultiModalFiles {
  t1: File;
  t1ce: File;
  t2: File;
  flair: File;
}

export async function uploadMultiModalFiles(
  files: MultiModalFiles,
  patientId: number,
  caseId: number,
  scanDate?: string
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("t1", files.t1);
  formData.append("t1ce", files.t1ce);
  formData.append("t2", files.t2);
  formData.append("flair", files.flair);

  let url = `${API_BASE_URL}/api/upload-multimodal?patient_id=${patientId}&case_id=${caseId}`;
  if (scanDate) {
    url += `&scan_date=${encodeURIComponent(scanDate)}`;
  }

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Multi-modal upload failed");
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
  }

  return response.json();
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

// Timeline API types
export interface TimelineScanInfo {
  job_id: string;
  scan_timestamp: string;
  original_filename: string;
  index: number;
}

export interface TimelineMetadata {
  patient_id: number;
  case_id: number;
  scan_count: number;
  scans: TimelineScanInfo[];
  has_timeline_mesh: boolean;
  timeline_job_id: string | null;
  timeline_status: string | null;
}

export interface TimelineJobStatus {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  current_step: string | null;
  mesh_url: string | null;
  error: string | null;
  total_frames: number | null;
  frames_generated: number | null;
}

// Helper to extract error message from FastAPI error responses
function extractErrorMessage(error: unknown, defaultMsg: string): string {
  if (!error || typeof error !== 'object') return defaultMsg;
  const err = error as { detail?: unknown };
  if (typeof err.detail === 'string') return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((e: { msg?: string }) => e.msg || '').filter(Boolean).join(', ') || defaultMsg;
  }
  return defaultMsg;
}

export async function getTimelineInfo(
  patientId: number,
  caseId: number
): Promise<TimelineMetadata> {
  // Ensure we have valid numbers
  const pid = Number(patientId);
  const cid = Number(caseId);
  if (isNaN(pid) || isNaN(cid)) {
    throw new Error("Invalid patient or case ID");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/timeline/${pid}/${cid}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to get timeline info"));
  }

  return response.json();
}

export async function generateTimeline(
  patientId: number,
  caseId: number,
  framesBetweenScans: number = 10
): Promise<TimelineJobStatus> {
  // Ensure we have valid numbers
  const pid = Number(patientId);
  const cid = Number(caseId);
  if (isNaN(pid) || isNaN(cid)) {
    throw new Error("Invalid patient or case ID");
  }

  const response = await fetch(
    `${API_BASE_URL}/api/timeline/${pid}/${cid}/generate`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ frames_between_scans: framesBetweenScans }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to generate timeline"));
  }

  return response.json();
}

export async function getTimelineStatus(
  jobId: string
): Promise<TimelineJobStatus> {
  const response = await fetch(`${API_BASE_URL}/api/timeline/status/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to get timeline status"));
  }

  return response.json();
}

export function getTimelineMeshUrl(jobId: string): string {
  return `${API_BASE_URL}/api/timeline/mesh/${jobId}`;
}

export function getTimelineMorphDataUrl(jobId: string): string {
  return `${API_BASE_URL}/api/timeline/mesh/${jobId}/morphs`;
}

// Notes API types
export interface NoteResponse {
  note_id: string;
  file_id: string;
  patient_id: number;
  case_id: number;
  content: string;
  doctor_name: string;
  color: string;
  created_at: string;
}

export interface CreateNoteRequest {
  content: string;
  doctor_name?: string;
}

export async function getNotesForFile(
  patientId: number,
  caseId: number,
  fileId: string
): Promise<NoteResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/api/notes/${patientId}/${caseId}/${fileId}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to get notes"));
  }

  return response.json();
}

export async function createNote(
  patientId: number,
  caseId: number,
  fileId: string,
  noteData: CreateNoteRequest
): Promise<NoteResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/notes/${patientId}/${caseId}/${fileId}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(noteData),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to create note"));
  }

  return response.json();
}

export async function deleteNote(
  patientId: number,
  caseId: number,
  fileId: string,
  noteId: string
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/notes/${patientId}/${caseId}/${fileId}/${noteId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to delete note"));
  }
}

// Feedback API types
export interface FeedbackMessageResponse {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface FeedbackMetrics {
  has_tumor: boolean;
  scan_count?: number;
  tumor_scan_count?: number;
  latest_metrics?: {
    total_lesion_volume_mm3?: number;
    active_enhancing_volume_mm3?: number;
    necrotic_core_volume_mm3?: number;
    edema_volume_mm3?: number;
    midline_shift_mm?: number;
    infiltration_index?: number;
  };
  progression?: {
    initial_volume_mm3: number;
    current_volume_mm3: number;
    absolute_change_mm3: number;
    percent_change: number;
    trend: "increasing" | "decreasing" | "stable";
  };
}

export interface FeedbackSessionResponse {
  session_id: string;
  patient_id: number;
  case_id: number;
  summary: string | null;
  metrics: FeedbackMetrics | null;
  scan_count: number;
  messages: FeedbackMessageResponse[];
  created_at: string;
  updated_at: string;
}

export interface GenerateSummaryResponse {
  session_id: string;
  summary: string;
  metrics: FeedbackMetrics;
  message: string;
}

export interface ChatResponse {
  user_message: FeedbackMessageResponse;
  assistant_message: FeedbackMessageResponse;
}

export async function getFeedbackSession(
  patientId: number,
  caseId: number
): Promise<FeedbackSessionResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/feedback/${patientId}/${caseId}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to get feedback session"));
  }

  return response.json();
}

export async function generateCaseSummary(
  patientId: number,
  caseId: number
): Promise<GenerateSummaryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/feedback/${patientId}/${caseId}/generate`,
    {
      method: "POST",
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to generate summary"));
  }

  return response.json();
}

export async function sendFeedbackMessage(
  patientId: number,
  caseId: number,
  content: string
): Promise<ChatResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/feedback/${patientId}/${caseId}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to send message"));
  }

  return response.json();
}

export async function clearFeedbackSession(
  patientId: number,
  caseId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/feedback/${patientId}/${caseId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(extractErrorMessage(error, "Failed to clear feedback session"));
  }
}
