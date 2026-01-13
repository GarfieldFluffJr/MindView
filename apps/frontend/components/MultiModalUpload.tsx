"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { MultiModalFiles } from "@/lib/api";
import { isHostedSite } from "@/lib/environment";
import UploadDisabledModal from "./UploadDisabledModal";

type Modality = "t1" | "t1ce" | "t2" | "flair";

interface ModalityInfo {
  key: Modality;
  label: string;
  description: string;
}

const MODALITIES: ModalityInfo[] = [
  { key: "t1", label: "T1", description: "T1-weighted MRI" },
  { key: "t1ce", label: "T1ce", description: "T1 contrast-enhanced" },
  { key: "t2", label: "T2", description: "T2-weighted MRI" },
  { key: "flair", label: "FLAIR", description: "Fluid-attenuated inversion recovery" },
];

interface MultiModalUploadProps {
  onFilesSelect: (files: MultiModalFiles, scanDate?: string) => void;
  disabled?: boolean;
}

export default function MultiModalUpload({ onFilesSelect, disabled }: MultiModalUploadProps) {
  const [files, setFiles] = useState<Partial<MultiModalFiles>>({});
  const [scanDate, setScanDate] = useState<string>("");
  const [activeDropzone, setActiveDropzone] = useState<Modality | null>(null);
  const [showDisabledModal, setShowDisabledModal] = useState(false);
  const isHosted = isHostedSite();

  const handleFileDrop = useCallback((modality: Modality, acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFiles((prev) => ({ ...prev, [modality]: acceptedFiles[0] }));
    }
  }, []);

  const removeFile = (modality: Modality) => {
    setFiles((prev) => {
      const next = { ...prev };
      delete next[modality];
      return next;
    });
  };

  const allFilesSelected = MODALITIES.every((m) => files[m.key]);

  const handleUpload = () => {
    if (allFilesSelected) {
      onFilesSelect(files as MultiModalFiles, scanDate || undefined);
    }
  };

  const clearAll = () => {
    setFiles({});
    setScanDate("");
  };

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-medium text-blue-800 mb-2">Multi-Modal MRI Upload</h3>
        <p className="text-sm text-blue-700">
          Upload all 4 MRI modalities for comprehensive brain and tumor segmentation.
          This enables both anatomical structure detection and tumor identification.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {MODALITIES.map((modality) => (
          <ModalityDropzone
            key={modality.key}
            modality={modality}
            file={files[modality.key]}
            onDrop={(acceptedFiles) => handleFileDrop(modality.key, acceptedFiles)}
            onRemove={() => removeFile(modality.key)}
            disabled={disabled}
            isActive={activeDropzone === modality.key}
            onDragEnter={() => setActiveDropzone(modality.key)}
            onDragLeave={() => setActiveDropzone(null)}
            isHosted={isHosted}
            onShowModal={() => setShowDisabledModal(true)}
          />
        ))}
      </div>

      {Object.keys(files).length > 0 && (
        <div className="bg-white rounded-xl border-2 border-gray-200 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">
                {Object.keys(files).length} of 4 files selected
              </p>
              <p className="text-sm text-gray-500">
                {allFilesSelected
                  ? "All modalities ready for upload"
                  : `Missing: ${MODALITIES.filter((m) => !files[m.key])
                      .map((m) => m.label)
                      .join(", ")}`}
              </p>
            </div>
            <button
              onClick={clearAll}
              className="text-red-600 hover:text-red-800 text-sm font-medium"
            >
              Clear All
            </button>
          </div>

          <div>
            <label
              htmlFor="scan-date-multi"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Scan Date (Optional)
            </label>
            <input
              id="scan-date-multi"
              type="date"
              value={scanDate}
              onChange={(e) => setScanDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={disabled || !allFilesSelected}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            {allFilesSelected
              ? "Upload and Process Multi-Modal Scan"
              : `Select All 4 Modalities to Continue`}
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

interface ModalityDropzoneProps {
  modality: ModalityInfo;
  file?: File;
  onDrop: (files: File[]) => void;
  onRemove: () => void;
  disabled?: boolean;
  isActive: boolean;
  onDragEnter: () => void;
  onDragLeave: () => void;
  isHosted: boolean;
  onShowModal: () => void;
}

function ModalityDropzone({
  modality,
  file,
  onDrop,
  onRemove,
  disabled,
  isActive,
  onDragEnter,
  onDragLeave,
  isHosted,
  onShowModal,
}: ModalityDropzoneProps) {
  const handleClick = (e: React.MouseEvent) => {
    if (isHosted) {
      e.preventDefault();
      e.stopPropagation();
      onShowModal();
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/gzip": [".nii.gz"],
      "application/octet-stream": [".nii", ".nii.gz"],
    },
    maxFiles: 1,
    disabled: disabled || isHosted,
    onDragEnter,
    onDragLeave,
    noClick: isHosted,
    noDrag: isHosted,
  });

  const rootProps = getRootProps();

  if (file) {
    return (
      <div className="border-2 border-green-300 bg-green-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="font-medium text-green-800">{modality.label}</span>
          <button
            onClick={onRemove}
            className="text-red-600 hover:text-red-800 text-xs"
          >
            Remove
          </button>
        </div>
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-green-600"
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
          <span className="text-sm text-green-700 truncate" title={file.name}>
            {file.name}
          </span>
        </div>
        <p className="text-xs text-green-600 mt-1">
          {(file.size / 1024 / 1024).toFixed(2)} MB
        </p>
      </div>
    );
  }

  return (
    <div
      {...rootProps}
      onClick={isHosted ? handleClick : rootProps.onClick}
      className={`
        border-2 border-dashed rounded-lg p-4 text-center cursor-pointer
        transition-all duration-200
        ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"}
        ${disabled || isHosted ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <input {...getInputProps()} disabled={isHosted} />
      <div className="space-y-2">
        <span className="inline-block px-3 py-1 bg-gray-100 rounded-full text-sm font-medium text-gray-700">
          {modality.label}
        </span>
        <p className="text-xs text-gray-500">{modality.description}</p>
        {isDragActive ? (
          <p className="text-sm text-blue-600">Drop here</p>
        ) : (
          <p className="text-xs text-gray-400">Drop or click to select</p>
        )}
      </div>
    </div>
  );
}
