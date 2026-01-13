"use client";

import { useState, useEffect } from "react";
import CreateCaseModal from "./CreateCaseModal";
import ConfirmModal from "./ConfirmModal";
import DeleteDisabledModal from "./DeleteDisabledModal";
import CreateDisabledModal from "./CreateDisabledModal";
import { API_BASE_URL } from "@/lib/api";
import { isHostedSite } from "@/lib/environment";

interface MedicalCase {
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

interface CaseListProps {
  patientId: number;
  onCaseSelected: (caseId: number, caseName: string) => void;
  onChangePatient: () => void;
}

export default function CaseList({
  patientId,
  onCaseSelected,
  onChangePatient,
}: CaseListProps) {
  const [cases, setCases] = useState<MedicalCase[]>([]);
  const [patientName, setPatientName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [caseToDelete, setCaseToDelete] = useState<MedicalCase | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteDisabledModalOpen, setDeleteDisabledModalOpen] = useState(false);
  const [createDisabledModalOpen, setCreateDisabledModalOpen] = useState(false);
  const isHosted = isHostedSite();

  useEffect(() => {
    fetchPatient();
    fetchCases();
  }, [patientId]);

  const fetchPatient = async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/patients/${patientId}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch patient");
      }

      const data = await response.json();
      setPatientName(data.first_name);
    } catch (err) {
      console.error("Failed to load patient name:", err);
    }
  };

  const fetchCases = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/cases/?patient_id=${patientId}`
      );

      if (!response.ok) {
        throw new Error("Failed to fetch cases");
      }

      const data = await response.json();
      setCases(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load cases");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async (caseName: string) => {
    setCreating(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/cases/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          patient_id: patientId,
          case_name: caseName,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to create case");
      }

      const newCase = await response.json();
      setCases([newCase, ...cases]);
      setCreateModalOpen(false);

      // Automatically select the newly created case
      onCaseSelected(newCase.case_id, newCase.case_name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteClick = (medicalCase: MedicalCase) => {
    if (isHosted) {
      setDeleteDisabledModalOpen(true);
      return;
    }
    setCaseToDelete(medicalCase);
    setDeleteModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!caseToDelete) return;

    setDeleting(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/cases/${patientId}/${caseToDelete.case_id}?force=true`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to delete case");
      }

      // Remove from local state
      setCases(cases.filter((c) => c.case_id !== caseToDelete.case_id));
      setDeleteModalOpen(false);
      setCaseToDelete(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete case");
    } finally {
      setDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setDeleteModalOpen(false);
    setCaseToDelete(null);
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">
              Cases for Patient {patientId}{patientName ? ` (${patientName})` : ""}
            </h2>
            <button
              onClick={onChangePatient}
              className="text-sm text-blue-600 hover:text-blue-800 mt-1"
            >
              Change Patient
            </button>
          </div>
          <button
            onClick={() => {
              if (isHosted) {
                setCreateDisabledModalOpen(true);
              } else {
                setCreateModalOpen(true);
              }
            }}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            Create New Case
          </button>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-600 mt-4">Loading cases...</p>
          </div>
        ) : cases.length === 0 ? (
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <p className="text-gray-600 mb-4">
              No cases found for this patient.
            </p>
            <button
              onClick={() => setCreateModalOpen(true)}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Create your first case
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {cases.map((medicalCase) => (
              <div
                key={medicalCase.case_id}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 hover:shadow-sm transition-all"
              >
                <div className="flex items-center justify-between">
                  <button
                    onClick={() =>
                      onCaseSelected(medicalCase.case_id, medicalCase.case_name)
                    }
                    className="flex-1 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <span className="text-blue-700 font-semibold">
                          {medicalCase.case_id}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">
                          {medicalCase.case_name}
                        </h3>
                        <p className="text-sm text-gray-500">
                          Created {new Date(medicalCase.created_at).toLocaleDateString()} • {medicalCase.file_count} file{medicalCase.file_count !== 1 ? "s" : ""}
                        </p>
                      </div>
                    </div>
                  </button>
                  <button
                    onClick={() => handleDeleteClick(medicalCase)}
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

      <CreateCaseModal
        isOpen={createModalOpen}
        patientId={patientId}
        onCreateCase={handleCreateCase}
        onCancel={() => setCreateModalOpen(false)}
        isCreating={creating}
      />

      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Case?"
        message={
          caseToDelete
            ? `Are you sure you want to delete "${caseToDelete.case_name}" (Case ID: ${caseToDelete.case_id})? This will permanently delete the case and ${caseToDelete.file_count} file${caseToDelete.file_count !== 1 ? "s" : ""}. This action cannot be undone.`
            : ""
        }
        confirmText={deleting ? "Deleting..." : "Delete"}
        cancelText="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
        isDestructive
      />

      <DeleteDisabledModal
        isOpen={deleteDisabledModalOpen}
        onClose={() => setDeleteDisabledModalOpen(false)}
      />

      <CreateDisabledModal
        isOpen={createDisabledModalOpen}
        onClose={() => setCreateDisabledModalOpen(false)}
        type="case"
      />
    </div>
  );
}
