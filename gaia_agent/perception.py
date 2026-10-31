"""Task-independent image input preparation for vision calls.

Vision models see an image through a bounded pixel budget: a 1280x720 frame is
rendered at roughly 768 pixels on its short side, so a distant animal, a small
label or a background object may occupy only a few dozen pixels. The harness
cannot make the model perceive better, but it controls which pixels it sees.

`multiscale_views` returns the full image (global context: what is where, so the
same object is not counted twice) plus overlapping zoomed tiles, each enlarged
so the model spends its whole budget on one region. This is the same idea as
reading a chessboard cell by cell, made generic: it knows nothing about the
task, the objects, or any benchmark item.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image

TARGET_SHORT_SIDE = 768
GRID_LABELS = {(0, 0): 'top-left', (1, 0): 'top-right', (0, 1): 'bottom-left', (1, 1): 'bottom-right'}


def tile_boxes(width, height, grid=2, overlap=0.2):
    """Overlapping grid boxes; overlap keeps an object on a tile border whole in one tile."""
    if grid < 1 or not 0 <= overlap < 0.5:
        raise ValueError('grid must be >= 1 and overlap in [0, 0.5)')
    tile_w, tile_h = width / grid, height / grid
    pad_w, pad_h = tile_w * overlap, tile_h * overlap
    boxes = []
    for row in range(grid):
        for col in range(grid):
            left = max(0, round(col * tile_w - pad_w))
            top = max(0, round(row * tile_h - pad_h))
            right = min(width, round((col + 1) * tile_w + pad_w))
            bottom = min(height, round((row + 1) * tile_h + pad_h))
            label = GRID_LABELS[(col, row)] if grid == 2 else f'row {row + 1} column {col + 1}'
            boxes.append((label, (left, top, right, bottom)))
    return boxes


def multiscale_views(image_path, output_dir, grid=2, overlap=0.2, target_short_side=TARGET_SHORT_SIDE):
    """Return [(label, path)]: the full image first, then enlarged overlapping tiles.

    Tiles are upscaled (never downscaled) so their short side reaches the vision
    budget; upscaling adds no information but makes the model allocate its full
    resolution to a smaller region. Files are cached by source name and grid.
    """
    image_path, output_dir = Path(image_path), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    views = [('full image', image_path)]
    with Image.open(image_path) as source:
        image = source.convert('RGB')
    width, height = image.size
    for index, (label, box) in enumerate(tile_boxes(width, height, grid, overlap)):
        path = output_dir / f'{image_path.stem}_tile{grid}_{index}.jpg'
        if not path.exists():
            tile = image.crop(box)
            short = min(tile.size)
            if short < target_short_side:
                scale = target_short_side / short
                tile = tile.resize((round(tile.width * scale), round(tile.height * scale)), Image.LANCZOS)
            tile.save(path, quality=95)
        views.append((label, path))
    return views


def describe_views(views):
    """Prompt text that tells the model how the images relate (order matters)."""
    parts = [f'image {i + 1}: {label}' for i, (label, _) in enumerate(views)]
    return ('The images are ONE scene: ' + '; '.join(parts) + '. Tiles are enlarged, overlapping crops of '
            'the full image, so the same object can appear in several tiles; use the full image to decide '
            'what is the same object and the tiles to see small or distant details.')
