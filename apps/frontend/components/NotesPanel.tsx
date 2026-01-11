"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { NoteResponse, getNotesForFile, createNote } from "@/lib/api";

interface NotesPanelProps {
  patientId: number;
  caseId: number;
  fileId: string;
}

function formatTimestamp(dateString: string): string {
  // Backend returns UTC timestamps without Z suffix, so append it
  const utcDateString = dateString.endsWith("Z") ? dateString : dateString + "Z";
  const date = new Date(utcDateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

export default function NotesPanel({
  patientId,
  caseId,
  fileId,
}: NotesPanelProps) {
  const [notes, setNotes] = useState<NoteResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newNoteContent, setNewNoteContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const notesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    notesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchNotes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getNotesForFile(patientId, caseId, fileId);
      setNotes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load notes");
    } finally {
      setLoading(false);
    }
  }, [patientId, caseId, fileId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  // Auto-scroll to bottom when notes load
  useEffect(() => {
    if (!loading && notes.length > 0) {
      scrollToBottom();
    }
  }, [loading, notes.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteContent.trim() || submitting) return;

    try {
      setSubmitting(true);
      const newNote = await createNote(patientId, caseId, fileId, {
        content: newNoteContent.trim(),
        doctor_name: "Dr. Smith",
      });
      setNotes((prev) => [...prev, newNote]);
      setNewNoteContent("");
      setTimeout(scrollToBottom, 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add note");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-gray-900/95 backdrop-blur-sm rounded-lg overflow-hidden flex flex-col max-h-[70vh]">
      {/* Header */}
      <div className="p-3 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <h3 className="text-white font-semibold text-sm">Collaborative Notes</h3>
          <span className="text-gray-400 text-xs">{notes.length} notes</span>
        </div>
      </div>

      {/* Notes List */}
      <div className="overflow-y-auto flex-1 p-2 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/30 border border-red-700 rounded p-3 text-center">
            <p className="text-red-300 text-xs">{error}</p>
            <button
              onClick={fetchNotes}
              className="mt-2 text-xs text-red-400 hover:text-red-300 underline"
            >
              Try again
            </button>
          </div>
        ) : notes.length === 0 ? (
          <div className="text-center py-8">
            <svg
              className="w-10 h-10 mx-auto text-gray-600 mb-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
              />
            </svg>
            <p className="text-gray-500 text-xs">No notes yet</p>
            <p className="text-gray-600 text-xs mt-1">Add the first note below</p>
          </div>
        ) : (
          <>
            {notes.map((note) => (
              <div
                key={note.note_id}
                className="rounded-lg p-3 transition-all hover:shadow-md"
                style={{ backgroundColor: note.color + "40" }}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ backgroundColor: note.color, color: "#1f2937" }}
                  >
                    {note.doctor_name}
                  </span>
                  <span className="text-gray-400 text-[10px] whitespace-nowrap">
                    {formatTimestamp(note.created_at)}
                  </span>
                </div>
                <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
                  {note.content}
                </p>
              </div>
            ))}
            <div ref={notesEndRef} />
          </>
        )}
      </div>

      {/* Add Note Form */}
      <div className="p-3 border-t border-gray-700">
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <textarea
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (newNoteContent.trim() && !submitting) {
                    handleSubmit(e);
                  }
                }
              }}
              placeholder="Add a note..."
              rows={2}
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 resize-none"
              disabled={submitting}
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-gray-500 text-xs">Posting as Dr. Smith</span>
            <button
              type="submit"
              disabled={!newNoteContent.trim() || submitting}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white text-xs px-4 py-1.5 rounded transition-colors flex items-center gap-1"
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                  Adding...
                </>
              ) : (
                <>
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  Add Note
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
