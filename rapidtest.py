#!/usr/bin/env python
import time

import numpy as np

from proj.location import Location
import proj.numLocation as location
from ants import Ants

rows = 190
cols = 200

"""
a = np.arange(12).reshape(3,4)
field = np.array([[3,21,5,0],[0,0,1,3],[7,2,0,9]])
print a
print field
print field.nonzero()
a[field.nonzero()] = field[field.nonzero()]
print a
field[0,0] += 99
print a
print field


a = np.array([[True, False], [True, False]])
b = np.array([[True, True], [False, False]])
print a
print b
print a|b
print a.shape
print ~a
print (~a) + 2.5

a = np.arange(12).reshape(3,4)
a[[(1,2),(0,3)]] *=2
print 'a', a
b = np.roll(a,1,axis=1)
print 'b', b

c = np.concatenate((a,b))
print 'c', c, c.shape

s = location.gen_stamp(5)
print s.astype(np.int8)
base_a = np.zeros((12,12), dtype=bool)
base_b = np.zeros((200,190), dtype=bool)
def original():
    stamp = location.or_stamp
    a = np.zeros((12,12), dtype=bool)
    a = location.or_stamp(a, s, (3,3))
    a = location.or_stamp(a, s, (8,6))
    a = location.or_stamp(a, s, (0,0))
    a = location.or_stamp(a, s, (4,7))
    a = location.or_stamp(a, s, (6,10))
    b = np.zeros((200,190), dtype=bool)
    b = location.or_stamp(b, s, (24,0))
    b = location.or_stamp(b, s, (48,189))
    b = location.or_stamp(b, s, (1, 72))
    b = location.or_stamp(b, s, (198, 100))
    #return (a,b)
def testrun(stamp):
    a = base_a
    b = base_b
    stamp(a, s, (3,3))
    stamp(a, s, (8,6))
    stamp(a, s, (0,0))
    stamp(a, s, (4,7))
    stamp(a, s, (6,10))
    stamp(b, s, (24,0))
    stamp(b, s, (48,189))
    stamp(b, s, (1, 72))
    stamp(b, s, (198, 100))
    #return a,b
#a1, b1 = testrun(location.or_stamp)
#a,b = testrun(location.or_stamp_mod)
#print np.array_equal(a, a1)
#print np.array_equal(b, b1)
import timeit
t = timeit.Timer('testrun(location.or_stamp)', 'import proj.numLocation as location; from __main__ import testrun;')
print t.repeat(3,1000)
##t = timeit.Timer('testrun(location.or_stamp_mod)', 'import proj.numLocation as location; from __main__ import testrun;')
##print t.repeat(3,1000)


g = Ants()
t = time.time()
locs = [[Location(r, c,g) for c in xrange(200)] for r in xrange(200)]
#print time.time()-t
#for r in xrange(200):
    #for c in xrange(200):
        #locs[r][c] = 
    #print r, time.time()-t
raw_input(time.time()-t)


class Ant(object):
    def __init__(self):
        Ant.attackradius2 = 5
        Ant.attack_stamp = location.gen_stamp(Ant.attackradius2)
from math import sqrt
from proj.numLocation import or_stamp
ants = Ant()
radius = int(sqrt(ants.attackradius2)) + 1 # 1 longer
approx_side = 2 * radius + 1
approx_stamp = np.zeros((approx_side, approx_side), dtype=bool)
print ants.attack_stamp.astype(int)
print approx_stamp.astype(int)
or_stamp(approx_stamp, ants.attack_stamp, (radius, radius))
or_stamp(approx_stamp, ants.attack_stamp, (radius, radius+1))
or_stamp(approx_stamp, ants.attack_stamp, (radius, radius-1))
or_stamp(approx_stamp, ants.attack_stamp, (radius+1, radius))
or_stamp(approx_stamp, ants.attack_stamp, (radius-1, radius))
print approx_stamp.astype(int)
"""
