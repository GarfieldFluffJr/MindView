"use client";

import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import PatientSelection from "@/components/PatientSelection";
import CaseList from "@/components/CaseList";
import FileList from "@/components/FileList";
import FileUpload from "@/components/FileUpload";
import ProcessingStatus from "@/components/ProcessingStatus";
import RegionControls from "@/components/RegionControls";
import { uploadFile, getMeshUrl, getMetadata, MeshMetadata, RegionInfo } from "@/lib/api";

const BrainViewer = dynamic(() => import("@/components/BrainViewer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[500px] bg-gray-900 rounded-xl flex items-center justify-center">
      <p className="text-white">Loading 3D viewer...</p>
    </div>
  ),
});

type AppState =
  | "patient-selection"
  | "case-selection"
  | "file-list"
  | "file-upload"
  | "uploading"
  | "processing"
  | "viewing"
  | "error";

interface RegionState {
  visible: boolean;
  opacity: number;
}

export default function Home() {
  const [state, setState] = useState<AppState>("patient-selection");
  const [patientId, setPatientId] = useState<number | null>(null);
  const [caseId, setCaseId] = useState<number | null>(null);
  const [caseName, setCaseName] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [meshUrl, setMeshUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<MeshMetadata | null>(null);
  const [regionStates, setRegionStates] = useState<Record<string, RegionState>>({});

  // Fetch metadata when jobId changes and we're in viewing state
  useEffect(() => {
    if (jobId && state === "viewing") {
      getMetadata(jobId)
        .then((data) => {
          setMetadata(data);
          // Initialize region states from metadata
          const initialStates: Record<string, RegionState> = {};
          for (const region of data.regions) {
            initialStates[region.name] = {
              visible: region.defaultVisible,
              opacity: region.opacity,
            };
          }
          setRegionStates(initialStates);
        })
        .catch((err) => {
          console.error("Failed to fetch metadata:", err);
        });
    }
  }, [jobId, state]);

  const handlePatientSelected = useCallback((id: number) => {
    setPatientId(id);
    setState("case-selection");
  }, []);

  const handleCaseSelected = useCallback((id: number, name: string) => {
    setCaseId(id);
    setCaseName(name);
    setState("file-list");
  }, []);

  const handleFileSelectedFromList = useCallback((jobId: string, filename: string) => {
    setFileName(filename);
    setMeshUrl(getMeshUrl(jobId));
    setState("viewing");
  }, []);

  const handleUploadFileClick = useCallback(() => {
    setState("file-upload");
  }, []);

  const handleFileSelect = useCallback(async (file: File, scanDate?: string) => {
    if (patientId === null || caseId === null) {
      setError("Patient ID and Case ID are required");
      setState("error");
      return;
    }

    setFileName(file.name);
    setState("uploading");
    setProgress(0);
    setError(null);
    setMetadata(null);
    setRegionStates({});

    try {
      setProgress(10);

      const response = await uploadFile(file, patientId, caseId, scanDate);
      setJobId(response.job_id);

      if (response.status === "completed") {
        setProgress(100);
        setMeshUrl(getMeshUrl(response.job_id));
        setState("viewing");
      } else if (response.status === "failed") {
        throw new Error("Processing failed");
      } else {
        setProgress(response.status === "processing" ? 50 : 20);
        setMeshUrl(getMeshUrl(response.job_id));
        setState("viewing");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
      setState("error");
    }
  }, [patientId, caseId]);

  const handleReset = useCallback(() => {
    setState("file-list");
    setProgress(0);
    setError(null);
    setMeshUrl(null);
    setFileName(null);
  }, []);

  const handleChangePatient = useCallback(() => {
    setState("patient-selection");
    setPatientId(null);
    setCaseId(null);
    setCaseName(null);
    setProgress(0);
    setError(null);
    setMeshUrl(null);
    setFileName(null);
    setJobId(null);
    setMetadata(null);
    setRegionStates({});
  }, []);

  const handleRegionChange = useCallback(
    (regionName: string, changes: Partial<RegionState>) => {
      setRegionStates((prev) => ({
        ...prev,
        [regionName]: {
          ...prev[regionName],
          ...changes,
        },
      }));
    },
    []
  );

  const handleShowAll = useCallback(() => {
    if (!metadata) return;
    setRegionStates((prev) => {
      const next = { ...prev };
      for (const region of metadata.regions) {
        next[region.name] = {
          ...next[region.name],
          visible: true,
        };
      }
      return next;
    });
  }, [metadata]);

  const handleHideAll = useCallback(() => {
    if (!metadata) return;
    setRegionStates((prev) => {
      const next = { ...prev };
      for (const region of metadata.regions) {
        next[region.name] = {
          ...next[region.name],
          visible: false,
        };
      }
      return next;
    });
  }, [metadata]);

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">MindView</h1>
          <p className="text-gray-600">
            Upload and visualize MRI brain scans in 3D
          </p>
        </header>

        {state === "patient-selection" && (
          <PatientSelection onPatientSelected={handlePatientSelected} />
        )}

        {state === "case-selection" && patientId !== null && (
          <CaseList
            patientId={patientId}
            onCaseSelected={handleCaseSelected}
            onChangePatient={handleChangePatient}
          />
        )}

        {state === "file-list" && patientId !== null && caseId !== null && caseName !== null && (
          <FileList
            patientId={patientId}
            caseId={caseId}
            caseName={caseName}
            onFileSelected={handleFileSelectedFromList}
            onUploadFile={handleUploadFileClick}
            onChangeCase={() => setState("case-selection")}
          />
        )}

        {state === "file-upload" && (
          <div className="max-w-2xl mx-auto">
            <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="text-sm text-blue-800">
                <p>
                  <span className="font-semibold">Patient ID:</span> {patientId}
                </p>
                <p className="mt-1">
                  <span className="font-semibold">Case:</span> {caseName} (ID: {caseId})
                </p>
              </div>
              <div className="flex gap-4 mt-2">
                <button
                  onClick={() => setState("file-list")}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Back to Files
                </button>
                <button
                  onClick={() => setState("case-selection")}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Change Case
                </button>
                <button
                  onClick={handleChangePatient}
                  className="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  Change Patient
                </button>
              </div>
            </div>
            <FileUpload onFileSelect={handleFileSelect} />
          </div>
        )}

        {(state === "uploading" || state === "processing") && (
          <div className="max-w-2xl mx-auto">
            <ProcessingStatus
              status={state}
              progress={progress}
              error={error}
            />
            {fileName && (
              <p className="text-center text-sm text-gray-500 mt-4">
                {fileName}
              </p>
            )}
          </div>
        )}

        {state === "viewing" && meshUrl && (

          <div className="w-full">
            <div className="mb-4 bg-blue-50 border border-blue-200 rounded-lg p-3 max-w-2xl mx-auto">
              <div className="text-sm text-blue-800">
                <p>
                  <span className="font-semibold">Patient ID:</span> {patientId} |
                  <span className="font-semibold ml-2">Case:</span> {caseName} (ID: {caseId})
                </p>
                <div className="flex gap-4 mt-2">
                  <button
                    onClick={() => setState("file-list")}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    Back to Files
                  </button>
                  <button
                    onClick={() => setState("case-selection")}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    Change Case
                  </button>
                  <button
                    onClick={handleChangePatient}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    Change Patient
                  </button>
                </div>
              </div>
            </div>
            
            {/* Region Controls - Left Panel */}
            {metadata && metadata.regions.length > 0 && (
              <div className="w-72 flex-shrink-0">
                <RegionControls
                  regions={metadata.regions}
                  regionStates={regionStates}
                  onRegionChange={handleRegionChange}
                  onShowAll={handleShowAll}
                  onHideAll={handleHideAll}
                  hasTumor={metadata.has_tumor}
                />
              </div>
            )}
            
            {/* Brain Viewer - Main Area */}
            <div className="flex-1">
              <BrainViewer
                meshUrl={meshUrl}
                regionStates={regionStates}
                onReset={handleReset}
              />
            </div>
          </div>
        )}

        {state === "error" && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-red-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-red-800 mb-2">
                Error Processing File
              </h3>
              <p className="text-red-600 mb-6">{error}</p>
              <button
                onClick={handleReset}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
