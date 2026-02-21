import { useState, useEffect } from "react";
import { getApplications } from "../api";

const STATUS_COLORS = {
  submitted: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

const STATUS_LABELS = {
  submitted: "ارسال شده",
  pending: "در انتظار",
  failed: "ناموفق",
};

function ApplicationsPanel() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");

  useEffect(() => {
    setLoading(true);
    getApplications({ status: filterStatus || undefined })
      .then(setApps)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filterStatus]);

  const submitted = apps.filter((a) => a.status === "submitted").length;
  const failed = apps.filter((a) => a.status === "failed").length;

  return (
    <div>
      {/* Stats */}
      {apps.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="bg-white rounded-xl border border-gray-200 p-3 text-center">
            <div className="text-2xl font-bold text-gray-900">{apps.length}</div>
            <div className="text-xs text-gray-500">کل درخواست‌ها</div>
          </div>
          <div className="bg-white rounded-xl border border-green-200 p-3 text-center">
            <div className="text-2xl font-bold text-green-700">{submitted}</div>
            <div className="text-xs text-green-600">ارسال شده</div>
          </div>
          <div className="bg-white rounded-xl border border-red-200 p-3 text-center">
            <div className="text-2xl font-bold text-red-700">{failed}</div>
            <div className="text-xs text-red-600">ناموفق</div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-600">وضعیت:</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-500"
          >
            <option value="">همه</option>
            <option value="submitted">ارسال شده</option>
            <option value="pending">در انتظار</option>
            <option value="failed">ناموفق</option>
          </select>
        </div>
      </div>

      {/* List */}
      {loading && (
        <div className="text-center py-16">
          <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">در حال بارگذاری...</p>
        </div>
      )}

      {!loading && apps.length === 0 && (
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-gray-500">
            هنوز درخواستی ارسال نشده است. از دکمه «ارسال خودکار» روی کارت‌های
            شغلی استفاده کنید.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {apps.map((app) => (
          <div
            key={app.id}
            className="bg-white rounded-xl border border-gray-200 p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-900">
                درخواست #{app.id}
              </span>
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                  STATUS_COLORS[app.status] || "bg-gray-100 text-gray-700"
                }`}
              >
                {STATUS_LABELS[app.status] || app.status}
              </span>
            </div>

            <div className="text-xs text-gray-500 space-y-1">
              <p>شغل: #{app.job_id}</p>
              <p>
                روش: {app.method === "auto" ? "خودکار" : "دستی"}
              </p>
              {app.applied_at && (
                <p>
                  تاریخ:{" "}
                  {new Date(app.applied_at).toLocaleDateString("fa-IR")} -{" "}
                  {new Date(app.applied_at).toLocaleTimeString("fa-IR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              )}
              {app.notes && (
                <p className="text-gray-400 mt-1 ltr text-left">
                  {app.notes}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ApplicationsPanel;
