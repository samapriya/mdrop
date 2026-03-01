import uuid
import asyncio
import re
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from markitdown import MarkItDown
import aiofiles
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MDrop API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("/tmp/mdrop/uploads")
OUTPUT_DIR = Path("/tmp/mdrop/outputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE    = 256 * 1024         # 256KB read chunks

ALLOWED_EXTENSIONS = {
    ".pdf", ".pptx", ".ppt", ".docx", ".doc",
    ".xlsx", ".xls", ".jpg", ".jpeg", ".png",
    ".gif", ".webp", ".bmp", ".html", ".htm",
    ".csv", ".json", ".xml", ".zip", ".epub",
    ".wav", ".mp3", ".txt", ".md"
}

md_converter = MarkItDown(enable_plugins=False)

# --- Serve frontend ---
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend not found in /app/static/")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))

app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

# --- Helpers ---
def cleanup_file(path: Path):
    """
    Called as a FastAPI BackgroundTask — runs AFTER the response has been fully
    sent to the client. Waits 60 seconds before deleting so the file is never
    removed mid-transfer even on very slow connections.
    """
    import time
    time.sleep(60)
    try:
        if path.exists():
            path.unlink()
            logger.info(f"Deleted (post-download): {path}")
    except Exception as e:
        logger.error(f"Failed to delete {path}: {e}")

async def cleanup_files(*paths: Path):
    """Async cleanup for use during request handling (errors, input files)."""
    for path in paths:
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Deleted: {path}")
        except Exception as e:
            logger.error(f"Failed to delete {path}: {e}")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MDrop"}


@app.post("/convert")
async def convert_file(request: Request, file: UploadFile = File(...)):
    """
    Stream the upload in chunks and abort early if the file exceeds MAX_FILE_SIZE.
    The input file is deleted immediately after conversion completes.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    job_id = uuid.uuid4().hex
    raw_stem = Path(file.filename).stem
    # Sanitize stem — replace anything not alphanumeric/hyphen with underscore
    # so the token is always URL-safe and passes validation
    stem = re.sub(r'[^a-zA-Z0-9\-]', '_', raw_stem).strip('_') or "file"
    input_path  = UPLOAD_DIR / f"{job_id}{suffix}"
    output_path = OUTPUT_DIR / f"{job_id}_{stem}.md"

    bytes_written = 0
    try:
        # Stream to disk in chunks — abort early if size limit exceeded
        async with aiofiles.open(input_path, "wb") as f:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_FILE_SIZE:
                    await f.flush()
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum allowed size is {MAX_FILE_SIZE // (1024*1024)}MB."
                    )
                await f.write(chunk)

        logger.info(f"Saved upload: {input_path} ({bytes_written / 1024:.1f} KB)")

        # Convert
        result = md_converter.convert(str(input_path))

        # Write output
        async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
            await f.write(result.text_content)
        logger.info(f"Converted to: {output_path}")

        # Delete input immediately — conversion is done, we no longer need it
        await cleanup_files(input_path)

        return JSONResponse({
            "job_id": job_id,
            "original_filename": file.filename,
            "output_filename": f"{stem}.md",
            "download_token": f"{job_id}_{stem}"
        })

    except HTTPException:
        await cleanup_files(input_path)
        raise
    except Exception as e:
        await cleanup_files(input_path, output_path)
        logger.error(f"Conversion error: {e}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


@app.get("/download/{token}")
async def download_file(token: str, background_tasks: BackgroundTasks):
    """
    Serves the converted markdown file and schedules deletion as a BackgroundTask.
    BackgroundTasks run AFTER the full response has been sent — the file is guaranteed
    to exist for the entire transfer, unlike asyncio.sleep(2) which races the download.
    """
    # Strict token validation — alphanumeric + underscore/hyphen only
    if not all(c.isalnum() or c in ("_", "-") for c in token):
        raise HTTPException(status_code=400, detail="Invalid token")

    matches = list(OUTPUT_DIR.glob(f"{token}.md"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found or already downloaded")

    output_path = matches[0]
    stem = token.split("_", 1)[1] if "_" in token else token

    # Schedule deletion AFTER response is fully sent — no race condition
    background_tasks.add_task(cleanup_file, output_path)

    return FileResponse(
        path=str(output_path),
        media_type="text/markdown",
        filename=f"{stem}.md",
        headers={"Content-Disposition": f'attachment; filename="{stem}.md"'}
    )
