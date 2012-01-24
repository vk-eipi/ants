#!/usr/bin/env sh
tools/playgame.py -So --player_seed=42 --end_wait=0.25 --verbose --log_dir=game_logs --turns=1000 --map_file=tools/maps/maze/maze_04p_01.map "python $1" \
	"python tools/sample_bots/python/HunterBot.py" \
	"python tools/sample_bots/python/GreedyBot.py" \
	"python tools/sample_bots/python/LeftyBot.py" |
java -jar tools/visualizer.jar
