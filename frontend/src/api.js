/**
 * API client for the Job Hunter Agent backend.
 */

const BASE_URL = "/api";

/**
 * Upload a resume file (PDF/DOCX) and get the parsed profile.
 */
export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload-resume`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

/**
 * Set user preferences from a natural language message.
 */
export async function setPreferences(resumeId, message) {
  const res = await fetch(`${BASE_URL}/set-preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resume_id: resumeId, message }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to set preferences");
  }

  return res.json();
}

/**
 * Start a job search and return an SSE event source reader.
 * Calls the callback for each event received.
 */
export async function searchJobs(resumeId, preferencesId, onEvent) {
  const res = await fetch(`${BASE_URL}/search-jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resume_id: resumeId,
      preferences_id: preferencesId,
    }),
  });

  if (!res.ok) {
    throw new Error("Search request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6));
          onEvent(event);
        } catch {
          // Ignore parse errors
        }
      }
    }
  }

  // Process remaining buffer
  if (buffer.startsWith("data: ")) {
    try {
      const event = JSON.parse(buffer.slice(6));
      onEvent(event);
    } catch {
      // Ignore
    }
  }
}

/**
 * Get stored job listings with optional filters.
 */
export async function getJobs({ resumeId, minScore, source, sortBy } = {}) {
  const params = new URLSearchParams();
  if (resumeId) params.set("resume_id", resumeId);
  if (minScore) params.set("min_score", minScore);
  if (source) params.set("source", source);
  if (sortBy) params.set("sort_by", sortBy);

  const res = await fetch(`${BASE_URL}/jobs?${params}`);
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

/**
 * Update a job's status (new/saved/dismissed).
 */
export async function updateJobStatus(jobId, status) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/status?status=${status}`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

/**
 * Send a chat message.
 */
export async function sendChat(content) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role: "user", content }),
  });
  if (!res.ok) throw new Error("Chat failed");
  return res.json();
}

/**
 * List all uploaded resumes.
 */
export async function getResumes() {
  const res = await fetch(`${BASE_URL}/resumes`);
  if (!res.ok) throw new Error("Failed to fetch resumes");
  return res.json();
}

/**
 * Check backend health.
 */
export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error("Backend unavailable");
  return res.json();
}
