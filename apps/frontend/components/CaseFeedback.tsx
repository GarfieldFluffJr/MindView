"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import ReactMarkdown from "react-markdown";
import {
  FeedbackSessionResponse,
  FeedbackMessageResponse,
  FeedbackMetrics,
  getFeedbackSession,
  generateCaseSummary,
  sendFeedbackMessage,
  clearFeedbackSession,
} from "@/lib/api";

interface CaseFeedbackProps {
  patientId: number;
  caseId: number;
  caseName: string;
  onBack: () => void;
}

function formatTimestamp(dateString: string): string {
  const utcDateString = dateString.endsWith("Z") ? dateString : dateString + "Z";
  const date = new Date(utcDateString);
  return date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

function formatVolume(volumeMm3: number): string {
  if (volumeMm3 >= 1000) {
    return `${(volumeMm3 / 1000).toFixed(2)} cm³`;
  }
  return `${volumeMm3.toFixed(2)} mm³`;
}

function MetricsCard({ metrics }: { metrics: FeedbackMetrics }) {
  const latest = metrics.latest_metrics;
  const progression = metrics.progression;

  return (
    <div className="bg-gray-800/50 rounded-lg p-4 mb-4">
      <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
        <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        Tumor Metrics
      </h4>

      <div className="grid grid-cols-2 gap-3">
        {latest?.total_lesion_volume_mm3 !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Total Lesion Volume</p>
            <p className="text-white font-medium">{formatVolume(latest.total_lesion_volume_mm3)}</p>
          </div>
        )}

        {latest?.active_enhancing_volume_mm3 !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Enhancing Volume</p>
            <p className="text-white font-medium">{formatVolume(latest.active_enhancing_volume_mm3)}</p>
          </div>
        )}

        {latest?.edema_volume_mm3 !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Edema Volume</p>
            <p className="text-white font-medium">{formatVolume(latest.edema_volume_mm3)}</p>
          </div>
        )}

        {latest?.midline_shift_mm !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Midline Shift</p>
            <p className="text-white font-medium">{latest.midline_shift_mm.toFixed(2)} mm</p>
          </div>
        )}

        {latest?.infiltration_index !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Infiltration Index</p>
            <p className="text-white font-medium">{latest.infiltration_index.toFixed(2)}</p>
          </div>
        )}

        {latest?.necrotic_core_volume_mm3 !== undefined && (
          <div className="bg-gray-900/50 rounded p-2">
            <p className="text-gray-400 text-xs">Necrotic Core</p>
            <p className="text-white font-medium">{formatVolume(latest.necrotic_core_volume_mm3)}</p>
          </div>
        )}
      </div>

      {progression && (
        <div className="mt-3 bg-gray-900/50 rounded p-3">
          <p className="text-gray-400 text-xs mb-2">Volume Progression</p>
          <div className="flex items-center gap-3">
            <div className={`px-2 py-1 rounded text-xs font-medium ${
              progression.trend === "increasing" ? "bg-red-900/50 text-red-300" :
              progression.trend === "decreasing" ? "bg-green-900/50 text-green-300" :
              "bg-gray-700 text-gray-300"
            }`}>
              {progression.trend === "increasing" ? "Increasing" :
               progression.trend === "decreasing" ? "Decreasing" : "Stable"}
            </div>
            <span className={`text-sm font-medium ${
              progression.percent_change > 0 ? "text-red-400" :
              progression.percent_change < 0 ? "text-green-400" : "text-gray-400"
            }`}>
              {progression.percent_change > 0 ? "+" : ""}{progression.percent_change.toFixed(1)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: FeedbackMessageResponse }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
        isUser
          ? "bg-blue-600 text-white"
          : "bg-gray-800 text-gray-100"
      }`}>
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-invert max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        <p className={`text-xs mt-1 ${isUser ? "text-blue-200" : "text-gray-500"}`}>
          {formatTimestamp(message.created_at)}
        </p>
      </div>
    </div>
  );
}

export default function CaseFeedback({
  patientId,
  caseId,
  caseName,
  onBack,
}: CaseFeedbackProps) {
  const [session, setSession] = useState<FeedbackSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMessage, setInputMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getFeedbackSession(patientId, caseId);
      setSession(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load feedback session");
    } finally {
      setLoading(false);
    }
  }, [patientId, caseId]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  useEffect(() => {
    if (!loading && session?.messages.length) {
      scrollToBottom();
    }
  }, [loading, session?.messages.length]);

  const handleGenerateSummary = async () => {
    try {
      setGenerating(true);
      setError(null);
      const result = await generateCaseSummary(patientId, caseId);
      setSession((prev) => prev ? {
        ...prev,
        summary: result.summary,
        metrics: result.metrics,
        messages: [
          ...prev.messages,
          {
            message_id: result.session_id + "_summary",
            role: "assistant" as const,
            content: result.summary,
            created_at: new Date().toISOString(),
          }
        ]
      } : null);
      setTimeout(scrollToBottom, 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate summary");
    } finally {
      setGenerating(false);
    }
  };

  const handleClearSession = async () => {
    if (!confirm("Are you sure you want to clear the chat history and summary?")) return;
    try {
      await clearFeedbackSession(patientId, caseId);
      await fetchSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear session");
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || sending) return;

    const content = inputMessage.trim();
    setInputMessage("");

    // Optimistically add user message
    const tempUserMessage: FeedbackMessageResponse = {
      message_id: "temp_" + Date.now(),
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setSession((prev) => prev ? {
      ...prev,
      messages: [...prev.messages, tempUserMessage]
    } : null);
    setTimeout(scrollToBottom, 100);

    try {
      setSending(true);
      const result = await sendFeedbackMessage(patientId, caseId, content);

      // Replace temp message with real messages
      setSession((prev) => prev ? {
        ...prev,
        messages: [
          ...prev.messages.filter(m => m.message_id !== tempUserMessage.message_id),
          result.user_message,
          result.assistant_message
        ]
      } : null);
      setTimeout(scrollToBottom, 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      // Remove temp message on error
      setSession((prev) => prev ? {
        ...prev,
        messages: prev.messages.filter(m => m.message_id !== tempUserMessage.message_id)
      } : null);
      setInputMessage(content);
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading feedback session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-gray-950 flex flex-col">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between max-w-6xl mx-auto">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="text-gray-400 hover:text-white transition-colors flex items-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back
            </button>
            <div>
              <h1 className="text-white font-semibold text-lg">Case Feedback</h1>
              <p className="text-gray-400 text-sm">
                Patient #{patientId} - {caseName}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleClearSession}
              disabled={generating}
              className="text-gray-400 hover:text-red-400 transition-colors text-sm flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Clear Chat
            </button>
            <button
              onClick={handleGenerateSummary}
              disabled={generating}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
            >
              {generating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  Generating...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Generate New Summary
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-900/30 border-b border-red-700 px-6 py-3">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <p className="text-red-300 text-sm">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-400 hover:text-red-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Metrics Sidebar */}
        {session?.metrics && session.metrics.has_tumor && (
          <div className="w-80 bg-gray-900/50 border-r border-gray-800 p-4 overflow-y-auto">
            <MetricsCard metrics={session.metrics} />
            <div className="bg-gray-800/50 rounded-lg p-3">
              <p className="text-gray-400 text-xs mb-1">Scans Analyzed</p>
              <p className="text-white text-2xl font-bold">{session.scan_count}</p>
            </div>
          </div>
        )}

        {/* Chat Area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-3xl mx-auto">
              {session?.messages.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="w-16 h-16 mx-auto text-gray-700 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <h3 className="text-white font-medium mb-2">No feedback yet</h3>
                  <p className="text-gray-500 text-sm mb-4">
                    Click &quot;Generate New Summary&quot; to get an AI-powered analysis of this case.
                  </p>
                </div>
              ) : (
                session?.messages.map((message) => (
                  <MessageBubble key={message.message_id} message={message} />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div className="border-t border-gray-800 bg-gray-900/50 p-4">
            <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      if (inputMessage.trim() && !sending) {
                        handleSendMessage(e);
                      }
                    }
                  }}
                  placeholder="Ask a question about this case..."
                  disabled={sending || generating}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || sending || generating}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-4 rounded-lg transition-colors flex items-center justify-center"
                >
                  {sending ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
