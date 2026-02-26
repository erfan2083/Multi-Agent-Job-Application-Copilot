/**
 * API client for the Job Hunter Agent backend.
 */

const BASE_URL = "/api";

/**
 * Get the stored auth token.
 */
function getToken() {
  return localStorage.getItem("token");
}

/**
 * Build headers with optional auth token.
 */
function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

// ── Authentication ──────────────────────────────────────────────

/**
 * Register a new user.
 */
export async function registerUser(email, password, fullName = "") {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }

  return res.json();
}

/**
 * Login an existing user.
 */
export async function loginUser(email, password) {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }

  return res.json();
}

/**
 * Get current user info (requires token).
 */
export async function getMe(token) {
  const res = await fetch(`${BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ── Resume ──────────────────────────────────────────────────────

/**
 * Upload a resume file (PDF/DOCX) and get the parsed profile.
 */
export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/upload-resume`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

/**
 * List all uploaded resumes.
 */
export async function getResumes() {
  const res = await fetch(`${BASE_URL}/resumes`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch resumes");
  return res.json();
}

/**
 * Delete a resume and its associated data.
 */
export async function deleteResume(resumeId) {
  const res = await fetch(`${BASE_URL}/resumes/${resumeId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete resume");
  }
  return res.json();
}

// ── Preferences ─────────────────────────────────────────────────

/**
 * Set user preferences from a natural language message.
 */
export async function setPreferences(resumeId, message) {
  const res = await fetch(`${BASE_URL}/set-preferences`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ resume_id: resumeId, message }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to set preferences");
  }

  return res.json();
}

// ── Job Search ──────────────────────────────────────────────────

/**
 * Start a job search and return an SSE event source reader.
 * Calls the callback for each event received.
 */
export async function searchJobs(resumeId, preferencesId, onEvent) {
  const res = await fetch(`${BASE_URL}/search-jobs`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
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

  const res = await fetch(`${BASE_URL}/jobs?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch jobs");
  return res.json();
}

/**
 * Update a job's status (new/saved/dismissed).
 */
export async function updateJobStatus(jobId, status) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/status?status=${status}`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}

// ── Chat ────────────────────────────────────────────────────────

/**
 * Send a chat message.
 */
export async function sendChat(content) {
  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ role: "user", content }),
  });
  if (!res.ok) throw new Error("Chat failed");
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

// ── Saved Searches ──────────────────────────────────────────────

/**
 * Create a saved search.
 */
export async function createSavedSearch(data) {
  const res = await fetch(`${BASE_URL}/saved-searches`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to save search");
  return res.json();
}

/**
 * List all saved searches, optionally filtered by resume.
 */
export async function getSavedSearches(resumeId) {
  const params = new URLSearchParams();
  if (resumeId) params.set("resume_id", resumeId);
  const res = await fetch(`${BASE_URL}/saved-searches?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch saved searches");
  return res.json();
}

/**
 * Update a saved search.
 */
export async function updateSavedSearch(searchId, data) {
  const res = await fetch(`${BASE_URL}/saved-searches/${searchId}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update saved search");
  return res.json();
}

/**
 * Delete a saved search.
 */
export async function deleteSavedSearch(searchId) {
  const res = await fetch(`${BASE_URL}/saved-searches/${searchId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete saved search");
  return res.json();
}

/**
 * Re-run a saved search (SSE stream).
 */
export async function runSavedSearch(searchId, onEvent) {
  const res = await fetch(`${BASE_URL}/saved-searches/${searchId}/run`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to run saved search");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop();

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(line.slice(6)));
        } catch {
          // Ignore
        }
      }
    }
  }

  if (buffer.startsWith("data: ")) {
    try {
      onEvent(JSON.parse(buffer.slice(6)));
    } catch {
      // Ignore
    }
  }
}

// ── Alerts ──────────────────────────────────────────────────────

/**
 * Get alerts, optionally filtered.
 */
export async function getAlerts({ savedSearchId, unreadOnly } = {}) {
  const params = new URLSearchParams();
  if (savedSearchId) params.set("saved_search_id", savedSearchId);
  if (unreadOnly) params.set("unread_only", "true");
  const res = await fetch(`${BASE_URL}/alerts?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

/**
 * Get unread alert count.
 */
export async function getAlertCount() {
  const res = await fetch(`${BASE_URL}/alerts/count`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch alert count");
  return res.json();
}

/**
 * Mark a single alert as read.
 */
export async function markAlertRead(alertId) {
  const res = await fetch(`${BASE_URL}/alerts/${alertId}/read`, {
    method: "PATCH",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to mark alert as read");
  return res.json();
}

/**
 * Mark all alerts as read.
 */
export async function markAllAlertsRead(savedSearchId) {
  const params = new URLSearchParams();
  if (savedSearchId) params.set("saved_search_id", savedSearchId);
  const res = await fetch(`${BASE_URL}/alerts/mark-all-read?${params}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to mark all alerts as read");
  return res.json();
}

// ── Job Tracking ────────────────────────────────────────────────

/**
 * Mark a job as viewed (records timestamp).
 */
export async function markJobViewed(jobId) {
  const res = await fetch(`${BASE_URL}/jobs/${jobId}/view`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to mark job as viewed");
  return res.json();
}

// ── CSV Export ──────────────────────────────────────────────────

/**
 * Get the CSV export URL with filters.
 */
export function getExportCsvUrl({ resumeId, minScore, source, status } = {}) {
  const params = new URLSearchParams();
  if (resumeId) params.set("resume_id", resumeId);
  if (minScore) params.set("min_score", minScore);
  if (source) params.set("source", source);
  if (status) params.set("status", status);
  return `${BASE_URL}/export/csv?${params}`;
}

// ── Auto-Apply ─────────────────────────────────────────────────

/**
 * Auto-apply to a job (requires user confirmation first).
 */
export async function applyToJob(jobId, resumeId) {
  const res = await fetch(`${BASE_URL}/apply`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ job_id: jobId, resume_id: resumeId }),
  });
  if (!res.ok) throw new Error("Auto-apply failed");
  return res.json();
}

/**
 * List application records.
 */
export async function getApplications({ jobId, status } = {}) {
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (status) params.set("status", status);
  const res = await fetch(`${BASE_URL}/applications?${params}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch applications");
  return res.json();
}

/**
 * Get list of sites that support auto-apply.
 */
export async function getAutoApplySites() {
  const res = await fetch(`${BASE_URL}/apply/supported-sites`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch supported sites");
  return res.json();
}

// ── LLM Provider ────────────────────────────────────────────────

/**
 * Get current LLM provider status.
 */
export async function getLLMStatus() {
  const res = await fetch(`${BASE_URL}/llm/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch LLM status");
  return res.json();
}

/**
 * Switch the active LLM provider.
 */
export async function switchLLMProvider(provider) {
  const res = await fetch(`${BASE_URL}/llm/switch`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) throw new Error("Failed to switch LLM provider");
  return res.json();
}
