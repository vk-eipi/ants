#!/usr/bin/env python

"""AstarBot
 v0
 - A* pathfinding
   - for food
 - created Node class
"""

import sys
import os
import time
import logging
from optparse import OptionParser
#from collections import deque
import heapq
import itertools
#from functools import total_ordering # if Python 2.7
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

#@total_ordering
class Node(object):
    def __init__(self, loc, target, dist):
        self.loc = loc
        self.g = dist
        self.h = loc.manhattan(target)
        self.f = dist + self.h
    def update(self, dist):
        self.g = min(self.g, dist)
        self.f = self.g + self.h
    @property
    def key(self):
        return (self.f, self.g, self.loc)
    def __cmp__(self, other):
        (self.key).__cmp__(other.key)
    ##def __eq__(self, other):
        ##self.loc == other.loc
    ##def __lt__(self, other):
        ##(self.f, self.g, self.loc) < (other.f, other.g, other.loc)

def regionalize(lset):
    land = set(loc for loc in lset if loc.terrain is LAND)
    sanctum = set(loc for loc in land if loc.vision_range.issubset(lset))
    suburb = land - sanctum
    return (sanctum, suburb)

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us
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
        self.orders = {} # to: from
        self.targets = {} # to: from
        inner_land, outer_land = regionalize(ants.explored)
        
        orders = self.orders
        targets = self.targets
        
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
                self.move_astar(ants, ant_loc, food_loc)
        
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
        
        ants.log_time("BEFORE EXPLORE")
        
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
        
        log.debug("self.orders (to: from): %s", self.orders)
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
            if do_move_direction(loc, direction):
                self.targets[dest] = loc
                return True
        return False
    
    def move_astar(self, ants, start, dest):
        """Implement A* with manhattan heuristic.
        
        The nature of a manhattan heuristic on a grid is such that this 
        is essentially a modified form of Dijkstra: nodes do not need
        to be checked twice
        """
        #log.debug("move_astar %r to %r", start, dest)
        dist = {} # g(x) = real path from start
        cost = {} # g(x)+h(x) = estimated total distance
        action = {}
        heap = []
        blocked = []
        done = [start]
        dist[start] = 0
        cost[start] = start.manhattan(dest)
        for direction in ('n','w','s','e'):
            adj = start.aim(direction)
            if adj.unoccupied and adj not in self.orders:
                if adj == dest:
                    # start right beside dest
                    success = self.do_move_direction(ants, start, direction)
                    assert success
                    self.targets[dest] = start
                    return success
                dist[adj] = 1
                cost[adj] = 1 + adj.manhattan(dest)
                action[adj] = direction
                heapq.heappush(heap, (cost[adj], adj))
            else:
                blocked.append(adj)
                #cost[adj] = INF
        if len(heap) == 0:
            return False
        while heap:
            loc_cost, loc = heapq.heappop(heap)
            for next_dir in ('n','w','s','e'):
                new_loc = loc.aim(next_dir)
                if new_loc == dest or new_loc.terrain is UNKNOWN:
                    # either 1) goal reached, should be best path
                    # or 2) unknown on best path, just end to be lazy
                    success = self.do_move_direction(ants, start, action[loc])
                    assert success
                    self.targets[dest] = start
                    return success
                if new_loc not in done and new_loc not in blocked:
                    if new_loc.terrain is WATER:
                        blocked.append(new_loc)
                    elif new_loc in cost: # (cost[new_loc], new_loc) in heap
                        heap.remove((cost[new_loc], new_loc))
                        dist[new_loc] = min(dist[new_loc], dist[loc] + 1)
                        cost[new_loc] = dist[new_loc] + new_loc.manhattan(dest)
                        heapq.heappush(heap, (cost[new_loc], new_loc))
                    else:
                        dist[new_loc] = dist[loc] + 1
                        cost[new_loc] = dist[new_loc] + new_loc.manhattan(dest)
                        action[new_loc] = action[loc]
                        heapq.heappush(heap, (cost[new_loc], new_loc))

            done.append(loc)
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
