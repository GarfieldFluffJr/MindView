"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import FileUpload from "@/components/FileUpload";
import ProcessingStatus from "@/components/ProcessingStatus";
import { uploadFile, getMeshUrl } from "@/lib/api";

const BrainViewer = dynamic(() => import("@/components/BrainViewer"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[500px] bg-gray-900 rounded-xl flex items-center justify-center">
      <p className="text-white">Loading 3D viewer...</p>
    </div>
  ),
});

type AppState = "idle" | "uploading" | "processing" | "viewing" | "error";

export default function Home() {
  const [state, setState] = useState<AppState>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [meshUrl, setMeshUrl] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFileSelect = useCallback(async (file: File) => {
    setFileName(file.name);
    setState("uploading");
    setProgress(0);
    setError(null);

    try {
      setProgress(10);
      const response = await uploadFile(file);

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
  }, []);

  const handleReset = useCallback(() => {
    setState("idle");
    setProgress(0);
    setError(null);
    setMeshUrl(null);
    setFileName(null);
  }, []);

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <header className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">MindView</h1>
          <p className="text-gray-600">
            Upload and visualize MRI brain scans in 3D
          </p>
        </header>

        {state === "idle" && (
          <div className="max-w-2xl mx-auto">
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
            <BrainViewer meshUrl={meshUrl} onReset={handleReset} />
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
