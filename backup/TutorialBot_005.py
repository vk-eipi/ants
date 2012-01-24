#!/usr/bin/env python

"""
 TutorialBot
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
class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        pass
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    # the ants class is created and setup by the Ants.run method
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        self.world = set(c for r in ants.loc for c in r)
        self.unknown = copy.copy(self.world)
    
    # do turn is run once per turn
    # the ants class has the game state and is updated by the Ants.run method
    # it also has several helper methods to use
    def do_turn(self, ants):
        log.info("= TURN {0} - do_turn - BEGINS =".format(ants.cur_turn))
        
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
        
        # explore unknown terrain
        self.unknown -= ants.vision #* try replace with difference_update or world-ants.explored
        for ant_loc in ants.my_ants():
            if ant_loc not in orders.values():
                unknown_locs = sorted(self.unknown, 
                                key=lambda u: (ant_loc.manhattan(u),u))
                for unknown_loc in unknown_locs:
                    if do_move_location(ant_loc, unknown_loc):
                        break
                
        #unblock spawn hills
        for hill_loc in ants.my_hills():
            if hill_loc in ants.my_ants() and hill_loc not in orders.values():
                for direction in ('s','e','w','n'):
                    if do_move_direction(hill_loc, direction):
                        break


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
