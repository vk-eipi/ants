#!/usr/bin/env python
from collections import namedtuple

class Location(namedtuple('Location', 'r c')):
    def __repr__(self):
        return 'L({0.r}, {0.c})'.format(self)
