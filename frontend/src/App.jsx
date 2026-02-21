import { useState, useEffect } from "react";
import ChatInterface from "./components/ChatInterface";
import ResumeUpload from "./components/ResumeUpload";
import JobDashboard from "./components/JobDashboard";
import StatusStream from "./components/StatusStream";
import SavedSearches from "./components/SavedSearches";
import AlertsPanel from "./components/AlertsPanel";
import ApplicationsPanel from "./components/ApplicationsPanel";
import LLMSelector from "./components/LLMSelector";
import { searchJobs, checkHealth, getAlertCount } from "./api";

function App() {
  const [resume, setResume] = useState(null);
  const [profile, setProfile] = useState(null);
  const [preferencesId, setPreferencesId] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [statusMessages, setStatusMessages] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchDone, setSearchDone] = useState(false);
  const [report, setReport] = useState("");
  const [backendOk, setBackendOk] = useState(null);
  const [activeTab, setActiveTab] = useState("chat");
  const [alertCount, setAlertCount] = useState(0);

  useEffect(() => {
    checkHealth()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false));
  }, []);

  // Periodically check alert count
  useEffect(() => {
    const loadAlertCount = () => {
      getAlertCount()
        .then((data) => setAlertCount(data.unread_count))
        .catch(() => {});
    };
    loadAlertCount();
    const interval = setInterval(loadAlertCount, 60000); // Every 60s
    return () => clearInterval(interval);
  }, []);

  const handleResumeUploaded = (data) => {
    setResume(data.resume);
    setProfile(data.profile);
    setStatusMessages((prev) => [
      ...prev,
      { type: "status", message: "رزومه با موفقیت آنالیز شد" },
    ]);
  };

  const handlePreferencesSet = (prefsId) => {
    setPreferencesId(prefsId);
    setStatusMessages((prev) => [
      ...prev,
      { type: "status", message: "ترجیحات شغلی ذخیره شد" },
    ]);
  };

  const handleStartSearch = async () => {
    if (!resume) return;

    setIsSearching(true);
    setSearchDone(false);
    setJobs([]);
    setReport("");
    setActiveTab("dashboard");

    setStatusMessages((prev) => [
      ...prev,
      { type: "status", message: "شروع جستجوی مشاغل..." },
    ]);

    try {
      await searchJobs(resume.id, preferencesId, (event) => {
        if (event.type === "status") {
          setStatusMessages((prev) => [...prev, event]);
        } else if (event.type === "job") {
          setJobs((prev) => [...prev, event.data]);
        } else if (event.type === "done") {
          setSearchDone(true);
          setIsSearching(false);
          setReport(event.report || "");
          setStatusMessages((prev) => [
            ...prev,
            {
              type: "status",
              message: `جستجو تمام شد! ${event.total} موقعیت شغلی با تطابق بالا پیدا شد.`,
            },
          ]);
        } else if (event.type === "error") {
          setStatusMessages((prev) => [
            ...prev,
            { type: "error", message: event.message },
          ]);
          setIsSearching(false);
        }
      });
    } catch (err) {
      setStatusMessages((prev) => [
        ...prev,
        { type: "error", message: `خطا: ${err.message}` },
      ]);
      setIsSearching(false);
    }
  };

  const handleSavedSearchRun = (search) => {
    setActiveTab("dashboard");
    setJobs([]);
    setIsSearching(true);
    setStatusMessages((prev) => [
      ...prev,
      {
        type: "status",
        message: `اجرای مجدد جستجوی ذخیره‌شده: ${search.name}...`,
      },
    ]);
  };

  const handleSavedSearchJobs = (jobData) => {
    setJobs((prev) => [...prev, jobData]);
  };

  return (
    <div className="min-h-screen bg-gray-50" dir="rtl">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xl font-bold">JH</span>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Job Hunter Agent
              </h1>
              <p className="text-sm text-gray-500">
                دستیار هوشمند جستجوی کار
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <LLMSelector />
            {backendOk === true && (
              <span className="inline-flex items-center gap-1 text-sm text-green-700 bg-green-50 px-2 py-1 rounded-full">
                <span className="w-2 h-2 bg-green-500 rounded-full" />
                متصل
              </span>
            )}
            {backendOk === false && (
              <span className="inline-flex items-center gap-1 text-sm text-red-700 bg-red-50 px-2 py-1 rounded-full">
                <span className="w-2 h-2 bg-red-500 rounded-full" />
                قطع
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="max-w-7xl mx-auto px-4 pt-4">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
          <button
            onClick={() => setActiveTab("chat")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "chat"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            چت و رزومه
          </button>
          <button
            onClick={() => setActiveTab("dashboard")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "dashboard"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            داشبورد مشاغل
            {jobs.length > 0 && (
              <span className="mr-1 bg-brand-100 text-brand-700 px-1.5 py-0.5 rounded-full text-xs">
                {jobs.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("saved")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "saved"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            جستجوهای ذخیره‌شده
          </button>
          <button
            onClick={() => setActiveTab("alerts")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors relative ${
              activeTab === "alerts"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            هشدارها
            {alertCount > 0 && (
              <span className="mr-1 bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full text-xs font-bold">
                {alertCount}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab("applications")}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === "applications"
                ? "bg-white text-brand-700 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            درخواست‌ها
          </button>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {activeTab === "chat" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Resume Upload + Profile */}
            <div className="lg:col-span-1 space-y-6">
              <ResumeUpload
                onUploaded={handleResumeUploaded}
                resume={resume}
                profile={profile}
              />

              {/* Search Button */}
              {resume && (
                <div className="bg-white rounded-xl border border-gray-200 p-4">
                  <button
                    onClick={handleStartSearch}
                    disabled={isSearching}
                    className="w-full bg-brand-600 hover:bg-brand-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {isSearching ? (
                      <>
                        <span className="flex gap-1">
                          <span className="pulse-dot w-2 h-2 bg-white rounded-full" />
                          <span className="pulse-dot w-2 h-2 bg-white rounded-full" />
                          <span className="pulse-dot w-2 h-2 bg-white rounded-full" />
                        </span>
                        در حال جستجو...
                      </>
                    ) : (
                      "شروع جستجوی مشاغل"
                    )}
                  </button>
                </div>
              )}

              {/* Status Stream */}
              {statusMessages.length > 0 && (
                <StatusStream messages={statusMessages} />
              )}
            </div>

            {/* Right: Chat Interface */}
            <div className="lg:col-span-2">
              <ChatInterface
                resumeId={resume?.id}
                onPreferencesSet={handlePreferencesSet}
              />
            </div>
          </div>
        )}

        {activeTab === "dashboard" && (
          <div>
            {report && (
              <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
                <h3 className="font-bold text-gray-900 mb-2">
                  گزارش جستجو
                </h3>
                <p className="text-gray-700 whitespace-pre-line text-sm">
                  {report}
                </p>
              </div>
            )}
            <JobDashboard
              jobs={jobs}
              isSearching={isSearching}
              resumeId={resume?.id}
            />
          </div>
        )}

        {activeTab === "saved" && (
          <div className="max-w-2xl mx-auto">
            <SavedSearches
              resumeId={resume?.id}
              preferencesId={preferencesId}
              onRunSearch={handleSavedSearchRun}
              onJobsFound={handleSavedSearchJobs}
            />

            {!resume && (
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
                    d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                  />
                </svg>
                <p className="text-gray-500">
                  ابتدا رزومه خود را آپلود کرده و جستجو انجام دهید تا بتوانید
                  جستجوها را ذخیره کنید.
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === "alerts" && (
          <AlertsPanel onAlertCountChange={setAlertCount} />
        )}

        {activeTab === "applications" && <ApplicationsPanel />}
      </main>
    </div>
  );
}

export default App;
