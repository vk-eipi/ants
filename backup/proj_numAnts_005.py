#!/usr/bin/env python

"""proj/numAnts.py
v2.4
- timer cutoff
v2.3
- remove extraneous water set
- implement passable & ant fields
v2.2
- world_list
v2.1
- track invisible food
ants v2 (001)
- remove ranges in favor of numpy arrays and cell.adj
"""

from __future__ import division

import sys # stdin, stdout, etc
import os # os.name for timer
import traceback
import signal
import random
import time
#from math import sqrt
import logging
import itertools

import numpy as np

import numLocation as location
from constants import *

log = logging.getLogger(__name__)

class Ants():

    # Control Flow functions

    def __init__(self):
        self.cols = None
        self.rows = None
        self.dimensions = None
        self.loc = None
        self.world_list = None

        self.passable_field = None
        self.ant_field = None
        self.explored_field = None
        self.visible_field = None
        self.vision_stamp = None

        self.hill_set = set()
        self.ant_set = set()
        self.dead_set = set()
        self.food_set = set()
        self.explored = set()
        self.vision = set()
        
        self.cur_turn = 0
        
        self.turntime = 500
        self.loadtime = 3000
        self.turn_start_time = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0

    def setup(self, data):
        'parse initial input and setup starting game state'

        # start timer
        self.turn_start_time = time.time()

        log.info("== SETUP BEGINS == ")

        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = min(500, int(tokens[1]))
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        self.cur_turn = 0
        self.dimensions = (self.rows, self.cols)

        log.info("Dimensions: %s", self.dimensions)

        self.passable_field = np.ones(self.dimensions, dtype=bool)
        self.ant_field = np.zeros(self.dimensions, dtype=bool)
        self.explored_field = np.zeros(self.dimensions, dtype=bool)
        self.visible_field = np.zeros(self.dimensions, dtype=bool)
        self.vision_stamp = location.gen_stamp(self.viewradius2)

        time_before_loc = time.time()
        self.loc = [[location.Location(r,c,self) for c in xrange(self.cols)]
                    for r in xrange(self.rows)]
        self.world_list = list(itertools.chain.from_iterable(self.loc))
        loc_time = time.time() - time_before_loc
        log.debug('Used on Locations = {0} seconds'.format(loc_time))

        # preset ranges
        time_before_range = time.time()
        do_rows = self.rows
        for cell in self.world_list:
            cell.gen_adj()
        range_time = time.time() - time_before_range
        done_cells = do_rows*self.cols
        self.cell_time = 1000 * range_time / done_cells # milliseconds
        log.debug('Used on gen_ranges p1 = %f seconds', range_time)
        log.debug('Per cell: %f milliseconds', self.cell_time)
        time_before_range = time.time()

        log.debug('remaining in setup = {0} milliseconds'.format(self.setup_time_remaining()))


    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.time()

        #increment turn
        self.cur_turn += 1
        log.info("\n== TURN %s - Update - BEGINS ==", self.cur_turn)

        new_hill_set = set()
        new_food_set = set()
        # resetting ant/food/dead contents, sets
        #* can consider keeping record of food (but subpar? or equal?)
        self.ant_field = np.zeros(self.dimensions, dtype=bool)
        for obj_loc in self.ant_set:
            obj_loc.contents = None
        self.ant_set.clear()
        for death_loc in self.dead_set:
            death_loc.recent_deaths = []
        self.dead_set.clear()

        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    letter = tokens[0]
                    row = int(tokens[1])
                    col = int(tokens[2])
                    cur_loc = self.loc[row][col]
                    if letter == 'w':
                        cur_loc.terrain = WATER
                        self.explored.add(cur_loc) # know terrain
                        for neighbor in cur_loc.adj:
                            neighbor.adj.remove(cur_loc)
                        cur_loc.adj = []
                        self.passable_field[cur_loc] = False
                    elif letter == 'f':
                        cur_loc.contents = FOOD
                        new_food_set.add(cur_loc)
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            cur_loc.contents = owner
                            self.ant_set.add(cur_loc)
                            self.ant_field[cur_loc] = True
                        elif tokens[0] == 'd':
                            # no restriction on what else is on square
                            cur_loc.recent_deaths.append(owner)
                            self.dead_set.add(cur_loc)
                        elif tokens[0] == 'h':
                            cur_loc.hill = owner
                            new_hill_set.add(cur_loc)
                            # add to Player info

        # reset vision (must come after my_ants generated)
        self.gen_vision_field()

        self.vision = set([self.loc[r][c] 
                      for r,c in zip(*self.visible_field.nonzero())])
        # update razed hills using vision
        razed_hills = self.vision & (self.hill_set - new_hill_set)
        for razed in razed_hills:
            razed.hill = None # razed
        self.hill_set.difference_update(razed_hills)
        self.hill_set.update(new_hill_set)
        
        # update eaten food
        eaten_food = (self.food_set - new_food_set) & self.vision
        for eaten in (eaten_food - self.ant_set):
            eaten.contents = None
        self.food_set.difference_update(eaten_food)
        self.food_set.update(new_food_set)
        
        # updating seen but unexplored terrain as LAND
        # new water is not marked in explored_field yet
        for land_loc in (self.vision - self.explored):
            land_loc.terrain = LAND
        self.explored_field |= self.visible_field
        #self.explored = set([self.loc[r][c] 
                      #for r,c in zip(*self.visible_field.nonzero())])
        self.explored.update(self.vision)              
        
        # mark occupied status
        for cell in self.world_list:
            cell.unoccupied_next = cell.unoccupied
        
        self.log_time()

    def time_remaining(self):
        return self.turntime - int(1000 * (time.time() - self.turn_start_time))
    def log_time(self, msg="TIME"):
        used = 1000*(time.time() - self.turn_start_time)
        left = self.turntime - used
        log.debug("%s: %f ms used, %f ms remaining", msg, used, left)
    def setup_time_remaining(self):
        """Return remaining time for setup in milliseconds."""
        return self.loadtime - int(1000 * (time.time() - self.turn_start_time))


    def issue_order(self, order):
        'issue an order by writing the proper ant location and direction'
        (row, col), direction = order
        sys.stdout.write('o %s %s %s\n' % (row, col, direction))
        sys.stdout.flush()

    def finish_turn(self):
        'finish the turn by writing the go line'
        sys.stdout.write('go\n')
        sys.stdout.flush()

    # Utility Functions

    # a) Precalculation
    def gen_vision_field(self):
        
        vision = np.zeros(self.dimensions, dtype=bool)
        for ant in self.my_ants():
            vision = location.or_stamp(vision, self.vision_stamp, 
                                       centre=ant)
        self.visible_field = vision
        for cell in self.world_list:
            cell.visible = vision[cell]

    # b) Location sets

    def my_hills(self):
        return set(loc for loc in self.hill_set if loc.hill == ME)

    def enemy_hills(self):
        """Return a set of all enemy hills last seen standing."""
        # previously returned tuple w/ owner, now only location
        return set(loc for loc in self.hill_set if loc.hill != ME)

    def my_ants(self):
        """Return a set of all my ant Locations."""
        # consider cache
        return set(loc for loc in self.ant_set if loc.contents == ME)

    def enemy_ants(self):
        """Return a set of all visible enemy ants."""
        return set(loc for loc in self.ant_set if loc.contents != ME)

    @property
    def food(self):
        """Return a list of all food locations."""
        return self.food_set
        
    # c) Other Functions

    def manhattan(self, loc1, loc2):
        """Calculate closest Manhattan distance between 2 locations."""
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def render_text_map(self):
        'return a pretty string representing the map'
        tmp = ''
        for row in self.loc:
            tmp += '# %s\n' % ''.join([str(col) for col in row])
        return tmp

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        'parse input, update game state and call the bot classes do_turn method'
        log.info("\n\n======= GAME BEGINS ======= ")
        ants = Ants()
        map_data = ''
        if os.name == 'posix':
            signal.signal(signal.SIGALRM, timeout_handler)
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    if os.name == 'posix':
                        signal.setitimer(signal.ITIMER_REAL, 
                                         (ants.loadtime-100)/1000.0)
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'end':
                    break
                elif current_line.lower() == 'go':
                    if os.name == 'posix':
                        signal.setitimer(signal.ITIMER_REAL,
                                         (ants.turntime-30)/1000.0)
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
                log.error("There was an ERROR!")

def timeout_handler(signum, frame):
    signal.setitimer(signal.ITIMER_REAL, 0)
    log.error("TIMEOUT!")
    raise Exception("Timeout!")
