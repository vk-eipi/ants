#!/usr/bin/env python

# proj/location.py : Version 1.0.1
# - fixed bug in Location.direction

from collections import namedtuple
from math import sqrt
from logging import getLogger

from constants import *

log = getLogger(__name__)

LocTuple = namedtuple('L', 'r c')

def gen_offsets(radius2, dimensions):
    """
    Returns set of LocTuple objects representing offsets within
    math.sqrt(radius2) of Euclidean distance.
    Code adapted from aichallenge starter bot.
    """

    offsets = set()
    mx = int(sqrt(radius2))

    for d_row in range(-mx,mx+1):
        for d_col in range(-mx,mx+1):
            d = d_row**2 + d_col**2
            if d <= radius2:
                offsets.add(Offset(d_row, d_col, dimensions))

    return offsets

class Offset(LocTuple):
    """ Relative co-ordinates, as a named tuple (r,c)

    Co-ordinates are negative to take advantage of negative index
    behaviour of Python.

    """
    def __new__(cls, r, c, dimensions):
        rows, cols = dimensions
        new_r = (r % rows) - rows
        new_c = (c % cols) - cols
        return LocTuple.__new__(cls, new_r, new_c)
    def __add__(self, other):
        return Offset(self.r+other.r, self.c+other.c, dimensions)

class Location(LocTuple):


    def __new__(cls, r, c, game=None):
        return LocTuple.__new__(cls, r, c)

    def __init__(self, r, c, game=None):
        if game is not None:
            self.game = game
        else:
            self.game = DEFAULT_GAME

        self.AIM = {
        'n': Offset(-1, 0, game.dimensions),
        'e': Offset(0, 1, game.dimensions),
        's': Offset(1, 0, game.dimensions),
        'w': Offset(0, -1, game.dimensions)}
        self._attack_range = None
        self.vision_range = None
        self._gather_range = None

        self.visible = False # None?
        self.terrain = UNKNOWN
        # others can only exist on LAND
        self.contents = None # player -> ant, FOOD
        self.recent_deaths = []
        self.hill = None # player, consider showing razed
        #self.ghost = None # previous contents if invisible, maybe timed

    def __repr__(self):
        return "<Location ({0.r}, {0.c})>".format(self)
        # <Location ({0.r}, {0.c}), game={0.game}>
    def __str__(self):
        if self.hill is not None:
            assert self.terrain == LAND
            if self.contents is None:
                return PLAYER_HILL[self.hill]
            else:
                # ant on hill
                assert self.hill == self.contents
                return HILL_ANT[self.hill]
        elif self.contents is not None:
            # Food / Ant
            assert self.terrain == LAND
            return MAP_RENDER[self.contents]
        elif self.recent_deaths:
            assert self.terrain == LAND
            return MAP_OBJECT[DEAD]
        else:
            return str(self.terrain)

    def __add__(self, other):
        # other is presumably an Offset, so modulus is unnecessary
        try:
            return self.game.loc[self.r+other.r][self.c+other.c]
        except IndexError:
            new_r = (self.r + other.r) % self.game.rows
            new_c = (self.c + other.c) % self.game.cols
            return self.game.loc[new_r][new_c]

    def gen_ranges(self):
        if ( #self._attack_range is None or
             self.vision_range is None or
             self._gather_range is None
           ):
            
            #self._attack_range = self.gen_range(self.game.attack_offsets)
            self.vision_range = self.gen_range(self.game.vision_offsets)
            self._gather_range = self.gen_range(self.game.gather_offsets)
            #log.debug("gen_ranges of %r: vision %s", self, self.vision_range)

    def gen_vision_range(self):
        if self.vision_range is None:
            self.vision_range = self.gen_range(self.game.vision_offsets)

    def gen_range(self, offsets):
        """Generate set of locations within range from offsets."""
        return set( (self+offset) for offset in offsets ) 

    @property
    def attack_range(self):
        if self._attack_range is None:
            self._attack_range = self.gen_range(self.game.attack_offsets)
        return self._attack_range
        
    @property
    def gather_range(self):
        if self._gather_range is None:
            self._gather_range = self.gen_range(self.game.gather_offsets)
        return self._gather_range

    @property
    def ant(self):
        if self.contents is not FOOD:
            return self.contents
        else:
            return None

    @property
    def passable(self):
        """Return True if not water."""
        return self.terrain is not WATER # compare with == speed
        #return self.game.map[self.r][self.c] != WATER

    @property
    def unoccupied(self):
        """Return True if location is empty land or hill."""
        # may be just invisible
        return (self.terrain is LAND) and (self.contents is None)
        #return self.game.map[self.r][self.c] in (LAND, DEAD)

    def aim(self, direction): # previously called destination
        """Calculate new Location given the direction"""
        return (self + self.AIM[direction])
    
    def manhattan(self, target):
        """Calculate closest Manhattan distance to target."""
        d_col = min(abs(self.c - target.c), 
                    self.game.cols - abs(self.c - target.c))
        d_row = min(abs(self.r - target.r), 
                    self.game.rows - abs(self.r - target.r))
        return d_row + d_col

    def direction(self, target):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = self
        row2, col2 = target
        height2 = self.game.rows//2
        width2 = self.game.cols//2
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

class LocationSet(set):
    pass
LSet = LocationSet

#if __name__ == "__main__":
    #from ants import DEFAULT_GAME
    #print Offset(3,1,(20,20))
