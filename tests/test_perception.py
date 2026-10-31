import json
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from gaia_agent.perception import describe_views, multiscale_views, tile_boxes
from gaia_agent.tracing import Trace


def test_tiles_overlap_and_cover_the_whole_image():
    boxes = [box for _, box in tile_boxes(1280, 720, grid=2, overlap=0.2)]
    assert len(boxes) == 4
    covered = Image.new('1', (1280, 720), 0)
    for box in boxes:
        covered.paste(1, box)
    assert covered.getbbox() == (0, 0, 1280, 720) and min(covered.getdata()) == 1
    (l1, _, r1, _), (l2, _, _, _) = boxes[0], boxes[1]
    assert r1 > l2  # adjacent tiles overlap so an object on the seam stays whole in one tile


def test_views_put_full_image_first_and_enlarge_tiles(tmp_path):
    source = tmp_path / 'frame.jpg'
    Image.new('RGB', (1280, 720), 'white').save(source)
    views = multiscale_views(source, tmp_path / 'zoom')
    assert views[0] == ('full image', source)
    assert [label for label, _ in views[1:]] == ['top-left', 'top-right', 'bottom-left', 'bottom-right']
    for _, path in views[1:]:
        with Image.open(path) as tile:
            assert min(tile.size) >= 768
    assert multiscale_views(source, tmp_path / 'zoom') == views  # cached
    text = describe_views(views)
    assert 'image 1: full image' in text and 'same object can appear in several tiles' in text


def test_large_images_are_never_downscaled(tmp_path):
    source = tmp_path / 'big.jpg'
    Image.new('RGB', (4000, 3000), 'white').save(source)
    _, tile = multiscale_views(source, tmp_path / 'zoom')[1]
    with Image.open(tile) as image:
        assert image.size == (2400, 1800)  # half plus 20% overlap on the inner edges, unscaled


def group(key, stage='adult'):
    return dict(species_key=key, life_stage=stage, visual_features='traits', location='left', uncertain=False)


def _frames(tmp_path, stamps):
    paths = {}
    for stamp in stamps:
        path = tmp_path / f'f{stamp}.jpg'
        Image.new('RGB', (640, 360), 'white').save(path)
        paths[stamp] = path
    return paths


def _scripted(replies, calls):
    queue = iter(replies)
    def vision(prompt, images, trace, event, json_output=False):
        calls.append((event, len(images)))
        return json.dumps(next(queue))
    return SimpleNamespace(_vision_observation=vision)


def test_zoom_pass_replaces_top_frames_instead_of_adding_names(tmp_path):
    from gaia_agent.resolution import census_count, refine_with_zoom
    paths = _frames(tmp_path, (0.0, 15.0, 30.0, 45.0, 60.0))
    coarse = [{'timestamp': 0.0, 'groups': [group('Emperor'), group('Skua')]},
              {'timestamp': 15.0, 'groups': [group('Emperor')]},
              {'timestamp': 30.0, 'groups': [group('Emperor'), group('Petrel')]},
              {'timestamp': 45.0, 'groups': [group('Emperor')]},
              {'timestamp': 60.0, 'groups': []}]
    calls = []
    agent = _scripted([{'groups': [group('Emperor'), group('Emperor', 'chick'), group('Petrel'), group('Adelie')]},
                       {'groups': [group('Emperor'), group('Petrel')]},
                       {'groups': [group('Emperor')]}, {'groups': [group('Emperor')]}], calls)
    refined = refine_with_zoom(agent, 'How many species at once?', coarse, paths, tmp_path, Trace('t', 'q'))
    by_time = {f['timestamp']: f for f in refined}
    assert [g['species_key'] for g in by_time[0.0]['groups']] == ['Emperor', 'Emperor', 'Petrel', 'Adelie']
    assert by_time[60.0]['groups'] == []  # lowest ranked, beyond the zoom budget
    assert census_count({'frames': refined}, list(paths)) == 3  # the renamed bird is not double counted
    assert calls == [('video_census_zoom', 5)] * 4


def test_zoomed_frames_are_spread_over_time(tmp_path):
    from gaia_agent.resolution import refine_with_zoom
    paths = _frames(tmp_path, (38.0, 41.0, 44.0, 90.0))
    coarse = [{'timestamp': t, 'groups': [group('Emperor'), group('Petrel')]} for t in (38.0, 41.0, 44.0)]
    coarse.append({'timestamp': 90.0, 'groups': [group('Emperor')]})
    calls = []
    trace = Trace('t', 'q')
    agent = _scripted([{'groups': []}] * 4, calls)
    refine_with_zoom(agent, 'q', coarse, paths, tmp_path, trace)
    zoomed = [e['timestamp'] for e in trace.events if e['type'] == 'video_census_refined']
    assert zoomed == [38.0, 90.0]  # 41 and 44 are the same scene as 38


def test_only_the_requested_category_is_counted():
    from gaia_agent.resolution import census_count
    seal = dict(group('Weddell Seal'), in_requested_category=False)
    frames = {'frames': [{'timestamp': 1.0, 'groups': [group('Emperor'), group('Petrel'), seal]}]}
    assert census_count(frames, [1.0]) == 2
    assert census_count(frames, [1.0], details=True)['excluded_groups'] == 1
