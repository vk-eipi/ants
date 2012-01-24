#!/usr/bin/python
import pstats

p = pstats.Stats('game_logs/profile')
p.strip_dirs()
p.sort_stats('cum').print_stats(15)
p.sort_stats('time').print_stats(15)
p.sort_stats('time').print_callees(10)
p.sort_stats('calls').print_stats(15)
p.sort_stats('calls').print_callers(10)
