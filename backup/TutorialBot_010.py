#!/usr/bin/env python

"""TutorialBot : based on tutorial on aichallenge.org.
 v1.2
 - regionalize function
 - exploration: unknown -> explored suburb
 v1.1
 - Time limit on exploration
 v 1.0
 Follows online tutorial:
 - Bot instance attributes: world, unknown sets
 - collision detection
 - food gathering
 - evac hill
 - exploration
 - attack hills
"""

import sys
import os
import time
import logging
from optparse import OptionParser
import itertools
import copy

from proj.ants import Ants
from proj.constants import LAND, WATER, UNKNOWN, ME, FOOD

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

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us

def regionalize(lset):
    land = set(loc for loc in lset if loc.terrain is LAND)
    sanctum = set(loc for loc in land if loc.vision_range.issubset(lset))
    suburb = land - sanctum
    return (sanctum, suburb)

class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        pass # ants.TIME_GREEDY = True
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    # the ants class is created and setup by the Ants.run method
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        self.world = set(c for r in ants.loc for c in r)
        #self.unknown = copy.copy(self.world)
        self.prev_explore_time = 10 # milliseconds
        log.debug("%s ms left after bot setup", ants.setup_time_remaining())
        
    # do turn is run once per turn
    # the ants class has the game state and is updated by the Ants.run method
    # it also has several helper methods to use
    def do_turn(self, ants):
        log.info("= TURN {0} - do_turn - BEGINS =".format(ants.cur_turn))
        
        #self.unknown -= ants.vision #* try replace with difference_update or world-ants.explored
        inner_land, outer_land = regionalize(ants.explored)
        
        orders = {}
        def do_move_direction(loc, direction):
            # the aim method will wrap around the map properly
            # and give us a new Location
            new_loc = loc.aim(direction)
            if (new_loc.unoccupied and new_loc not in orders):
                ants.issue_order((loc, direction))
                orders[new_loc] = loc
                return True
            else:
                return False
        targets = {}
        def do_move_location(loc, dest):
            directions = loc.direction(dest)
            for direction in directions:
                if do_move_direction(loc, direction):
                    targets[dest] = loc
                    return True
            return False
        
        # prevent stepping on own hill
        for hill_loc in ants.my_hills():
            orders[hill_loc] = None

        # gather food
        # like example, nested loops w/ food on outer
        foodpaths = sorted(itertools.product(ants.food, ants.my_ants()),
                           key=lambda (f,a): (a.manhattan(f),a,f))
        for food_loc, ant_loc in foodpaths:
            if food_loc not in targets and ant_loc not in targets.values():
                do_move_location(ant_loc, food_loc)
        
        # attack hills
        # unlike tutorial, group equal distances by hill
        hillpaths = []
        for hill_loc in ants.enemy_hills():
            for ant_loc in ants.my_ants():
                if ant_loc not in orders.values():
                    hillpaths.append((hill_loc, ant_loc))
        hillpaths.sort(key=lambda (h,a): (a.manhattan(h),h,a))
        for hill_loc, ant_loc in hillpaths:
            do_move_location(ant_loc, hill_loc)
        
        log.debug("%s of %s ms left before exploration", ants.time_remaining(), ants.turntime)
        
        # explore unknown terrain: target suburb of exploration
        
        exploration_start = time.time()
        num_explorers = 0
        for ant_loc in ants.my_ants():
            if ant_loc not in orders.values():
                if ants.time_remaining() < self.prev_explore_time + 25:
                    log.debug("%s ms left. Quitting exploration...", ants.time_remaining())
                    break
                explore_time_begin = time.time()
                unknown_locs = sorted(outer_land, 
                                key=lambda u: (ant_loc.manhattan(u),u))
                for unknown_loc in unknown_locs:
                    if do_move_location(ant_loc, unknown_loc):
                        break
                self.prev_explore_time = 1000*(time.time() - explore_time_begin)
                num_explorers += 1
        exploration_time = 1000*(time.time()-exploration_start)
        if num_explorers > 0:
            log.debug("%s ms used in ant exploration for %s ants", exploration_time, num_explorers)
            log.debug("%s ms each", exploration_time/num_explorers)
                
        #unblock spawn hills
        for hill_loc in ants.my_hills():
            if hill_loc in ants.my_ants() and hill_loc not in orders.values():
                for direction in ('s','e','w','n'):
                    if do_move_direction(hill_loc, direction):
                        break
        
        ants.log_time()

            ## check if we still have time left to calculate more orders
            #if ants.time_remaining() < 10:
                #break
            
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
