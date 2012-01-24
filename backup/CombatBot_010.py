#!/usr/bin/env python

"""
CombatBot
v4.3
- Memetix-style combat safety

v4.2
- hilldist (limit=15) and threat_value based on hilldist 
- change colour map code
v4.1 (006)
- Attack diffusion against enemy hills + ants with co-op factor
- eliminate unnecessary unoccupied_next setup
- iterations: U120, E120, A40
v4.0
- use concatenate & indexing instead of roll for speed boost
- rearrange unblocked /diff setup

ExploreBot
v3.2
- use passable/ant fields from numAnts v2.3
v3, v3.1 (002)
- exploration diffusion
  - exploration scent reset every turn
  - unexplored edge is clamp; invisible just initialized
- food scent decreases over time
- ants emit repelling food scent
- tune factors / iterations

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
from math import sqrt

import numpy as np

from proj.numAnts import Ants
from proj.numLocation import or_stamp, increment_stamp, min_stamp
from proj.constants import LAND, WATER, UNKNOWN, ME, FOOD, INF, SAFE, NEUTRAL, DIE

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

##def regionalize(lset):
    ##land = set(loc for loc in lset if loc.terrain is LAND)
    ##sanctum = set(loc for loc in land if loc.vision_range.issubset(lset))
    ##suburb = land - sanctum
    ##return (sanctum, suburb)

def roll_all(matrix):
    n = np.vstack((matrix[-1], matrix[:-1]))
    s = np.vstack((matrix[1:], matrix[0]))
    w = np.hstack((matrix[:,-1:], matrix[:,:-1]))
    e = np.hstack((matrix[:,1:], matrix[:,:1]))
    return (n, s, w, e)

class MyBot(object):
    def __init__(self):
        MyBot.DIFF_FACTOR = 0.2
        MyBot.U_ITERATIONS = 100
        MyBot.U_DECAY = 0.95
        
        MyBot.E_FACTOR = 0.15
        MyBot.E_ITERATIONS = 100
        
        MyBot.A_FACTOR = 0.2
        MyBot.COOP_FACTOR = 1.01
        MyBot.A_ITERATIONS = 40
        MyBot.A_DECAY = 0.9
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    def do_setup(self, ants):
        self.ants = ants
        ##self.world = set(c for r in ants.loc for c in r)
        
        if Settings.VISUALIZE:
            self.timer_cutoff = False
        
        self.u_scent_field = np.zeros(ants.dimensions) # unified
        self.e_scent_field = np.zeros(ants.dimensions) # exploration
        self.a_scent_field = np.zeros(ants.dimensions) # attack
        self.enemy_seen = False
        
        self.player_dimensions = (10, ants.rows, ants.cols)
        self.attack_field = np.empty(self.player_dimensions, dtype=int)
        self.weakness_field = np.empty(self.player_dimensions, dtype=int)
        self.lowest_enemy_weakness = np.empty(ants.dimensions, dtype=int)
        self.safety_field = np.empty(ants.dimensions, dtype=np.int8)
        self.soldiers = None
        self.normal_ants = None
        
        # calculate rough combat influence after 1 move
        radius = int(sqrt(ants.attackradius2)) + 1 # 1 longer
        approx_side = 2 * radius + 1
        approx_stamp = np.zeros((approx_side, approx_side), dtype=bool)
        or_stamp(approx_stamp, ants.attack_stamp, (radius, radius))
        or_stamp(approx_stamp, ants.attack_stamp, (radius, radius+1))
        or_stamp(approx_stamp, ants.attack_stamp, (radius, radius-1))
        or_stamp(approx_stamp, ants.attack_stamp, (radius+1, radius))
        or_stamp(approx_stamp, ants.attack_stamp, (radius-1, radius))
        self.approx_combat_stamp = approx_stamp
        
        self.worst_time_used = 0.0 
        log.debug("%s ms left after bot setup", ants.setup_time_remaining())
        
    # do turn is run once per turn
    def do_turn(self, ants):
        log.info("= TURN {0} - do_turn - BEGINS =".format(ants.cur_turn))
        
        self.soldiers = set()
        self.diffuse_attack(ants)
        self.normal_ants = ants.my_ants() - self.soldiers
        
        self.diffuse_food(ants)
        self.diffuse_explore(ants)
        
        scent_field = (self.u_scent_field + 
                       5.0 * self.e_scent_field + 
                       self.a_scent_field)
        safety = self.safety_field
        
        # Movement
        # - combat logic
        for ant_loc in self.soldiers:
            if ant_loc.adj:
                scent_field[ant_loc] = (sum(scent_field[a] 
                                           for a in ant_loc.adj) / 
                                        len(ant_loc.adj))
                for target in sorted(ant_loc.moves, reverse=True,
                                    key=lambda a: (scent_field[a], a)):
                    if target.unoccupied_next and safety[target] == SAFE:
                        if target != self:
                            direction = ant_loc.direction(target)[0]
                            ants.issue_order((ant_loc, direction))
                            target.unoccupied_next = False
                            ant_loc.unoccupied_next = True
                            #log.debug("%r to %r", ant_loc, target)
                        break
        
        # - regular movement
        for ant_loc in self.normal_ants:
            for target in sorted(ant_loc.adj, reverse=True,
                                key=lambda a: (scent_field[a], a)):
                if target.unoccupied_next:
                    direction = ant_loc.direction(target)[0]
                    ants.issue_order((ant_loc, direction))
                    target.unoccupied_next = False
                    ant_loc.unoccupied_next = True
                    #log.debug("%r to %r", ant_loc, target)
                    break
        
        ants.log_time("BEFORE VISUALIZE")
        log.info("VISUALIZE: %s", Settings.VISUALIZE)
        if Settings.VISUALIZE and 127  < ants.cur_turn < 135:
            intensities = [[] for i in xrange(256)]
            for cell in ants.explored:
                txts = [ "u_scent: {0}".format(self.u_scent_field[cell]),
                         "e_scent: {0}".format(5.0*self.e_scent_field[cell]),
                         "a_scent: {0}".format(self.a_scent_field[cell]),
                         "scent: {0}".format(scent_field[cell])
                        ]
                txt = "; ".join(txts)
                cmd = "i {0} {1} {2}\n".format(cell.r, cell.c, txt)
                sys.stdout.write(cmd)
                
                intensity = max(0,min(255, int((scent_field[cell]+5)/100*256)))
                intensities[intensity].append(cell)                
                ##intensity = max(0,min(255, int((self.a_scent_field[cell])/50*256)))
                ##intensities[intensity].append(cell)
            for i in xrange(256):
                if intensities[i]:
                    color = (255-i, 0, i, 0.5)
                    color = map(str, color)
                    cmd1 = "v setFillColor {0}\n".format(" ".join(color))
                    sys.stdout.write(cmd1)
                    for cell in intensities[i]:
                        cmd2 = "v tile {0.r} {0.c}\n".format(cell)
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
        
        scent_field = MyBot.U_DECAY * self.u_scent_field
        diff_factor = MyBot.DIFF_FACTOR
        
        # clamped source setup
        clamps = []
        clamp_field = np.empty(ants.dimensions)
        for ant in ants.ant_set:
            clamp_field[ant] = -1.0
        clamps.extend(ants.ant_set)
        for food in ants.food_set:
            clamp_field[food] = 50.0
        clamps.extend(ants.food_set)
        #for hill_loc in ants.enemy_hills():
            #clamp_field[hill_loc] = 100.0
        #clamps.extend(ants.enemy_hills())
        clamp_index = zip(*clamps)
                
        # unblocked and diff fields
        unblocked_field = ants.passable_field # WATER blocks diffusion
        scent_field[~unblocked_field] = 0.0 # reset scent of water (unnecessary)
        
        unblocked_n = (np.roll(unblocked_field, 1, axis=0) & 
                       unblocked_field)
        unblocked_s = (np.roll(unblocked_field,-1, axis=0) &
                       unblocked_field)
        unblocked_w = (np.roll(unblocked_field, 1, axis=1) &
                       unblocked_field)
        unblocked_e = (np.roll(unblocked_field,-1, axis=1) &
                       unblocked_field)
        adj_field = (unblocked_n.astype(np.int8) + unblocked_s + 
                       unblocked_w + unblocked_e)
        diff_loss = 1 - (diff_factor * adj_field)
        diff_n = diff_factor * unblocked_n
        diff_s = diff_factor * unblocked_s
        diff_w = diff_factor * unblocked_w
        diff_e = diff_factor * unblocked_e

        dif_setup_time = 1000*(time.time()-dif_setup_begin)
        log.info("Diff setup: %s ms", dif_setup_time)
        
        dif_begin = time.time()
        for diffusion in xrange(MyBot.U_ITERATIONS):
            # source blocks
            scent_field[clamp_index] = clamp_field[clamp_index]
            # build new scents
            n = np.concatenate((scent_field[-1:], scent_field[:-1]), axis=0)
            s = np.concatenate((scent_field[1:], scent_field[:1]), axis=0)
            w = np.concatenate((scent_field[:,-1:], scent_field[:,:-1]), axis=1)
            e = np.concatenate((scent_field[:,1:], scent_field[:,:1]), axis=1)
            scent_field = (diff_loss * scent_field
                + (diff_n * n)
                + (diff_s * s)
                + (diff_w * w)
                + (diff_e * e))
        self.u_scent_field = scent_field # store scent field
        dif_time = 1000*(time.time()-dif_begin)
        log.info("Unified: %s diff iterations: %s ms", MyBot.U_ITERATIONS, dif_time)
        
    def diffuse_explore(self, ants):
        # setting up variables
        dif_setup_begin = time.time()
        
        diff_factor = MyBot.E_FACTOR
        invisible = ~ants.visible_field
        unexplored = ~ants.explored_field
        # clamped source setup
        clamp_field = 3.0*unexplored
        clamp_index = unexplored
        clamp_useless = (np.roll(clamp_index, 1, axis=0) &
                         np.roll(clamp_index,-1, axis=0) &
                         np.roll(clamp_index, 1, axis=1) &
                         np.roll(clamp_index,-1, axis=1))
        clamp_index = clamp_index - clamp_useless
        
        # re-initialize scent field with 1.0 at invisible squares
        scent_field = invisible.astype(np.float64) 
        
        # preset unblocked and diff fields
        # WATER or ant : do not receive diffusion
        unblocked_field = ants.passable_field & (~ ants.ant_field)
        scent_field[~unblocked_field] = 0.0 # reset ant/water scent
        
        unblocked_n = (np.roll(unblocked_field, 1, axis=0) & 
                       unblocked_field)
        unblocked_s = (np.roll(unblocked_field,-1, axis=0) &
                       unblocked_field)
        unblocked_w = (np.roll(unblocked_field, 1, axis=1) &
                       unblocked_field)
        unblocked_e = (np.roll(unblocked_field,-1, axis=1) &
                       unblocked_field)
        adj_field = (unblocked_n.astype(np.int8) + unblocked_s + 
                       unblocked_w + unblocked_e)
        diff_loss = 1 - (diff_factor * adj_field)
        diff_n = diff_factor * unblocked_n
        diff_s = diff_factor * unblocked_s
        diff_w = diff_factor * unblocked_w
        diff_e = diff_factor * unblocked_e
        
        dif_setup_time = 1000*(time.time()-dif_setup_begin)
        log.info("Diff setup: %s ms", dif_setup_time)
        
        dif_begin = time.time()
        log.debug(len(clamp_index.nonzero()[0]))
        for diffusion in xrange(MyBot.E_ITERATIONS):
            # source blocks
            scent_field[clamp_index] = 3.0 # should get from clamp_field
            # build new scents
            n = np.concatenate((scent_field[-1:], scent_field[:-1]), axis=0)
            s = np.concatenate((scent_field[1:], scent_field[:1]), axis=0)
            w = np.concatenate((scent_field[:,-1:], scent_field[:,:-1]), axis=1)
            e = np.concatenate((scent_field[:,1:], scent_field[:,:1]), axis=1)
            scent_field = (
                (diff_loss * scent_field)
                + (diff_n * n)
                + (diff_s * s)
                + (diff_w * w)
                + (diff_e * e))
        self.e_scent_field = scent_field # store scent field
        dif_time = 1000*(time.time()-dif_begin)
        log.info("Explore: %s diff iterations: %s ms", MyBot.E_ITERATIONS, dif_time)

    def diffuse_attack(self, ants):
        dif_setup_begin = time.time()
        
        my_hills = ants.my_hills()
        target_hills = ants.enemy_hills()
        enemies = ants.enemy_ants()
        
        if not self.enemy_seen:
            if len(target_hills) == 0 and len(enemies) == 0:
                return
            else:
                self.enemy_seen = True
        
        if my_hills:
            hilldist_begin = time.time()
            self.hilldist_calc(ants, limit=15)
            hilldist_time = 1000*(time.time()-hilldist_begin)
            log.debug("hilldist generation time: %s ms", hilldist_time)
            threat_value = {0:0.0, 1:90.0, 2:85.0, 3:80.0, 4:75.0, 
                            5:70.0, 6:64.0, 7:60.0, 8:50.0, 9:48.0, 
                            10:46.0, 11:44.0, 12:42.0, 13:40.0, 14:38.0,
                            13:36.0, 14:34.0, 15:32.0, INF:25.0}
            for dist in threat_value.keys():
                # multiple hills -> less value
                threat_value[dist] /= len(my_hills)
        
        if enemies:
            combat_safety_begin = time.time()
            self.gen_combat_safety(ants)
            combat_safety_time = 1000*(time.time()-combat_safety_begin)
            log.debug("Combat Safety generation: %s ms", combat_safety_time)
        
        # clamped source setup
        
        clamps = []
        clamp_field = np.empty(ants.dimensions)
        for hill_loc in target_hills:
            clamp_field[hill_loc] = 50.0
        clamps.extend(target_hills)
        clamp_index = zip(*clamps)
                
        # scaling setup
        coop_factor = MyBot.COOP_FACTOR
        coop_index = zip(*ants.my_ants())
                
        # unblocked and diff fields
        diff_factor = MyBot.A_FACTOR
        unblocked_field = ants.passable_field # WATER blocks diffusion
        unblocked_n = (np.roll(unblocked_field, 1, axis=0) & 
                       unblocked_field)
        unblocked_s = (np.roll(unblocked_field,-1, axis=0) &
                       unblocked_field)
        unblocked_w = (np.roll(unblocked_field, 1, axis=1) &
                       unblocked_field)
        unblocked_e = (np.roll(unblocked_field,-1, axis=1) &
                       unblocked_field)
        adj_field = (unblocked_n.astype(np.int8) + unblocked_s + 
                       unblocked_w + unblocked_e)
        diff_loss = 1 - (diff_factor * adj_field)
        diff_n = diff_factor * unblocked_n
        diff_s = diff_factor * unblocked_s
        diff_w = diff_factor * unblocked_w
        diff_e = diff_factor * unblocked_e

        # scent field initialize
        scent_field = MyBot.A_DECAY * self.a_scent_field
        scent_field[~unblocked_field] = 0.0 # reset scent of water (unnecessary)
        if my_hills:
            for ant in enemies:
                # affected by distance from my_hills
                scent_field[ant] += threat_value[ant.hilldist]

        dif_setup_time = 1000*(time.time()-dif_setup_begin)
        log.info("Diff setup: %s ms", dif_setup_time)
        
        # iteration
        dif_begin = time.time()
        for diffusion in xrange(MyBot.A_ITERATIONS):
            # source blocks
            scent_field[clamp_index] = clamp_field[clamp_index]
            # build new scents
            n = np.concatenate((scent_field[-1:], scent_field[:-1]), axis=0)
            s = np.concatenate((scent_field[1:], scent_field[:1]), axis=0)
            w = np.concatenate((scent_field[:,-1:], scent_field[:,:-1]), axis=1)
            e = np.concatenate((scent_field[:,1:], scent_field[:,:1]), axis=1)
            scent_field = (diff_loss * scent_field
                + (diff_n * n)
                + (diff_s * s)
                + (diff_w * w)
                + (diff_e * e))
            # scaling
            scent_field[coop_index] *= coop_factor
        dif_time = 1000*(time.time()-dif_begin)
        log.info("Attack: %s diff iterations: %s ms", MyBot.A_ITERATIONS, dif_time)
        
        # store scent field
        self.a_scent_field = scent_field

    def hilldist_calc(self, ants, limit=10):
        cur_dist = 0
        my_hills = ants.my_hills()
        # hill_num = len(my_hills)
        queue = list(my_hills)
        complete = set()
        for cell in ants.world_list:
            cell.hilldist = INF
        while queue and cur_dist <= limit:
            new_queue = []
            while queue:
                cell = queue.pop()
                if cell not in complete:
                    cell.hilldist = cur_dist
                    new_queue.extend(cell.adj)
                    complete.add(cell)
            queue = new_queue
            cur_dist += 1
        
    def gen_combat_safety(self, ants):
        player_ants = []
        positions = []
        for owner in xrange(10):
            player_ants.append([a for a in ants.ant_set if a.contents == owner])
        
        attack_stamp = ants.attack_stamp
        combat_stamp = self.approx_combat_stamp
        attack_field = self.attack_field
        weakness_field = self.weakness_field
        best_enemy = self.lowest_enemy_weakness
        safety_field = self.safety_field
        attack_field.fill(0)
        weakness_field.fill(0)
        best_enemy.fill(INF)
        safety_field.fill(SAFE)
        
        for owner in xrange(10):
            player_attack = attack_field[owner]
            for ant in player_ants[owner]:
                increment_stamp(player_attack, combat_stamp, ant)
        for owner in xrange(10):
            weakness_field[owner] = sum(attack_field[p] 
                                    for p in xrange(10) if p != owner)
            arena = set(loc for a in player_ants[owner]
                                for loc in a.moves
                                    if weakness_field[owner][loc] > 0)
            positions.append(arena)
        for enemy in xrange(1,10):
            for enemy_position in positions[enemy]:
                min_stamp(best_enemy, 
                          (attack_stamp, weakness_field[enemy][enemy_position]),
                          enemy_position)
        my_weakness = weakness_field[ME]
        safety_field[my_weakness > best_enemy] = DIE
        safety_field[my_weakness == best_enemy] = NEUTRAL
        
        self.soldiers = positions[ME].intersection(player_ants[ME])

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
