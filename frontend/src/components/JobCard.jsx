import { useState } from "react";
import { updateJobStatus } from "../api";

const SITE_LABELS = {
  jobinja: "Jobinja",
  irantalent: "IranTalent",
  jobvision: "JobVision",
  linkedin: "LinkedIn",
  indeed: "Indeed",
  remotive: "Remotive",
  weworkremotely: "WWR",
  wellfound: "Wellfound",
};

function getScoreColor(score) {
  if (score >= 80) return "score-high";
  if (score >= 60) return "score-mid";
  return "score-low";
}

function getSiteBadgeClass(site) {
  return `badge badge-${site}`;
}

function JobCard({ job }) {
  const [status, setStatus] = useState(job.status || "new");
  const [expanded, setExpanded] = useState(false);

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

  if (status === "dismissed") {
    return null;
  }

  return (
    <div
      className={`bg-white rounded-xl border p-4 transition-shadow hover:shadow-md ${
        status === "saved" ? "border-brand-300 bg-brand-50/30" : "border-gray-200"
      }`}
    >
      {/* Top row: title + score */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-gray-900 text-sm leading-tight truncate">
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
      </div>

      {/* Match reason */}
      {job.match_reason && (
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

      {/* Actions */}
      <div className="flex items-center gap-2">
        <a
          href={job.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 text-center bg-brand-600 hover:bg-brand-700 text-white text-xs font-medium py-2 px-3 rounded-lg transition-colors"
        >
          مشاهده آگهی
        </a>

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
      </div>
    </div>
  );
}

export default JobCard;
