import { useState, useEffect } from "react";
import { getAlerts, getAlertCount, markAlertRead, markAllAlertsRead } from "../api";
import JobCard from "./JobCard";

function AlertsPanel({ onAlertCountChange }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const loadAlerts = async () => {
    setLoading(true);
    try {
      const data = await getAlerts({ unreadOnly });
      setAlerts(data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  const loadCount = async () => {
    try {
      const data = await getAlertCount();
      setUnreadCount(data.unread_count);
      if (onAlertCountChange) onAlertCountChange(data.unread_count);
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    loadAlerts();
    loadCount();
  }, [unreadOnly]);

  const handleMarkRead = async (alertId) => {
    try {
      await markAlertRead(alertId);
      setAlerts((prev) =>
        prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
      if (onAlertCountChange) onAlertCountChange(Math.max(0, unreadCount - 1));
    } catch {
      // Ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllAlertsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      setUnreadCount(0);
      if (onAlertCountChange) onAlertCountChange(0);
    } catch {
      // Ignore
    }
  };

  return (
    <div>
      {/* Header bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="font-bold text-gray-900">هشدارهای شغلی</h2>
            {unreadCount > 0 && (
              <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">
                {unreadCount} خوانده نشده
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={unreadOnly}
                onChange={(e) => setUnreadOnly(e.target.checked)}
                className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
              />
              فقط خوانده‌نشده
            </label>

            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-sm text-brand-600 hover:text-brand-800 font-medium"
              >
                خواندن همه
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Alert list */}
      {loading && (
        <div className="text-center py-16">
          <div className="w-12 h-12 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">در حال بارگذاری هشدارها...</p>
        </div>
      )}

      {!loading && alerts.length === 0 && (
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
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
          <p className="text-gray-500">
            {unreadOnly
              ? "هشدار خوانده‌نشده‌ای وجود ندارد"
              : "هنوز هشداری ثبت نشده است. یک جستجوی ذخیره‌شده اجرا کنید تا هشدار مشاغل جدید دریافت کنید."}
          </p>
        </div>
      )}

      <div className="space-y-3">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={`rounded-xl border transition-colors ${
              alert.is_read
                ? "border-gray-200 bg-white"
                : "border-brand-200 bg-brand-50/30"
            }`}
          >
            {/* Alert header */}
            <div className="flex items-center justify-between px-4 pt-3 pb-1">
              <div className="flex items-center gap-2">
                {!alert.is_read && (
                  <span className="w-2 h-2 bg-brand-500 rounded-full" />
                )}
                <span className="text-xs text-gray-400">
                  {new Date(alert.created_at).toLocaleDateString("fa-IR")} -{" "}
                  {new Date(alert.created_at).toLocaleTimeString("fa-IR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>

              {!alert.is_read && (
                <button
                  onClick={() => handleMarkRead(alert.id)}
                  className="text-xs text-brand-600 hover:text-brand-800"
                >
                  خوانده شد
                </button>
              )}
            </div>

            {/* Job card */}
            {alert.job && (
              <div className="px-3 pb-3">
                <JobCard job={alert.job} compact />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default AlertsPanel;
