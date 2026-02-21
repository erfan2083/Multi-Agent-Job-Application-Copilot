import { useState, useEffect } from "react";
import {
  getSavedSearches,
  createSavedSearch,
  deleteSavedSearch,
  updateSavedSearch,
  runSavedSearch,
} from "../api";

function SavedSearches({ resumeId, preferencesId, onRunSearch, onJobsFound }) {
  const [searches, setSearches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saveName, setSaveName] = useState("");
  const [saving, setSaving] = useState(false);
  const [runningId, setRunningId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState("");

  const loadSearches = async () => {
    if (!resumeId) return;
    setLoading(true);
    try {
      const data = await getSavedSearches(resumeId);
      setSearches(data);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSearches();
  }, [resumeId]);

  const handleSave = async () => {
    if (!resumeId) return;
    setSaving(true);
    try {
      await createSavedSearch({
        resume_id: resumeId,
        preferences_id: preferencesId,
        name: saveName || undefined,
      });
      setSaveName("");
      await loadSearches();
    } catch {
      // Ignore
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteSavedSearch(id);
      setSearches((prev) => prev.filter((s) => s.id !== id));
    } catch {
      // Ignore
    }
  };

  const handleToggleActive = async (search) => {
    try {
      const updated = await updateSavedSearch(search.id, {
        is_active: !search.is_active,
      });
      setSearches((prev) =>
        prev.map((s) =>
          s.id === search.id ? updated.saved_search : s
        )
      );
    } catch {
      // Ignore
    }
  };

  const handleRename = async (id) => {
    if (!editName.trim()) {
      setEditingId(null);
      return;
    }
    try {
      const updated = await updateSavedSearch(id, { name: editName });
      setSearches((prev) =>
        prev.map((s) => (s.id === id ? updated.saved_search : s))
      );
    } catch {
      // Ignore
    }
    setEditingId(null);
    setEditName("");
  };

  const handleRun = async (search) => {
    setRunningId(search.id);
    if (onRunSearch) onRunSearch(search);

    try {
      await runSavedSearch(search.id, (event) => {
        if (event.type === "job" && onJobsFound) {
          onJobsFound(event.data);
        }
      });
    } catch {
      // Ignore
    } finally {
      setRunningId(null);
      await loadSearches();
    }
  };

  if (!resumeId) {
    return null;
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h2 className="font-bold text-gray-900">جستجوهای ذخیره‌شده</h2>
        <p className="text-sm text-gray-500 mt-1">
          جستجوهای خود را ذخیره کنید و هشدار مشاغل جدید دریافت کنید
        </p>
      </div>

      <div className="p-4 space-y-4">
        {/* Save current search */}
        {preferencesId && (
          <div className="flex gap-2">
            <input
              type="text"
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              placeholder="نام جستجو (اختیاری)"
              className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500"
            />
            <button
              onClick={handleSave}
              disabled={saving}
              className="bg-brand-600 hover:bg-brand-700 disabled:bg-gray-400 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
            >
              {saving ? "..." : "ذخیره جستجو"}
            </button>
          </div>
        )}

        {/* List of saved searches */}
        {loading && (
          <p className="text-sm text-gray-500 text-center py-4">
            در حال بارگذاری...
          </p>
        )}

        {!loading && searches.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">
            هنوز جستجویی ذخیره نشده است
          </p>
        )}

        <div className="space-y-2">
          {searches.map((search) => (
            <div
              key={search.id}
              className={`border rounded-lg p-3 transition-colors ${
                search.is_active
                  ? "border-gray-200"
                  : "border-gray-100 bg-gray-50 opacity-60"
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-2">
                {editingId === search.id ? (
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => handleRename(search.id)}
                    onKeyDown={(e) =>
                      e.key === "Enter" && handleRename(search.id)
                    }
                    autoFocus
                    className="flex-1 text-sm font-medium border border-brand-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                ) : (
                  <h4
                    className="text-sm font-medium text-gray-900 truncate cursor-pointer hover:text-brand-700"
                    onClick={() => {
                      setEditingId(search.id);
                      setEditName(search.name);
                    }}
                    title="Click to rename"
                  >
                    {search.name}
                  </h4>
                )}

                <div className="flex items-center gap-1 shrink-0">
                  {/* Toggle active */}
                  <button
                    onClick={() => handleToggleActive(search)}
                    className={`p-1.5 rounded transition-colors ${
                      search.is_active
                        ? "text-green-600 hover:bg-green-50"
                        : "text-gray-400 hover:bg-gray-100"
                    }`}
                    title={search.is_active ? "غیرفعال‌سازی" : "فعال‌سازی"}
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      {search.is_active ? (
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                        />
                      ) : (
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                        />
                      )}
                    </svg>
                  </button>

                  {/* Delete */}
                  <button
                    onClick={() => handleDelete(search.id)}
                    className="p-1.5 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                    title="حذف"
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Keywords */}
              {search.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {search.keywords.map((kw, i) => (
                    <span
                      key={i}
                      className="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded"
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              )}

              {/* Meta info */}
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>
                  {search.last_run_at
                    ? `آخرین اجرا: ${new Date(search.last_run_at).toLocaleDateString("fa-IR")}`
                    : "اجرا نشده"}
                </span>

                {/* Run button */}
                <button
                  onClick={() => handleRun(search)}
                  disabled={runningId === search.id}
                  className="inline-flex items-center gap-1 text-brand-600 hover:text-brand-800 font-medium disabled:opacity-50"
                >
                  {runningId === search.id ? (
                    <>
                      <span className="w-3 h-3 border-2 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
                      در حال جستجو
                    </>
                  ) : (
                    <>
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
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      اجرای مجدد
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default SavedSearches;
