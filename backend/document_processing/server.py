"""Credential-free Unix-socket parser broker; each input gets a fresh process."""

import asyncio
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import tempfile

from fastapi import FastAPI, HTTPException, Request

from document_processing.contracts import (
    MAX_BYTES,
    MAX_OUTPUT_BYTES,
    MIME_SUFFIXES,
)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
slot = asyncio.Semaphore(1)
parse_timeout = int(os.environ.get("ASILA_PARSER_TIMEOUT_SECONDS", "120"))
if not 1 <= parse_timeout <= 120:
    raise ValueError("Parser timeout must be between 1 and 120 seconds")


@app.post("/extract")
async def extract(request: Request):
    mime = request.headers.get("x-asila-mime")
    if mime not in MIME_SUFFIXES:
        raise HTTPException(422, "FORMAT_MISMATCH")
    if slot.locked():
        raise HTTPException(429, "PARSER_UNAVAILABLE")
    async with slot:
        with tempfile.TemporaryDirectory(dir="/tmp") as directory:
            path = Path(directory) / ("original" + MIME_SUFFIXES[mime])
            output = Path(directory) / "extraction.json"
            count, digest = 0, hashlib.sha256()
            with path.open("wb") as target:
                async with asyncio.timeout(30):
                    async for chunk in request.stream():
                        count += len(chunk)
                        if count > MAX_BYTES:
                            raise HTTPException(
                                413, "EXTRACTION_LIMIT_EXCEEDED"
                            )
                        digest.update(chunk)
                        target.write(chunk)
            if not count or digest.hexdigest() != request.headers.get(
                "x-asila-sha256"
            ):
                raise HTTPException(422, "ORIGINAL_INTEGRITY_FAILED")
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "document_processing.parser",
                str(path),
                mime,
                str(output),
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
            try:
                async with asyncio.timeout(parse_timeout):
                    await process.wait()
            except (TimeoutError, asyncio.CancelledError) as error:
                if process.returncode is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                await process.wait()
                if isinstance(error, asyncio.CancelledError):
                    raise
                raise HTTPException(504, "PARSER_TIMEOUT") from None
            finally:
                if process.returncode is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await process.wait()
            if process.returncode == -signal.SIGXCPU:
                raise HTTPException(504, "PARSER_TIMEOUT")
            if process.returncode in (-signal.SIGKILL, -signal.SIGXFSZ):
                raise HTTPException(422, "EXTRACTION_LIMIT_EXCEEDED")
            if process.returncode or not output.is_file():
                raise HTTPException(422, "PARSER_FAILED")
            if output.stat().st_size > MAX_OUTPUT_BYTES:
                raise HTTPException(422, "EXTRACTION_LIMIT_EXCEEDED")
            payload = json.loads(output.read_text(encoding="utf-8"))
            if "failure_reason" in payload:
                raise HTTPException(422, payload["failure_reason"])
            return payload
