#!/usr/bin/env sh
##tools/playgame.py --player_seed 42 --end_wait=0.25 --verbose --log_dir game_logs --turns 500 -e --strict --capture_errors \
    ##--map_file tools/maps/maze/maze_04p_01.map --engine_seed 760 -I \
    ##"python $1 $2" \
    ##"python ExploreBot_002.py" \
    ##"python ExploreBot_002.py" \
    ##"python ExploreBot_002.py"
tools/playgame.py --player_seed 42 --end_wait=0.25 --verbose --log_dir game_logs --turns 150 -e --strict --capture_errors \
    --map_file tools/maps/random_walk/random_walk_p04_02.map --engine_seed 11760 -I \
    "python $1 $2" \
    "python ExploreBot_002.py" \
    "python NumDiffBot_006.py" \
    "python ExploreBot_002.py"
##tools/playgame.py --player_seed 42 --end_wait=0.25 --verbose --log_dir game_logs --turns 500 -e --strict --capture_errors \
    ##--map_file tools/maps/maze/maze_p03_03.map --engine_seed 760 -I \
    ##"python NumDiffBot_004.py" \
    ##"python NumDiffBot_006.py" \
    ##"python $1 $2"
