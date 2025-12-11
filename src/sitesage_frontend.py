# sitesage_frontend.py
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import your backend (must expose run_sitesage_session_async)
import sitesage_backend as backend


def _configure_console_logging() -> None:
    """
    Console logging with clear INFO-level events:
    - System start, GET /, POST /api/run request in, returned summary.
    """
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s"))
    root.addHandler(ch)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sitesage.frontend").setLevel(logging.INFO)


logger = logging.getLogger("sitesage.frontend")


def create_app() -> FastAPI:
    """
    Create the FastAPI app.

    Endpoints:
    - GET  /               -> serve frontend/index.html
    - POST /api/run        -> run analysis (awaits backend async pipeline)
    - GET  /healthz        -> liveness
    - Static /save         -> serve generated reports/logs
    - Static /frontend     -> serve static frontend assets
    """
    _configure_console_logging()
    base_dir = Path(__file__).resolve().parent
    app = FastAPI(title="SiteSage Frontend", version="0.3.0")

    # Ensure folders exist
    save_dir = base_dir / "save"
    frontend_dir = base_dir / "frontend"
    save_dir.mkdir(exist_ok=True)
    frontend_dir.mkdir(exist_ok=True)

    # Static mounts
    app.mount("/save", StaticFiles(directory=str(save_dir)), name="save")
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")

    @app.on_event("startup")
    async def _on_startup() -> None:
        logger.info("System start: SiteSage frontend server is up.")

    @app.get("/", response_class=FileResponse)
    async def index() -> FileResponse:
        index_path = frontend_dir / "index.html"
        if not index_path.is_file():
            logger.error("frontend/index.html not found.")
            raise HTTPException(status_code=404, detail="frontend/index.html not found")
        logger.info("GET / -> serving index.html")
        return FileResponse(str(index_path))

    @app.post("/api/run", response_class=JSONResponse)
    async def api_run(req: Request) -> JSONResponse:
        """
        Accept JSON: {session_id: str (optional), prompt: str, language: str="en", region: str="north_america"}.
        Uses backend.run_sitesage_session_async to avoid nested event loop issues.
        """
        try:
            body: Dict[str, Any] = await req.json()
        except Exception:
            logger.exception("POST /api/run -> invalid JSON body")
            raise HTTPException(status_code=400, detail="Invalid JSON")

        # If session_id not provided, generate one from timestamp
        session_id = str(body.get("session_id") or "").strip()
        if not session_id:
            now = time.strftime("sess_%Y%m%d_%H%M%S")
            session_id = now

        prompt = str(body.get("prompt") or "").strip()
        language = str(body.get("language") or "en")
        region = str(body.get("region") or "north_america")

        if not prompt:
            raise HTTPException(status_code=400, detail="prompt is required")

        logger.info(
            "POST /api/run -> request in: session_id=%s, language=%s, region=%s, prompt_len=%d",
            session_id, language, region, len(prompt),
        )
        t0 = time.time()
        try:
            if hasattr(backend, "run_sitesage_session_async"):
                result = await backend.run_sitesage_session_async(
                    session_id=session_id,
                    prompt=prompt,
                    language=language,
                    region=region,
                )
            else:
                # Fallback to sync, but not recommended inside async servers
                result = backend.run_sitesage_session(
                    session_id=session_id,
                    prompt=prompt,
                    language=language,
                    region=region,
                )
        except Exception as e:
            logger.exception("POST /api/run -> backend error for session=%s", session_id)
            raise HTTPException(status_code=500, detail=f"Backend failure: {e!r}")

        dt = (time.time() - t0) * 1000.0
        final_score = result.get("final_score")
        logger.info(
            "POST /api/run -> returned: session_id=%s, final_score=%s, elapsed=%.1f ms",
            session_id, f"{final_score:.2f}" if isinstance(final_score, (int, float)) else "n/a", dt
        )
        return JSONResponse(result)

    @app.get("/healthz", response_class=PlainTextResponse)
    async def healthz() -> PlainTextResponse:
        logger.info("GET /healthz")
        return PlainTextResponse("ok")

    return app


def main() -> None:
    """
    Start the frontend server.
    Run: python -c "import sitesage_frontend as f; f.main()"
    Then open http://127.0.0.1:8000
    """
    app = create_app()
    logger.info("Launching Uvicorn...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
