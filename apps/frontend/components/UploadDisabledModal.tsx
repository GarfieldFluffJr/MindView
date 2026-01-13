"use client";

interface UploadDisabledModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function UploadDisabledModal({ isOpen, onClose }: UploadDisabledModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop with blur */}
      <div
        className="absolute inset-0 backdrop-blur-sm bg-white/30"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 z-10 border-2 border-gray-200">
        <div className="flex flex-col items-center text-center space-y-4">
          {/* Icon */}
          <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center">
            <svg
              className="w-8 h-8 text-yellow-600"
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

          {/* Title */}
          <h3 className="text-2xl font-bold text-gray-900">
            Upload Not Available
          </h3>

          {/* Message */}
          <p className="text-gray-600">
            File uploads are currently disabled on the hosted version of this site.
          </p>
          <p className="text-sm text-gray-500">
            Please run the application locally to upload and process brain scan files.
          </p>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors mt-4"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
