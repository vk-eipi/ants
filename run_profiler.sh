#!/usr/bin/env sh
python -m cProfile -o game_logs/profile $1 < game_logs/0.bot0.input > /dev/null
