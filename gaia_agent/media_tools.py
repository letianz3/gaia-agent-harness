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
            "bestvideo[height<=720][ext=mp4][vcodec!=none]/"
            "best[height<=720][vcodec!=none]/worst[vcodec!=none]"
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

    frames: list[tuple[float, Image.Image]] = []
    try:
        for timestamp in timestamps:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
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


def video_detail_frames(video_path, output_dir, timestamps):
    """Bounded individual frames: keep native detail instead of a thumbnail sheet."""
    import cv2
    capture=cv2.VideoCapture(str(video_path))
    paths=[]
    try:
        fps=capture.get(cv2.CAP_PROP_FPS)
        duration=capture.get(cv2.CAP_PROP_FRAME_COUNT)/fps if fps>0 else 0
        if duration<=0: raise ValueError('invalid video duration')
        timestamps=coverage_times(timestamps,duration)
        for i,t in enumerate(timestamps):
            if not isinstance(t,(float,int)) or isinstance(t,bool) or not math.isfinite(t) or not 0<=t<duration:
                continue
            capture.set(cv2.CAP_PROP_POS_MSEC,t*1000)
            ok,frame=capture.read()
            if not ok:continue
            image=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            image.thumbnail((1280,720))
            path=output_dir/f'detail_{i}_{t:.2f}.jpg'
            image.save(path,quality=95)
            paths.append((t,path))
    finally:
        capture.release()
    if not paths:raise ValueError('no valid detail frames')
    return paths


def coverage_times(requested,duration,limit=6):
    """Fill largest temporal gaps so model-selected early frames cannot hide later events."""
    times=sorted(set(float(t) for t in requested[:limit] if isinstance(t,(int,float))
                     and not isinstance(t,bool) and math.isfinite(t) and 0<=t<duration))
    while len(times)<limit:
        edges=[0,*times,duration]
        a,b=max(zip(edges,edges[1:]),key=lambda pair:pair[1]-pair[0])
        if b-a<0.01:break
        times.append((a+b)/2);times.sort()
    return times


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
            return (f"Local engine best move: {board.san(move)} (UCI {move.uci()}). "
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


def grid_to_fen(grid):
    """Map visual screen cells to chess coordinates without LLM FEN arithmetic."""
    import chess
    if not isinstance(grid, dict):
        raise ValueError('board must be an object')
    files = grid.get('files_left_to_right')
    ranks = grid.get('ranks_top_to_bottom')
    rows = grid.get('rows')
    turn = grid.get('turn')
    if files not in ('abcdefgh','hgfedcba') or ranks not in ('12345678','87654321'):
        raise ValueError('read coordinate labels: files/ranks must be ordered axis strings')
    if not isinstance(rows,list) or len(rows)!=8 or any(
            not isinstance(r,str) or not re.fullmatch(r'[.PNBRQKpnbrqk]{8}',r) for r in rows):
        raise ValueError('rows must contain exactly eight strings, eight cells each; use dots for empty squares')
    if turn not in ('w','b'):
        raise ValueError('turn must be w or b')
    board=chess.Board(None)
    for y,row in enumerate(rows):
        for x,piece in enumerate(row):
            if piece!='.':
                board.set_piece_at(chess.parse_square(files[x]+ranks[y]),chess.Piece.from_symbol(piece))
    board.turn=turn=='w'
    # A still image cannot establish move-history-dependent castling/en-passant rights.
    if not board.is_valid():
        raise ValueError('illegal board inventory; recheck coordinates, colors, king safety and piece counts')
    return board.fen()


def chess_cell_sheets(image_path, output_dir):
    """Detect flat two-color digital boards; refuse photos/non-regular grids."""
    from collections import Counter
    image=Image.open(image_path).convert('RGB')
    counts=Counter(image.getdata())
    colors=[color for color,_ in counts.most_common(2)]
    if len(colors)!=2 or sum(counts[c] for c in colors)<image.width*image.height*0.4:
        raise ValueError('not a flat two-color digital board')
    import numpy as np
    pixels=np.asarray(image)
    mask=np.all(pixels==colors[0],axis=2)|np.all(pixels==colors[1],axis=2)
    ys,xs=np.nonzero(mask)
    left=int(xs.min()); right=int(xs.max())+1
    top=int(ys.min()); bottom=int(ys.max())+1
    if abs((right-left)/(bottom-top)-1)>0.1:
        raise ValueError('detected board is not square')
    cells=[]; backgrounds=[]
    for row in range(8):
        for col in range(8):
            cell=image.crop((round(left+col*(right-left)/8), round(top+row*(bottom-top)/8),
                             round(left+(col+1)*(right-left)/8), round(top+(row+1)*(bottom-top)/8)))
            cc=Counter(cell.getdata())
            backgrounds.append(0 if cc[colors[0]]>cc[colors[1]] else 1)
            cells.append(cell)
    matches=sum(backgrounds[i]==(backgrounds[0]^((i//8+i%8)%2)) for i in range(64))
    if matches<62:
        raise ValueError('could not validate the alternating 8x8 grid')
    output_dir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for batch in range(2):
        sheet=Image.new('RGB',(8*112,4*136),'white'); draw=ImageDraw.Draw(sheet)
        for local in range(32):
            index=batch*32+local; x=(local%8)*112; y=(local//8)*136
            cell=cells[index].copy(); cell.thumbnail((104,104))
            sheet.paste(cell,(x+4,y+24));draw.text((x+4,y+5),f'r{index//8}c{index%8}',fill='black')
        path=output_dir/f'cells_{batch}.png';sheet.save(path);paths.append(path)
    return paths


def cell_maps_to_grid(axes, batches):
    cells={}
    for batch in batches:
        if not isinstance(batch,dict) or set(cells)&set(batch):
            raise ValueError('invalid or duplicate cell map')
        cells.update(batch)
    expected={f'r{r}c{c}' for r in range(8) for c in range(8)}
    if set(cells)!=expected or any(not isinstance(p,str) or not re.fullmatch(r'[.PNBRQKpnbrqk]',p) for p in cells.values()):
        raise ValueError('each of the 64 labelled cells requires exactly one piece symbol or dot')
    return dict(axes, rows=[''.join(cells[f'r{r}c{c}'] for c in range(8)) for r in range(8)])
