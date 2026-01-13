"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { isHostedSite } from "@/lib/environment";
import UploadDisabledModal from "./UploadDisabledModal";

interface FileUploadProps {
  onFileSelect: (file: File, scanDate?: string) => void;
  disabled?: boolean;
}

export default function FileUpload({ onFileSelect, disabled }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scanDate, setScanDate] = useState<string>("");
  const [showDisabledModal, setShowDisabledModal] = useState(false);
  const isHosted = isHostedSite();

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0) {
        setSelectedFile(acceptedFiles[0]);
      }
    },
    []
  );

  const handleUpload = () => {
    if (selectedFile) {
      onFileSelect(selectedFile, scanDate || undefined);
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    if (isHosted) {
      e.preventDefault();
      e.stopPropagation();
      setShowDisabledModal(true);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/gzip": [".nii.gz"],
      "application/octet-stream": [".nii", ".nii.gz", ".obj"],
      "model/obj": [".obj"],
    },
    maxFiles: 1,
    disabled: disabled || isHosted,
    noClick: isHosted,
    noDrag: isHosted,
  });

  const rootProps = getRootProps();

  return (
    <div className="space-y-6">
      {!selectedFile ? (
        <div
          {...rootProps}
          onClick={isHosted ? handleClick : rootProps.onClick}
          className={`
            border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
            transition-all duration-200
            ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"}
            ${disabled || isHosted ? "opacity-50 cursor-not-allowed" : ""}
          `}
        >
          <input {...getInputProps()} disabled={isHosted} />
          <div className="flex flex-col items-center gap-4">
            <svg
              className="w-16 h-16 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            {isDragActive ? (
              <p className="text-lg text-blue-600">Drop the file here</p>
            ) : (
              <>
                <p className="text-lg text-gray-600">
                  Drag and drop your file here
                </p>
                <p className="text-sm text-gray-400">or click to browse</p>
                <p className="text-xs text-gray-400 mt-2">
                  Supports .nii, .nii.gz, and .obj files
                </p>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-blue-600"
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
              <div>
                <p className="font-medium text-gray-900">{selectedFile.name}</p>
                <p className="text-sm text-gray-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedFile(null)}
              className="text-red-600 hover:text-red-800 text-sm font-medium"
            >
              Remove
            </button>
          </div>

          <div>
            <label
              htmlFor="scan-date"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Scan Date (Optional)
            </label>
            <input
              id="scan-date"
              type="date"
              value={scanDate}
              onChange={(e) => setScanDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              When was this brain scan taken? Leave empty to use upload date.
            </p>
          </div>

          <button
            onClick={handleUpload}
            disabled={disabled}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Upload and Process
          </button>
        </div>
      )}

      <UploadDisabledModal
        isOpen={showDisabledModal}
        onClose={() => setShowDisabledModal(false)}
      />
    </div>
  );
}
