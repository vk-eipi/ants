#!/usr/bin/env sh
python tools/playgame.py "python $1 $2" "python tools/sample_bots/python/HunterBot.py" --map_file tools/maps/example/tutorial1.map \
--log_dir game_logs --turns 60 --scenario --food none --viewradius 55 --player_seed 7 --verbose -e
# scenario uses food placements specified on map
# viewradius 55 to follow online tutorial
