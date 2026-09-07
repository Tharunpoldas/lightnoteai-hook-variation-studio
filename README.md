# LightNoteAI — Full-Stack AI Hook Variation Studio

A full-stack AI-powered prototype for analyzing winning short-form video
advertisements, extracting their opening hook, understanding the creative
structure, generating alternative hook concepts, and producing downloadable
MP4 preview clips.

This project was developed as a technical assignment for LightNoteAI.

---

## Overview

Short-form advertisements often depend heavily on the first few seconds to
capture attention.

LightNoteAI analyzes the opening hook of a video and identifies:

- Spoken dialogue
- On-screen text
- Visual action
- Emotion
- Product appearance
- Hook structure
- Target audience
- Why the hook works

The system then uses Gemini to generate multiple alternative hook concepts
while preserving the original creative intent and energy.

The generated concepts are presented in the web interface and corresponding
preview MP4 clips are produced using FFmpeg.

---

# Architecture

```text
                         USER
                           |
                           v
                 React / Vite Frontend
                           |
                           | REST API
                           | multipart upload / URL
                           v
                    FastAPI Backend
                           |
             +-------------+-------------+
             |                           |
             v                           v
       Video Processing             Gemini API
          / FFmpeg               Multimodal Analysis
             |                           |
             |                    +------+------+
             |                    |             |
             |                    v             v
             |               Hook Analysis   Variations
             |                    |             |
             +--------------------+-------------+
                                  |
                                  v
                           Variation JSON
                                  |
                                  v
                              FFmpeg
                                  |
                                  v
                         Preview MP4 Clips
                                  |
                                  v
                         React Results UI
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
                 Preview                    Download


                 System Components
1. React + Vite Frontend

The frontend provides the user interface for the complete workflow.

Users can:

Upload a short-form video.
Drag and drop a video file.
Provide a public video URL.
Select variation strength.
Select the number of variations.
Start the generation process.
Monitor processing progress.
View the extracted hook.
View AI-generated hook analysis.
View creative insights.
Preview generated MP4 variations.
Download individual clips.

The frontend is responsible only for presentation and API communication.

Core AI and video-processing logic remains on the backend.

2. FastAPI Backend

FastAPI acts as the central application and orchestration layer.

When the user starts a generation request, the backend:

Receives the video or URL.
Validates the request.
Creates a unique job ID.
Saves the uploaded video or downloads the provided URL.
Checks the video metadata.
Starts the processing workflow in the background.
Sends the opening hook to Gemini.
Processes the generated variations using FFmpeg.
Stores the job state and output information.
Makes the results available to the frontend.

This architecture keeps the frontend lightweight and prevents expensive video and AI processing from happening inside the browser.

3. FFmpeg Video Processing

FFmpeg is responsible for deterministic video processing.

It is used for:

Reading video duration through ffprobe.
Extracting the first approximately 3 seconds of the source video.
Creating a lightweight preview for Gemini.
Creating MP4 variation previews.
Applying deterministic visual transformations.
Encoding the final preview clips.

The first few seconds of the source video are converted into a lightweight preview before being sent to Gemini. This reduces the amount of data transferred to the AI API and makes the processing workflow more efficient.

4. Gemini Multimodal AI

Gemini provides the intelligence layer of the application.

The backend sends the hook preview to Gemini along with a structured prompt.

Gemini analyzes the advertisement opening and identifies elements such as:

Hook timing
Spoken line
On-screen text
Visual action
Emotional tone
Product appearance
Hook structure
Target audience
Creative strategy
Reason why the hook works

Gemini then generates multiple alternative hook concepts.

Each variation can contain information such as:

Hook line
On-screen text
Visual direction
Emotion
Creative rationale

The AI response is requested as structured JSON, allowing the backend to parse and use the generated information reliably.

5. AI Prompting Strategy

The Gemini prompt is designed to make the model behave as a short-form advertising creative analyst.

The prompt instructs the model to:

Focus primarily on the first 1–3 seconds.
Identify the main attention-grabbing mechanism.
Understand the visual and verbal structure.
Preserve the original energy and creative intent.
Generate meaningful variations rather than simple word replacements.
Adjust variation strength according to the selected setting.
Avoid unsupported factual claims.
Avoid inventing statistics or numerical results.
Return structured JSON.

This allows the application to separate AI reasoning from frontend presentation.

6. Variation Strength

The application supports different creative variation strengths.

Light

Makes relatively small changes while preserving most of the original hook structure.

Balanced

Preserves the main creative idea while changing wording, framing, or presentation.

Strong

Creates more significant creative alternatives while attempting to preserve the original energy and advertising objective.

This parameter is passed to the backend and influences the Gemini generation strategy.

7. Structured AI Output

Instead of relying on free-form text, the backend requests structured JSON from Gemini.

Conceptually, the response contains:

{
  "hook": {
    "start": 0,
    "end": 3,
    "spoken_line": "...",
    "on_screen_text": "...",
    "visual_action": "...",
    "emotion": "..."
  },
  "analysis": {
    "why_it_works": "...",
    "target_audience": "...",
    "creative_insight": "..."
  },
  "variations": [
    {
      "hook_line": "...",
      "on_screen_text": "...",
      "visual_direction": "...",
      "emotion": "...",
      "rationale": "..."
    }
  ]
}

The actual AI response is validated and cleaned by the backend before being returned to the frontend.

Structured output makes the application more reliable than directly displaying unrestricted model-generated text.

8. Background Job Processing

Video analysis and processing can take several seconds.

Instead of keeping the frontend waiting for a long synchronous request, the backend creates a job and processes it in the background.

The workflow is:

POST /api/jobs
       |
       v
Create Job ID
       |
       v
Background Processing
       |
       +------> Video Processing
       |
       +------> Gemini Analysis
       |
       +------> FFmpeg Variations
       |
       v
Update Job Status
       |
       v
Completed

The frontend periodically checks the job status using:

GET /api/jobs/{job_id}

Typical job states are:

queued
   ↓
processing
   ↓
completed

or:

queued
   ↓
processing
   ↓
failed

This provides a better user experience and creates a foundation for replacing the prototype background mechanism with a production job queue.

9. End-to-End Data Flow
User
 |
 | Upload Video / Video URL
 v
React + Vite Frontend
 |
 | POST /api/jobs
 v
FastAPI Backend
 |
 | Create Job ID
 v
Save / Download Source Video
 |
 v
FFmpeg
 |
 | Extract approximately first 3 seconds
 v
Lightweight Hook Preview
 |
 v
Gemini Multimodal AI
 |
 +-----------------------------+
 |                             |
 v                             v
Hook Analysis             Hook Variations
 |                             |
 +-------------+---------------+
               |
               v
        Structured JSON
               |
               v
             FFmpeg
               |
               v
       MP4 Preview Clips
               |
               v
          Job Completed
               |
               v
       React Results Page
               |
        +------+------+
        |             |
        v             v
      Preview       Download
10. Storage Architecture

The prototype uses filesystem-based storage.

storage/
├── uploads/
│   └── {job_id}/
│       └── source.mp4
│
├── jobs/
│   └── {job_id}.json
│
└── outputs/
    └── {job_id}/
        ├── variation_1.mp4
        ├── variation_2.mp4
        ├── variation_3.mp4
        ├── variation_4.mp4
        └── variation_5.mp4
uploads/

Stores the original source video associated with each job.

jobs/

Stores job metadata, status, analysis, and variation information.

outputs/

Stores the generated MP4 preview clips.

For the assignment prototype, filesystem storage keeps the implementation simple.

For production, this layer could be replaced with:

PostgreSQL for persistent metadata.
Redis for job state and queues.
Amazon S3 or Google Cloud Storage for video files.
11. Results Layer

Once the job is completed, the React frontend displays the generated results.

The results interface includes:

Original video
Original hook
Hook timing
Spoken line
On-screen text
Visual action
Emotional tone
Product appearance
Creative insight
Target audience
Hook variations
Video previews
Download buttons

This gives the user both the AI explanation and the practical creative outputs.

API Endpoints
Health Check
GET /api/health

Returns the health status of the backend.

Create Processing Job
POST /api/jobs

Accepts:

Video upload
Video URL
Variation count
Variation strength

Returns a unique job ID.

Get Job Status
GET /api/jobs/{job_id}

Returns:

Job ID
Status
Progress
Analysis
Variations
Output information
Error information when applicable
Get Original Source
GET /api/jobs/{job_id}/source

Returns the uploaded source video.

Get Generated Clip
GET /api/jobs/{job_id}/clips/{filename}

Returns an individual generated MP4 preview.

Frontend Workflow

The frontend follows this flow:

1. Select Video
       ↓
2. Configure Variations
       ↓
3. Click Generate
       ↓
4. Create Backend Job
       ↓
5. Show Processing Status
       ↓
6. Poll Job Status
       ↓
7. Receive Completed Results
       ↓
8. Display Hook Analysis
       ↓
9. Display Variations
       ↓
10. Preview / Download Clips
URL Input

The application also supports processing through a public video URL.

The backend handles URL downloading rather than performing the operation in the browser.

yt-dlp is used as the downloader for supported public video sources.

The downloaded media then enters the same processing pipeline as an uploaded video.

Video URL
   |
   v
FastAPI
   |
   v
yt-dlp
   |
   v
Local Source Video
   |
   v
FFmpeg + Gemini
Technology Stack
Frontend
React
Vite
JavaScript
CSS
Fetch API
Backend
Python
FastAPI
Uvicorn
BackgroundTasks
python-dotenv
AI
Google Gemini Multimodal API
Structured JSON generation
Video Processing
FFmpeg
FFprobe
yt-dlp
Storage
Local filesystem for prototype
Why Gemini?

Gemini was selected because the application requires multimodal understanding of short-form video.

The model can reason about multiple components of an advertisement opening, including:

Visual content
Spoken content
Text overlays
Emotional tone
Product presence
Creative structure

This makes a multimodal model more suitable than a text-only LLM for the hook-analysis problem.

Why FastAPI?

FastAPI was selected because it provides:

Lightweight REST APIs
Strong Python ecosystem support
Easy file upload handling
Background task support
Simple integration with FFmpeg
Easy integration with Gemini
Automatic API documentation

It also provides a clean separation between the frontend and AI/video-processing layers.

Why FFmpeg?

FFmpeg provides reliable and deterministic video processing.

Instead of depending on an AI model to perform basic media operations, FFmpeg handles:

Video trimming
Encoding
Scaling
Video metadata extraction
Preview generation
MP4 generation

This makes the media-processing part of the pipeline predictable.

Gemini Reliability and Error Handling

External AI APIs can experience temporary failures such as:

HTTP 503
HTTP 429
HTTP 408
HTTP 500
HTTP 502
HTTP 504
Network connection failures
Connection resets
Timeouts

The backend therefore implements retry handling with exponential backoff and jitter.

The application also supports a primary and fallback Gemini model.

Conceptually:

Gemini Request
      |
      v
Primary Model
      |
   Failure?
      |
      v
Retry with Backoff
      |
   Still failing?
      |
      v
Fallback Model
      |
      v
Return Result / Error

This improves reliability when temporary API failures occur.

Error Handling

The backend handles common failures such as:

Missing video
Invalid URL
Unsupported input
Video download failure
FFmpeg failure
Gemini API failure
Invalid AI response
Job processing failure

The frontend displays user-friendly error messages instead of exposing raw backend exceptions.

Prototype Design Decision

The current prototype deliberately separates AI creative generation from deterministic video processing.

Gemini is responsible for:

Understanding the hook.
Analyzing the advertisement.
Generating creative hook concepts.
Producing variation copy and creative directions.

FFmpeg is responsible for:

Extracting the opening footage.
Processing the video.
Creating MP4 preview variations.
Applying deterministic visual transformations.

The current prototype uses the original opening footage as the basis for the generated preview clips.

The AI-generated hook copy and creative directions are presented in the interface rather than being burned directly into the MP4 files.

This design was chosen to keep the prototype:

Reliable
Fast
Reproducible
Easy to debug
Explainable

It also avoids falsely claiming that the prototype generates entirely new AI video scenes.

Current Prototype Limitations

The current implementation is an MVP/prototype and has several limitations.

1. Video Generation

The current output clips reuse the original opening footage with deterministic FFmpeg visual transformations.

It does not currently generate completely new video scenes using a generative video model.

2. Text Rendering

The generated hook copy is displayed in the application interface.

It is not currently burned directly into the generated MP4 files.

3. Voice Generation

The prototype does not currently generate new voiceovers or perform lip synchronization.

4. Storage

The prototype uses local filesystem storage instead of cloud object storage.

5. Background Processing

FastAPI background tasks are used for the prototype.

A production deployment should use a durable distributed task queue.

6. Database

Job metadata is currently stored using local files.

A production system should use a persistent database.

Production Architecture

A production-ready version could evolve into the following architecture:

                         USER
                           |
                           v
                  +----------------+
                  | React Frontend |
                  +-------+--------+
                          |
                          v
                  +----------------+
                  | API Gateway /  |
                  | Load Balancer  |
                  +-------+--------+
                          |
                          v
                  +----------------+
                  | FastAPI API    |
                  +-------+--------+
                          |
             +------------+------------+
             |                         |
             v                         v
      +--------------+          +-------------+
      | PostgreSQL   |          |    Redis    |
      | Job Metadata |          | Queue/State |
      +--------------+          +------+------+
                                        |
                                        v
                                +---------------+
                                | Worker        |
                                | Processing    |
                                +-------+-------+
                                        |
                       +----------------+----------------+
                       |                                 |
                       v                                 v
                +-------------+                   +-------------+
                | Gemini API  |                   |   FFmpeg   |
                | AI Analysis |                   | Processing |
                +-------------+                   +------+------+
                                                       |
                                                       v
                                               +---------------+
                                               | S3 / GCS     |
                                               | Video Storage|
                                               +---------------+

A production version could additionally introduce:

Redis queues
Celery/RQ or another worker system
PostgreSQL
S3/GCS object storage
Signed download URLs
Authentication
Rate limiting
Monitoring
Logging
Containerization
Horizontal scaling
Engineering Decisions
Separation of Concerns

The frontend, backend, AI layer, and video-processing layer are separated.

This makes the application easier to maintain and extend.

Deterministic Video Processing

FFmpeg is used for predictable media operations instead of relying on an AI model for basic video manipulation.

Multimodal AI

Gemini is used because the task requires understanding both visual and textual/spoken components of a video.

Structured Output

JSON-based AI output makes downstream processing more predictable.

Asynchronous Processing

Background processing prevents long-running AI/video operations from blocking the user interface.

Retry and Fallback

AI API failures are handled using retries, exponential backoff, jitter, and a fallback model.

Prototype-to-Production Path

The current filesystem and background-task architecture is intentionally simple, while the components are separated so they can later be replaced by PostgreSQL, Redis, workers, and cloud storage.

Project Structure
lightnoteai_assignment/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   └── video.py
│   │
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   └── styles.css
│   │
│   ├── index.html
│   ├── package.json
│   └── package-lock.json
│
├── storage/
│   ├── uploads/
│   ├── jobs/
│   └── outputs/
│
├── .gitignore
└── README.md
Requirements

Before running the application, install:

Python 3.9+
Node.js
npm
FFmpeg
Gemini API key

FFmpeg is expected to be available on the system PATH. The current prototype also supports a configured local FFmpeg fallback path.

Installation
1. Clone the Repository
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd lightnoteai_assignment
Backend Setup

Navigate to the backend:

cd backend

Create a Python virtual environment:

python -m venv .venv

Activate it on Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt
Environment Variables

Create:

backend/.env

Add:

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
GEMINI_FALLBACK_MODEL=gemini-3.7-flash
MAX_UPLOAD_MB=100
HOOK_SECONDS=3
OUTPUT_VARIATIONS=5

Never commit the real .env file or API keys to GitHub.

Start the Backend

From the backend directory:

.venv\Scripts\activate
python -m uvicorn app.main:app --reload --port 8000

The backend will run at:

http://127.0.0.1:8000

API documentation is available at:

http://127.0.0.1:8000/docs

Health check:

http://127.0.0.1:8000/api/health
Frontend Setup

Open another terminal.

Navigate to:

cd frontend

Install dependencies:

npm install

Start the development server:

npm run dev

The frontend will normally be available at:

http://localhost:5173
Demo Flow

A typical demo follows this workflow:

1. Open the LightNoteAI frontend.
2. Upload a short-form advertisement.
3. Select the desired variation strength.
4. Select the number of variations.
5. Click Generate.
6. Observe the processing state.
7. Wait for Gemini analysis and FFmpeg processing.
8. View the extracted hook.
9. Read the AI-generated hook analysis.
10. Review the generated hook variations.
11. Preview the MP4 clips.
12. Download the desired variation.
Assignment Requirement Mapping
Assignment Requirement	Implementation
Upload winning video	React file upload
Video URL input	FastAPI + yt-dlp
Identify 1–3 second hook	FFmpeg extracts opening preview + Gemini analyzes it
Analyze hook structure	Gemini multimodal analysis
Analyze visual action	Gemini
Analyze text overlay	Gemini
Analyze spoken line	Gemini
Analyze emotion	Gemini
Analyze product appearance	Gemini
Generate 5–10 variations	Gemini structured generation
Variation strength	Light / Balanced / Strong
Preview generated clips	React video player
Download clips	Backend MP4 endpoints
Backend required	FastAPI
AI integration	Gemini API
Video processing	FFmpeg
Background processing	FastAPI BackgroundTasks
Error handling	Backend retry/error handling
Clean API	REST endpoints
Comparison/review UI	Variation cards and previews
Security Considerations

The application should follow basic API security practices.

Important considerations include:

Never commit API keys.
Keep secrets in environment variables.
Add .env to .gitignore.
Validate uploaded file types.
Limit upload size.
Sanitize filenames.
Validate public URLs.
Apply authentication in production.
Add rate limiting in production.
Use signed URLs for cloud video downloads.
Restrict access to job results.
Git Ignore

The repository should not commit:

.env
.venv/
node_modules/
frontend/dist/
storage/uploads/
storage/jobs/
storage/outputs/

Example .gitignore:

# Environment
.env
*.env

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Node
node_modules/
frontend/dist/

# Generated files
storage/uploads/*
storage/jobs/*
storage/outputs/*

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
Future Improvements

The prototype can be extended into a more complete AI creative generation platform.

Potential improvements include:

AI Video Generation

Integrate a dedicated generative-video model to create entirely new visual scenes for each hook.

Text Overlay Generation

Automatically render AI-generated hook text into the video using FFmpeg or a video composition engine.

Voice Generation

Add text-to-speech for generated hook scripts.

Lip Synchronization

Synchronize generated speech with the speaker's mouth movement.

Better Video Understanding

Use speech-to-text and OCR models alongside multimodal vision analysis.

Persistent Database

Replace JSON job storage with PostgreSQL.

Distributed Processing

Replace FastAPI BackgroundTasks with Redis + Celery/RQ workers.

Cloud Storage

Move videos to S3/GCS for scalable storage.

Authentication

Add user accounts and protected job histories.

Analytics

Track which hook variations users select or download.

A/B Testing

Allow marketers to compare different hook variations and measure performance.

Future Vision

The long-term vision is to transform LightNoteAI from a hook-analysis prototype into an AI-powered creative production platform.

A future workflow could be:

Winning Advertisement
        |
        v
Hook Detection
        |
        v
Multimodal Analysis
        |
        v
Creative Strategy
        |
        v
Multiple Hook Concepts
        |
        +-------------------+
        |                   |
        v                   v
   New Scripts         New Visuals
        |                   |
        +---------+---------+
                  |
                  v
            AI Video Generation
                  |
                  v
             Voice / TTS
                  |
                  v
             Lip Sync
                  |
                  v
          Final Advertisement
                  |
                  v
             A/B Testing
                  |
                  v
          Performance Feedback
                  |
                  +-------> Future AI Generation

This would create a feedback-driven creative optimization system where successful advertising patterns can continuously influence future variations.

Demo

The demo demonstrates the complete workflow:

Upload
  ↓
Hook Extraction
  ↓
Gemini Analysis
  ↓
Variation Generation
  ↓
FFmpeg Processing
  ↓
Preview
  ↓
Download
Limitations

This project is an assignment-focused prototype rather than a production advertising-generation platform.

The main limitations are:

Local filesystem storage.
Prototype background processing.
No persistent database.
No authentication.
No completely AI-generated video scenes.
No automated voice generation.
No lip synchronization.
AI-generated copy is displayed in the interface rather than burned directly into the MP4.
Generated preview clips are based on the original opening footage.

These limitations are intentional for the scope of the prototype and provide clear opportunities for future development.

Conclusion

LightNoteAI demonstrates a practical full-stack architecture for AI-assisted short-form advertising analysis and hook variation generation.

The system combines:

React + Vite for the user interface.
FastAPI for backend orchestration.
Gemini Multimodal AI for creative understanding and variation generation.
FFmpeg for deterministic video processing.
Background processing for long-running tasks.
Filesystem storage for the prototype.

The architecture is modular and provides a clear path toward a production system using distributed workers, persistent databases, cloud storage, generative video, voice synthesis, and analytics