# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import numpy as np
from scipy import optimize
from scipy.spatial import distance

a = np.array([[4, 8, 1, 2, 0, 0, 1],
              [3, 4, 3, 1, 4, 0, 4],
              [1, 4, 3, 1, 0, 0, 0],
              [0, 0, 0, 0, 0, 0, 0],
              [0, 4, 4, 0, 4, 0, 3]])

b = np.array([[2, 7, 1, 5, 0, 0, 4],
              [3, 4, 3, 1, 4, 0, 4],
              [1, 4, 3, 1, 0, 0, 0],
              [0, 0, 0, 0, 0, 0, 0],
              [0, 4, 4, 0, 4, 0, 3]])

c = np.array([[7, 1, 3, 2, 0, 0, 3],
              [3, 4, 3, 1, 4, 0, 4],
              [1, 4, 3, 1, 0, 0, 0],
              [0, 0, 0, 0, 0, 0, 0],
              [0, 4, 4, 0, 4, 0, 3]])




'''
q = np.array([2,4,0,5,8,0,5])
b = np.random.randint(10,size=[5,7])
b[a==0]=0
print(b)
q = q[q!=0]
print(q)
meanRes = a.mean(axis=0)
test = a[:,meanRes>1]
print(test)
'''