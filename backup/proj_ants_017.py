#!/usr/bin/env python

"""proj/ants.py
Version 1.2
- add WATER locations to self.water
Version 1.1.2
- gen_ranges() for all seen LAND locations
- log_time: reports used/remaining time in reg turn to log
"""

from __future__ import division
import sys
import traceback
import random
import time
from collections import defaultdict
#from math import sqrt
import logging

#from location import Location, Offset, gen_offsets
import location
from constants import *

log = logging.getLogger(__name__)

class Ants():

    # Control Flow functions

    def __init__(self):
        self.cols = None
        self.rows = None
        self.dimensions = None
        self.loc = None

        self.hill_set = set()
        self.ant_set = set()
        self.dead_set = set()
        self.food_set = set()
        self.explored = set()
        self.water = set()

        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.vision = set()
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
                    self.turntime = int(tokens[1])
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

        self.attack_offsets = self.gen_offsets(self.attackradius2)
        self.vision_offsets = self.gen_offsets(self.viewradius2)
        self.gather_offsets = self.gen_offsets(self.spawnradius2)
        self.gather_offsets.remove(location.Offset(0,0,self.dimensions))

        time_before_loc = time.time()
        self.loc = [[location.Location(r,c,self) for c in xrange(self.cols)]
                    for r in xrange(self.rows)]
        loc_time = time.time() - time_before_loc
        log.debug('Used on Locations = {0} seconds'.format(loc_time))

        # preset ranges
        time_before_range = time.time()
        do_rows = min(self.rows, 2500//self.cols)
        for r in xrange(min(self.rows, do_rows)):
            for c in xrange(self.cols):
                self.loc[r][c].gen_ranges()
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
        log.info("== TURN %s - Update - BEGINS ==", self.cur_turn)

        new_hill_set = set()
        # resetting ant/food/dead contents, sets
        #* can consider keeping record of food (but subpar? or equal?)
        for obj_loc in (self.ant_set | self.food_set):
            obj_loc.contents = None
        self.ant_set.clear()
        self.food_set.clear()
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
                        self.water.add(cur_loc)
                    elif letter == 'f':
                        cur_loc.contents = FOOD
                        self.food_set.add(cur_loc)
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            cur_loc.contents = owner
                            self.ant_set.add(cur_loc)
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

        # update razed hills using vision
        razed_hills = self.vision & (self.hill_set - new_hill_set)
        for razed in razed_hills:
            razed.hill = None # razed
        self.hill_set.difference_update(razed_hills)
        self.hill_set.update(new_hill_set)
        # updating seen but unexplored terrain as LAND
        for land_loc in (self.vision - self.explored):
            land_loc.terrain = LAND
            land_loc.gen_ranges()
        self.explored.update(self.vision)
        
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

    def gen_offsets(self, r2):
        return location.gen_offsets(r2, self.dimensions)

    def gen_vision_field(self):
        for row in self.loc: # if necessary, only check in self.vision
            for cell in row:
                cell.visible = False
        self.vision.clear()
        for ant in self.my_ants(): # change once my_ants() returns set
            a_row, a_col = ant
            L = self.loc[a_row][a_col]
            #log.debug("%r range %s", L, L.vision_range)
            if L.vision_range is None: # check if None
                L.gen_ranges() #L.gen_vision_range()
            self.vision.update(L.vision_range)
        for field_loc in self.vision:
            field_loc.visible = True

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
        log.info("======= GAME BEGINS ======= ")
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
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
