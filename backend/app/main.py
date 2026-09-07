import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import FileResponse, JSONResponse

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from .video import (
    analyze_with_gemini,
    create_hook_variation_clips,
    download_video,
    get_video_duration,
    save_upload,
)


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"

load_dotenv(
    ENV_FILE,
    override=True
)


# ============================================================
# STORAGE
# ============================================================

STORAGE = (
    BASE_DIR.parent
    / "storage"
)

UPLOADS = (
    STORAGE
    / "uploads"
)

JOBS = (
    STORAGE
    / "jobs"
)

OUTPUTS = (
    STORAGE
    / "outputs"
)


for directory in [
    UPLOADS,
    JOBS,
    OUTPUTS,
]:

    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# SETTINGS
# ============================================================

MAX_UPLOAD_MB = int(
    os.getenv(
        "MAX_UPLOAD_MB",
        "100"
    )
)

HOOK_SECONDS = float(
    os.getenv(
        "HOOK_SECONDS",
        "3"
    )
)

DEFAULT_VARIATIONS = int(
    os.getenv(
        "OUTPUT_VARIATIONS",
        "5"
    )
)


# Keep value safe
if DEFAULT_VARIATIONS < 5:
    DEFAULT_VARIATIONS = 5

if DEFAULT_VARIATIONS > 10:
    DEFAULT_VARIATIONS = 10


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="LightNoteAI Hook Generator",
    description=(
        "AI-powered short-form video "
        "hook analysis and variation generator."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# FRONTEND BUILD
# ============================================================

FRONTEND_DIR = (
    BASE_DIR.parent
    / "frontend"
    / "dist"
)


if FRONTEND_DIR.exists():

    app.mount(
        "/app",
        StaticFiles(
            directory=FRONTEND_DIR,
            html=True,
        ),
        name="frontend",
    )


# ============================================================
# PYDANTIC MODELS
# ============================================================

class GenerateRequest(BaseModel):

    variation_count: int = Field(
        default=5,
        ge=5,
        le=10,
    )

    strength: str = Field(
        default="balanced",
        pattern="^(light|balanced|strong)$",
    )


class JobResponse(BaseModel):

    job_id: str


# ============================================================
# JOB FILE
# ============================================================

def job_path(
    job_id: str,
) -> Path:

    return (
        JOBS
        / f"{job_id}.json"
    )


# ============================================================
# WRITE JOB
# ============================================================

def write_job(
    job_id: str,
    **updates,
):

    path = job_path(
        job_id
    )

    data = {}

    if path.exists():

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

        except Exception:

            data = {}

    # --------------------------------------------------------
    # IMPORTANT
    # Always preserve job_id.
    # --------------------------------------------------------

    data["job_id"] = job_id

    # Apply new values
    data.update(
        updates
    )

    # Never allow job_id to disappear
    data["job_id"] = job_id

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ============================================================
# READ JOB
# ============================================================

def read_job(
    job_id: str,
):

    path = job_path(
        job_id
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Job not found.",
        )

    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Could not read job data.",
        )

    # --------------------------------------------------------
    # Safety: always return job_id
    # --------------------------------------------------------

    data["job_id"] = job_id

    return data


# ============================================================
# BACKGROUND PROCESSING
# ============================================================

def process_job(
    job_id: str,
    video_path: Path,
    variation_count: int,
    strength: str,
):

    try:

        print("=" * 70)

        print(
            f"[Job {job_id}] "
            "STARTED"
        )

        print(
            f"[Job {job_id}] "
            f"Variations: {variation_count}"
        )

        print(
            f"[Job {job_id}] "
            f"Strength: {strength}"
        )

        print("=" * 70)


        # ====================================================
        # STEP 1 — GEMINI
        # ====================================================

        write_job(

            job_id,

            status="processing",

            progress=15,

            message=(
                "Analyzing the first "
                "3 seconds with Gemini..."
            ),

        )


        print(
            f"[Job {job_id}] "
            "Starting Gemini analysis..."
        )


        analysis = analyze_with_gemini(

            video_path=video_path,

            hook_seconds=HOOK_SECONDS,

            strength=strength,

            variation_count=variation_count,

        )


        # ====================================================
        # STEP 2 — ANALYSIS COMPLETE
        # ====================================================

        write_job(

            job_id,

            status="processing",

            progress=55,

            message=(
                "Hook analyzed. "
                "Creating video variations..."
            ),

            analysis=analysis,

        )


        # ====================================================
        # STEP 3 — OUTPUT DIRECTORY
        # ====================================================

        output_dir = (
            OUTPUTS
            / job_id
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        # ====================================================
        # STEP 4 — GET VARIATIONS
        # ====================================================

        variations = analysis.get(
            "variations",
            []
        )


        if not isinstance(
            variations,
            list,
        ):

            variations = []


        variations = variations[
            :variation_count
        ]


        if not variations:

            raise RuntimeError(
                "No hook variations "
                "were generated."
            )


        # ====================================================
        # STEP 5 — CREATE CLIPS
        # ====================================================

        print(
            f"[Job {job_id}] "
            f"Creating {len(variations)} clips..."
        )


        clips = create_hook_variation_clips(

            video_path=video_path,

            output_dir=output_dir,

            variations=variations,

            hook_seconds=HOOK_SECONDS,

            strength=strength,

        )


        # ====================================================
        # STEP 6 — ADD CLIP URLS
        # ====================================================

        for index, variation in enumerate(
            variations
        ):

            if index >= len(clips):
                continue


            filename = Path(
                clips[index]
            ).name


            variation["clip_url"] = (
                f"/api/jobs/"
                f"{job_id}/clips/"
                f"{filename}"
            )


            variation["clip_filename"] = (
                filename
            )


        # ====================================================
        # STEP 7 — COMPLETED
        # ====================================================

        write_job(

            job_id,

            status="completed",

            progress=100,

            message=(
                "Hook analysis and "
                "variations completed."
            ),

            analysis=analysis,

            variations=variations,

            clip_count=len(clips),

        )


        print("=" * 70)

        print(
            f"[Job {job_id}] "
            "COMPLETED SUCCESSFULLY"
        )

        print(
            f"[Job {job_id}] "
            f"Clips: {len(clips)}"
        )

        print("=" * 70)


    except Exception as exc:

        print("=" * 70)

        print(
            f"[Job {job_id}] FAILED"
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        print("=" * 70)


        write_job(

            job_id,

            status="failed",

            progress=100,

            message=str(exc),

            error_type=(
                type(exc).__name__
            ),

        )


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/api/health"
)
def health():

    return {

        "status": "ok",

        "service":
            "lightnoteai-hook-generator",

        "gemini_model":
            os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ),

    }


# ============================================================
# CREATE JOB
# ============================================================

@app.post(
    "/api/jobs",
    response_model=JobResponse,
)
async def create_job(

    background_tasks: BackgroundTasks,

    video: Optional[
        UploadFile
    ] = File(
        default=None
    ),

    url: Optional[
        str
    ] = Form(
        default=None
    ),

    variation_count: int = Form(
        default=5
    ),

    strength: str = Form(
        default="balanced"
    ),

):

    # ========================================================
    # VALIDATE VIDEO SOURCE
    # ========================================================

    if (
        video is None
        and not url
    ):

        raise HTTPException(

            status_code=400,

            detail=(
                "Upload a video "
                "or provide a video URL."
            ),

        )


    # ========================================================
    # VALIDATE VARIATION COUNT
    # ========================================================

    if not 5 <= variation_count <= 10:

        raise HTTPException(

            status_code=400,

            detail=(
                "Variation count must "
                "be between 5 and 10."
            ),

        )


    # ========================================================
    # VALIDATE STRENGTH
    # ========================================================

    if strength not in {
        "light",
        "balanced",
        "strong",
    }:

        raise HTTPException(

            status_code=400,

            detail=(
                "Strength must be "
                "light, balanced or strong."
            ),

        )


    # ========================================================
    # CREATE JOB ID
    # ========================================================

    job_id = uuid.uuid4().hex


    job_upload_dir = (
        UPLOADS
        / job_id
    )


    job_upload_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    try:

        # ====================================================
        # UPLOAD FILE
        # ====================================================

        if video is not None:

            filename = Path(
                video.filename
                or "input.mp4"
            ).name


            suffix = (
                Path(filename)
                .suffix
                .lower()
            )


            allowed_formats = {

                ".mp4",
                ".mov",
                ".avi",
                ".mkv",
                ".webm",
                ".m4v",

            }


            if suffix not in allowed_formats:

                raise HTTPException(

                    status_code=400,

                    detail=(
                        "Unsupported video format. "
                        "Use MP4, MOV, AVI, MKV, "
                        "WEBM or M4V."
                    ),

                )


            video_path = (
                job_upload_dir
                / f"source{suffix}"
            )


            write_job(

                job_id,

                status="uploading",

                progress=5,

                message="Uploading video...",

            )


            await save_upload(

                video,

                video_path,

                MAX_UPLOAD_MB,

            )


        # ====================================================
        # VIDEO URL
        # ====================================================

        else:

            video_path = (
                job_upload_dir
                / "source.mp4"
            )


            write_job(

                job_id,

                status="downloading",

                progress=5,

                message="Downloading video...",

            )


            download_video(

                url.strip(),

                video_path,

            )


        # ====================================================
        # VERIFY VIDEO
        # ====================================================

        duration = get_video_duration(
            video_path
        )


        if duration <= 0:

            raise ValueError(
                "Could not read video duration."
            )


        if duration < 0.5:

            raise ValueError(
                "Video is too short."
            )


        # ====================================================
        # QUEUE JOB
        # ====================================================

        write_job(

            job_id,

            status="queued",

            progress=10,

            message=(
                "Video ready. "
                "Starting AI analysis..."
            ),

            duration=duration,

            variation_count=variation_count,

            strength=strength,

        )


        # ====================================================
        # START BACKGROUND TASK
        # ====================================================

        background_tasks.add_task(

            process_job,

            job_id,

            video_path,

            variation_count,

            strength,

        )


        print(
            f"[Job {job_id}] "
            "Queued successfully."
        )


        return {
            "job_id": job_id
        }


    except HTTPException:

        shutil.rmtree(
            job_upload_dir,
            ignore_errors=True
        )

        raise


    except Exception as exc:

        print(
            f"[Job {job_id}] "
            "Creation failed:"
        )

        print(
            exc
        )


        shutil.rmtree(
            job_upload_dir,
            ignore_errors=True
        )


        raise HTTPException(

            status_code=400,

            detail=str(exc),

        )


# ============================================================
# GET JOB STATUS
# ============================================================

@app.get(
    "/api/jobs/{job_id}"
)
def get_job(
    job_id: str
):

    data = read_job(
        job_id
    )


    response = JSONResponse(
        content=data
    )


    # Prevent browser/proxy caching
    response.headers[
        "Cache-Control"
    ] = "no-store, no-cache, must-revalidate, max-age=0"

    response.headers[
        "Pragma"
    ] = "no-cache"

    return response


# ============================================================
# GET SOURCE VIDEO
# ============================================================

@app.get(
    "/api/jobs/{job_id}/source"
)
def get_source(
    job_id: str
):

    directory = (
        UPLOADS
        / job_id
    )


    if not directory.exists():

        raise HTTPException(

            status_code=404,

            detail="Source video not found.",

        )


    matches = list(
        directory.glob(
            "source.*"
        )
    )


    if not matches:

        raise HTTPException(

            status_code=404,

            detail="Source video not found.",

        )


    source_path = matches[0]


    return FileResponse(

        source_path,

        media_type="video/mp4",

    )


# ============================================================
# GET GENERATED CLIP
# ============================================================

@app.get(
    "/api/jobs/{job_id}/clips/{filename}"
)
def get_clip(
    job_id: str,
    filename: str,
):

    # Prevent path traversal
    safe_filename = Path(
        filename
    ).name


    output_path = (
        OUTPUTS
        / job_id
        / safe_filename
    )


    if not output_path.exists():

        raise HTTPException(

            status_code=404,

            detail="Generated clip not found.",

        )


    return FileResponse(

        output_path,

        media_type="video/mp4",

        filename=safe_filename,

    )


# ============================================================
# FRONTEND FALLBACK
# ============================================================

@app.get(
    "/{full_path:path}"
)
def frontend_fallback(
    full_path: str
):

    index_file = (
        FRONTEND_DIR
        / "index.html"
    )


    if (
        index_file.exists()
        and not full_path.startswith(
            "api/"
        )
    ):

        return FileResponse(
            index_file
        )


    raise HTTPException(

        status_code=404,

        detail="Not found.",

    )