"use client";

import { useState } from "react";
import ManagePatients from "./ManagePatients";

interface PatientSelectionProps {
  onPatientSelected: (patientId: number) => void;
}

export default function PatientSelection({
  onPatientSelected,
}: PatientSelectionProps) {
  const [mode, setMode] = useState<"select" | "create" | "manage" | null>(null);
  const [patientId, setPatientId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
        `http://localhost:8000/api/patients/${id}`
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
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/patients/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
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
            Enter Patient ID
          </h2>

          <div className="space-y-4">
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
          </div>
        </div>
      </div>
    );
  }

  if (mode === "create") {
    return (
      <div className="max-w-md mx-auto">
        <div className="bg-white rounded-xl shadow-lg p-8">
          <button
            onClick={() => {
              setMode(null);
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

          <p className="text-gray-600 mb-6">
            A new patient will be created with an auto-generated ID.
          </p>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <button
            onClick={handleCreateNew}
            disabled={loading}
            className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            {loading ? "Creating Patient..." : "Create Patient"}
          </button>
        </div>
      </div>
    );
  }

  if (mode === "manage") {
    return <ManagePatients onBack={() => setMode(null)} />;
  }

  return null;
}
