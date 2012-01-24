#!/usr/bin/env sh
python visual_overlay/ants/playgame.py --player_seed 42 --end_wait=0.25 --verbose --log_dir game_logs --turns 130 \
    -e --strict --capture_errors --engine_seed 11760 --turntime 2000 \
    --map_file tools/maps/random_walk/random_walk_p04_02.map \
    "python $1 $2 --visual" \
    "python ExploreBot_002.py" \
    "python NumDiffBot_006.py" \
    "python ExploreBot_002.py"
