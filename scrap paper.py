# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import numpy as np
from scipy import optimize
from scipy.spatial import distance

def neighbors(node):
    moves = [[1,0],[0,1],[-1,0],[0,-1]]
    results = []
    for move in moves:
        results.append([move[0] + node[0],move[1] + node[1]])
    return results

nodes = []
for i in range(8):
    for j in range(8):
        nodes.append([i,j])