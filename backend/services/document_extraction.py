"""Private scanner/parser transports; never construct an embedding or LLM provider."""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import struct

import httpx

from core.config.settings import settings

from document_processing.contracts import (
    MAX_OUTPUT_BYTES,
    ParserResult,
    ProcessingError,
)


async def _clam_command(socket, command):
    reader, writer = await asyncio.open_unix_connection(socket, limit=2048)
    try:
        writer.write(command)
        await writer.drain()
        return (await reader.readuntil(b"\0")).decode("ascii").rstrip("\0")
    finally:
        writer.close()
        await writer.wait_closed()


async def scan_original(path: Path) -> str:
    socket = os.environ.get(
        "ASILA_SCANNER_SOCKET", settings.ASILA_SCANNER_SOCKET
    )
    if not socket:
        raise ProcessingError("SCANNER_UNAVAILABLE")
    try:
        async with asyncio.timeout(45):
            version = await _clam_command(socket, b"zVERSION\0")
            try:
                built = datetime.strptime(
                    version.rsplit("/", 1)[1], "%a %b %d %H:%M:%S %Y"
                ).replace(tzinfo=timezone.utc)
                maximum_age = int(
                    os.environ.get(
                        "ASILA_SCANNER_MAX_AGE_DAYS",
                        str(settings.ASILA_SCANNER_MAX_AGE_DAYS),
                    )
                )
                if not 1 <= maximum_age <= 30:
                    raise ValueError()
                if (
                    datetime.now(timezone.utc) - built
                ).total_seconds() > maximum_age * 86400:
                    raise ProcessingError("SCANNER_DATABASE_STALE")
            except (ValueError, IndexError):
                raise ProcessingError("SCANNER_UNAVAILABLE") from None
            reader, writer = await asyncio.open_unix_connection(
                socket, limit=2048
            )
            try:
                writer.write(b"zINSTREAM\0")
                with path.open("rb") as original:
                    while chunk := await asyncio.to_thread(
                        original.read, 64 * 1024
                    ):
                        writer.write(struct.pack("!I", len(chunk)) + chunk)
                        await writer.drain()
                writer.write(struct.pack("!I", 0))
                await writer.drain()
                response = (
                    (await reader.readuntil(b"\0")).decode("ascii").rstrip("\0")
                )
            finally:
                writer.close()
                await writer.wait_closed()
            if response == "stream: OK":
                return version
            if (
                "Heuristics.Limits.Exceeded" in response
                or "size limit exceeded" in response
            ):
                raise ProcessingError("SCAN_LIMIT_EXCEEDED")
            if "Heuristics.Encrypted" in response:
                raise ProcessingError("ENCRYPTED_DOCUMENT_UNSUPPORTED")
            if response.endswith(" FOUND"):
                raise ProcessingError("MALWARE_DETECTED")
            raise ProcessingError("SCANNER_UNAVAILABLE")
    except ProcessingError:
        raise
    except (
        OSError,
        TimeoutError,
        asyncio.IncompleteReadError,
        asyncio.LimitOverrunError,
        UnicodeError,
    ):
        raise ProcessingError("SCANNER_UNAVAILABLE") from None


async def parse_original(
    path: Path, mime_type: str, checksum: str
) -> ParserResult:
    socket = os.environ.get("ASILA_PARSER_SOCKET", settings.ASILA_PARSER_SOCKET)
    if not socket:
        raise ProcessingError("PARSER_UNAVAILABLE")

    async def content():
        with path.open("rb") as original:
            while chunk := await asyncio.to_thread(original.read, 64 * 1024):
                yield chunk

    try:
        transport = httpx.AsyncHTTPTransport(uds=socket, retries=0)
        async with (
            asyncio.timeout(140),
            httpx.AsyncClient(
                transport=transport,
                timeout=httpx.Timeout(135, connect=3),
                trust_env=False,
            ) as client,
        ):
            async with client.stream(
                "POST",
                "http://parser/extract",
                content=content(),
                headers={"X-Asila-Mime": mime_type, "X-Asila-Sha256": checksum},
            ) as response:
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_OUTPUT_BYTES:
                        raise ProcessingError("EXTRACTION_LIMIT_EXCEEDED")
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ProcessingError("PARSER_FAILED")
                if response.status_code != 200:
                    from pydantic import TypeAdapter, ValidationError
                    from document_processing.contracts import FailureReason

                    try:
                        reason = TypeAdapter(FailureReason).validate_python(
                            payload.get("detail")
                        )
                    except ValidationError:
                        reason = "PARSER_FAILED"
                    raise ProcessingError(reason)
                parsed = ParserResult.model_validate(payload)
                if parsed.sha256 != checksum:
                    raise ProcessingError("ORIGINAL_INTEGRITY_FAILED")
                return parsed
    except ProcessingError:
        raise
    except (httpx.TimeoutException, TimeoutError):
        raise ProcessingError("PARSER_TIMEOUT") from None
    except httpx.TransportError:
        raise ProcessingError("PARSER_UNAVAILABLE") from None
    except (ValueError, TypeError):
        raise ProcessingError("PARSER_FAILED") from None
