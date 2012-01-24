#!/usr/bin/env python
import sys
import traceback
import random
import time
from collections import defaultdict
from math import sqrt
import logging

#from location import Location, Offset, gen_offsets
import location
from constants import *

LOGGING = True
LOG_FILENAME = 'MyBot.log'
if LOGGING:
    logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
log = logging.getLogger(__name__)

class Ants():
    
    # Control Flow functions
    
    def __init__(self):
        self.cols = None
        self.rows = None
        self.dimensions = None
        self.map = None
        self.loc = None
        
        self.hill_set = set()
        self.hill_list = {}
        self.ant_set = set()
        self.ant_list = {}
        self.dead_set = set()
        self.dead_list = defaultdict(list)
        self.food_set = set()
        self.food_list = []
        self.explored = set()
        
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
        
        log.debug("== SETUP BEGINS == ")
        
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
        self.map = [[LAND for col in xrange(self.cols)]
                    for row in xrange(self.rows)]
        
        self.attack_offsets = self.gen_offsets(self.attackradius2)
        self.vision_offsets = self.gen_offsets(self.viewradius2)
        self.gather_offsets = self.gen_offsets(self.spawnradius2)
        self.gather_offsets.remove(location.Offset(0,0,self.dimensions))
        
        time_before_loc = time.time()
        self.loc = [[location.Location(r,c,self) for c in xrange(self.cols)]
                    for r in xrange(self.rows)]
        # preset ranges
        for r in xrange(self.rows):
            for c in xrange(self.cols):
                self.loc[r][c].gen_ranges()
        
        #log.debug(self.loc[1][18].vision_range)
        
        loc_time = time.time() - time_before_loc
        
        log.debug('Used on Locations = {0} seconds'.format(loc_time))
        log.debug('remaining in setup = {0} milliseconds'.format(self.setup_time_remaining()))
        

    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.time()
        
        #increment turn
        self.cur_turn += 1
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        
        # clear hill?
        new_hill_set = set()
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
                    row = int(tokens[1])
                    col = int(tokens[2])
                    cur_loc = self.loc[row][col]
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                        cur_loc.terrain = WATER
                        self.explored.add(cur_loc) # know terrain
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                        cur_loc.contents = FOOD
                        self.food_set.add(cur_loc)
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                            cur_loc.contents = owner
                            self.ant_set.add(cur_loc)
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                            cur_loc.recent_deaths.append(owner)
                            self.dead_set.add(cur_loc)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
                            cur_loc.hill = owner
                            new_hill_set.add(cur_loc)
                            # add to Player info
        
        # reset vision (must come after my_ants generated)
        self.gen_vision_field()
        
        # update razed hills, unmentioned land using vision
        razed_hills = self.vision & (self.hill_set - new_hill_set)
        for razed in razed_hills:
            razed.hill = None # razed
        self.hill_set.difference_update(razed_hills)
        self.hill_set.update(new_hill_set)
        for land_loc in (self.vision - self.explored):
            land_loc.terrain = LAND
        self.explored.update(self.vision)
                        
    def time_remaining(self):
        return self.turntime - int(1000 * (time.time() - self.turn_start_time))
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
            self.vision.update(L.vision_range) # check if None
        for field_loc in self.vision:
            field_loc.visible = True
            
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        'return a list of all food locations'
        return self.food_list[:]       

    def manhattan(self, loc1, loc2):
        'calculate the closest Manhattan distance between two locations'
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def direction(self, loc1, loc2):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = loc1
        row2, col2 = loc2
        height2 = self.rows//2
        width2 = self.cols//2
        d = []
        if row1 < row2:
            if row2 - row1 >= height2:
                d.append('n')
            if row2 - row1 <= height2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= height2:
                d.append('s')
            if row1 - row2 <= height2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= width2:
                d.append('w')
            if col2 - col1 <= width2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= width2:
                d.append('e')
            if col1 - col2 <= width2:
                d.append('w')
        return d


    
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

DEFAULT_GAME = Ants()
