"""Media and chess helpers used by task-scoped tools."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw


def download_youtube_video(url_or_id: str, output_dir: Path) -> Path:
    """Download a small progressive YouTube video for visual inspection."""
    from yt_dlp import YoutubeDL

    output_dir.mkdir(parents=True, exist_ok=True)
    template = str(output_dir / "video.%(ext)s")
    options: dict[str, Any] = {
        # Visual inspection does not need an audio stream. Many YouTube videos expose
        # low-resolution video only as a separate stream, so keep video-only fallbacks.
        "format": (
            "worstvideo[ext=mp4][vcodec!=none]/"
            "worstvideo[vcodec!=none]/worst[vcodec!=none]"
        ),
        "outtmpl": template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 80_000_000,
    }
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url_or_id, download=True)
        downloaded = Path(downloader.prepare_filename(info))
    if downloaded.exists():
        return downloaded
    candidates = sorted(output_dir.glob("video.*"))
    if not candidates:
        raise FileNotFoundError("yt-dlp completed but no video file was produced")
    return candidates[0]


def download_youtube_audio(url: str, output_dir: Path) -> Path:
    """Fetch audio separately; no ffmpeg dependency or video-dialogue guessing."""
    from yt_dlp import YoutubeDL
    output_dir.mkdir(parents=True, exist_ok=True)
    with YoutubeDL({'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]',
                    'outtmpl': str(output_dir / 'audio.%(ext)s'), 'quiet': True,
                    'noplaylist': True, 'max_filesize': 24000000,
                    'socket_timeout': 20, 'retries': 2}) as downloader:
        info = downloader.extract_info(url, download=True)
        path = Path(downloader.prepare_filename(info))
    if not path.is_file() or path.stat().st_size > 24000000:
        raise ValueError('audio unavailable or exceeds transcription upload limit')
    return path


def sample_video_contact_sheets(
    video_path: Path,
    output_dir: Path,
    timestamps_seconds: list[float] | None = None,
    frame_count: int = 48,
) -> list[Path]:
    """Sample video frames and combine them into compact, timestamped sheets."""
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError(f"cannot open downloaded video: {video_path.name}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps > 0 and total_frames > 0 else 0
    if duration <= 0:
        raise ValueError("video duration could not be determined")
    # Always retain whole-video coverage. Model-supplied timestamps may be guesses when
    # captions are disabled, so they supplement rather than replace uniform samples.
    uniform = [duration * (index + 0.5) / frame_count for index in range(frame_count)]
    requested = [
        max(0.0, min(duration, float(value))) for value in (timestamps_seconds or [])[:6]
    ]
    timestamps = sorted({*uniform, *requested})

    output_dir.mkdir(parents=True, exist_ok=True)
    frames: list[tuple[float, Image.Image]] = []
    try:
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            image.save(output_dir / f"frame_{timestamp:.1f}.png")
            image.thumbnail((480, 270))
            frames.append((timestamp, image.copy()))
    finally:
        capture.release()
    if not frames:
        raise ValueError("no frames could be sampled from the video")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    per_sheet = 9
    for sheet_index in range(math.ceil(len(frames) / per_sheet)):
        group = frames[sheet_index * per_sheet : (sheet_index + 1) * per_sheet]
        cell_width, cell_height = 500, 310
        sheet = Image.new("RGB", (cell_width * 3, cell_height * 3), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (timestamp, image) in enumerate(group):
            x = (index % 3) * cell_width
            y = (index // 3) * cell_height
            sheet.paste(image, (x + 10, y + 28))
            draw.text((x + 10, y + 7), f"{timestamp:.1f}s", fill="black")
        path = output_dir / f"contact_sheet_{sheet_index + 1}.jpg"
        sheet.save(path, quality=88)
        paths.append(path)
    return paths


def extract_fen(text: str) -> str:
    """Extract and validate one full FEN string from a model response."""
    import chess

    cleaned = re.sub(r"```(?:text)?|```", "", text, flags=re.IGNORECASE).strip()
    candidates = [cleaned, *cleaned.splitlines()]
    for candidate in candidates:
        candidate = re.sub(r"^\s*(?:fen\s*:?)\s*", "", candidate, flags=re.IGNORECASE)
        fields = candidate.strip().split()
        if len(fields) < 4:
            continue
        fen = " ".join(fields[:6] if len(fields) >= 6 else [*fields[:4], "0", "1"])
        try:
            if not chess.Board(fen).is_valid():
                continue
        except ValueError:
            continue
        return fen
    raise ValueError("vision model did not return a valid FEN position")


def cloud_chess_analysis(fen: str) -> str:
    """Return the best cached Lichess engine line, expressed in UCI and SAN."""
    import chess
    import chess.engine
    import os
    import shutil

    engine_path = os.getenv('STOCKFISH_PATH') or shutil.which('stockfish')
    if not engine_path:
        local = Path(__file__).resolve().parents[1] / '.tools' / 'stockfish'
        engine_path = next((str(p) for p in local.rglob('stockfish*.exe')), None)
    if engine_path:
        board = chess.Board(fen)
        if not board.is_valid():
            raise ValueError('illegal chess position; recheck image transcription')
        with chess.engine.SimpleEngine.popen_uci(engine_path, timeout=15) as engine:
            result = engine.analyse(board, chess.engine.Limit(time=3))
            move = result['pv'][0]
            score = result['score'].pov(board.turn)
            return (f"Side-to-move score: cp={score.score()}, mate={score.mate()}; positive favors the mover, negative favors the opponent. "
                    f"Local engine best move: {board.san(move)} (UCI {move.uci()}). "
                    f"Score: {result['score']}; depth: {result.get('depth')}. "
                    'Analysis is conditional on the image-derived FEN being correct.')

    response = requests.get(
        "https://lichess.org/api/cloud-eval",
        params={"fen": fen, "multiPv": 1, "variant": "standard"},
        headers={"User-Agent": "GAIA educational agent"},
        timeout=20,
    )
    if response.status_code == 404:
        return "No cached cloud evaluation is available for this position."
    response.raise_for_status()
    payload = response.json()
    principal_variation = payload.get("pvs", [{}])[0]
    moves = str(principal_variation.get("moves", "")).split()
    if not moves:
        raise ValueError("cloud evaluation returned no principal variation")
    board = chess.Board(fen)
    first_move = chess.Move.from_uci(moves[0])
    san = board.san(first_move)
    return (
        f"Best move: {san} (UCI {moves[0]}). "
        f"Principal variation (UCI): {' '.join(moves[:8])}. "
        f"Evaluation: cp={principal_variation.get('cp')}, mate={principal_variation.get('mate')}."
    )
