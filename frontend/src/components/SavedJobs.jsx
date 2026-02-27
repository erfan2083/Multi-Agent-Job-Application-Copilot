import { useState, useEffect } from "react";
import JobCard from "./JobCard";
import { getJobs } from "../api";

function SavedJobs({ resumeId }) {
  const [savedJobs, setSavedJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadSavedJobs = async () => {
    if (!resumeId) return;
    setLoading(true);
    try {
      const jobs = await getJobs({ resumeId, status: "saved" });
      setSavedJobs(jobs);
    } catch {
      // Ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSavedJobs();
  }, [resumeId]);

  if (!resumeId) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div>
          <h2 className="font-bold text-gray-900">مشاغل ذخیره‌شده</h2>
          <p className="text-sm text-gray-500 mt-1">
            مشاغلی که از داشبورد ذخیره کرده‌اید
          </p>
        </div>
        <button
          onClick={loadSavedJobs}
          className="text-xs text-brand-600 hover:text-brand-800 font-medium"
        >
          بروزرسانی
        </button>
      </div>

      <div className="p-4">
        {loading && (
          <p className="text-sm text-gray-500 text-center py-4">
            در حال بارگذاری...
          </p>
        )}

        {!loading && savedJobs.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-4">
            هنوز شغلی ذخیره نشده است. از داشبورد مشاغل، دکمه نشانک را بزنید.
          </p>
        )}

        <div className="grid grid-cols-1 gap-3">
          {savedJobs.map((job) => (
            <JobCard key={job.id} job={job} compact resumeId={resumeId} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default SavedJobs;
