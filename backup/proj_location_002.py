#!/usr/bin/env python
from collections import namedtuple
from math import sqrt

LocTuple = namedtuple('L', 'r c')

def gen_offsets(radius2, dimensions):
    '''
    Returns set of LocTuple objects representing offsets within 
    math.sqrt(radius2) of Euclidean distance.
    Code adapted from aichallenge starter bot.
    '''
    
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
    
    # vision_offsets, attack_offsets
    
    def __new__(cls, r, c, game=None):
        return LocTuple.__new__(cls, r, c)
        
    def __init__(self, r, c, game=None):
        if game is not None:
            self.game = game
        else:
            self.game = DEFAULT_GAME
        self.attack_range = None
        self.vision_range = None
        self.gather_range = None
        visible = False # None?

    def __repr__(self):
        return 'L({0.r}, {0.c})'.format(self)
        
    def __add__(self, other):
        # other is presumably an Offset, so modulus is unnecessary
        try:
            return self.game.loc[self.r+other.r][self.c+other.c]
        except IndexError:
            new_r = (self.r + other.r) % self.game.rows
            new_c = (self.c + other.c) % self.game.cols
            return self.game.loc[new_r][new_c]
            
    def gen_ranges(self):
        if ( self.attack_range is None or
             self.vision_range is None or
             self.gather_range is None
           ):
            self.attack_range = set()
            self.vision_range = set()
            self.gather_range = set()
            for dif in self.game.attack_offsets:
                self.attack_range.add(self+dif)
            for dif in self.game.vision_offsets:
                self.vision_range.add(self+dif)
            for dif in self.game.gather_offsets:
                self.gather_range.add(self+dif)

if __name__ == "__main__":
    from ants import DEFAULT_GAME
    print Offset(3,1,(20,20))
