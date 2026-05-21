import React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { FiMessageSquare, FiSend } from "react-icons/fi";
import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";
import { useWebSocket } from "../hooks/useWebSocket.js";

export default function CommentThread({ submissionId, title = "Conversation", onCommentsChange }) {
  const { user } = useAuth();
  const [comments, setComments] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const loadComments = useCallback(async () => {
    if (!submissionId) return;
    setLoading(true);
    setError("");
    try {
      const response = await api.get(`/submissions/${submissionId}/comments`);
      setComments(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load comments.");
    } finally {
      setLoading(false);
    }
  }, [submissionId]);

  useEffect(() => {
    setComments([]);
    setMessage("");
    loadComments();
  }, [loadComments]);

  useWebSocket("comments", useCallback((event) => {
    if (event.event !== "new_comment" || event.payload?.submission_id !== submissionId) return;
    setComments((current) => {
      if (current.some((comment) => comment.id === event.payload.id)) return current;
      return [...current, event.payload];
    });
  }, [submissionId]));

  const sortedComments = useMemo(
    () => [...comments].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)),
    [comments]
  );

  useEffect(() => {
    onCommentsChange?.(sortedComments);
  }, [onCommentsChange, sortedComments]);

  async function sendComment(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || !submissionId) return;
    setSending(true);
    setError("");
    try {
      const response = await api.post(`/submissions/${submissionId}/comments`, { message: trimmed });
      setComments((current) => current.some((comment) => comment.id === response.data.id) ? current : [...current, response.data]);
      setMessage("");
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to send comment.");
    } finally {
      setSending(false);
    }
  }

  if (!submissionId) return null;

  return (
    <section className="comment-thread">
      <div className="comment-thread-header">
        <div>
          <h3><FiMessageSquare /> {title}</h3>
          <p>{sortedComments.length ? `${sortedComments.length} comment${sortedComments.length === 1 ? "" : "s"}` : "No comments yet"}</p>
        </div>
      </div>

      <div className="comment-list">
        {loading && <div className="comment-empty">Loading conversation...</div>}
        {!loading && sortedComments.map((comment) => {
          const mine = comment.user_id === user?.id;
          return (
            <article className={`comment-item ${mine ? "is-mine" : ""}`} key={comment.id}>
              <div className="comment-meta">
                <strong>{comment.user_name}</strong>
                <span className={`comment-role comment-role-${comment.user_role}`}>{comment.user_role}</span>
                <time>{new Date(comment.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</time>
              </div>
              <p>{comment.message}</p>
            </article>
          );
        })}
        {!loading && !sortedComments.length && (
          <div className="comment-empty">Start a focused review thread for this submission.</div>
        )}
      </div>

      {error && <div className="comment-error">{error}</div>}

      <form className="comment-form" onSubmit={sendComment}>
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Write a comment..."
          maxLength={2000}
        />
        <button className="primary-button" disabled={sending || !message.trim()}>
          <FiSend /> {sending ? "Sending..." : "Send"}
        </button>
      </form>
    </section>
  );
}
