import { useState, useRef } from "react";
import { updateJobStatus, markJobViewed, applyToJob } from "../api";

const SITE_LABELS = {
  "jobspy-indeed": "Indeed",
  "jobspy-linkedin": "LinkedIn",
  "jobspy-glassdoor": "Glassdoor",
  "jobspy-google": "Google",
  remotive: "Remotive",
  jobinja: "Jobinja",
  irantalent: "IranTalent",
  jobvision: "JobVision",
};

// Sites that support auto-apply
const AUTO_APPLY_SITES = new Set(["jobinja", "irantalent", "wellfound"]);

function getScoreColor(score) {
  if (score >= 80) return "score-high";
  if (score >= 60) return "score-mid";
  return "score-low";
}

function getSiteBadgeClass(site) {
  return `badge badge-${site}`;
}

function JobCard({ job, compact = false, resumeId, onApplied }) {
  const [status, setStatus] = useState(job.status || "new");
  const [expanded, setExpanded] = useState(false);
  const [viewed, setViewed] = useState(!!job.viewed_at);
  const [showApplyConfirm, setShowApplyConfirm] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const viewedRef = useRef(!!job.viewed_at);

  const canAutoApply =
    AUTO_APPLY_SITES.has(job.source_site) &&
    status !== "applied" &&
    status !== "dismissed" &&
    !compact;

  const handleViewClick = async () => {
    // Track view on first click
    if (!viewedRef.current && job.id) {
      viewedRef.current = true;
      setViewed(true);
      try {
        await markJobViewed(job.id);
      } catch {
        // Ignore
      }
    }
  };

  const handleSave = async () => {
    const newStatus = status === "saved" ? "new" : "saved";
    try {
      if (job.id) {
        await updateJobStatus(job.id, newStatus);
      }
      setStatus(newStatus);
    } catch {
      // Ignore - the job might not be saved to DB yet (streaming)
      setStatus(newStatus);
    }
  };

  const handleDismiss = async () => {
    try {
      if (job.id) {
        await updateJobStatus(job.id, "dismissed");
      }
      setStatus("dismissed");
    } catch {
      setStatus("dismissed");
    }
  };

  const handleApply = async () => {
    if (!job.id || !resumeId) return;
    setApplying(true);
    setShowApplyConfirm(false);
    try {
      const result = await applyToJob(job.id, resumeId);
      setApplyResult(result);
      if (result.success) {
        setStatus("applied");
        if (onApplied) onApplied(job.id);
      }
    } catch (err) {
      setApplyResult({ success: false, notes: err.message });
    } finally {
      setApplying(false);
    }
  };

  if (status === "dismissed") {
    return null;
  }

  return (
    <div
      className={`bg-white rounded-xl border p-4 transition-shadow hover:shadow-md ${
        status === "saved"
          ? "border-brand-300 bg-brand-50/30"
          : status === "applied"
          ? "border-green-300 bg-green-50/30"
          : "border-gray-200"
      }`}
    >
      {/* New badge for alerts */}
      {job.is_new && (
        <span className="inline-block bg-brand-100 text-brand-700 text-[10px] font-bold px-1.5 py-0.5 rounded mb-2">
          جدید
        </span>
      )}

      {/* Applied badge */}
      {status === "applied" && (
        <span className="inline-block bg-green-100 text-green-700 text-[10px] font-bold px-1.5 py-0.5 rounded mb-2">
          درخواست ارسال شده
        </span>
      )}

      {/* Top row: title + score */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3
            className={`font-bold text-sm leading-tight truncate ${
              viewed ? "text-gray-500" : "text-gray-900"
            }`}
          >
            {job.title}
          </h3>
          <p className="text-sm text-gray-600 mt-0.5">{job.company}</p>
        </div>

        <div
          className={`shrink-0 border rounded-lg px-2 py-1 text-center ${getScoreColor(
            job.match_score
          )}`}
        >
          <div className="text-lg font-bold leading-none">
            {job.match_score}
          </div>
          <div className="text-[10px] opacity-70">امتیاز</div>
        </div>
      </div>

      {/* Badges row */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        <span className={getSiteBadgeClass(job.source_site)}>
          {SITE_LABELS[job.source_site] || job.source_site}
        </span>

        {job.is_remote && (
          <span className="badge bg-green-100 text-green-800">Remote</span>
        )}

        {job.location && !job.is_remote && (
          <span className="badge bg-gray-100 text-gray-700">
            {job.location}
          </span>
        )}

        {job.salary_range && (
          <span className="badge bg-amber-100 text-amber-800">
            {job.salary_range}
          </span>
        )}

        {viewed && (
          <span className="badge bg-gray-50 text-gray-400">مشاهده شده</span>
        )}
      </div>

      {/* Match reason */}
      {job.match_reason && !compact && (
        <p className="text-xs text-gray-500 mb-3 leading-relaxed line-clamp-2">
          {job.match_reason}
        </p>
      )}

      {/* Expanded description */}
      {expanded && job.description && (
        <div className="mb-3 p-2 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-600 leading-relaxed line-clamp-6 ltr">
            {job.description}
          </p>
        </div>
      )}

      {/* Apply confirmation modal */}
      {showApplyConfirm && (
        <div className="mb-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800 mb-2">
            آیا مطمئنید؟ رزومه شما به <strong>{job.company}</strong> ارسال
            می‌شود.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleApply}
              className="bg-green-600 hover:bg-green-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
            >
              بله، ارسال کن
            </button>
            <button
              onClick={() => setShowApplyConfirm(false)}
              className="bg-gray-200 hover:bg-gray-300 text-gray-700 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors"
            >
              انصراف
            </button>
          </div>
        </div>
      )}

      {/* Apply result feedback */}
      {applyResult && (
        <div
          className={`mb-3 p-2 rounded-lg text-xs ${
            applyResult.success
              ? "bg-green-50 text-green-800"
              : "bg-red-50 text-red-800"
          }`}
        >
          {applyResult.success
            ? "درخواست با موفقیت ارسال شد!"
            : `خطا: ${applyResult.notes}`}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={handleViewClick}
          className="flex-1 text-center bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium py-2 px-3 rounded-lg transition-colors"
        >
          مشاهده آگهی
        </a>

        {/* Auto-apply button */}
        {canAutoApply && (
          <button
            onClick={() => setShowApplyConfirm(true)}
            disabled={applying || !resumeId}
            className="flex items-center gap-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white text-xs font-medium py-2 px-3 rounded-lg transition-colors"
            title="ارسال خودکار رزومه"
          >
            {applying ? (
              <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
            )}
            ارسال
          </button>
        )}

        <button
          onClick={handleSave}
          className={`p-2 rounded-lg border transition-colors ${
            status === "saved"
              ? "bg-brand-50 border-brand-300 text-brand-700"
              : "border-gray-200 text-gray-400 hover:text-brand-600 hover:border-brand-300"
          }`}
          title={status === "saved" ? "ذخیره شده" : "ذخیره"}
        >
          <svg
            className="w-4 h-4"
            fill={status === "saved" ? "currentColor" : "none"}
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
            />
          </svg>
        </button>

        {!compact && (
          <>
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-2 rounded-lg border border-gray-200 text-gray-400 hover:text-gray-600 transition-colors"
              title="جزئیات"
            >
              <svg
                className={`w-4 h-4 transition-transform ${
                  expanded ? "rotate-180" : ""
                }`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>

            <button
              onClick={handleDismiss}
              className="p-2 rounded-lg border border-gray-200 text-gray-400 hover:text-red-500 hover:border-red-300 transition-colors"
              title="رد کردن"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default JobCard;
