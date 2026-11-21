# -*- coding: utf-8 -*-
"""
Feita.ai film pipeline client.

Flow: create session -> send story brief -> poll until the feita agent finishes
writing -> auto-approve -> poll until shots/clips exist -> POST desk/render ->
poll until exported video URL.

Runs on plain threads + requests so FastAPI handlers stay sync-simple.
"""
import logging
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("uvicorn.error")

FEITA_BASE = "https://api.feita.ai"
POLL_INTERVAL_S = 10
JOB_TIMEOUT_S = 30 * 60
MAX_NUDGES = 3

FILM_BRIEF = """Crie um curta-metragem cinematográfico a partir desta história contada em entrevista de voz.

HISTÓRIA (transcrição da entrevista):
\"\"\"{transcript}\"\"\"


Instruções de produção:
- NÃO faça perguntas e NÃO peça aprovação: escreva o roteiro, gere os materiais,
  produza os shots e renderize o filme final de uma vez.
- Duração alvo: 30-60 segundos, 16:9.
- Narração ou diálogos em português brasileiro quando houver fala.
- Estilo cinematográfico e emocional, fiel aos detalhes da história.
"""

APPROVAL_NUDGE = (
    "Aprovado — siga sem perguntas: produza os shots, monte o filme e renderize "
    "a versão final agora."
)

_JOBS: Dict[str, Dict[str, Any]] = {}
_JOBS_LOCK = threading.Lock()


def _api_key() -> str:
    key = os.getenv("FEITA_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FEITA_API_KEY is not configured")
    return key


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {_api_key()}"}


def _request(method: str, path: str, timeout: int = 30, **kwargs) -> Any:
    resp = requests.request(
        method, f"{FEITA_BASE}{path}", headers=_headers(), timeout=timeout, **kwargs
    )
    if resp.status_code == 404:
        raise FeitaNotFound(path)
    resp.raise_for_status()
    return resp.json()


class FeitaNotFound(RuntimeError):
    pass


def _find_video_url(payload: Any) -> Optional[str]:
    """Depth-first search for the first http(s) url that looks like a video."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            k = str(key).lower()
            if isinstance(value, str) and value.startswith("http"):
                if any(hint in k for hint in ("video", "export", "render", "film", "url")):
                    if any(ext in value for ext in (".mp4", ".webm", ".mov")) or "video" in k:
                        return value
            found = _find_video_url(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_video_url(item)
            if found:
                return found
    return None


def _desk_progress(desk_payload: Dict[str, Any]) -> Dict[str, int]:
    desk = desk_payload.get("desk") or {}
    edit = desk_payload.get("edit") or {}
    clips = edit.get("project", {}).get("tracks", [{}])
    n_clips = 0
    for track in clips if isinstance(clips, list) else []:
        n_clips += len(track.get("clips") or [])
    return {
        "docs": len(desk.get("documents") or []),
        "shots": len(desk.get("shots") or []),
        "clips": max(n_clips, len(desk.get("clips") or [])),
        "jobs": len(desk.get("jobs") or []),
    }


def _set(job_id: str, **fields) -> None:
    with _JOBS_LOCK:
        _JOBS[job_id].update(fields)
        _JOBS[job_id]["updated_at"] = time.time()


def start_film(transcript: str, title: Optional[str] = None) -> str:
    _api_key()  # fail fast if unconfigured
    transcript = (transcript or "").strip()
    if not transcript:
        raise ValueError("transcript is required")
    if len(transcript) > 30000:
        transcript = transcript[-30000:]

    job_id = uuid.uuid4().hex[:12]
    with _JOBS_LOCK:
        _JOBS[job_id] = {
            "id": job_id,
            "status": "queued",
            "title": title or "Meu filme",
            "video_url": None,
            "session_id": None,
            "detail": "na fila",
            "created_at": time.time(),
            "updated_at": time.time(),
        }
    thread = threading.Thread(
        target=_run_film, args=(job_id, transcript, title), daemon=True
    )
    thread.start()
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def _run_film(job_id: str, transcript: str, title: Optional[str]) -> None:
    deadline = time.time() + JOB_TIMEOUT_S
    nudges = 0
    render_requested = False
    try:
        session = _request("POST", "/v1/sessions", json={"name": title or "storyteller"})
        session_id = session["id"]
        _set(job_id, session_id=session_id, status="writing",
             detail="escrevendo o roteiro")

        brief = FILM_BRIEF.format(transcript=transcript)
        _request("POST", f"/v1/sessions/{session_id}/messages",
                 json={"text": brief}, timeout=60)

        while time.time() < deadline:
            time.sleep(POLL_INTERVAL_S)

            session_state = _request("GET", f"/v1/sessions/{session_id}")
            running = bool(session_state.get("running"))

            desk_payload = {}
            try:
                desk_payload = _request("GET", f"/v1/sessions/{session_id}/desk")
            except Exception:
                logger.debug("desk fetch failed, will retry", exc_info=True)

            exported = _find_video_url(
                {"exported": desk_payload.get("exported"),
                 "media": (desk_payload.get("edit") or {}).get("media")}
            )
            if exported:
                _set(job_id, status="ready", video_url=exported,
                     detail="filme pronto")
                return

            progress = _desk_progress(desk_payload)

            if running:
                status = "producing" if (progress["shots"] or progress["clips"] or progress["jobs"]) else "writing"
                _set(job_id, status=status,
                     detail="produzindo shots" if status == "producing" else "escrevendo o roteiro",
                     progress=progress)
                continue

            # agent is idle
            if render_requested:
                # render finished but no export yet — keep polling a few cycles
                _set(job_id, status="rendering", detail="finalizando exportação",
                     progress=progress)
                continue

            if progress["clips"] or progress["shots"]:
                try:
                    _request("POST", f"/v1/sessions/{session_id}/desk/render",
                             json={}, timeout=60)
                    render_requested = True
                    _set(job_id, status="rendering", detail="renderizando o filme",
                         progress=progress)
                except Exception:
                    logger.exception("render request failed")
                    if nudges < MAX_NUDGES:
                        nudges += 1
                        _nudge(session_id)
                continue

            if nudges < MAX_NUDGES:
                nudges += 1
                _set(job_id, detail="aprovando o roteiro")
                _nudge(session_id)
                continue

            _set(job_id, status="error",
                 detail="o estúdio não produziu o filme a tempo")
            return

        _set(job_id, status="error", detail="tempo esgotado na produção")
    except Exception as exc:
        logger.exception("film job %s failed", job_id)
        _set(job_id, status="error", detail=f"falha: {type(exc).__name__}: {exc}")


def _nudge(session_id: str) -> None:
    try:
        _request("POST", f"/v1/sessions/{session_id}/messages",
                 json={"text": APPROVAL_NUDGE}, timeout=60)
    except Exception:
        logger.exception("failed to nudge session %s", session_id)
