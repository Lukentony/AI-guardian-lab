"""Bounded local Kev adapter. No tools, workspace access or execution authority."""

import argparse
import hmac
import os
import threading

MODEL_RUN = "jaredpalmer/kev-0.8b@v1.0"
SOURCE_REVISION = "1f04cfa28e6a708485b28a9585010b9e436b776e"


def build_app(backend, key, request_factory):
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Guardian System One observer")
    admission = threading.BoundedSemaphore(1)

    @app.middleware("http")
    async def authenticate_and_limit(request, call_next):
        if request.url.path != "/health":
            if not key or not hmac.compare_digest(
                request.headers.get("authorization", "").encode(), f"Bearer {key}".encode()
            ):
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
        if request.method == "POST":
            try:
                length = int(request.headers.get("content-length", "-1"))
            except ValueError:
                length = -1
            if not 0 <= length <= 24000 or request.headers.get("transfer-encoding"):
                return JSONResponse({"error": "Bounded Content-Length required"}, status_code=413)
        return await call_next(request)

    @app.get("/health")
    def health():
        return {"status": "ready", "run": MODEL_RUN, "source_revision": SOURCE_REVISION}

    @app.post("/v1/systemone")
    def evaluate(payload: dict):
        # Sync worker retains admission until inference really finishes, even if
        # the caller times out/disconnects. No unbounded model work queues.
        if not admission.acquire(blocking=False):
            return JSONResponse({"error": "Inference busy"}, status_code=503)
        try:
            request = request_factory(payload)
            result = backend.answer(request)
            result["model"] = MODEL_RUN
            result["source_revision"] = SOURCE_REVISION
            return result
        except (ValueError, TypeError):
            return JSONResponse({"error": "Invalid inference request"}, status_code=422)
        except Exception:
            return JSONResponse({"error": "Inference unavailable"}, status_code=503)
        finally:
            admission.release()

    return app


def main():
    from qualification import require_qualified_runtime

    # Check before credentials, model imports, downloads or opening a socket.
    require_qualified_runtime()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8009)
    args = parser.parse_args()
    key = os.getenv("SYSTEM_ONE_API_KEY", "")
    if not key or key == "CHANGE_ME":
        raise SystemExit("Set a dedicated SYSTEM_ONE_API_KEY (never printed)")
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["KEV_TRUNCATE_STATES"] = "0"
    # The authorization context is stable across requests. A small prefix cache
    # keeps repeated observations warm without unbounded state growth.
    os.environ.setdefault("KEV_PREFIX_CACHE", "4")
    try:
        threads = int(os.environ.get("SYSTEM_ONE_THREADS", "8"))
    except ValueError:
        threads = 8
    threads = min(16, max(1, threads))
    import torch
    import uvicorn
    from kev.api import SystemOneRequest
    from kev.checkpoint import Checkpoint, LoadOptions
    from kev.serve import Server

    # CPU is intentional: do not silently consume another session's GPU or
    # guess ROCm support. GPU rollout needs separate hardware/latency validation.
    torch.set_num_threads(threads)
    checkpoint = Checkpoint(MODEL_RUN)
    tokenizer, model = checkpoint.load("cpu", LoadOptions.from_env())
    backend = Server(checkpoint, tokenizer, model, "cpu", truncate_states=False)
    # Load kernels and the prefix path before advertising readiness. The first
    # request after a cold start can otherwise exceed the observer budget even
    # though /health is already answerable.
    warmup = SystemOneRequest.model_validate(
        {
            "model": MODEL_RUN,
            "state": {
                "authorization_context": {"task": "warmup", "trust": "registered"},
                "proposed_command": "true",
                "parsed_commands": [],
                "recent_actions": [],
                "untrusted_observation": {"trust": "untrusted", "content": ""},
            },
            "questions": {"coherence": {"type": "noul", "instructions": "Warm up."}},
        }
    )
    backend.answer(warmup)
    app = build_app(backend, key, SystemOneRequest.model_validate)
    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            limit_concurrency=4,
            backlog=4,
            timeout_keep_alive=1,
            access_log=False,
        )
    finally:
        backend.close()


if __name__ == "__main__":
    main()
