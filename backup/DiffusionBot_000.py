#!/usr/bin/env python

"""DiffusionBot
v0
- implemented diffusion
"""

import sys
import os
import time
import logging
from optparse import OptionParser
import copy

from proj.ants import Ants
from proj.constants import LAND, WATER, UNKNOWN, ME, FOOD, INF

LOGGING = False
log = logging.getLogger(__name__)

def init_log():
    level = {"DEBUG": logging.DEBUG,
             "INFO": logging.INFO,
             "WARNING": logging.WARNING,
             "ERROR": logging.ERROR} #logging.FATAL left out on purpose
    
    # Option for logging
    parser = OptionParser()
    parser.add_option("-l", "--loglevel", "--log", dest="level", 
        type="choice", choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="LEVEL defines minimum importance for logging. "
             "If not defined, no logging is done." )
                     
    (options, args) = parser.parse_args()

    if options.level is not None:
        LOGGING = True
        LOGLEVEL = level[options.level]
        FILENAME = os.path.splitext(sys.argv[0].strip())[0]
        LOG_FILENAME = os.path.join("game_logs", FILENAME + '.log')
        if LOGGING:
            logging.basicConfig(filename=LOG_FILENAME,level=LOGLEVEL)

def regionalize(lset):
    land = set(loc for loc in lset if loc.terrain is LAND)
    sanctum = set(loc for loc in land if loc.vision_range.issubset(lset))
    suburb = land - sanctum
    return (sanctum, suburb)

class MyBot(object):
    def __init__(self):
        MyBot.DIFF_FACTOR = 0.2
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    def do_setup(self, ants):
        self.ants = ants
        ##self.world = set(c for r in ants.loc for c in r)
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                cell.u_scent = 0.0 # unified scent
                cell.diff = MyBot.DIFF_FACTOR
                cell.u_source = None
                cell.u_pump = 0.0
                cell.unoccupied_next = False # normally True though
        self.worst_time_used = 0.0 
        log.debug("%s ms left after bot setup", ants.setup_time_remaining())
        
    # do turn is run once per turn
    def do_turn(self, ants):
        log.info("= TURN {0} - do_turn - BEGINS =".format(ants.cur_turn))
        
        # setting up diffusion
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                cell.u_source = None
                cell.u_pump = 0.0
                cell.adj = [] # ants will have no adj??
                if cell.passable and cell.contents in (None, FOOD):
                    cell.diff = MyBot.DIFF_FACTOR
                    cell.unoccupied_next = True # unless food
                    for direction in ("n", "e", "s", "w"):
                        adj = cell.aim(direction)
                        if adj.passable and adj.contents in (None, FOOD):
                            cell.adj.append(adj)
                else: # WATER or ant : do not receive diffusion
                    cell.diff = 0.0
                    cell.unoccupied_next = False
        u_sources = set()
        for food in ants.food_set:
            food.u_source = 50.0
            u_sources.add(food)
            food.unoccupied_next = False
        for hill_loc in ants.enemy_hills():
            hill_loc.u_source = 100.0
            u_sources.add(hill_loc)
        for hill_loc in ants.my_hills():
            hill_loc.u_source = -5.0
            u_sources.add(hill_loc)      
        for source in u_sources:
            source.u_pump = len(source.adj)*source.diff*source.u_source
        # build diffusion deltas
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                cell.u_scent_change = cell.u_pump
                for neighbor in cell.adj:
                    cell.u_scent_change += cell.diff * (adj.u_scent -
                                                        cell.u_scent)
        # update scents
        for r in xrange(ants.rows):
            for c in xrange(ants.cols):
                cell = ants.loc[r][c]
                cell.u_scent += cell.u_scent_change
        
        # movement
        for ant_loc in ants.my_ants():
            log.debug("ant: %r; ant.adj: %s", ant_loc, ant_loc.adj)
            for target in sorted(ant_loc.gather_range, reverse=True,
                                key=lambda a: a.u_scent):
                if target.unoccupied_next:
                    direction = ant_loc.direction(target)
                    ants.issue_order((ant_loc, direction))
                    target.unoccupied_next = False
                    ant_loc.unoccupied_next = True
                    log.debug("%r to %r", ant_loc, target)
                    break
        
        
        self.worst_time_used = max(self.worst_time_used, 
                        1000 * (time.time() - ants.turn_start_time) )
        ##log.debug("self.orders (to: from): %s", self.orders)
        log.info("Most used: %s ms", self.worst_time_used)
        ants.log_time("FINAL")
        
    
    def do_move_direction(self, ants, loc, direction):
        # the aim method will wrap around the map properly
        # and give us a new Location
        new_loc = loc.aim(direction)
        if (new_loc.unoccupied and new_loc not in self.orders):
            ants.issue_order((loc, direction))
            #log.debug("Order Issued: %s", (loc,direction))
            self.orders[new_loc] = loc
            return True
        else:
            return False   

    def move_manhattan(self, ants, loc, dest):
        directions = loc.direction(dest)
        for direction in directions:
            if self.do_move_direction(ants, loc, direction):
                self.targets[dest] = loc
                return True
        return False

if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    init_log()
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
