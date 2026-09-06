import { useState } from "react";

function App() {
  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const processDPR = async () => {
    if (!text.trim()) {
      setError("Please enter a site progress report.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/process-dpr",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            text: text,
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          `Backend returned ${response.status}`
        );
      }

      const data = await response.json();

      setResult(data);
    } catch (err) {
      console.error(err);

      setError(
        "Could not process the DPR. Check that the backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    if (status === "MATCHED") {
      return "#22c55e";
    }

    if (status === "REVIEW") {
      return "#f59e0b";
    }

    return "#ef4444";
  };

  return (
    <div
      style={{
        maxWidth: "1100px",
        margin: "0 auto",
        padding: "40px 20px",
        fontFamily: "Arial, sans-serif",
      }}
    >
      <h1 style={{ marginBottom: "5px" }}>
        SIH26122 Progress Linking
      </h1>

      <p
        style={{
          color: "#888",
          marginBottom: "35px",
        }}
      >
        Intelligent DPR Extraction & Schedule Linking
      </p>

      {/* DPR INPUT */}

      <div
        style={{
          border: "1px solid #444",
          borderRadius: "12px",
          padding: "24px",
          marginBottom: "30px",
        }}
      >
        <h2>Site Progress Report</h2>

        <textarea
          rows="6"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Example: F101 concreting completed. Reinforcement for F102 started."
          style={{
            width: "100%",
            padding: "14px",
            boxSizing: "border-box",
            borderRadius: "8px",
            fontSize: "16px",
            resize: "vertical",
          }}
        />

        <button
          onClick={processDPR}
          disabled={loading}
          style={{
            marginTop: "15px",
            padding: "12px 24px",
            borderRadius: "8px",
            border: "none",
            cursor: loading
              ? "not-allowed"
              : "pointer",
            fontSize: "15px",
          }}
        >
          {loading
            ? "Processing..."
            : "Process DPR"}
        </button>

        {error && (
          <p
            style={{
              color: "#ef4444",
              marginTop: "15px",
            }}
          >
            {error}
          </p>
        )}
      </div>

      {/* RESULTS */}

      {result && (
        <div>
          <h2>
            Processing Results
          </h2>

          <p>
            Activities detected:{" "}
            <strong>
              {result.activities?.length || 0}
            </strong>
          </p>

          {result.activities?.map(
            (item, activityIndex) => {
              const activity =
                item.extracted_activity;

              const matching =
                item.matching;

              return (
                <div
                  key={activityIndex}
                  style={{
                    border:
                      "1px solid #444",
                    borderRadius: "12px",
                    padding: "22px",
                    marginTop: "20px",
                  }}
                >
                  {/* EXTRACTED ACTIVITY */}

                  <h3>
                    Activity{" "}
                    {activityIndex + 1}
                  </h3>

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(180px, 1fr))",
                      gap: "12px",
                      marginBottom: "20px",
                    }}
                  >
                    <InfoBox
                      label="Description"
                      value={
                        activity?.activity_description
                      }
                    />

                    <InfoBox
                      label="Discipline"
                      value={
                        activity?.discipline
                      }
                    />

                    <InfoBox
                      label="Progress Status"
                      value={
                        activity?.status
                      }
                    />

                    <InfoBox
                      label="Tag"
                      value={
                        activity?.tag
                      }
                    />

                    <InfoBox
                      label="Date"
                      value={
                        activity?.date
                      }
                    />
                  </div>

                  {/* MATCHING STATUS */}

                  <div
                    style={{
                      display: "flex",
                      gap: "20px",
                      alignItems: "center",
                      marginBottom: "20px",
                    }}
                  >
                    <span
                      style={{
                        padding:
                          "7px 13px",
                        borderRadius:
                          "20px",
                        backgroundColor:
                          getStatusColor(
                            matching?.status
                          ),
                        color: "white",
                        fontWeight:
                          "bold",
                      }}
                    >
                      {matching?.status}
                    </span>

                    <span>
                      Confidence:{" "}
                      <strong>
                        {matching?.confidence ??
                          0}
                        %
                      </strong>
                    </span>

                    <span>
                      Gap:{" "}
                      <strong>
                        {matching?.confidence_gap ??
                          0}
                        %
                      </strong>
                    </span>
                  </div>

                  {/* TOP MATCHES */}

                  <h4>
                    Top Schedule Matches
                  </h4>

                  {matching?.matches?.map(
                    (
                      match,
                      matchIndex
                    ) => (
                      <div
                        key={
                          matchIndex
                        }
                        style={{
                          padding:
                            "14px",
                          border:
                            "1px solid #555",
                          borderRadius:
                            "8px",
                          marginBottom:
                            "10px",
                        }}
                      >
                        <div
                          style={{
                            display:
                              "flex",
                            justifyContent:
                              "space-between",
                            gap: "20px",
                          }}
                        >
                          <div>
                            <strong>
                              #
                              {matchIndex +
                                1}{" "}
                              {
                                match.activity_name
                              }
                            </strong>

                            <div
                              style={{
                                marginTop:
                                  "8px",
                                color:
                                  "#999",
                              }}
                            >
                              Activity ID:{" "}
                              {match.activity_id ||
                                "—"}
                            </div>

                            <div
                              style={{
                                color:
                                  "#999",
                              }}
                            >
                              Project:{" "}
                              {match.project_id ||
                                "—"}
                            </div>

                            <div
                              style={{
                                color:
                                  "#999",
                              }}
                            >
                              Discipline:{" "}
                              {match.discipline ||
                                "—"}
                            </div>
                          </div>

                          <div
                            style={{
                              fontSize:
                                "20px",
                              fontWeight:
                                "bold",
                            }}
                          >
                            {
                              match.confidence
                            }
                            %
                          </div>
                        </div>
                      </div>
                    )
                  )}
                </div>
              );
            }
          )}
        </div>
      )}
    </div>
  );
}


function InfoBox({ label, value }) {
  return (
    <div
      style={{
        padding: "12px",
        border: "1px solid #444",
        borderRadius: "8px",
      }}
    >
      <div
        style={{
          fontSize: "12px",
          color: "#888",
          marginBottom: "5px",
        }}
      >
        {label}
      </div>

      <strong>
        {value || "—"}
      </strong>
    </div>
  );
}


export default App;