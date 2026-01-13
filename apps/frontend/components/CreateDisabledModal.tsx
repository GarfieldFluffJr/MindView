"use client";

import { useEffect, useState } from "react";

interface CreateDisabledModalProps {
  isOpen: boolean;
  onClose: () => void;
  type: "patient" | "case";
}

export default function CreateDisabledModal({ isOpen, onClose, type }: CreateDisabledModalProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => setIsVisible(true), 10);
    } else {
      setIsVisible(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop with blur */}
      <div
        className={`absolute inset-0 backdrop-blur-sm bg-white/30 transition-opacity duration-300 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className={`relative bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 z-10 border-2 border-gray-200 transition-all duration-500 ${
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 -translate-y-8"
        }`}
      >
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
            Create {type === "patient" ? "Patient" : "Case"} Not Available
          </h3>

          {/* Message */}
          <p className="text-gray-600">
            Due to server upload restrictions, we've decided to also disable create operations.
          </p>
          <p className="text-sm text-gray-500">
            Please reach out to louieyin6@gmail.com for assistance.
          </p>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 hover:scale-105 mt-4"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
