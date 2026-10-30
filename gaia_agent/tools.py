"""Task-scoped web, file, transcript, and guarded Python tools."""

from __future__ import annotations

import ast
import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from .attachments import list_task_files, read_attachment, resolve_task_file
from .registry import ToolRegistry

ALLOWED_IMPORTS = {
    "collections", "datetime", "decimal", "fractions", "functools", "itertools",
    "json", "math", "re", "statistics",
}
BANNED_NAMES = {
    "__import__", "breakpoint", "compile", "eval", "exec", "globals", "input",
    "locals", "open", "vars",
}


class _ExternalToolCache:
    """Persist identical read-only tool observations across experiment runs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def call(self, name: str, function: Callable[..., str], **arguments: Any) -> str:
        key = json.dumps([name, arguments], sort_keys=True, ensure_ascii=False)
        with self._lock:
            try:
                cache = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                cache = {}
            if key in cache:
                return str(cache[key])

        result = function(**arguments)
        with self._lock:
            try:
                cache = json.loads(self.path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                cache = {}
            cache[key] = result
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        return result


def _validate_python(code: str) -> None:
    if len(code) > 8_000:
        raise ValueError("code exceeds the 8,000 character limit")
    tree = ast.parse(code, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name.split(".")[0] for alias in node.names]
            if any(module not in ALLOWED_IMPORTS for module in modules):
                raise ValueError(f"allowed imports: {sorted(ALLOWED_IMPORTS)}")
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if module not in ALLOWED_IMPORTS:
                raise ValueError(f"allowed imports: {sorted(ALLOWED_IMPORTS)}")
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise ValueError(f"use of {node.id!r} is blocked")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError("dunder attribute access is blocked")


def run_python(code: str) -> str:
    """Run calculation-oriented Python in an isolated child process."""
    _validate_python(code)
    environment = {"PYTHONIOENCODING": "utf-8", "PATH": os.getenv("PATH", "")}
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        timeout=8,
        env=environment,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    if completed.returncode:
        raise RuntimeError(output[:4_000] or f"process exited {completed.returncode}")
    return output[:8_000] or "(completed with no output; use print() to return a result)"


def _validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("only public http(s) URLs are allowed")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("private, loopback, and link-local addresses are blocked")
    return url


def search_web(query: str, max_results: int) -> str:
    from ddgs import DDGS

    results = []
    errors = []
    for backend in ("auto", "bing", "duckduckgo"):
        try:
            results = DDGS(timeout=12).text(query, max_results=max_results, backend=backend)
            if results:
                break
        except Exception as exc:
            errors.append(type(exc).__name__)
    if not results:
        raise RuntimeError(f"No search results after bounded backend fallback: {errors}")
    compact = [
        {"title": item.get("title"), "url": item.get("href"), "snippet": item.get("body")}
        for item in results
    ]
    return json.dumps(compact, ensure_ascii=False)


HTML_DOWNLOAD_LIMIT = 3_000_000
PDF_DOWNLOAD_LIMIT = 50_000_000


def bounded_response_body(response) -> bytes:
    """Choose the byte budget from actual magic bytes, never a claimed MIME type."""
    body = bytearray()
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        body.extend(chunk)
        # Wait for the five-byte PDF signature even if the stream splits it.
        if len(body) < 5:
            continue
        limit = PDF_DOWNLOAD_LIMIT if body.startswith(b'%PDF-') else HTML_DOWNLOAD_LIMIT
        if len(body) > limit:
            raise ValueError(f'document exceeds the {limit // 1_000_000} MB download limit')
    return bytes(body)


def fetch_url(url: str, link_query: str | None = None) -> str:
    for _ in range(5):
        response = requests.get(
            _validate_public_url(url), timeout=20, allow_redirects=False, stream=True,
            headers={"User-Agent": "Mozilla/5.0 GAIA educational agent"})
        if response.is_redirect:
            from urllib.parse import urljoin
            url = urljoin(url, response.headers['Location'])
            response.close()
            continue
        break
    else:
        raise ValueError("too many redirects")
    try:
        response.raise_for_status()
        body = bounded_response_body(response)
    finally:
        response.close()
    if body.startswith(b'%PDF-'):
        from io import BytesIO
        from pypdf import PdfReader
        text = '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(body)).pages)
        if not text.strip():
            raise ValueError('PDF has no extractable text; use OCR or another accessible source')
        # Preserve both introduction and acknowledgements for long papers.
        excerpt = text if len(text) <= 30000 else text[:20000] + '\n[Middle text omitted]\n' + text[-10000:]
        return f"SOURCE: {url}\n{excerpt}"
    soup = BeautifulSoup(body, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    if any(marker in text.lower()[:1500] for marker in (
        'verify you are human', 'checking your browser', 'enable javascript and cookies',
        'performing security verification')):
        raise ValueError("Blocked by website challenge; no factual page evidence retrieved")
    links=''
    if link_query:
        from urllib.parse import urljoin
        candidates=[]
        for a in soup.find_all('a',href=True):
            href=urljoin(url,a['href']); label=a.get_text(' ',strip=True)
            if href.startswith(('http://','https://')):
                candidates.append((label,href))
        candidates=list(dict.fromkeys(candidates))
        candidates.sort(key=lambda pair:link_query.casefold() not in (' '.join(pair)).casefold())
        links='\nNAVIGATION LINKS (discovery only, not factual evidence):\n'+json.dumps(candidates[:60],ensure_ascii=False)
    return f"SOURCE: {url}\n{text[:30_000]}{links}"


def _youtube_video_id(url_or_id: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    parsed = urlparse(url_or_id)
    if parsed.hostname in {"youtu.be", "www.youtu.be"}:
        return parsed.path.strip("/")
    if parsed.hostname and "youtube.com" in parsed.hostname:
        return parse_qs(parsed.query).get("v", [""])[0]
    raise ValueError("provide a YouTube URL or 11-character video ID")


def youtube_transcript(url_or_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi

    video_id = _youtube_video_id(url_or_id)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    return "\n".join(
        f"[{snippet.start:.1f}s] {snippet.text}" for snippet in transcript
    )[:30_000]


def build_tool_registry(
    task_dir: Path,
    search_results: int,
    video_inspector: Callable[..., str] | None = None,
    chess_analyzer: Callable[..., str] | None = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    external_cache = _ExternalToolCache(task_dir.parent / "tool_cache.json")
    registry.register(
        "search_web",
        "Search the public web. Use several focused queries and inspect promising pages.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        lambda query: external_cache.call(
            "search_web",
            search_web,
            query=query,
            max_results=search_results,
        ),
    )
    registry.register(
        "fetch_url",
        "Read the visible text of a public web page returned by search_web.",
        {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
            "additionalProperties": False,
        },
        lambda url: external_cache.call("fetch_url", fetch_url, url=url),
    )
    registry.register(
        "youtube_transcript",
        "Retrieve timestamped captions for a YouTube video when captions are available.",
        {
            "type": "object",
            "properties": {"url_or_id": {"type": "string"}},
            "required": ["url_or_id"],
            "additionalProperties": False,
        },
        lambda url_or_id: external_cache.call(
            "youtube_transcript", youtube_transcript, url_or_id=url_or_id
        ),
    )
    if video_inspector is not None:
        registry.register(
            "inspect_youtube_video",
            "Inspect YouTube video frames when the answer depends on visible actions, objects, text, or other non-caption evidence. Optionally provide transcript timestamps to inspect.",
            {
                "type": "object",
                "properties": {
                    "url_or_id": {"type": "string"},
                    "timestamps_seconds": {
                        "type": "array",
                        "items": {"type": "number", "minimum": 0},
                        "maxItems": 24,
                    },
                },
                "required": ["url_or_id"],
                "additionalProperties": False,
            },
            lambda url_or_id, timestamps_seconds=None: external_cache.call(
                "inspect_youtube_video",
                video_inspector,
                url_or_id=url_or_id,
                timestamps_seconds=timestamps_seconds,
            ),
        )
    registry.register(
        "list_files",
        "List attachment file names available for the current task.",
        {"type": "object", "properties": {}, "additionalProperties": False},
        lambda: json.dumps(list_task_files(task_dir)),
    )
    registry.register(
        "read_file",
        "Read a task attachment. Supports text, Python, CSV, PDF, DOCX, and XLSX.",
        {
            "type": "object",
            "properties": {"file_name": {"type": "string"}},
            "required": ["file_name"],
            "additionalProperties": False,
        },
        lambda file_name: read_attachment(resolve_task_file(task_dir, file_name)),
    )
    if chess_analyzer is not None:
        registry.register(
            "analyze_chess_position",
            "Convert an attached chessboard image to a validated FEN position and obtain a chess-engine line. Use for chess questions instead of relying only on visual intuition.",
            {
                "type": "object",
                "properties": {"file_name": {"type": "string"}},
                "required": ["file_name"],
                "additionalProperties": False,
            },
            lambda file_name: external_cache.call(
                "analyze_chess_position", chess_analyzer, file_name=file_name
            ),
        )
    registry.register(
        "run_python",
        "Run calculation-only Python. Print the result. No file/network/process access; only safe standard-library imports are allowed.",
        {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        },
        run_python,
    )
    # Only reviewed read-only tools may overlap. Media writes shared frame files;
    # Python and future mutation tools conservatively remain serial.
    from dataclasses import replace
    for name in ('search_web', 'fetch_url', 'youtube_transcript', 'list_files', 'read_file'):
        registry._tools[name] = replace(registry._tools[name], parallel_safe=True)
    return registry
