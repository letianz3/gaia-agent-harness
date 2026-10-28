import pytest
from gaia_agent.media_tools import grid_to_fen


def test_rotated_grid_maps_to_same_position():
    # Synthetic minimal legal position, not a benchmark puzzle.
    grid=dict(files_left_to_right='abcdefgh',ranks_top_to_bottom='87654321',turn='w',
              rows=['.......k','........','........','........','........','........','........','K.......'])
    fen=grid_to_fen(grid)
    rotated=dict(grid, files_left_to_right='hgfedcba',ranks_top_to_bottom='12345678',
                 rows=[r[::-1] for r in grid['rows'][::-1]])
    assert grid_to_fen(rotated)==fen
    assert fen=='7k/8/8/8/8/8/8/K7 w - - 0 1'


@pytest.mark.parametrize('rows', [['........']*8, ['K......k']*7, ['K......?']*8])
def test_invalid_grid_rejected(rows):
    with pytest.raises(ValueError):
        grid_to_fen(dict(files_left_to_right='abcdefgh',ranks_top_to_bottom='87654321',turn='w',rows=rows))


def test_labelled_cell_map_requires_full_coverage():
    from gaia_agent.media_tools import cell_maps_to_grid
    cells={f'r{r}c{c}':'.' for r in range(8) for c in range(8)}
    axes=dict(files_left_to_right='abcdefgh',ranks_top_to_bottom='87654321',turn='w')
    assert cell_maps_to_grid(axes,[cells])['rows']==['........']*8
    del cells['r0c0']
    with pytest.raises(ValueError,match='64 labelled'):
        cell_maps_to_grid(axes,[cells])


def test_digital_grid_segmentation_and_nonboard_refusal(tmp_path):
    from PIL import Image,ImageDraw
    from gaia_agent.media_tools import chess_cell_sheets
    im=Image.new('RGB',(160,160),'white'); draw=ImageDraw.Draw(im)
    for r in range(8):
        for c in range(8):
            draw.rectangle((c*20,r*20,c*20+19,r*20+19),fill='green' if (r+c)%2 else 'beige')
    path=tmp_path/'grid.png';im.save(path)
    assert len(chess_cell_sheets(path,tmp_path/'out'))==2
    Image.new('RGB',(160,160),'white').save(path)
    with pytest.raises(ValueError):
        chess_cell_sheets(path,tmp_path/'bad')
