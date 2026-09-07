import React, {
  useRef,
  useState,
} from "react";

import {
  createRoot,
} from "react-dom/client";

import "./styles.css";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  window.location.origin;

// ============================================================
// APP
// ============================================================

function App() {

  const [file, setFile] =
    useState(null);

  const [url, setUrl] =
    useState("");

  const [strength, setStrength] =
    useState("balanced");

  const [count, setCount] =
    useState(5);

  const [job, setJob] =
    useState(null);

  const [busy, setBusy] =
    useState(false);

  const [error, setError] =
    useState("");

  const [dragActive, setDragActive] =
    useState(false);

  const fileInputRef =
    useRef(null);


  // ==========================================================
  // POLL JOB
  // ==========================================================

  async function pollJob(jobId) {

    console.log(
      "[Frontend] Starting polling:",
      jobId
    );


    while (true) {

      try {

        const response =
          await fetch(
            `${API_BASE}/api/jobs/${jobId}?t=${Date.now()}`,
            {
              method: "GET",

              cache: "no-store",

              headers: {
                Accept:
                  "application/json",

                "Cache-Control":
                  "no-cache",

                Pragma:
                  "no-cache",
              },
            }
          );


        if (!response.ok) {

          throw new Error(
            `Job request failed: ${response.status}`
          );

        }


        const data =
          await response.json();


        console.log(
          "[Frontend] Job update:",
          data
        );


        // ------------------------------------------------------
        // IMPORTANT
        // Always preserve jobId from polling.
        // ------------------------------------------------------

        const updatedJob = {
          ...data,

          job_id:
            data.job_id ||
            jobId,
        };


        setJob(
          updatedJob
        );


        // ======================================================
        // COMPLETED
        // ======================================================

        if (
          data.status ===
          "completed"
        ) {

          console.log(
            "[Frontend] Job completed successfully."
          );


          setBusy(false);


          setTimeout(
            () => {

              const results =
                document.getElementById(
                  "results"
                );


              if (results) {

                results.scrollIntoView({
                  behavior: "smooth",
                  block: "start",
                });

              }

            },
            200
          );


          return;
        }


        // ======================================================
        // FAILED
        // ======================================================

        if (
          data.status ===
          "failed"
        ) {

          console.error(
            "[Frontend] Job failed:",
            data.message
          );


          setBusy(false);


          setError(
            data.message ||
              "Video processing failed."
          );


          return;
        }


        // ======================================================
        // CONTINUE
        // ======================================================

        await new Promise(
          (resolve) =>
            setTimeout(
              resolve,
              1000
            )
        );

      }


      catch (err) {

        console.error(
          "[Frontend] Polling error:",
          err
        );


        await new Promise(
          (resolve) =>
            setTimeout(
              resolve,
              2000
            )
        );

      }

    }

  }


  // ==========================================================
  // GENERATE
  // ==========================================================

  async function generate() {

    setError("");


    if (
      !file &&
      !url.trim()
    ) {

      setError(
        "Please upload a video or enter a video URL."
      );

      return;
    }


    setBusy(true);

    setJob(null);


    try {

      const form =
        new FormData();


      // ------------------------------------------------------
      // FILE
      // ------------------------------------------------------

      if (file) {

        form.append(
          "video",
          file
        );

      }


      // ------------------------------------------------------
      // URL
      // ------------------------------------------------------

      if (
        url.trim()
      ) {

        form.append(
          "url",
          url.trim()
        );

      }


      // ------------------------------------------------------
      // SETTINGS
      // ------------------------------------------------------

      form.append(
        "variation_count",
        String(count)
      );


      form.append(
        "strength",
        strength
      );


      console.log(
        "[Frontend] Creating job..."
      );


      // ======================================================
      // CREATE JOB
      // ======================================================

      const response =
        await fetch(
          `${API_BASE}/api/jobs`,
          {
            method: "POST",
            body: form,
          }
        );


      const data =
        await response.json();


      console.log(
        "[Frontend] Create job response:",
        data
      );


      if (!response.ok) {

        throw new Error(
          data.detail ||
            data.message ||
            "Could not create job."
        );

      }


      const jobId =
        data.job_id;


      if (!jobId) {

        throw new Error(
          "Backend did not return a job ID."
        );

      }


      // ======================================================
      // INITIAL JOB STATE
      // ======================================================

      setJob({

        job_id: jobId,

        status: "queued",

        progress: 10,

        message:
          "Video ready. Starting AI analysis...",

      });


      // ======================================================
      // START POLLING
      // ======================================================

      await pollJob(
        jobId
      );

    }


    catch (err) {

      console.error(
        "[Frontend] Generate error:",
        err
      );


      setBusy(false);


      setError(
        err.message ||
          "Something went wrong."
      );

    }

  }


  // ==========================================================
  // FILE SELECT
  // ==========================================================

  function handleFileChange(
    event
  ) {

    const selected =
      event.target.files?.[0];


    if (!selected) {
      return;
    }


    if (
      !selected.type.startsWith(
        "video/"
      )
    ) {

      setError(
        "Please select a video file."
      );

      return;
    }


    setFile(
      selected
    );


    setUrl(
      ""
    );


    setError(
      ""
    );

  }


  // ==========================================================
  // DRAG DROP
  // ==========================================================

  function handleDrop(
    event
  ) {

    event.preventDefault();

    setDragActive(false);


    const droppedFile =
      event.dataTransfer.files?.[0];


    if (!droppedFile) {
      return;
    }


    if (
      !droppedFile.type.startsWith(
        "video/"
      )
    ) {

      setError(
        "Please drop a video file."
      );

      return;
    }


    setFile(
      droppedFile
    );


    setUrl(
      ""
    );


    setError(
      ""
    );

  }


  // ==========================================================
  // CLEAR FILE
  // ==========================================================

  function clearFile() {

    setFile(
      null
    );


    if (
      fileInputRef.current
    ) {

      fileInputRef.current.value =
        "";

    }

  }


  // ==========================================================
  // SAFE DATA
  // ==========================================================

  const analysis =
    job?.analysis &&
    typeof job.analysis ===
      "object"
      ? job.analysis
      : {};


  const hook =
    analysis?.hook &&
    typeof analysis.hook ===
      "object"
      ? analysis.hook
      : {};


  const hookAnalysis =
    analysis?.analysis &&
    typeof analysis.analysis ===
      "object"
      ? analysis.analysis
      : {};


  const variations =
    Array.isArray(
      job?.variations
    )
      ? job.variations
      : Array.isArray(
          analysis?.variations
        )
      ? analysis.variations
      : [];


  const completed =
    job?.status ===
    "completed";


  const progress =
    completed
      ? 100
      : Math.max(
          0,
          Math.min(
            100,
            Number(
              job?.progress ||
                0
            )
          )
        );


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="app-shell">

      {/* ====================================================
          HEADER
      ==================================================== */}

      <header className="topbar">

        <div className="brand">

          <div className="brand-mark">
            LN
          </div>


          <div>

            <div className="brand-name">
              LightNoteAI
            </div>

            <div className="brand-subtitle">
              AI Hook Generator
            </div>

          </div>

        </div>


        <div className="status-pill">

          <span className="status-dot"></span>

          AI Video Studio

        </div>

      </header>


      {/* ====================================================
          MAIN
      ==================================================== */}

      <main className="main-container">


        {/* ==================================================
            HERO
        ================================================== */}

        <section className="hero">

          <div className="eyebrow">
            SHORT-FORM AD INTELLIGENCE
          </div>


          <h1>

            Turn winning ads into

            <span>
              high-converting hooks.
            </span>

          </h1>


          <p className="hero-description">

            Upload a winning short-form video.
            LightNoteAI analyzes the opening hook
            and generates meaningful creative
            variations in seconds.

          </p>

        </section>


        {/* ==================================================
            INPUT
        ================================================== */}

        <section className="card input-card">

          <div className="card-heading">

            <h2>
              Create hook variations
            </h2>

            <p>
              Upload a video or provide a
              video URL.
            </p>

          </div>


          {/* =================================================
              DROP ZONE
          ================================================= */}

          <div

            className={
              "drop-zone " +
              (
                dragActive
                  ? "drag-active"
                  : ""
              )
            }


            onDragOver={(event) => {

              event.preventDefault();

              setDragActive(
                true
              );

            }}


            onDragLeave={() => {

              setDragActive(
                false
              );

            }}


            onDrop={
              handleDrop
            }


            onClick={() => {

              if (!file) {

                fileInputRef.current?.click();

              }

            }}

          >

            <input

              ref={
                fileInputRef
              }

              type="file"

              accept="video/*"

              onChange={
                handleFileChange
              }

              hidden

            />


            {!file ? (

              <>

                <div className="upload-icon">
                  ↑
                </div>


                <h3>
                  Drop your video here
                </h3>


                <p>
                  or click to browse
                </p>


                <small>
                  MP4, MOV, AVI, MKV, WEBM
                </small>

              </>

            ) : (

              <div className="selected-file">

                <div className="file-icon">
                  ▶
                </div>


                <div className="file-info">

                  <strong>
                    {file.name}
                  </strong>


                  <span>

                    {(
                      file.size /
                      (
                        1024 *
                        1024
                      )
                    ).toFixed(2)}

                    {" "}MB

                  </span>

                </div>


                <button

                  type="button"

                  className="remove-button"

                  onClick={(event) => {

                    event.stopPropagation();

                    clearFile();

                  }}

                >
                  ×
                </button>

              </div>

            )}

          </div>


          {/* =================================================
              DIVIDER
          ================================================= */}

          <div className="or-divider">
            <span>OR</span>
          </div>


          {/* =================================================
              URL
          ================================================= */}

          <div className="field">

            <label>
              Video URL
            </label>


            <input

              type="text"

              placeholder="Paste a video URL..."

              value={
                url
              }


              onChange={(event) => {

                setUrl(
                  event.target.value
                );


                if (
                  event.target.value
                ) {

                  setFile(
                    null
                  );

                }

              }}

            />

          </div>


          {/* =================================================
              OPTIONS
          ================================================= */}

          <div className="options-grid">


            <div className="field">

              <label>
                Variation strength
              </label>


              <select

                value={
                  strength
                }

                onChange={(event) =>
                  setStrength(
                    event.target.value
                  )
                }

              >

                <option value="light">
                  Light
                </option>

                <option value="balanced">
                  Balanced
                </option>

                <option value="strong">
                  Strong
                </option>

              </select>

            </div>


            <div className="field">

              <label>
                Number of variations
              </label>


              <select

                value={
                  count
                }

                onChange={(event) =>
                  setCount(
                    Number(
                      event.target.value
                    )
                  )
                }

              >

                <option value={5}>
                  5 variations
                </option>

                <option value={6}>
                  6 variations
                </option>

                <option value={7}>
                  7 variations
                </option>

                <option value={8}>
                  8 variations
                </option>

                <option value={9}>
                  9 variations
                </option>

                <option value={10}>
                  10 variations
                </option>

              </select>

            </div>

          </div>


          {/* =================================================
              ERROR
          ================================================= */}

          {error && (

            <div className="error-box">

              <strong>
                Processing error
              </strong>

              <div>
                {error}
              </div>

            </div>

          )}


          {/* =================================================
              GENERATE BUTTON
          ================================================= */}

          <button

            className="generate-button"

            onClick={
              generate
            }

            disabled={
              busy
            }

          >

            {busy ? (

              <>

                <span className="spinner"></span>

                Processing...

              </>

            ) : (

              <>

                Generate Hook Variations

                <span>
                  →
                </span>

              </>

            )}

          </button>

        </section>


        {/* ==================================================
            PROCESSING
        ================================================== */}

        {job &&
          !completed &&
          job.status !== "failed" && (

            <section className="card progress-card">

              <div className="progress-header">

                <div>

                  <h2>
                    Processing video
                  </h2>

                  <p>
                    {job.message ||
                      "Working on your video..."}
                  </p>

                </div>


                <strong>
                  {progress}%
                </strong>

              </div>


              <div className="progress-track">

                <div

                  className="progress-fill"

                  style={{
                    width:
                      `${progress}%`,
                  }}

                />

              </div>


              <div className="processing-steps">

                <div
                  className={
                    progress >= 10
                      ? "step active"
                      : "step"
                  }
                >

                  <span>
                    ✓
                  </span>

                  Upload

                </div>


                <div
                  className={
                    progress >= 15
                      ? "step active"
                      : "step"
                  }
                >

                  <span>
                    ✓
                  </span>

                  Analyze Hook

                </div>


                <div
                  className={
                    progress >= 55
                      ? "step active"
                      : "step"
                  }
                >

                  <span>
                    ✓
                  </span>

                  Generate

                </div>


                <div
                  className={
                    progress >= 100
                      ? "step active"
                      : "step"
                  }
                >

                  <span>
                    ✓
                  </span>

                  Complete

                </div>

              </div>

            </section>

        )}


        {/* ==================================================
            RESULTS
        ================================================== */}

        {completed && (

          <section
            id="results"
            className="results-section"
          >


            {/* =================================================
                SUCCESS
            ================================================= */}

            <div className="success-banner">

              <div className="success-icon">
                ✓
              </div>


              <div>

                <strong>
                  Hook analysis complete
                </strong>


                <p>
                  Your AI-generated hook
                  variations are ready.
                </p>

              </div>


              <div className="complete-percent">
                100%
              </div>

            </div>


            {/* =================================================
                HOOK + ANALYSIS
            ================================================= */}

            <div className="results-grid">


              {/* ORIGINAL HOOK */}

              <div className="card result-card">

                <div className="section-label">
                  EXTRACTED HOOK
                </div>


                <h2>
                  Original Hook
                </h2>


                <div className="hook-preview">

                  {job?.job_id ? (

                    <video

                      controls

                      playsInline

                      preload="metadata"

                      src={
                        `${API_BASE}/api/jobs/` +
                        `${job.job_id}/source`
                      }

                    />

                  ) : (

                    <div className="video-placeholder">

                      No source video

                    </div>

                  )}

                </div>


                <div className="hook-time">

                  <span>
                    Hook duration
                  </span>


                  <strong>

                    {hook.start ?? 0}s

                    {" – "}

                    {hook.end ?? 3}s

                  </strong>

                </div>

              </div>


              {/* HOOK ANALYSIS */}

              <div className="card result-card">

                <div className="section-label">
                  HOOK ANALYSIS
                </div>


                <h2>
                  What makes it work
                </h2>


                <div className="analysis-item">

                  <span>
                    Spoken line
                  </span>

                  <strong>
                    {hook.spoken_line ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="analysis-item">

                  <span>
                    On-screen text
                  </span>

                  <strong>
                    {hook.on_screen_text ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="analysis-item">

                  <span>
                    Visual action
                  </span>

                  <strong>
                    {hook.visual_action ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="analysis-item">

                  <span>
                    Emotion
                  </span>

                  <strong>
                    {hook.emotion ||
                      "Not detected"}
                  </strong>

                </div>


                <div className="analysis-item">

                  <span>
                    Product
                  </span>

                  <strong>
                    {hook.product_appearance ||
                      "Not clearly visible"}
                  </strong>

                </div>

              </div>

            </div>


            {/* =================================================
                CREATIVE INSIGHT
            ================================================= */}

            <div className="card explanation-card">

              <div className="section-label">
                CREATIVE INSIGHT
              </div>


              <h2>
                Why this hook works
              </h2>


              <p>

                {hookAnalysis.why_it_works ||
                  "No explanation was returned."}

              </p>


              <div className="insight-grid">

                <div>

                  <span>
                    Target audience
                  </span>


                  <strong>

                    {hookAnalysis.target_audience ||
                      "Not specified"}

                  </strong>

                </div>


                <div>

                  <span>
                    Structure
                  </span>


                  <strong>

                    {hookAnalysis.structure ||
                      "Not specified"}

                  </strong>

                </div>

              </div>

            </div>


            {/* =================================================
                VARIATIONS TITLE
            ================================================= */}

            <div className="variations-heading">

              <div>

                <div className="section-label">
                  AI-GENERATED
                </div>


                <h2>
                  Hook Variations
                </h2>


                <p>

                  {variations.length}
                  {" "}
                  creative alternatives generated
                  from the original hook.

                </p>

              </div>


              <div className="variation-count">

                {variations.length}

              </div>

            </div>


            {/* =================================================
                VARIATIONS
            ================================================= */}

            {variations.length === 0 ? (

              <div className="card empty-results">

                <h3>
                  No variations returned
                </h3>


                <p>
                  The AI analysis completed,
                  but no variation data was
                  returned.
                </p>

              </div>

            ) : (

              <div className="variation-grid">

                {variations.map(
                  (variation, index) => {

                    const clipUrl =
                      variation?.clip_url
                        ? `${API_BASE}${variation.clip_url}`
                        : null;


                    return (

                      <article

                        className="card variation-card"

                        key={
                          variation?.id ||
                          index
                        }

                      >


                        {/* TOP */}

                        <div className="variation-top">

                          <span className="variation-number">

                            {String(
                              index + 1
                            ).padStart(
                              2,
                              "0"
                            )}

                          </span>


                          <span className="variation-tag">
                            AI VARIATION
                          </span>

                        </div>


                        {/* VIDEO */}

                        {clipUrl ? (

                          <video

                            className="variation-video"

                            controls

                            playsInline

                            preload="metadata"

                            src={
                              clipUrl
                            }

                          />

                        ) : (

                          <div className="video-placeholder">

                            Clip unavailable

                          </div>

                        )}


                        {/* CONTENT */}

                        <div className="variation-content">


                          <div className="mini-label">
                            HOOK LINE
                          </div>


                          <h3>

                            {variation?.hook_line ||
                              "No hook line returned"}

                          </h3>


                          <div className="variation-detail">

                            <span>
                              On-screen text
                            </span>


                            <p>

                              {variation?.on_screen_text ||
                                "Not specified"}

                            </p>

                          </div>


                          <div className="variation-detail">

                            <span>
                              Visual direction
                            </span>


                            <p>

                              {variation?.visual_direction ||
                                "Not specified"}

                            </p>

                          </div>


                          <div className="variation-detail">

                            <span>
                              Emotion
                            </span>


                            <p>

                              {variation?.emotion ||
                                "Not specified"}

                            </p>

                          </div>


                          <div className="variation-detail">

                            <span>
                              Why this variation
                            </span>


                            <p>

                              {variation?.rationale ||
                                "Not specified"}

                            </p>

                          </div>

                        </div>


                        {/* DOWNLOAD */}

                        {clipUrl && (

                          <a

                            className="download-button"

                            href={
                              clipUrl
                            }

                            download={
                              variation?.clip_filename ||
                              `variation_${index + 1}.mp4`
                            }

                          >

                            Download Clip

                            <span>
                              ↓
                            </span>

                          </a>

                        )}

                      </article>

                    );

                  }
                )}

              </div>

            )}

          </section>

        )}

      </main>


      {/* ====================================================
          FOOTER
      ==================================================== */}

      <footer className="footer">

        <span>
          LightNoteAI
        </span>


        <span>
          AI-powered creative intelligence
        </span>

      </footer>

    </div>

  );

}


// ============================================================
// ERROR BOUNDARY
// ============================================================

class ErrorBoundary
  extends React.Component {

  constructor(props) {

    super(props);

    this.state = {
      hasError: false,
      error: null,
    };

  }


  static getDerivedStateFromError(
    error
  ) {

    return {

      hasError: true,

      error,

    };

  }


  componentDidCatch(
    error,
    info
  ) {

    console.error(
      "[React Error]",
      error,
      info
    );

  }


  render() {

    if (
      this.state.hasError
    ) {

      return (

        <div
          style={{
            minHeight: "100vh",

            display: "flex",

            alignItems: "center",

            justifyContent: "center",

            padding: "40px",

            background: "#f5f7fb",

            fontFamily:
              "Arial, sans-serif",
          }}
        >

          <div
            style={{
              maxWidth: "700px",

              width: "100%",

              background: "white",

              padding: "32px",

              borderRadius: "18px",

              boxShadow:
                "0 20px 60px rgba(0,0,0,.08)",
            }}
          >

            <h1>
              Frontend error
            </h1>


            <p>

              The backend completed the job,
              but the frontend encountered
              an error while displaying the result.

            </p>


            <pre
              style={{
                whiteSpace:
                  "pre-wrap",

                background:
                  "#f3f4f6",

                padding: "16px",

                borderRadius: "10px",

                overflow: "auto",
              }}
            >

              {String(
                this.state.error
              )}

            </pre>


            <p>

              Open

              <strong>
                {" "}F12 → Console
              </strong>

              {" "}for the complete error.

            </p>

          </div>

        </div>

      );

    }


    return this.props.children;

  }

}


// ============================================================
// ROOT
// ============================================================

createRoot(
  document.getElementById(
    "root"
  )
).render(

  <ErrorBoundary>

    <App />

  </ErrorBoundary>

);