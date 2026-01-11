"use client";

import { useState, useEffect, useCallback } from "react";
import ConfirmModal from "./ConfirmModal";
import TimelineViewer from "./TimelineViewer";
import {
  getTimelineInfo,
  generateTimeline,
  getTimelineStatus,
  getTimelineMeshUrl,
  TimelineMetadata,
  TimelineJobStatus,
} from "@/lib/api";

interface ScanFile {
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

interface FileListProps {
  patientId: number;
  caseId: number;
  caseName: string;
  onFileSelected: (jobId: string, filename: string) => void;
  onUploadFile: () => void;
  onChangeCase: () => void;
}

export default function FileList({
  patientId,
  caseId,
  caseName,
  onFileSelected,
  onUploadFile,
  onChangeCase,
}: FileListProps) {
  const [files, setFiles] = useState<ScanFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState<ScanFile | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Timeline state
  const [showTimeline, setShowTimeline] = useState(false);
  const [timelineData, setTimelineData] = useState<TimelineMetadata | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineGenerating, setTimelineGenerating] = useState(false);
  const [timelineProgress, setTimelineProgress] = useState(0);
  const [timelineStep, setTimelineStep] = useState<string | null>(null);

  useEffect(() => {
    fetchFiles();
  }, [patientId, caseId]);

  const fetchFiles = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/files/${patientId}/${caseId}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch files");
      }

      const data = await response.json();
      setFiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load files");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (file: ScanFile) => {
    setFileToDelete(file);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!fileToDelete) return;

    setDeleting(true);

    try {
      const response = await fetch(
        `http://localhost:8000/api/files/${patientId}/${caseId}/${fileToDelete.job_id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to delete file");
      }

      // Remove from local state
      setFiles(files.filter((f) => f.job_id !== fileToDelete.job_id));
      setDeleteModalOpen(false);
      setFileToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete file");
    } finally {
      setDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteModalOpen(false);
    setFileToDelete(null);
  };

  // Count completed NIfTI files (only NIfTI files can be morphed)
  const completedNiftiFiles = files.filter(
    (f) => f.status === "completed" &&
    (f.original_filename.endsWith(".nii") || f.original_filename.endsWith(".nii.gz"))
  );
  const canViewTimeline = completedNiftiFiles.length >= 2;

  // Poll for timeline generation status
  const pollTimelineStatus = useCallback(async (jobId: string) => {
    const poll = async () => {
      try {
        const status = await getTimelineStatus(jobId);
        setTimelineProgress(status.progress);
        setTimelineStep(status.current_step);

        if (status.status === "completed") {
          // Fetch updated timeline info and show viewer
          const info = await getTimelineInfo(patientId, caseId);
          setTimelineData(info);
          setTimelineGenerating(false);
          setShowTimeline(true);
        } else if (status.status === "failed") {
          setError(status.error || "Timeline generation failed");
          setTimelineGenerating(false);
        } else {
          // Continue polling
          setTimeout(poll, 1000);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to check timeline status");
        setTimelineGenerating(false);
      }
    };

    poll();
  }, [patientId, caseId]);

  // Handle timeline view button click
  const handleViewTimeline = async () => {
    setTimelineLoading(true);
    setError(null);

    try {
      const info = await getTimelineInfo(patientId, caseId);
      setTimelineData(info);

      if (info.has_timeline_mesh && info.timeline_job_id) {
        // Timeline already generated, show viewer
        setTimelineLoading(false);
        setShowTimeline(true);
      } else {
        // Need to generate timeline
        setTimelineLoading(false);
        setTimelineGenerating(true);
        setTimelineProgress(0);
        setTimelineStep("Starting timeline generation...");

        const job = await generateTimeline(patientId, caseId, 10);
        pollTimelineStatus(job.job_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load timeline");
      setTimelineLoading(false);
    }
  };

  // Close timeline viewer
  const handleCloseTimeline = () => {
    setShowTimeline(false);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Files for {caseName}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              Patient {patientId} | Case {caseId}
            </p>
            <button
              onClick={onChangeCase}
              className="text-sm text-blue-600 hover:text-blue-800 mt-1"
            >
              Change Case
            </button>
          </div>
          <div className="flex items-center gap-3">
            {canViewTimeline && (
              <button
                onClick={handleViewTimeline}
                disabled={timelineLoading || timelineGenerating}
                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {timelineLoading
                  ? "Loading..."
                  : timelineGenerating
                  ? `Generating (${timelineProgress}%)`
                  : "View Timeline"}
              </button>
            )}
            <button
              onClick={onUploadFile}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Upload New File
            </button>
          </div>
        </div>

        {/* Timeline generation progress */}
        {timelineGenerating && (
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-purple-800 font-medium">
                Generating Timeline...
              </span>
            </div>
            <div className="w-full bg-purple-200 rounded-full h-2 mb-1">
              <div
                className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${timelineProgress}%` }}
              />
            </div>
            <p className="text-sm text-purple-600">{timelineStep}</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600 mt-4">Loading files...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
              <svg
                className="w-8 h-8 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
            </div>
            <p className="text-gray-600 mb-4">
              No files found for this case.
            </p>
            <button
              onClick={onUploadFile}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Upload your first file
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {files.map((file) => (
              <div
                key={file.job_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <button
                    onClick={() =>
                      file.status === "completed" &&
                      onFileSelected(file.job_id, file.original_filename)
                    }
                    disabled={file.status !== "completed"}
                    className="flex-1 text-left disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          file.status === "completed"
                            ? "bg-green-100"
                            : file.status === "failed"
                            ? "bg-red-100"
                            : "bg-yellow-100"
                        }`}
                      >
                        {file.status === "completed" ? (
                          <svg
                            className="w-6 h-6 text-green-700"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        ) : file.status === "failed" ? (
                          <svg
                            className="w-6 h-6 text-red-700"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M6 18L18 6M6 6l12 12"
                            />
                          </svg>
                        ) : (
                          <div className="w-5 h-5 border-2 border-yellow-700 border-t-transparent rounded-full animate-spin" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {file.original_filename}
                        </h3>
                        <p className="text-sm text-gray-500">
                          Scan Date: {new Date(file.scan_timestamp || file.uploaded_at).toLocaleDateString()} •{" "}
                          <span className="capitalize">{file.status}</span>
                          {file.error && ` • ${file.error}`}
                        </p>
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDeleteClick(file)}
                    className="text-red-600 hover:text-red-800 font-medium text-sm px-3 py-1 rounded transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete File?"
        message={
          fileToDelete
            ? `Are you sure you want to delete "${fileToDelete.original_filename}"? This action cannot be undone.`
            : ""
        }
        confirmText={deleting ? "Deleting..." : "Delete"}
        cancelText="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
        isDestructive
      />

      {/* Timeline Viewer */}
      {showTimeline && timelineData && timelineData.timeline_job_id && (
        <TimelineViewer
          patientId={patientId}
          caseId={caseId}
          scans={timelineData.scans}
          meshUrl={getTimelineMeshUrl(timelineData.timeline_job_id)}
          timelineJobId={timelineData.timeline_job_id}
          onClose={handleCloseTimeline}
        />
      )}
    </div>
  );
}
