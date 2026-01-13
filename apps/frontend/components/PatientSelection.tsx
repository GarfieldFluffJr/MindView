"use client";

import { useState } from "react";
import ManagePatients from "./ManagePatients";
import CreateDisabledModal from "./CreateDisabledModal";
import { API_BASE_URL } from "@/lib/api";
import { isHostedSite } from "@/lib/environment";

interface PatientSelectionProps {
  onPatientSelected: (patientId: number) => void;
}

interface Patient {
  patient_id: number;
  first_name: string | null;
  case_count: number;
  file_count: number;
}

export default function PatientSelection({
  onPatientSelected,
}: PatientSelectionProps) {
  const [mode, setMode] = useState<"select" | "create" | "manage" | null>(null);
  const [searchMode, setSearchMode] = useState<"id" | "name">("id");
  const [patientId, setPatientId] = useState<string>("");
  const [patientName, setPatientName] = useState<string>("");
  const [nameSearchQuery, setNameSearchQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [createDisabledModalOpen, setCreateDisabledModalOpen] = useState(false);
  const isHosted = isHostedSite();

  const handleSearchByName = async (query: string) => {
    setNameSearchQuery(query);
    setError(null);

    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setSearching(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/patients/stats/all`);

      if (!response.ok) {
        throw new Error("Failed to fetch patients");
      }

      const patients: Patient[] = await response.json();
      const filtered = patients.filter((p) =>
        p.first_name?.toLowerCase().includes(query.toLowerCase())
      );
      setSearchResults(filtered);
    } catch (err) {
      setError("Failed to search patients. Please try again.");
    } finally {
      setSearching(false);
    }
  };

  const handleSelectExisting = async () => {
    const id = parseInt(patientId, 10);
    if (isNaN(id) || id < 0) {
      setError("Please enter a valid patient ID (0 or higher)");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Verify patient exists
      const response = await fetch(
        `${API_BASE_URL}/api/patients/${id}`
      );

      if (!response.ok) {
        if (response.status === 404) {
          setError(`Patient ${id} not found. Please check the ID or create a new patient.`);
        } else {
          setError("Failed to verify patient. Please try again.");
        }
        setLoading(false);
        return;
      }

      onPatientSelected(id);
    } catch (err) {
      setError("Failed to verify patient. Please try again.");
      setLoading(false);
    }
  };

  const handleCreateNew = async () => {
    if (!patientName.trim()) {
      setError("Please enter a patient name.");
      return;
    }

    // Show modal on hosted site instead of creating
    if (isHosted) {
      setCreateDisabledModalOpen(true);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/patients/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          first_name: patientName.trim(),
        }),
      });

      if (!response.ok) {
        setError("Failed to create patient. Please try again.");
        setLoading(false);
        return;
      }

      const patient = await response.json();
      onPatientSelected(patient.patient_id);
    } catch (err) {
      setError("Failed to create patient. Please try again.");
      setLoading(false);
    }
  };

  if (mode === null) {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Select Patient
          </h2>
          <p className="text-gray-600 mb-8 text-center">
            Choose an existing patient or create a new one
          </p>

          <div className="space-y-4">
            <button
              onClick={() => setMode("select")}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Select Existing Patient
            </button>

            <button
              onClick={() => setMode("create")}
              className="w-full bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Create New Patient
            </button>

            <button
              onClick={() => setMode("manage")}
              className="w-full bg-gray-600 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
            >
              Manage Patients
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (mode === "select") {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <button
            onClick={() => {
              setMode(null);
              setPatientId("");
              setNameSearchQuery("");
              setSearchResults([]);
              setError(null);
            }}
            className="mb-6 text-blue-600 hover:text-blue-800 flex items-center gap-2"
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
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back
          </button>

          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Select Existing Patient
          </h2>

          {/* Search mode toggle */}
          <div className="flex gap-2 mb-6">
            <button
              onClick={() => {
                setSearchMode("id");
                setNameSearchQuery("");
                setSearchResults([]);
                setError(null);
              }}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                searchMode === "id"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Search by ID
            </button>
            <button
              onClick={() => {
                setSearchMode("name");
                setPatientId("");
                setError(null);
              }}
              className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                searchMode === "name"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-700 hover:bg-gray-200"
              }`}
            >
              Search by Name
            </button>
          </div>

          <div className="space-y-4">
            {searchMode === "id" ? (
              <>
                <div>
                  <label
                    htmlFor="patient-id"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Patient ID
                  </label>
                  <input
                    id="patient-id"
                    type="number"
                    min="0"
                    value={patientId}
                    onChange={(e) => setPatientId(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !loading) {
                        handleSelectExisting();
                      }
                    }}
                    placeholder="0"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading}
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-600">{error}</p>
                  </div>
                )}

                <button
                  onClick={handleSelectExisting}
                  disabled={loading || !patientId}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
                >
                  {loading ? "Verifying..." : "Continue"}
                </button>
              </>
            ) : (
              <>
                <div>
                  <label
                    htmlFor="patient-name-search"
                    className="block text-sm font-medium text-gray-700 mb-2"
                  >
                    Patient Name
                  </label>
                  <input
                    id="patient-name-search"
                    type="text"
                    value={nameSearchQuery}
                    onChange={(e) => handleSearchByName(e.target.value)}
                    placeholder="Start typing patient name..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-600">{error}</p>
                  </div>
                )}

                {nameSearchQuery.trim() && (
                  <div className="mt-4">
                    {searching ? (
                      <div className="text-center py-4">
                        <div className="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      </div>
                    ) : searchResults.length > 0 ? (
                      <div className="space-y-2">
                        <p className="text-sm text-gray-600 mb-2">
                          Found {searchResults.length} patient(s):
                        </p>
                        {searchResults.map((patient) => (
                          <button
                            key={patient.patient_id}
                            onClick={() => onPatientSelected(patient.patient_id)}
                            className="w-full text-left px-4 py-3 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 transition-all"
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-gray-900">
                                  {patient.first_name || "No name"}
                                </p>
                                <p className="text-sm text-gray-500">
                                  ID: {patient.patient_id} • {patient.case_count} case(s) • {patient.file_count} file(s)
                                </p>
                              </div>
                              <svg
                                className="w-5 h-5 text-gray-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M9 5l7 7-7 7"
                                />
                              </svg>
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-4 text-gray-500">
                        No patients found with name "{nameSearchQuery}"
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (mode === "create") {
    return (
      <>
        <div className="max-w-md mx-auto">
          <div className="bg-white rounded-xl shadow-lg p-8">
            <button
              onClick={() => {
                setMode(null);
                setPatientName("");
                setError(null);
              }}
              className="mb-6 text-blue-600 hover:text-blue-800 flex items-center gap-2"
              disabled={loading}
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
                  d="M15 19l-7-7 7-7"
                />
              </svg>
              Back
            </button>

            <h2 className="text-2xl font-bold text-gray-900 mb-6">
              Create New Patient
            </h2>

            <div className="space-y-4">
              <div>
                <label
                  htmlFor="patient-name"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Patient Name
                </label>
                <input
                  id="patient-name"
                  type="text"
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !loading) {
                      handleCreateNew();
                    }
                  }}
                  placeholder="Enter patient name"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  A patient ID will be auto-generated
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <button
                onClick={handleCreateNew}
                disabled={loading || !patientName.trim()}
                className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
              >
                {loading ? "Creating Patient..." : "Create Patient"}
              </button>
            </div>
          </div>
        </div>

        <CreateDisabledModal
          isOpen={createDisabledModalOpen}
          onClose={() => setCreateDisabledModalOpen(false)}
          type="patient"
        />
      </>
    );
  }

  if (mode === "manage") {
    return <ManagePatients onBack={() => setMode(null)} />;
  }

  return null;
}
