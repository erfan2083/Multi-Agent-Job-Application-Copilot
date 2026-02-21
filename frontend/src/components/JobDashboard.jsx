import { useState, useEffect } from "react";
import JobCard from "./JobCard";
import { getJobs, getExportCsvUrl } from "../api";

const SORT_OPTIONS = [
  { value: "match_score", label: "امتیاز تطابق" },
  { value: "found_at", label: "تاریخ" },
];

const SOURCE_OPTIONS = [
  { value: "", label: "همه سایت‌ها" },
  { value: "jobinja", label: "Jobinja" },
  { value: "irantalent", label: "IranTalent" },
  { value: "jobvision", label: "JobVision" },
  { value: "linkedin", label: "LinkedIn" },
  { value: "indeed", label: "Indeed" },
  { value: "remotive", label: "Remotive" },
  { value: "weworkremotely", label: "WeWorkRemotely" },
  { value: "wellfound", label: "Wellfound" },
];

const STATUS_OPTIONS = [
  { value: "", label: "همه وضعیت‌ها" },
  { value: "new", label: "جدید" },
  { value: "saved", label: "ذخیره‌شده" },
];

function JobDashboard({ jobs: streamedJobs, isSearching, resumeId }) {
  const [storedJobs, setStoredJobs] = useState([]);
  const [sortBy, setSortBy] = useState("match_score");
  const [filterSource, setFilterSource] = useState("");
  const [filterRemote, setFilterRemote] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [minScore, setMinScore] = useState(0);

  // Load stored jobs when not searching
  useEffect(() => {
    if (!isSearching && streamedJobs.length === 0 && resumeId) {
      getJobs({ resumeId })
        .then(setStoredJobs)
        .catch(() => {});
    }
  }, [isSearching, resumeId, streamedJobs.length]);

  // Use streamed jobs if available, otherwise stored jobs
  const allJobs = streamedJobs.length > 0 ? streamedJobs : storedJobs;

  // Filter and sort
  let displayJobs = [...allJobs];

  if (filterSource) {
    displayJobs = displayJobs.filter((j) => j.source_site === filterSource);
  }

  if (filterRemote) {
    displayJobs = displayJobs.filter((j) => j.is_remote);
  }

  if (filterStatus) {
    displayJobs = displayJobs.filter((j) => (j.status || "new") === filterStatus);
  }

  if (minScore > 0) {
    displayJobs = displayJobs.filter(
      (j) => (j.match_score || 0) >= minScore
    );
  }

  displayJobs.sort((a, b) => {
    if (sortBy === "match_score") {
      return (b.match_score || 0) - (a.match_score || 0);
    }
    return 0; // Default order for date (already ordered)
  });

  // Stats
  const totalJobs = allJobs.length;
  const highMatch = allJobs.filter((j) => (j.match_score || 0) >= 80).length;
  const midMatch = allJobs.filter(
    (j) => (j.match_score || 0) >= 60 && (j.match_score || 0) < 80
  ).length;
  const remotJobs = allJobs.filter((j) => j.is_remote).length;
  const savedJobs = allJobs.filter((j) => j.status === "saved").length;

  const handleExportCsv = () => {
    const url = getExportCsvUrl({
      resumeId,
      minScore: minScore > 0 ? minScore : undefined,
      source: filterSource || undefined,
      status: filterStatus || undefined,
    });
    window.open(url, "_blank");
  };

  return (
    <div>
      {/* Stats bar */}
      {totalJobs > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-3 text-center">
            <div className="text-2xl font-bold text-gray-900">{totalJobs}</div>
            <div className="text-xs text-gray-500">کل مشاغل</div>
          </div>
          <div className="bg-white rounded-xl border border-green-200 p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{highMatch}</div>
            <div className="text-xs text-green-600">تطابق بالا (80+)</div>
          </div>
          <div className="bg-white rounded-xl border border-yellow-200 p-3 text-center">
            <div className="text-2xl font-bold text-yellow-700">{midMatch}</div>
            <div className="text-xs text-yellow-600">تطابق متوسط (60-79)</div>
          </div>
          <div className="bg-white rounded-xl border border-blue-200 p-3 text-center">
            <div className="text-2xl font-bold text-blue-700">{remotJobs}</div>
            <div className="text-xs text-blue-600">ریموت</div>
          </div>
          <div className="bg-white rounded-xl border border-brand-200 p-3 text-center">
            <div className="text-2xl font-bold text-brand-700">{savedJobs}</div>
            <div className="text-xs text-brand-600">ذخیره‌شده</div>
          </div>
        </div>
      )}

      {/* Filters + Export */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-4">
          {/* Sort */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">مرتب‌سازی:</label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Source filter */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">سایت:</label>
            <select
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {SOURCE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Status filter */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">وضعیت:</label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Remote filter */}
          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox"
              checked={filterRemote}
              onChange={(e) => setFilterRemote(e.target.checked)}
              className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            فقط ریموت
          </label>

          {/* Min score filter */}
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">حداقل امتیاز:</label>
            <input
              type="range"
              min={0}
              max={100}
              step={10}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              className="w-24"
            />
            <span className="text-sm text-gray-700 w-8">{minScore}</span>
          </div>

          {/* Spacer */}
          <div className="flex-1" />

          {/* CSV Export */}
          {totalJobs > 0 && (
            <button
              onClick={handleExportCsv}
              className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-brand-700 border border-gray-300 hover:border-brand-300 rounded-lg px-3 py-1.5 transition-colors"
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
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              خروجی CSV
            </button>
          )}
        </div>
      </div>

      {/* Job grid */}
      {isSearching && displayJobs.length === 0 && (
        <div className="text-center py-16">
          <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">در حال جستجو و بررسی مشاغل...</p>
        </div>
      )}

      {!isSearching && displayJobs.length === 0 && (
        <div className="text-center py-16">
          <svg
            className="w-16 h-16 text-gray-300 mx-auto mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <p className="text-gray-500">
            هنوز جستجویی انجام نشده است. رزومه خود را آپلود کرده و جستجو را
            شروع کنید.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {displayJobs.map((job, idx) => (
          <JobCard key={job.url || idx} job={job} />
        ))}
      </div>
    </div>
  );
}

export default JobDashboard;
