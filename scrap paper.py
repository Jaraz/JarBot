# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import numpy as np
from scipy import optimize
from scipy.spatial import distance

x = np.array([[900,100,300,55],[300,200,50,50],[30,10,400,40],[10,10,20,400]])
ships = np.array([[0,1,0,0],[0,0,0,3],[2,0,0,0],[4,0,0,0]])
x > 100


row_ind, col_ind = optimize.linear_sum_assignment(x)
print(row_ind)
print(col_ind)

print(ships)
shipCoord = np.array([[0,1],[1,3],[2,0],[3,0]])
test = np.zeros([16,2])
for i in range(4):
    for j in range(4)
        test[i*4+j,j] = 

distance.cdist(coords, coords, 'cityblock')
