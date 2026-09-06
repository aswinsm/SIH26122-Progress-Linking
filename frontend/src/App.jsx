import { useEffect, useMemo, useRef, useState } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

const NAV_ITEMS = [
  { id: "overview", label: "Dashboard", icon: "▦" },
  { id: "capture", label: "Capture Progress", icon: "↑" },
  { id: "review", label: "Planner Review", icon: "✓" },
  { id: "schedule", label: "Project Schedule", icon: "▤" },
];

function App() {
  const [page, setPage] = useState("overview");

  const [backendOnline, setBackendOnline] = useState(false);
  const [schedule, setSchedule] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [latestResult, setLatestResult] = useState(null);

  const [inputMode, setInputMode] = useState("text");
  const [dprText, setDprText] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);

  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [scheduleSearch, setScheduleSearch] = useState("");
  const [scheduleStatusFilter, setScheduleStatusFilter] =
    useState("all");

  const [reviewSearch, setReviewSearch] = useState("");

  const [changingId, setChangingId] = useState(null);
  const [replacementActivity, setReplacementActivity] =
    useState("");

  const fileInputRef = useRef(null);

  // ============================================================
  // INITIAL LOAD
  // ============================================================

  useEffect(() => {
    refreshSystem();
  }, []);

  async function refreshSystem() {
    await Promise.all([
      checkHealth(),
      loadSchedule(),
      loadPendingReviews(),
      loadLatestProcessingResult(),
    ]);
  }

  async function checkHealth() {
    try {
      const response = await fetch(
        `${API_BASE}/health`
      );

      setBackendOnline(
        response.ok
      );
    } catch {
      setBackendOnline(false);
    }
  }

  async function loadSchedule() {
    try {
      const response = await fetch(
        `${API_BASE}/schedule-activities`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setSchedule(
        data.activities || []
      );
    } catch (err) {
      console.error(
        "Schedule load failed:",
        err
      );
    }
  }

  async function loadPendingReviews() {
    try {
      const response = await fetch(
        `${API_BASE}/reviews/pending`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setReviews(
        data.reviews || []
      );
    } catch (err) {
      console.error(
        "Review load failed:",
        err
      );
    }
  }

  async function loadLatestProcessingResult() {
    try {
      const response = await fetch(
        `${API_BASE}/processing/latest`
      );

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      setLatestResult(
        data.result || null
      );
    } catch (err) {
      console.error(
        "Latest result load failed:",
        err
      );
    }
  }

  // ============================================================
  // PAGE HELPERS
  // ============================================================

  function openScheduleFilter(filter) {
    setScheduleStatusFilter(filter);
    setScheduleSearch("");
    clearMessages();
    setPage("schedule");
    loadSchedule();
  }

  function openPlannerReview() {
    clearMessages();
    setPage("review");
    loadPendingReviews();
  }

  // ============================================================
  // TEXT DPR
  // ============================================================

  async function processTextDpr() {
    clearMessages();

    if (!dprText.trim()) {
      setError(
        "Enter a DPR or supervisor progress update first."
      );
      return;
    }

    setProcessing(true);

    try {
      const response = await fetch(
        `${API_BASE}/process-dpr`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            text: dprText,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "DPR processing failed."
        );
      }

      setLatestResult(data);

      setMessage(
        "Progress report processed successfully."
      );

      await Promise.all([
        loadPendingReviews(),
        loadSchedule(),
      ]);

      setPage("review");
    } catch (err) {
      setError(
        err.message
      );
    } finally {
      setProcessing(false);
    }
  }

  // ============================================================
  // FILE / VOICE / SCAN
  // ============================================================

  async function processFile() {
    clearMessages();

    if (!selectedFile) {
      setError(
        "Choose a file first."
      );
      return;
    }

    let endpoint =
      "/process-file";

    if (inputMode === "voice") {
      endpoint =
        "/process-audio";
    } else if (
      inputMode === "scan"
    ) {
      endpoint =
        "/process-scan";
    }

    const formData =
      new FormData();

    formData.append(
      "file",
      selectedFile,
      selectedFile.name
    );

    setProcessing(true);

    try {
      const response = await fetch(
        `${API_BASE}${endpoint}`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Input processing failed."
        );
      }

      setLatestResult(data);

      setMessage(
        `${selectedFile.name} processed successfully.`
      );

      setSelectedFile(null);

      if (
        fileInputRef.current
      ) {
        fileInputRef.current.value =
          "";
      }

      await Promise.all([
        loadPendingReviews(),
        loadSchedule(),
      ]);

      setPage("review");
    } catch (err) {
      setError(
        err.message ||
          "Could not process the uploaded file."
      );
    } finally {
      setProcessing(false);
    }
  }

  function openFilePicker() {
    if (
      !fileInputRef.current
    ) {
      return;
    }

    fileInputRef.current.value =
      "";

    fileInputRef.current.click();
  }

  // ============================================================
  // PLANNER REVIEW
  // ============================================================

  async function acceptMatch(id) {
    clearMessages();

    try {
      const response = await fetch(
        `${API_BASE}/reviews/${id}/accept`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not accept match."
        );
      }

      setMessage(
        "Activity accepted and live schedule updated."
      );

      await Promise.all([
        loadPendingReviews(),
        loadSchedule(),
        loadLatestProcessingResult(),
      ]);
    } catch (err) {
      setError(
        err.message
      );
    }
  }

  async function rejectMatch(id) {
    clearMessages();

    try {
      const response = await fetch(
        `${API_BASE}/reviews/${id}/reject`,
        {
          method: "POST",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not reject match."
        );
      }

      setMessage(
        "Activity match rejected."
      );

      await loadPendingReviews();
    } catch (err) {
      setError(
        err.message
      );
    }
  }

  async function changeMatch(id) {
    clearMessages();

    if (
      !replacementActivity
    ) {
      setError(
        "Choose the correct schedule activity."
      );
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/reviews/${id}/change`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            activity_id:
              replacementActivity,
          }),
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not change match."
        );
      }

      setChangingId(null);
      setReplacementActivity("");

      setMessage(
        "Match changed and progress applied to the selected schedule activity."
      );

      await Promise.all([
        loadPendingReviews(),
        loadSchedule(),
        loadLatestProcessingResult(),
      ]);
    } catch (err) {
      setError(
        err.message
      );
    }
  }

  // ============================================================
  // CLEAR DATA
  // ============================================================

  async function clearAllEnteredData() {
    const confirmed =
      window.confirm(
        "Delete all entered DPRs, planner reviews and actual progress?\n\nThe master schedule will be preserved."
      );

    if (!confirmed) {
      return;
    }

    clearMessages();

    try {
      const response = await fetch(
        `${API_BASE}/data/reset`,
        {
          method: "DELETE",
        }
      );

      const data =
        await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Could not clear entered data."
        );
      }

      setLatestResult(null);
      setReviews([]);
      setDprText("");
      setSelectedFile(null);

      if (
        fileInputRef.current
      ) {
        fileInputRef.current.value =
          "";
      }

      await Promise.all([
        loadSchedule(),
        loadPendingReviews(),
      ]);

      setMessage(
        "All entered progress data has been cleared."
      );

      setPage("overview");
    } catch (err) {
      setError(
        err.message ||
          "Could not clear entered data."
      );
    }
  }

  function clearMessages() {
    setMessage("");
    setError("");
  }

  // ============================================================
  // STATISTICS
  // ============================================================

  const stats =
    useMemo(() => {
      const total =
        schedule.length;

      const completed =
        schedule.filter(
          (activity) =>
            Number(
              activity.progress_percent ||
                0
            ) >= 100
        ).length;

      const inProgress =
        schedule.filter(
          (activity) => {
            const progress =
              Number(
                activity.progress_percent ||
                  0
              );

            return (
              progress > 0 &&
              progress < 100
            );
          }
        ).length;

      const notStarted =
        schedule.filter(
          (activity) =>
            Number(
              activity.progress_percent ||
                0
            ) === 0
        ).length;

      const averageProgress =
        total === 0
          ? 0
          : schedule.reduce(
              (
                sum,
                activity
              ) =>
                sum +
                Number(
                  activity.progress_percent ||
                    0
                ),
              0
            ) / total;

      return {
        total,
        completed,
        inProgress,
        notStarted,
        averageProgress,
      };
    }, [schedule]);

  // ============================================================
  // FILTERED SCHEDULE
  // ============================================================

  const filteredSchedule =
    useMemo(() => {
      let result =
        [...schedule];

      if (
        scheduleStatusFilter ===
        "completed"
      ) {
        result =
          result.filter(
            (activity) =>
              Number(
                activity.progress_percent ||
                  0
              ) >= 100
          );
      }

      if (
        scheduleStatusFilter ===
        "in-progress"
      ) {
        result =
          result.filter(
            (activity) => {
              const progress =
                Number(
                  activity.progress_percent ||
                    0
                );

              return (
                progress > 0 &&
                progress < 100
              );
            }
          );
      }

      if (
        scheduleStatusFilter ===
        "not-started"
      ) {
        result =
          result.filter(
            (activity) =>
              Number(
                activity.progress_percent ||
                  0
              ) === 0
          );
      }

      const query =
        scheduleSearch
          .trim()
          .toLowerCase();

      if (!query) {
        return result;
      }

      return result.filter(
        (activity) =>
          [
            activity.activity_id,
            activity.activity_name,
            activity.discipline,
            activity.wbs,
          ].some((value) =>
            String(
              value || ""
            )
              .toLowerCase()
              .includes(query)
          )
      );
    }, [
      schedule,
      scheduleSearch,
      scheduleStatusFilter,
    ]);

  // ============================================================
  // FILTERED REVIEWS
  // ============================================================

  const filteredReviews =
    useMemo(() => {
      const query =
        reviewSearch
          .trim()
          .toLowerCase();

      if (!query) {
        return reviews;
      }

      return reviews.filter(
        (review) =>
          [
            review.activity_description,
            review.activity_id,
            review.matched_activity_name,
            review.status,
          ].some((value) =>
            String(
              value || ""
            )
              .toLowerCase()
              .includes(query)
          )
      );
    }, [
      reviews,
      reviewSearch,
    ]);

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="shell">
      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            PL
          </div>

          <div>
            <h2>
              ProgressLink
            </h2>

            <p>
              Planning → Execution Bridge
            </p>
          </div>
        </div>

        <nav className="nav">
          {NAV_ITEMS.map(
            (item) => (
              <button
                key={item.id}
                className={`nav-item ${
                  page === item.id
                    ? "active"
                    : ""
                }`}
                onClick={() => {
                  setPage(
                    item.id
                  );

                  clearMessages();

                  if (
                    item.id ===
                    "review"
                  ) {
                    loadPendingReviews();
                  }

                  if (
                    item.id ===
                    "schedule"
                  ) {
                    setScheduleStatusFilter(
                      "all"
                    );

                    loadSchedule();
                  }
                }}
              >
                <span className="nav-icon">
                  {item.icon}
                </span>

                <span>
                  {item.label}
                </span>

                {item.id ===
                  "review" &&
                  reviews.length >
                    0 && (
                    <span className="nav-count">
                      {
                        reviews.length
                      }
                    </span>
                  )}
              </button>
            )
          )}
        </nav>

        <div className="system-card">
          <div className="system-card-title">
            <span
              className={`status-dot ${
                backendOnline
                  ? "online"
                  : "offline"
              }`}
            />

            {backendOnline
              ? "System Online"
              : "Backend Offline"}
          </div>

          <p>
            AI extraction,
            schedule matching and
            planner verification
            workflow.
          </p>
        </div>

        <div className="team-name">
          SIH26122 · Tech Titans
        </div>
      </aside>

      {/* ======================================================
          MAIN
      ====================================================== */}

      <main className="main">
        <header className="topbar">
          <div>
            <p className="eyebrow">
              SIH26122
            </p>

            <h1>
              {page ===
                "overview" &&
                "Project Progress Dashboard"}

              {page ===
                "capture" &&
                "Capture Site Progress"}

              {page ===
                "review" &&
                "Planner Review"}

              {page ===
                "schedule" &&
                "Live Project Schedule"}
            </h1>
          </div>

          <div className="header-actions">
            <button
              className="refresh-btn"
              onClick={
                refreshSystem
              }
            >
              ↻ Refresh Data
            </button>

            <button
              className="clear-data-btn"
              onClick={
                clearAllEnteredData
              }
            >
              Clear Data
            </button>
          </div>
        </header>

        {message && (
          <div className="notice success-notice">
            {message}
          </div>
        )}

        {error && (
          <div className="notice error-notice">
            {error}
          </div>
        )}

        {/* ====================================================
            DASHBOARD
        ==================================================== */}

        {page ===
          "overview" && (
          <InteractiveDashboard
            stats={stats}
            pendingReviews={
              reviews.length
            }
            latestResult={
              latestResult
            }
            openScheduleFilter={
              openScheduleFilter
            }
            openPlannerReview={
              openPlannerReview
            }
            setPage={
              setPage
            }
          />
        )}

        {/* ====================================================
            CAPTURE SITE PROGRESS
        ==================================================== */}

        {page ===
          "capture" && (
          <section>
            <div className="capture-intro">
              <p>
                Submit actual site
                progress in any
                supported format.
              </p>
            </div>

            <div className="mode-tabs">
              <ModeButton
                label="Typed Update"
                icon="✎"
                active={
                  inputMode ===
                  "text"
                }
                onClick={() => {
                  setInputMode(
                    "text"
                  );

                  setSelectedFile(
                    null
                  );

                  clearMessages();
                }}
              />

              <ModeButton
                label="DPR File"
                icon="▤"
                active={
                  inputMode ===
                  "file"
                }
                onClick={() => {
                  setInputMode(
                    "file"
                  );

                  setSelectedFile(
                    null
                  );

                  clearMessages();
                }}
              />

              <ModeButton
                label="Voice Update"
                icon="◉"
                active={
                  inputMode ===
                  "voice"
                }
                onClick={() => {
                  setInputMode(
                    "voice"
                  );

                  setSelectedFile(
                    null
                  );

                  clearMessages();
                }}
              />

              <ModeButton
                label="Scanned Note"
                icon="◫"
                active={
                  inputMode ===
                  "scan"
                }
                onClick={() => {
                  setInputMode(
                    "scan"
                  );

                  setSelectedFile(
                    null
                  );

                  clearMessages();
                }}
              />
            </div>

            <div className="capture-layout">
              <div className="card capture-card">
                {inputMode ===
                "text" ? (
                  <>
                    <h3>
                      Typed Supervisor /
                      Site Update
                    </h3>

                    <p className="muted">
                      Include actual
                      percentage or
                      completed quantities
                      whenever available.
                    </p>

                    <textarea
                      className="dpr-textarea"
                      value={
                        dprText
                      }
                      onChange={(
                        event
                      ) =>
                        setDprText(
                          event
                            .target
                            .value
                        )
                      }
                      placeholder={
                        "Example:\nRoad signboard installation at East Section is 63% complete.\nWaterproofing membrane in Zone B reached 47%.\nF101 concreting completed."
                      }
                    />

                    <button
                      className="primary-action"
                      onClick={
                        processTextDpr
                      }
                      disabled={
                        processing
                      }
                    >
                      {processing
                        ? "Processing..."
                        : "Process Progress Update"}
                    </button>
                  </>
                ) : (
                  <>
                    <h3>
                      {inputMode ===
                        "file" &&
                        "Upload DPR File"}

                      {inputMode ===
                        "voice" &&
                        "Upload Supervisor Voice Update"}

                      {inputMode ===
                        "scan" &&
                        "Upload Scanned Site Note"}
                    </h3>

                    <p className="muted">
                      {inputMode ===
                        "file" &&
                        "Supported: XLSX, XLSM, CSV, PDF and TXT."}

                      {inputMode ===
                        "voice" &&
                        "Supported: M4A, MP3, WAV, OGG, WEBM, MP4, MPEG, MPGA and FLAC."}

                      {inputMode ===
                        "scan" &&
                        "Supported: JPG, JPEG, PNG, WEBP and scanned PDF."}
                    </p>

                    <div
                      className="drop-area"
                      onClick={
                        openFilePicker
                      }
                    >
                      <input
                        ref={
                          fileInputRef
                        }
                        type="file"
                        hidden
                        onChange={(
                          event
                        ) =>
                          setSelectedFile(
                            event
                              .target
                              .files?.[0] ||
                              null
                          )
                        }
                        accept={
                          inputMode ===
                          "file"
                            ? ".xlsx,.xlsm,.csv,.pdf,.txt"
                            : inputMode ===
                              "voice"
                            ? ".m4a,.mp3,.wav,.ogg,.webm,.mp4,.mpeg,.mpga,.flac"
                            : ".jpg,.jpeg,.png,.webp,.pdf"
                        }
                      />

                      <div className="upload-symbol">
                        ↑
                      </div>

                      {selectedFile ? (
                        <>
                          <strong>
                            {
                              selectedFile.name
                            }
                          </strong>

                          <span>
                            {formatFileSize(
                              selectedFile.size
                            )}
                          </span>
                        </>
                      ) : (
                        <>
                          <strong>
                            Choose a file
                          </strong>

                          <span>
                            Click to browse
                          </span>
                        </>
                      )}
                    </div>

                    <button
                      className="primary-action"
                      onClick={
                        processFile
                      }
                      disabled={
                        processing ||
                        !selectedFile
                      }
                    >
                      {processing
                        ? "Processing..."
                        : "Process Progress Input"}
                    </button>
                  </>
                )}
              </div>

              <div className="card extraction-guide">
                <h3>
                  What the system
                  extracts
                </h3>

                <ExtractionField
                  label="Activity"
                  detail="Actual construction work reported"
                />

                <ExtractionField
                  label="Discipline"
                  detail="Civil, Piping, Electrical, Mechanical, Instrumentation, HSE"
                />

                <ExtractionField
                  label="Status"
                  detail="Started, In Progress, Completed, Delayed"
                />

                <ExtractionField
                  label="Progress"
                  detail="Actual percentage or quantity-derived percentage"
                />

                <ExtractionField
                  label="Tag"
                  detail="Foundation, line, equipment or structure identifier"
                />

                <ExtractionField
                  label="Date"
                  detail="Actual reporting or execution date"
                />

                <div className="guide-note">
                  In-progress
                  percentages are never
                  invented. If a DPR does
                  not provide quantitative
                  progress, the existing
                  percentage remains
                  unchanged.
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ====================================================
            REVIEW
        ==================================================== */}

        {page ===
          "review" && (
          <section>
            <div className="review-toolbar">
              <div>
                <strong>
                  {
                    reviews.length
                  }
                </strong>{" "}
                activities require
                planner verification
              </div>

              <input
                className="search-input"
                value={
                  reviewSearch
                }
                onChange={(
                  event
                ) =>
                  setReviewSearch(
                    event.target
                      .value
                  )
                }
                placeholder="Search pending reviews..."
              />
            </div>

            {latestResult
              ?.activities
              ?.length > 0 && (
              <div className="card latest-ai-card">
                <div className="card-heading">
                  <div>
                    <h3>
                      Latest AI
                      Matching Result
                    </h3>

                    <p>
                      Extracted
                      activities with
                      top schedule
                      candidates.
                    </p>
                  </div>
                </div>

                {(
                  latestResult.activities ||
                  []
                ).map(
                  (
                    item,
                    index
                  ) => (
                    <LatestMatchDetail
                      key={
                        index
                      }
                      item={
                        item
                      }
                    />
                  )
                )}
              </div>
            )}

            <div className="review-list">
              {filteredReviews.length ===
              0 ? (
                <div className="empty-state">
                  <div className="empty-check">
                    ✓
                  </div>

                  <h3>
                    No pending
                    planner reviews
                  </h3>

                  <p>
                    Process another
                    site progress
                    update or refresh
                    the review queue.
                  </p>

                  <button
                    className="secondary-action"
                    onClick={
                      loadPendingReviews
                    }
                  >
                    Refresh Queue
                  </button>
                </div>
              ) : (
                filteredReviews.map(
                  (review) => (
                    <div
                      className="review-card"
                      key={
                        review.id
                      }
                    >
                      <div className="review-main">
                        <div className="review-top">
                          <div>
                            <span className="review-id">
                              Review #
                              {
                                review.id
                              }
                            </span>

                            <h3>
                              {
                                review.activity_description
                              }
                            </h3>
                          </div>

                          <Confidence
                            value={
                              review.confidence
                            }
                          />
                        </div>

                        <div className="review-details">
                          <Detail
                            label="AI Schedule Match"
                            value={
                              review.activity_id
                                ? `${review.activity_id} — ${
                                    review.matched_activity_name ||
                                    ""
                                  }`
                                : "No confident match"
                            }
                          />

                          <Detail
                            label="Reported Status"
                            value={
                              review.status ||
                              "Unknown"
                            }
                          />

                          <Detail
                            label="Reported Progress"
                            value={
                              review.progress_percent !==
                                null &&
                              review.progress_percent !==
                                undefined
                                ? `${review.progress_percent}%`
                                : "Not quantified"
                            }
                          />
                        </div>

                        {changingId ===
                          review.id && (
                          <div className="change-panel">
                            <label>
                              Choose
                              correct
                              schedule
                              activity
                            </label>

                            <select
                              value={
                                replacementActivity
                              }
                              onChange={(
                                event
                              ) =>
                                setReplacementActivity(
                                  event
                                    .target
                                    .value
                                )
                              }
                            >
                              <option value="">
                                Select
                                schedule
                                activity...
                              </option>

                              {schedule.map(
                                (
                                  activity
                                ) => (
                                  <option
                                    key={
                                      activity.activity_id
                                    }
                                    value={
                                      activity.activity_id
                                    }
                                  >
                                    {
                                      activity.activity_id
                                    }{" "}
                                    —{" "}
                                    {
                                      activity.activity_name
                                    }
                                  </option>
                                )
                              )}
                            </select>

                            <div className="change-actions">
                              <button
                                className="primary-action compact"
                                onClick={() =>
                                  changeMatch(
                                    review.id
                                  )
                                }
                              >
                                Confirm
                                Replacement
                              </button>

                              <button
                                className="text-action"
                                onClick={() => {
                                  setChangingId(
                                    null
                                  );

                                  setReplacementActivity(
                                    ""
                                  );
                                }}
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="review-actions">
                        <button
                          className="accept-action"
                          onClick={() =>
                            acceptMatch(
                              review.id
                            )
                          }
                        >
                          ✓ Accept
                        </button>

                        <button
                          className="change-action"
                          onClick={() => {
                            setChangingId(
                              review.id
                            );

                            setReplacementActivity(
                              ""
                            );
                          }}
                        >
                          ↔ Change
                        </button>

                        <button
                          className="reject-action"
                          onClick={() =>
                            rejectMatch(
                              review.id
                            )
                          }
                        >
                          ✕ Reject
                        </button>
                      </div>
                    </div>
                  )
                )
              )}
            </div>
          </section>
        )}

        {/* ====================================================
            PROJECT SCHEDULE
        ==================================================== */}

        {page ===
          "schedule" && (
          <section>
            <div className="schedule-summary">
              <button
                onClick={() =>
                  openScheduleFilter(
                    "all"
                  )
                }
              >
                <strong>
                  {stats.total}
                </strong>
                <span>
                  Total
                </span>
              </button>

              <button
                onClick={() =>
                  openScheduleFilter(
                    "in-progress"
                  )
                }
              >
                <strong>
                  {
                    stats.inProgress
                  }
                </strong>
                <span>
                  In Progress
                </span>
              </button>

              <button
                onClick={() =>
                  openScheduleFilter(
                    "completed"
                  )
                }
              >
                <strong>
                  {
                    stats.completed
                  }
                </strong>
                <span>
                  Completed
                </span>
              </button>

              <div>
                <strong>
                  {stats.averageProgress.toFixed(
                    1
                  )}
                  %
                </strong>

                <span>
                  Average Progress
                </span>
              </div>
            </div>

            <div className="card schedule-card">
              <div className="schedule-toolbar">
                <div>
                  <h3>
                    Live Actual
                    Progress
                  </h3>

                  <p>
                    Approved DPR
                    updates are
                    reflected in this
                    schedule.
                  </p>
                </div>

                <div className="schedule-filter-controls">
                  <select
                    className="schedule-status-select"
                    value={
                      scheduleStatusFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setScheduleStatusFilter(
                        event.target
                          .value
                      )
                    }
                  >
                    <option value="all">
                      All Activities
                    </option>

                    <option value="completed">
                      Completed
                    </option>

                    <option value="in-progress">
                      In Progress
                    </option>

                    <option value="not-started">
                      Not Started
                    </option>
                  </select>

                  <input
                    className="search-input"
                    placeholder="Search ID, activity, discipline..."
                    value={
                      scheduleSearch
                    }
                    onChange={(
                      event
                    ) =>
                      setScheduleSearch(
                        event.target
                          .value
                      )
                    }
                  />
                </div>
              </div>

              <div className="schedule-table-wrap">
                <table className="schedule-table">
                  <thead>
                    <tr>
                      <th>
                        Activity ID
                      </th>

                      <th>
                        Activity
                      </th>

                      <th>
                        Discipline
                      </th>

                      <th>
                        Planned Start
                      </th>

                      <th>
                        Actual Start
                      </th>

                      <th>
                        Actual Finish
                      </th>

                      <th>
                        Actual Progress
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredSchedule.map(
                      (
                        activity
                      ) => {
                        const progress =
                          Number(
                            activity.progress_percent ||
                              0
                          );

                        return (
                          <tr
                            key={
                              activity.id ||
                              activity.activity_id
                            }
                          >
                            <td className="activity-code">
                              {
                                activity.activity_id
                              }
                            </td>

                            <td>
                              <strong>
                                {
                                  activity.activity_name
                                }
                              </strong>

                              {activity.wbs && (
                                <small>
                                  {
                                    activity.wbs
                                  }
                                </small>
                              )}
                            </td>

                            <td>
                              {activity.discipline ||
                                "—"}
                            </td>

                            <td>
                              {activity.planned_start ||
                                "—"}
                            </td>

                            <td>
                              {activity.actual_start ||
                                "—"}
                            </td>

                            <td>
                              {activity.actual_finish ||
                                "—"}
                            </td>

                            <td>
                              <div className="table-progress">
                                <div className="table-progress-top">
                                  <span>
                                    {scheduleStatus(
                                      progress,
                                      activity.actual_start
                                    )}
                                  </span>

                                  <strong>
                                    {formatPercent(
                                      progress
                                    )}
                                  </strong>
                                </div>

                                <ProgressBar
                                  value={
                                    progress
                                  }
                                  small
                                />
                              </div>
                            </td>
                          </tr>
                        );
                      }
                    )}
                  </tbody>
                </table>
              </div>

              <div className="table-footer">
                Showing{" "}
                {
                  filteredSchedule.length
                }{" "}
                of{" "}
                {
                  schedule.length
                }{" "}
                schedule activities
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

// ============================================================
// INTERACTIVE DASHBOARD
// ============================================================

function InteractiveDashboard({
  stats,
  pendingReviews,
  latestResult,
  openScheduleFilter,
  openPlannerReview,
  setPage,
}) {
  const total =
    stats.total || 0;

  const completed =
    stats.completed || 0;

  const inProgress =
    stats.inProgress || 0;

  const notStarted =
    stats.notStarted || 0;

  const overallProgress =
    Number(
      stats.averageProgress ||
        0
    );

  const completedShare =
    total > 0
      ? (completed / total) *
        100
      : 0;

  const inProgressShare =
    total > 0
      ? (inProgress /
          total) *
        100
      : 0;

  const notStartedShare =
    Math.max(
      0,
      100 -
        completedShare -
        inProgressShare
    );

  const donutStyle = {
    background: `conic-gradient(
      #10b981 0% ${completedShare}%,
      #f59e0b ${completedShare}% ${
      completedShare +
      inProgressShare
    }%,
      #e8edf4 ${
        completedShare +
        inProgressShare
      }% 100%
    )`,
  };

  return (
    <section className="live-dashboard">
      {/* TOP CARDS */}

      <div className="live-dashboard-stats">
        <DashboardStat
          label="Total Tasks"
          value={total}
          type="blue"
          subtitle="Master schedule"
          onClick={() =>
            openScheduleFilter(
              "all"
            )
          }
        />

        <DashboardStat
          label="Completed Tasks"
          value={completed}
          type="green"
          subtitle="100% complete"
          onClick={() =>
            openScheduleFilter(
              "completed"
            )
          }
        />

        <DashboardStat
          label="In Progress"
          value={inProgress}
          type="orange"
          subtitle="Active execution"
          onClick={() =>
            openScheduleFilter(
              "in-progress"
            )
          }
        />

        <DashboardStat
          label="Pending Linkage"
          value={
            pendingReviews
          }
          type="red"
          subtitle="Planner review"
          onClick={
            openPlannerReview
          }
        />
      </div>

      {/* CHARTS */}

      <div className="dashboard-visual-grid">
        <div className="dashboard-visual-card">
          <div className="visual-heading">
            <h3>
              Overall Project
              Progress
            </h3>

            <p>
              Live data from
              approved site DPRs.
            </p>
          </div>

          <div className="donut-section">
            <div
              className="dashboard-donut"
              style={
                donutStyle
              }
            >
              <div className="dashboard-donut-inner">
                <strong>
                  {overallProgress.toFixed(
                    1
                  )}
                  %
                </strong>

                <span>
                  Overall
                  Progress
                </span>
              </div>
            </div>

            <div className="dashboard-legend">
              <button
                onClick={() =>
                  openScheduleFilter(
                    "completed"
                  )
                }
              >
                <span className="legend-color green" />

                <div>
                  <strong>
                    Completed
                  </strong>

                  <small>
                    {
                      completed
                    }{" "}
                    activities
                  </small>
                </div>
              </button>

              <button
                onClick={() =>
                  openScheduleFilter(
                    "in-progress"
                  )
                }
              >
                <span className="legend-color orange" />

                <div>
                  <strong>
                    In Progress
                  </strong>

                  <small>
                    {
                      inProgress
                    }{" "}
                    activities
                  </small>
                </div>
              </button>

              <button
                onClick={() =>
                  openScheduleFilter(
                    "not-started"
                  )
                }
              >
                <span className="legend-color grey" />

                <div>
                  <strong>
                    Not Started
                  </strong>

                  <small>
                    {
                      notStarted
                    }{" "}
                    activities
                  </small>
                </div>
              </button>

              <button
                onClick={
                  openPlannerReview
                }
              >
                <span className="legend-color red" />

                <div>
                  <strong>
                    Pending Review
                  </strong>

                  <small>
                    {
                      pendingReviews
                    }{" "}
                    activities
                  </small>
                </div>
              </button>
            </div>
          </div>
        </div>

        <div className="dashboard-visual-card">
          <div className="visual-heading">
            <h3>
              Completion Progress
              Overview
            </h3>

            <p>
              Click a category to
              view its activities.
            </p>
          </div>

          <DashboardBar
            label="Completed"
            count={completed}
            percentage={
              completedShare
            }
            type="green"
            onClick={() =>
              openScheduleFilter(
                "completed"
              )
            }
          />

          <DashboardBar
            label="In Progress"
            count={inProgress}
            percentage={
              inProgressShare
            }
            type="orange"
            onClick={() =>
              openScheduleFilter(
                "in-progress"
              )
            }
          />

          <DashboardBar
            label="Pending Review"
            count={
              pendingReviews
            }
            percentage={
              total > 0
                ? Math.min(
                    100,
                    (pendingReviews /
                      total) *
                      100
                  )
                : 0
            }
            type="red"
            onClick={
              openPlannerReview
            }
          />

          <DashboardBar
            label="Not Started"
            count={notStarted}
            percentage={
              notStartedShare
            }
            type="grey"
            onClick={() =>
              openScheduleFilter(
                "not-started"
              )
            }
          />
        </div>
      </div>

      {/* QUICK ACTIONS */}

      <div className="dashboard-quick-actions">
        <div>
          <h3>
            Project Control
            Actions
          </h3>

          <p>
            Continue the
            planning-to-execution
            workflow.
          </p>
        </div>

        <div className="quick-action-buttons">
          <button
            className="quick-primary"
            onClick={() =>
              setPage(
                "capture"
              )
            }
          >
            ↑ Capture Site
            Progress
          </button>

          <button
            onClick={
              openPlannerReview
            }
          >
            ✓ Review Matches
            {pendingReviews >
              0 && (
              <span className="quick-count">
                {
                  pendingReviews
                }
              </span>
            )}
          </button>

          <button
            onClick={() =>
              openScheduleFilter(
                "all"
              )
            }
          >
            ▤ View Project
            Schedule
          </button>
        </div>
      </div>

      {/* LATEST UPDATE */}

      {latestResult &&
        latestResult
          .activities?.length >
          0 && (
          <div className="dashboard-latest-card">
            <div className="dashboard-latest-header">
              <div>
                <h3>
                  Latest
                  Processed Update
                </h3>

                <p>
                  Report #
                  {latestResult.report_id ||
                    "—"}
                  {" · "}
                  {latestResult.input_type ||
                    "DPR"}
                </p>
              </div>

              <span className="processed-badge">
                Processed
              </span>
            </div>

            <div className="dashboard-latest-list">
              {latestResult.activities
                .slice(0, 5)
                .map(
                  (
                    item,
                    index
                  ) => (
                    <LatestDashboardActivity
                      key={
                        index
                      }
                      item={
                        item
                      }
                    />
                  )
                )}
            </div>

            <button
              className="open-review-link"
              onClick={
                openPlannerReview
              }
            >
              Open Planner
              Review →
            </button>
          </div>
        )}
    </section>
  );
}

function DashboardStat({
  label,
  value,
  type,
  subtitle,
  onClick,
}) {
  return (
    <button
      className={`live-stat-card ${type}`}
      onClick={onClick}
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {subtitle} →
      </small>
    </button>
  );
}

function DashboardBar({
  label,
  count,
  percentage,
  type,
  onClick,
}) {
  const safePercentage =
    Math.max(
      0,
      Math.min(
        100,
        Number(
          percentage || 0
        )
      )
    );

  return (
    <button
      className="dashboard-bar-row"
      onClick={onClick}
    >
      <div className="dashboard-bar-top">
        <div>
          <strong>
            {label}
          </strong>

          <span>
            {count} activities
          </span>
        </div>

        <strong>
          {safePercentage.toFixed(
            1
          )}
          %
        </strong>
      </div>

      <div className="dashboard-bar-track">
        <div
          className={`dashboard-bar-fill ${type}`}
          style={{
            width: `${safePercentage}%`,
          }}
        />
      </div>
    </button>
  );
}

function LatestDashboardActivity({
  item,
}) {
  const extracted =
    item.extracted_activity ||
    {};

  const matching =
    item.matching || {};

  const candidate =
    matching.matches?.[0];

  return (
    <div className="dashboard-latest-row">
      <div>
        <strong>
          {extracted.activity_description ||
            "Unnamed activity"}
        </strong>

        <span>
          {extracted.discipline ||
            "Unknown discipline"}
          {" · "}
          {extracted.status ||
            "Unknown status"}
        </span>
      </div>

      <div>
        <span>
          Progress
        </span>

        <strong>
          {extracted.progress_percent !==
            null &&
          extracted.progress_percent !==
            undefined
            ? `${extracted.progress_percent}%`
            : "—"}
        </strong>
      </div>

      <div>
        <span>
          Schedule Match
        </span>

        <strong>
          {candidate?.activity_id ||
            "Review"}
        </strong>
      </div>

      <div>
        <span>
          Confidence
        </span>

        <strong>
          {Number(
            matching.confidence ||
              0
          ).toFixed(1)}
          %
        </strong>
      </div>
    </div>
  );
}

// ============================================================
// OTHER COMPONENTS
// ============================================================

function ModeButton({
  label,
  icon,
  active,
  onClick,
}) {
  return (
    <button
      className={`mode-btn ${
        active
          ? "active"
          : ""
      }`}
      onClick={onClick}
    >
      <span>
        {icon}
      </span>

      {label}
    </button>
  );
}

function ExtractionField({
  label,
  detail,
}) {
  return (
    <div className="extraction-field">
      <span>
        ✓
      </span>

      <div>
        <strong>
          {label}
        </strong>

        <p>
          {detail}
        </p>
      </div>
    </div>
  );
}

function LatestMatchDetail({
  item,
}) {
  const extracted =
    item.extracted_activity ||
    {};

  const matching =
    item.matching || {};

  const candidates =
    matching.matches || [];

  return (
    <div className="latest-match-detail">
      <div className="latest-match-head">
        <div>
          <h4>
            {
              extracted.activity_description
            }
          </h4>

          <p>
            {extracted.discipline ||
              "Unknown discipline"}
            {" · "}
            {extracted.status ||
              "Unknown status"}
            {" · "}
            {extracted.progress_percent !==
              null &&
            extracted.progress_percent !==
              undefined
              ? `${extracted.progress_percent}%`
              : "No numeric progress"}
          </p>
        </div>

        <Confidence
          value={
            matching.confidence
          }
        />
      </div>

      <div className="candidate-list">
        {candidates
          .slice(0, 3)
          .map(
            (
              candidate,
              index
            ) => (
              <div
                className="candidate"
                key={`${candidate.activity_id}-${index}`}
              >
                <span className="candidate-rank">
                  {index +
                    1}
                </span>

                <div>
                  <strong>
                    {
                      candidate.activity_id
                    }
                  </strong>

                  <p>
                    {
                      candidate.activity_name
                    }
                  </p>
                </div>

                <span>
                  {
                    candidate.confidence
                  }
                  %
                </span>
              </div>
            )
          )}
      </div>
    </div>
  );
}

function Confidence({
  value,
}) {
  const confidence =
    Number(
      value || 0
    );

  let className =
    "low";

  if (
    confidence >= 80
  ) {
    className =
      "high";
  } else if (
    confidence >= 60
  ) {
    className =
      "medium";
  }

  return (
    <span
      className={`confidence ${className}`}
    >
      {confidence.toFixed(
        2
      )}
      %
    </span>
  );
}

function Detail({
  label,
  value,
}) {
  return (
    <div className="detail">
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}

function ProgressBar({
  value,
  small = false,
}) {
  const progress =
    Math.max(
      0,
      Math.min(
        100,
        Number(
          value || 0
        )
      )
    );

  return (
    <div
      className={`progress-track ${
        small
          ? "small"
          : ""
      }`}
    >
      <div
        className="progress-value"
        style={{
          width: `${progress}%`,
        }}
      />
    </div>
  );
}

function scheduleStatus(
  progress,
  actualStart
) {
  if (
    progress >= 100
  ) {
    return "Completed";
  }

  if (
    progress > 0
  ) {
    return "In Progress";
  }

  if (actualStart) {
    return "Started";
  }

  return "Not Started";
}

function formatPercent(
  value
) {
  const number =
    Number(
      value || 0
    );

  if (
    Number.isInteger(
      number
    )
  ) {
    return `${number}%`;
  }

  return `${number.toFixed(
    1
  )}%`;
}

function formatFileSize(
  bytes
) {
  if (!bytes) {
    return "0 KB";
  }

  if (
    bytes >=
    1024 * 1024
  ) {
    return `${(
      bytes /
      (1024 * 1024)
    ).toFixed(2)} MB`;
  }

  return `${(
    bytes / 1024
  ).toFixed(1)} KB`;
}

export default App;