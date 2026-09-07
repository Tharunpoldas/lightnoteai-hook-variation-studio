import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types


# ============================================================
# ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

PRIMARY_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
).strip()

FALLBACK_MODEL = os.getenv(
    "GEMINI_FALLBACK_MODEL",
    "gemini-3.7-flash"
).strip()

MAX_RETRIES = int(
    os.getenv("GEMINI_MAX_RETRIES", "6")
)

HOOK_SECONDS = float(
    os.getenv("HOOK_SECONDS", "3")
)


# ============================================================
# STARTUP LOGGING
# ============================================================

print("=" * 70)
print("[LightNoteAI] Video module loaded")
print(f"[Gemini] API key loaded: {bool(GEMINI_API_KEY)}")
print(f"[Gemini] Primary model: {PRIMARY_MODEL}")
print(f"[Gemini] Fallback model: {FALLBACK_MODEL}")
print(f"[Gemini] Max retries: {MAX_RETRIES}")
print("=" * 70)


# ============================================================
# GEMINI CLIENT
# ============================================================

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Add it to backend/.env"
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# FFMPEG CONFIGURATION
# ============================================================

DEFAULT_FFMPEG_DIR = (
    Path.home()
    / "Desktop"
    / "ffmpeg-9.0.1-essentials_build"
    / "ffmpeg-9.0.1-essentials_build"
    / "bin"
)

FFMPEG_ENV = os.getenv(
    "FFMPEG_PATH",
    ""
).strip()

if FFMPEG_ENV:
    FFMPEG_DIR = Path(FFMPEG_ENV)
else:
    FFMPEG_DIR = DEFAULT_FFMPEG_DIR


def find_executable(name: str) -> str:
    """
    Locate FFmpeg executable.

    Search order:
    1. Windows PATH
    2. FFMPEG_PATH from .env
    3. Known Desktop installation
    """

    executable = shutil.which(name)

    if executable:
        return executable

    local_executable = (
        FFMPEG_DIR / f"{name}.exe"
    )

    if local_executable.exists():
        return str(local_executable)

    raise FileNotFoundError(
        f"{name}.exe was not found.\n"
        f"Expected location:\n"
        f"{local_executable}\n\n"
        f"Install FFmpeg or set FFMPEG_PATH in .env."
    )


def ffmpeg_path() -> str:
    return find_executable("ffmpeg")


def ffprobe_path() -> str:
    return find_executable("ffprobe")


# ============================================================
# FILE UPLOAD
# ============================================================

async def save_upload(
    upload_file,
    destination: Path,
    max_mb: int = 100
) -> Path:

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    max_bytes = (
        max_mb * 1024 * 1024
    )

    total_bytes = 0

    try:

        with destination.open("wb") as output:

            while True:

                chunk = await upload_file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > max_bytes:

                    output.close()

                    try:
                        destination.unlink()
                    except FileNotFoundError:
                        pass

                    raise ValueError(
                        f"Video exceeds the "
                        f"{max_mb} MB upload limit."
                    )

                output.write(chunk)

    finally:

        await upload_file.close()

    print(
        f"[Upload] Saved video: "
        f"{destination}"
    )

    print(
        f"[Upload] Size: "
        f"{total_bytes / (1024 * 1024):.2f} MB"
    )

    return destination


# ============================================================
# VIDEO URL DOWNLOAD
# ============================================================

def download_video(
    url: str,
    output_path: Path
) -> Path:

    if not url:
        raise ValueError(
            "Video URL is empty."
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    yt_dlp = shutil.which(
        "yt-dlp"
    )

    if yt_dlp:
        command = [yt_dlp]
    else:
        command = [
            sys.executable,
            "-m",
            "yt_dlp"
        ]

    command.extend([
        "--no-playlist",
        "-f",
        "mp4/bestvideo+bestaudio/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(output_path),
        url
    ])

    print(
        "[Download] Downloading video URL..."
    )

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            "[Download] Error:"
        )

        print(
            result.stderr
        )

        raise RuntimeError(
            "Could not download the video URL."
        )

    if not output_path.exists():

        raise RuntimeError(
            "Video download finished but "
            "output file was not created."
        )

    print(
        f"[Download] Download complete: "
        f"{output_path}"
    )

    return output_path


# ============================================================
# VIDEO DURATION
# ============================================================

def get_video_duration(
    video_path: Path
) -> float:

    command = [
        ffprobe_path(),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        raise RuntimeError(
            f"FFprobe failed:\n"
            f"{result.stderr}"
        )

    try:

        duration = float(
            result.stdout.strip()
        )

    except ValueError:

        raise RuntimeError(
            "Unable to determine video duration."
        )

    return duration


# ============================================================
# CREATE GEMINI HOOK PREVIEW
# ============================================================

def create_hook_preview(
    video_path: Path,
    output_path: Path,
    hook_seconds: float = 3.0
) -> Path:

    duration = get_video_duration(
        video_path
    )

    actual_duration = min(
        max(hook_seconds, 0.5),
        duration
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"[FFmpeg] Creating hook preview "
        f"({actual_duration:.2f}s)..."
    )

    command = [
        ffmpeg_path(),
        "-y",
        "-ss",
        "0",
        "-i",
        str(video_path),
        "-t",
        str(actual_duration),
        "-vf",
        "scale='min(720,iw)':-2",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "30",
        "-movflags",
        "+faststart",
        str(output_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        print(
            result.stderr
        )

        raise RuntimeError(
            "FFmpeg could not create "
            "the Gemini hook preview."
        )

    if not output_path.exists():

        raise RuntimeError(
            "Hook preview was not created."
        )

    size_mb = (
        output_path.stat().st_size
        / (1024 * 1024)
    )

    print(
        f"[FFmpeg] Hook preview ready: "
        f"{size_mb:.2f} MB"
    )

    return output_path


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(
    text: str
) -> Dict[str, Any]:

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    # Remove markdown JSON fences
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    # Direct JSON
    try:

        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # Search for JSON object
    start = text.find("{")
    end = text.rfind("}")

    if (
        start != -1
        and end != -1
        and end > start
    ):

        candidate = text[
            start:end + 1
        ]

        try:

            return json.loads(
                candidate
            )

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini returned invalid JSON."
    )


# ============================================================
# PROMPT
# ============================================================

def build_analysis_prompt(
    hook_seconds: float,
    strength: str,
    variation_count: int
) -> str:

    strength_description = {

        "light":
            "Keep variations very close to the original hook. "
            "Make subtle wording and presentation changes.",

        "balanced":
            "Preserve the original concept, energy and structure "
            "while creating meaningful new hook ideas.",

        "strong":
            "Create substantially different hook wording and "
            "presentation while preserving the original concept "
            "and advertising energy."

    }.get(
        strength,
        "Preserve the original concept and energy."
    )

    return f"""
You are an expert short-form video advertising strategist.

Analyze the first {hook_seconds:.1f} seconds of the supplied video.

This is a winning short-form advertisement.

Your job is to:

1. Identify the hook.
2. Analyze the hook structure.
3. Identify visible text.
4. Identify spoken dialogue if audible.
5. Identify visual action.
6. Identify emotion.
7. Identify product appearance.
8. Explain why the hook works.
9. Identify the target audience.
10. Generate exactly {variation_count} meaningful hook variations.

VARIATION STRENGTH:

{strength_description}

IMPORTANT ACCURACY RULES:

- Analyze only what is actually visible or audible.
- Do not invent facts.
- Do not invent statistics.
- Do not invent numerical claims.
- Do not invent product features.
- Do not invent brand names.
- Do not invent people.
- Do not invent results.
- Do not claim specific time savings unless the video explicitly says so.
- Preserve the original advertising intent.
- Preserve the original energy.
- Keep variations realistic for TikTok, Instagram Reels and YouTube Shorts.
- Variations should be usable by a video editor.
- If something cannot be determined, write "Not clearly visible".
- Do not write explanations outside the JSON.

The hook should focus on the first 1–3 seconds.

Return ONLY valid JSON.

Use exactly this format:

{{
    "hook": {{
        "start": 0,
        "end": {hook_seconds},
        "spoken_line": "",
        "on_screen_text": "",
        "visual_action": "",
        "emotion": "",
        "product_appearance": ""
    }},

    "analysis": {{
        "why_it_works": "",
        "target_audience": "",
        "structure": ""
    }},

    "variations": [
        {{
            "id": 1,
            "hook_line": "",
            "on_screen_text": "",
            "visual_direction": "",
            "emotion": "",
            "rationale": ""
        }}
    ]
}}
"""


# ============================================================
# RETRY ERROR DETECTION
# ============================================================

def is_retryable_error(
    error: Exception
) -> bool:

    message = str(
        error
    ).lower()

    retryable_patterns = [

        # HTTP
        "400",
        "408",
        "429",
        "500",
        "502",
        "503",
        "504",

        # Google API
        "unavailable",
        "service unavailable",
        "resource exhausted",
        "rate limit",
        "internal server error",

        # Network
        "timeout",
        "timed out",
        "deadline exceeded",
        "connection reset",
        "connection aborted",
        "connection error",
        "connection forcibly closed",
        "winerror 10054",
        "remote host",
        "broken pipe",
        "network error",

    ]

    return any(
        pattern in message
        for pattern in retryable_patterns
    )


# ============================================================
# GEMINI GENERATION WITH RETRIES
# ============================================================

def generate_with_retry(
    video_bytes: bytes,
    prompt: str,
    model: str
) -> str:

    size_mb = (
        len(video_bytes)
        / (1024 * 1024)
    )

    print(
        f"[Gemini] Sending "
        f"{size_mb:.2f} MB to {model}..."
    )

    last_error = None

    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        print(
            f"[Gemini] Attempt "
            f"{attempt}/{MAX_RETRIES} "
            f"using {model}"
        )

        try:

            response = client.models.generate_content(

                model=model,

                contents=[

                    types.Part.from_bytes(
                        data=video_bytes,
                        mime_type="video/mp4"
                    ),

                    prompt

                ],

                config=types.GenerateContentConfig(

                    temperature=0.7,

                    response_mime_type=(
                        "application/json"
                    )

                )
            )

            if not response:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            text = response.text

            if not text:

                raise RuntimeError(
                    "Gemini returned no text."
                )

            print(
                f"[Gemini] SUCCESS "
                f"on attempt {attempt}"
            )

            return text

        except Exception as exc:

            last_error = exc

            print(
                f"[Gemini] Attempt "
                f"{attempt} failed"
            )

            print(
                f"[Gemini] "
                f"{type(exc).__name__}: {exc}"
            )

            # Non-transient errors
            if not is_retryable_error(
                exc
            ):

                print(
                    "[Gemini] "
                    "Non-retryable error."
                )

                raise

            if attempt >= MAX_RETRIES:

                break

            # Exponential backoff
            base_delay = min(
                5 * (2 ** (attempt - 1)),
                60
            )

            # Random jitter
            jitter = random.uniform(
                0,
                3
            )

            delay = (
                base_delay
                + jitter
            )

            print(
                f"[Gemini] Temporary failure."
            )

            print(
                f"[Gemini] Retrying in "
                f"{delay:.1f} seconds..."
            )

            time.sleep(
                delay
            )

    raise RuntimeError(
        f"Gemini generation failed after "
        f"{MAX_RETRIES} retries using "
        f"{model}. "
        f"Last error: {last_error}"
    )


# ============================================================
# NORMALIZE ANALYSIS
# ============================================================

def normalize_analysis(
    analysis: Dict[str, Any],
    variation_count: int
) -> Dict[str, Any]:

    if not isinstance(
        analysis,
        dict
    ):
        raise ValueError(
            "Gemini analysis is not a JSON object."
        )

    hook = analysis.get(
        "hook",
        {}
    )

    if not isinstance(
        hook,
        dict
    ):
        hook = {}

    analysis_section = analysis.get(
        "analysis",
        {}
    )

    if not isinstance(
        analysis_section,
        dict
    ):
        analysis_section = {}

    variations = analysis.get(
        "variations",
        []
    )

    if not isinstance(
        variations,
        list
    ):
        variations = []

    cleaned = []

    for index, variation in enumerate(
        variations,
        start=1
    ):

        if not isinstance(
            variation,
            dict
        ):
            continue

        cleaned.append({

            "id": index,

            "hook_line":
                str(
                    variation.get(
                        "hook_line",
                        ""
                    )
                ),

            "on_screen_text":
                str(
                    variation.get(
                        "on_screen_text",
                        ""
                    )
                ),

            "visual_direction":
                str(
                    variation.get(
                        "visual_direction",
                        ""
                    )
                ),

            "emotion":
                str(
                    variation.get(
                        "emotion",
                        ""
                    )
                ),

            "rationale":
                str(
                    variation.get(
                        "rationale",
                        ""
                    )
                )

        })

    cleaned = cleaned[
        :variation_count
    ]

    if len(cleaned) < variation_count:

        raise ValueError(
            f"Gemini generated only "
            f"{len(cleaned)} variations. "
            f"Expected {variation_count}."
        )

    return {

        "hook": {

            "start":
                hook.get(
                    "start",
                    0
                ),

            "end":
                hook.get(
                    "end",
                    HOOK_SECONDS
                ),

            "spoken_line":
                hook.get(
                    "spoken_line",
                    ""
                ),

            "on_screen_text":
                hook.get(
                    "on_screen_text",
                    ""
                ),

            "visual_action":
                hook.get(
                    "visual_action",
                    ""
                ),

            "emotion":
                hook.get(
                    "emotion",
                    ""
                ),

            "product_appearance":
                hook.get(
                    "product_appearance",
                    ""
                )

        },

        "analysis": {

            "why_it_works":
                analysis_section.get(
                    "why_it_works",
                    ""
                ),

            "target_audience":
                analysis_section.get(
                    "target_audience",
                    ""
                ),

            "structure":
                analysis_section.get(
                    "structure",
                    ""
                )

        },

        "variations":
            cleaned
    }


# ============================================================
# MAIN GEMINI ANALYSIS
# ============================================================

def analyze_with_gemini(
    video_path: Path,
    hook_seconds: float = 3.0,
    strength: str = "balanced",
    variation_count: int = 5
) -> Dict[str, Any]:

    video_path = Path(
        video_path
    )

    if not video_path.exists():

        raise FileNotFoundError(
            f"Video not found: "
            f"{video_path}"
        )

    if variation_count < 5:
        variation_count = 5

    if variation_count > 10:
        variation_count = 10

    preview_path = (
        video_path.parent
        / "gemini_hook_preview.mp4"
    )

    print("=" * 70)
    print("[Gemini] STARTING ANALYSIS")
    print(f"[Gemini] Video: {video_path}")
    print(f"[Gemini] Hook: {hook_seconds}s")
    print(f"[Gemini] Strength: {strength}")
    print(
        f"[Gemini] Variations: "
        f"{variation_count}"
    )
    print("=" * 70)

    try:

        # ----------------------------------------------------
        # STEP 1
        # Create tiny preview
        # ----------------------------------------------------

        create_hook_preview(
            video_path=video_path,
            output_path=preview_path,
            hook_seconds=hook_seconds
        )

        # ----------------------------------------------------
        # STEP 2
        # Read bytes
        # ----------------------------------------------------

        video_bytes = (
            preview_path.read_bytes()
        )

        if not video_bytes:

            raise RuntimeError(
                "Gemini preview is empty."
            )

        print(
            f"[Gemini] Preview size: "
            f"{len(video_bytes) / (1024 * 1024):.2f} MB"
        )

        # ----------------------------------------------------
        # STEP 3
        # Build prompt
        # ----------------------------------------------------

        prompt = build_analysis_prompt(
            hook_seconds=hook_seconds,
            strength=strength,
            variation_count=variation_count
        )

        # ----------------------------------------------------
        # STEP 4
        # Models
        # ----------------------------------------------------

        models = []

        if PRIMARY_MODEL:
            models.append(
                PRIMARY_MODEL
            )

        if (
            FALLBACK_MODEL
            and FALLBACK_MODEL
            != PRIMARY_MODEL
        ):
            models.append(
                FALLBACK_MODEL
            )

        if not models:

            raise RuntimeError(
                "No Gemini models configured."
            )

        last_error = None

        # ----------------------------------------------------
        # STEP 5
        # Try models
        # ----------------------------------------------------

        for model_index, model in enumerate(
            models
        ):

            print(
                f"[Gemini] "
                f"Model {model_index + 1}/"
                f"{len(models)}: {model}"
            )

            try:

                raw_response = (
                    generate_with_retry(
                        video_bytes=video_bytes,
                        prompt=prompt,
                        model=model
                    )
                )

                print(
                    "[Gemini] Parsing JSON..."
                )

                raw_analysis = extract_json(
                    raw_response
                )

                analysis = normalize_analysis(
                    raw_analysis,
                    variation_count
                )

                print(
                    "[Gemini] Analysis completed."
                )

                print(
                    f"[Gemini] "
                    f"{len(analysis['variations'])} "
                    f"variations generated."
                )

                return analysis

            except Exception as exc:

                last_error = exc

                print(
                    f"[Gemini] Model "
                    f"{model} failed:"
                )

                print(
                    f"[Gemini] "
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                if (
                    model_index
                    < len(models) - 1
                ):

                    print(
                        "[Gemini] Switching "
                        f"to fallback model "
                        f"{models[model_index + 1]}"
                    )

                    continue

                raise RuntimeError(
                    "Gemini analysis failed.\n"
                    f"Primary model: "
                    f"{PRIMARY_MODEL}\n"
                    f"Fallback model: "
                    f"{FALLBACK_MODEL}\n"
                    f"Last error: "
                    f"{last_error}"
                )

    finally:

        # ----------------------------------------------------
        # Cleanup preview
        # ----------------------------------------------------

        try:

            if preview_path.exists():
                preview_path.unlink()

        except Exception:
            pass


# ============================================================
# CREATE OUTPUT HOOK CLIPS
# ============================================================

def create_hook_variation_clips(
    video_path: Path,
    output_dir: Path,
    variations: List[Dict[str, Any]],
    hook_seconds: float = 3.0,
    strength: str = "balanced"
) -> List[Path]:

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    duration = get_video_duration(
        video_path
    )

    actual_duration = min(
        hook_seconds,
        duration
    )

    clips = []

    print("=" * 70)
    print(
        f"[FFmpeg] Creating "
        f"{len(variations)} hook clips"
    )
    print("=" * 70)

    # Slight visual treatments
    # for comparison/demo purposes.
    treatments = [

        "scale=iw*1.02:ih*1.02,"
        "crop=iw/1.02:ih/1.02",

        "scale=iw*1.03:ih*1.03,"
        "crop=iw/1.03:ih/1.03",

        "scale=iw*1.04:ih*1.04,"
        "crop=iw/1.04:ih/1.04",

        "eq=contrast=1.05:saturation=1.05",

        "eq=contrast=1.08:brightness=0.02",

        "scale=iw*1.025:ih*1.025,"
        "crop=iw/1.025:ih/1.025",

        "eq=contrast=1.03:saturation=1.10",

        "scale=iw*1.05:ih*1.05,"
        "crop=iw/1.05:ih/1.05",

        "eq=contrast=1.06:brightness=0.01",

        "scale=iw*1.02:ih*1.02,"
        "crop=iw/1.02:ih/1.02"

    ]

    for index, variation in enumerate(
        variations,
        start=1
    ):

        output_path = (
            output_dir
            / f"variation_{index}.mp4"
        )

        print(
            f"[FFmpeg] Creating "
            f"variation {index}/"
            f"{len(variations)}..."
        )

        filter_expression = (
            treatments[
                (index - 1)
                % len(treatments)
            ]
        )

        command = [

            ffmpeg_path(),

            "-y",

            "-ss",
            "0",

            "-i",
            str(video_path),

            "-t",
            str(actual_duration),

            "-vf",
            filter_expression,

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "27",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            str(output_path)

        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:

            print(
                f"[FFmpeg] "
                f"Variation {index} failed"
            )

            print(
                result.stderr
            )

            raise RuntimeError(
                f"FFmpeg failed for "
                f"variation {index}."
            )

        if not output_path.exists():

            raise RuntimeError(
                f"Variation {index} "
                f"was not created."
            )

        clips.append(
            output_path
        )

        print(
            f"[FFmpeg] Variation "
            f"{index} created successfully."
        )

    print("=" * 70)
    print(
        f"[FFmpeg] Created "
        f"{len(clips)} clips successfully."
    )
    print("=" * 70)

    return clips