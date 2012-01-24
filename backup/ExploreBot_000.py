#!/usr/bin/env python

"""
ExploreBot
v3
- exploration diffusion
- 100 food iterations
- 100 exploration iterations

NumDiffBot
v 2.2 (006)
- use numAnts 
  - food is persistent
v 2.1
- clamps replace scents
- different visualization shading
v2 (004)
- reset blocked scents
- 50 iterations
v1.5 (003)
- use 2d arrays instead of iteration

DiffusionBot
v1 (003)
- 10 diffusion iterations
- figured out color map
v0.1 (002)
- implemented diffusion (unified)
- added custom visualization to options
"""

import sys
import os
import time
import logging
from optparse import OptionParser
import copy

import numpy as np

from proj.numAnts import Ants
from proj.constants import LAND, WATER, UNKNOWN, ME, FOOD, INF

class Settings:
    VISUALIZE = False
    LOGGING = False
log = logging.getLogger(__name__)

def init_options():
    parser = OptionParser()
    parser.add_option("-l", "--loglevel", "--log", dest="level", 
        type="choice", choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="LEVEL defines minimum importance for logging. "
             "If not defined, no logging is done." )
    parser.add_option("-v", "--visual", action="store_true", 
                      dest="visualize", default=False, 
                      help="Turns on custom visualization.")
                     
    (options, args) = parser.parse_args()
    
    # setup visualizer
    Settings.VISUALIZE = options.visualize

    # setup logging
    level = {"DEBUG": logging.DEBUG,
             "INFO": logging.INFO,
             "WARNING": logging.WARNING,
             "ERROR": logging.ERROR} #logging.FATAL left out on purpose
    if options.level is not None:
        Settings.LOGGING = True
        LOGLEVEL = level[options.level]
        FILENAME = os.path.splitext(sys.argv[0].strip())[0]
        LOG_FILENAME = os.path.join("game_logs", FILENAME + '.log')
        if Settings.LOGGING:
            logging.basicConfig(filename=LOG_FILENAME,level=LOGLEVEL)
            
    log.info("\n\noptions: %s", options)

def regionalize(lset):
    land = set(loc for loc in lset if loc.terrain is LAND)
    sanctum = set(loc for loc in land if loc.vision_range.issubset(lset))
    suburb = land - sanctum
    return (sanctum, suburb)

class MyBot(object):
    def __init__(self):
        MyBot.DIFF_FACTOR = 0.2
        MyBot.U_ITERATIONS = 100
        MyBot.E_FACTOR = 0.2
        MyBot.E_ITERATIONS = 100
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    def do_setup(self, ants):
        self.ants = ants
        ##self.world = set(c for r in ants.loc for c in r)
        
        self.u_scent_field = np.zeros(ants.dimensions) # unified
        self.e_scent_field = np.zeros(ants.dimensions) # exploration
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                cell.unoccupied_next = False # normally True though
        self.worst_time_used = 0.0 
        log.debug("%s ms left after bot setup", ants.setup_time_remaining())
        
    # do turn is run once per turn
    def do_turn(self, ants):
        log.info("= TURN {0} - do_turn - BEGINS =".format(ants.cur_turn))
        
        self.diffuse_food(ants)
        self.diffuse_explore(ants)
        
        # movement
        u_scent_field = self.u_scent_field + 15.0 * self.e_scent_field
        for ant_loc in ants.my_ants():
            for target in sorted(ant_loc.adj, reverse=True,
                                key=lambda a: (u_scent_field[a], a)):
                if target.unoccupied_next:
                    direction = ant_loc.direction(target)[0]
                    ants.issue_order((ant_loc, direction))
                    target.unoccupied_next = False
                    ant_loc.unoccupied_next = True
                    #log.debug("%r to %r", ant_loc, target)
                    break
        
        ants.log_time("BEFORE VISUALIZE")
        log.info("VISUALIZE: %s", Settings.VISUALIZE)
        if Settings.VISUALIZE:
            for cell in ants.explored:
                txts = [ "u_scent: {0}".format(u_scent_field[cell]),
                        #"u_adj_field: {0}".format(u_adj_field[cell])
                        #"diff_self: {0}".format(u_diff_self[cell]),
                        ]
                for txt in txts:
                    cmd = "i {0} {1} {2}\n".format(cell.r, cell.c, txt)
                    sys.stdout.write(cmd)
                ##txt = "u_scent: {0}".format(u_scent_field[cell])
                ##cmd = "i {0} {1} {2}\n".format(cell.r, cell.c, txt)
                ##sys.stdout.write(cmd)    
                
                intensity = max(0,min(255, int((u_scent_field[cell]+5)/100*256)))
                color = (255-intensity, 0, intensity, 0.5)
                color = map(str, color)
                cmd1 = "v setFillColor {0}\n".format(" ".join(color))
                cmd2 = "v tile {0.r} {0.c}\n".format(cell)
                sys.stdout.write(cmd1)
                sys.stdout.write(cmd2)
            sys.stdout.flush()
        
        
        self.worst_time_used = max(self.worst_time_used, 
                        1000 * (time.time() - ants.turn_start_time) )
        ##log.debug("self.orders (to: from): %s", self.orders)
        log.info("Most used: %s ms", self.worst_time_used)
        ants.log_time("FINAL")
        
    def diffuse_food(self, ants):
        # setting up diffusion
        dif_setup_begin = time.time()
        
        scent_field = self.u_scent_field
        unblocked_field = np.ones(ants.dimensions, dtype=bool)
        clamps = []
        clamp_field = np.empty(ants.dimensions)
        
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                if cell.passable and cell.contents in (None, FOOD):
                    cell.unoccupied_next = True # unless food
                else: # WATER or ant : do not receive diffusion
                    unblocked_field[cell] = False
                    scent_field[cell] = 0.0 # reset scent
                    cell.unoccupied_next = False
        unblocked_n = np.roll(unblocked_field, 1, axis=0)
        unblocked_s = np.roll(unblocked_field,-1, axis=0)
        unblocked_w = np.roll(unblocked_field, 1, axis=1)
        unblocked_e = np.roll(unblocked_field,-1, axis=1)
        adj_field = (unblocked_n.astype(np.int8) + unblocked_s + 
                       unblocked_w + unblocked_e)
        diff_self = MyBot.DIFF_FACTOR * adj_field * unblocked_field
        diff_n = (MyBot.DIFF_FACTOR * 
            (unblocked_field & unblocked_n))
        diff_s = (MyBot.DIFF_FACTOR * 
            (unblocked_field & unblocked_s))
        diff_w = (MyBot.DIFF_FACTOR * 
            (unblocked_field & unblocked_w))
        diff_e = (MyBot.DIFF_FACTOR * 
            (unblocked_field & unblocked_e))
        
        # clamped source setup
        for food in ants.food_set:
            food.unoccupied_next = False
            clamp_field[food] = 50.0
        clamps.extend(ants.food_set)
        for hill_loc in ants.enemy_hills():
            clamp_field[hill_loc] = 100.0
        clamps.extend(ants.enemy_hills())
        for hill_loc in ants.my_hills():
            clamp_field[hill_loc] = -5.0
        clamps.extend(ants.my_hills())
        clamp_index = zip(*clamps)
        
        dif_setup_time = 1000*(time.time()-dif_setup_begin)
        log.info("Diff setup: %s ms", dif_setup_time)
        
        dif_begin = time.time()
        for diffusion in xrange(MyBot.U_ITERATIONS):
            # source blocks
            scent_field[clamp_index] = clamp_field[clamp_index]
            # build new scents
            scent_field = (scent_field * (1 - diff_self)
                + (diff_n * np.roll(scent_field, 1, axis=0))
                + (diff_s * np.roll(scent_field,-1, axis=0))
                + (diff_w * np.roll(scent_field, 1, axis=1))
                + (diff_e * np.roll(scent_field,-1, axis=1)))
        self.u_scent_field = scent_field # store scent field
        dif_time = 1000*(time.time()-dif_begin)
        log.info("Unified: %s diff iterations: %s ms", MyBot.U_ITERATIONS, dif_time)
        
    def diffuse_explore(self, ants):
        # setting up variables
        dif_setup_begin = time.time()
        
        scent_field = self.e_scent_field
        unblocked_field = np.ones(ants.dimensions, dtype=bool)
        
        # clamped source setup
        invisible = ~ants.visible_field
        unexplored = ~ants.explored_field
        clamp_field = invisible + 3.0*unexplored
        clamp_index = invisible | unexplored
        
        # preset unblocked and diff fields
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                if ( cell.terrain is WATER or 
                     cell.contents not in (None, FOOD)):
                    # WATER or ant : do not receive diffusion
                    unblocked_field[cell] = False
                    scent_field[cell] = 0.0 # reset scent
        unblocked_n = np.roll(unblocked_field, 1, axis=0)
        unblocked_s = np.roll(unblocked_field,-1, axis=0)
        unblocked_w = np.roll(unblocked_field, 1, axis=1)
        unblocked_e = np.roll(unblocked_field,-1, axis=1)
        adj_field = (unblocked_n.astype(np.int8) + unblocked_s + 
                       unblocked_w + unblocked_e)
        diff_self = MyBot.E_FACTOR * adj_field * unblocked_field
        diff_n = (MyBot.E_FACTOR * 
            (unblocked_field & unblocked_n))
        diff_s = (MyBot.E_FACTOR * 
            (unblocked_field & unblocked_s))
        diff_w = (MyBot.E_FACTOR * 
            (unblocked_field & unblocked_w))
        diff_e = (MyBot.E_FACTOR * 
            (unblocked_field & unblocked_e))
        
        dif_setup_time = 1000*(time.time()-dif_setup_begin)
        log.info("Diff setup: %s ms", dif_setup_time)
        
        dif_begin = time.time()
        for diffusion in xrange(MyBot.E_ITERATIONS):
            # source blocks
            scent_field[clamp_index] = clamp_field[clamp_index]
            # build new scents
            scent_field = (scent_field * (1 - diff_self)
                + (diff_n * np.roll(scent_field, 1, axis=0))
                + (diff_s * np.roll(scent_field,-1, axis=0))
                + (diff_w * np.roll(scent_field, 1, axis=1))
                + (diff_e * np.roll(scent_field,-1, axis=1)))
        self.e_scent_field = scent_field # store scent field
        dif_time = 1000*(time.time()-dif_begin)
        log.info("Explore: %s diff iterations: %s ms", MyBot.E_ITERATIONS, dif_time)

if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    init_options()
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
