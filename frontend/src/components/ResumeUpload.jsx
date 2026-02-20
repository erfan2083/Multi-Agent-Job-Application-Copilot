import { useState, useRef } from "react";
import { uploadResume } from "../api";

function ResumeUpload({ onUploaded, resume, profile }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFile = async (file) => {
    if (!file) return;

    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx", "doc"].includes(ext)) {
      setError("فقط فایل‌های PDF و DOCX پشتیبانی می‌شوند");
      return;
    }

    setUploading(true);
    setError("");

    try {
      const data = await uploadResume(file);
      onUploaded(data);
    } catch (err) {
      setError(err.message || "خطا در آپلود رزومه");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="p-4 border-b border-gray-100">
        <h2 className="font-bold text-gray-900">آپلود رزومه</h2>
        <p className="text-sm text-gray-500 mt-1">
          فایل PDF یا DOCX خود را آپلود کنید
        </p>
      </div>

      <div className="p-4">
        {!resume ? (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              dragOver
                ? "border-brand-500 bg-brand-50"
                : "border-gray-300 hover:border-brand-400 hover:bg-gray-50"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={(e) => handleFile(e.target.files[0])}
              className="hidden"
            />

            {uploading ? (
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
                <p className="text-sm text-gray-600">در حال آنالیز رزومه...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <svg
                  className="w-10 h-10 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                  />
                </svg>
                <p className="text-sm text-gray-600">
                  فایل را اینجا بکشید یا کلیک کنید
                </p>
                <p className="text-xs text-gray-400">PDF, DOCX</p>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {/* Uploaded file info */}
            <div className="flex items-center gap-2 p-2 bg-green-50 rounded-lg">
              <svg
                className="w-5 h-5 text-green-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-sm text-green-800 font-medium">
                {resume.filename}
              </span>
            </div>

            {/* Profile summary */}
            {profile && (
              <div className="space-y-2">
                {profile.full_name && (
                  <p className="text-sm font-medium text-gray-900">
                    {profile.full_name}
                  </p>
                )}

                {profile.job_titles?.length > 0 && (
                  <p className="text-xs text-gray-600">
                    {profile.job_titles.join(" | ")}
                  </p>
                )}

                {profile.total_experience_years > 0 && (
                  <p className="text-xs text-gray-500">
                    {profile.total_experience_years} سال تجربه
                  </p>
                )}

                {profile.skills?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {profile.skills.slice(0, 10).map((skill, i) => (
                      <span
                        key={i}
                        className="inline-block bg-gray-100 text-gray-700 text-xs px-2 py-0.5 rounded"
                      >
                        {skill}
                      </span>
                    ))}
                    {profile.skills.length > 10 && (
                      <span className="text-xs text-gray-400">
                        +{profile.skills.length - 10} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Re-upload button */}
            <button
              onClick={() => {
                onUploaded({ resume: null, profile: null });
                fileInputRef.current?.value && (fileInputRef.current.value = "");
              }}
              className="text-xs text-brand-600 hover:text-brand-800 underline"
            >
              آپلود رزومه جدید
            </button>
          </div>
        )}

        {error && (
          <p className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}

export default ResumeUpload;
