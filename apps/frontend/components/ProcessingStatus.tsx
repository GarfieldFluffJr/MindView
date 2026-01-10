"use client";

interface ProcessingStatusProps {
  status: "uploading" | "queued" | "processing" | "completed" | "failed";
  progress: number;
  error?: string | null;
}

export default function ProcessingStatus({
  status,
  progress,
  error,
}: ProcessingStatusProps) {
  const getStatusMessage = () => {
    switch (status) {
      case "uploading":
        return "Uploading file...";
      case "queued":
        return "Queued for processing...";
      case "processing":
        return "Processing MRI scan...";
      case "completed":
        return "Processing complete!";
      case "failed":
        return "Processing failed";
      default:
        return "Unknown status";
    }
  };

  const getProgressSteps = () => {
    if (progress < 30) return "Loading NIfTI file...";
    if (progress < 50) return "Applying smoothing filter...";
    if (progress < 60) return "Thresholding brain tissue...";
    if (progress < 80) return "Generating 3D mesh...";
    if (progress < 90) return "Simplifying mesh...";
    if (progress < 100) return "Exporting to GLB format...";
    return "Complete!";
  };

  return (
    <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-200">
      <div className="flex flex-col items-center gap-6">
        {status !== "failed" ? (
          <div className="relative w-20 h-20">
            <svg className="w-20 h-20 animate-spin" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
              />
              <path
                className="opacity-75 text-blue-600"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-semibold text-gray-700">
                {progress}%
              </span>
            </div>
          </div>
        ) : (
          <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center">
            <svg
              className="w-10 h-10 text-red-600"
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
          </div>
        )}

        <div className="text-center">
          <h3 className="text-xl font-semibold text-gray-800">
            {getStatusMessage()}
          </h3>
          {status === "processing" && (
            <p className="text-sm text-gray-500 mt-2">{getProgressSteps()}</p>
          )}
          {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
        </div>

        <div className="w-full max-w-md">
          <div className="bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                status === "failed" ? "bg-red-600" : "bg-blue-600"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
