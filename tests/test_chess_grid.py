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
