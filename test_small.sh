#!/usr/bin/env sh
# example: $ ./test_small.sh StarterBot.py --loglevel=DEBUG
tools/playgame.py --engine_seed 42 --player_seed 42 --end_wait=0.25 --verbose --log_dir game_logs --turns 30 --map_file=tools/submission_test/test.map "python $1 $2" "python tools/submission_test/TestBot.py"  --food=none -e --strict --capture_errors --nolaunch
