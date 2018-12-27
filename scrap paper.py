# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import numpy as np
from scipy import optimize
from scipy.spatial import distance
'''
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


testList = np.asarray([a,b,c])
minMatrix = testList.min(0)
'''

a = np.arange(25).reshape(5,5)
b = np.arange(5)
c = np.arange(6).reshape(2,3)

print(a.shape)
print(b.shape)
print(c.shape)

t1 = np.arange(64*8*8).reshape(64,8,8)
t2 = np.arange(8*8).reshape(8,8)
res1 = np.einsum('ijk,jk',t1,t2)
print(res1.shape)

t1 = np.arange(64*8*8).reshape(8,8,8,8)
t2 = np.arange(8*8).reshape(8,8)
res1 = np.einsum('ijkl,kl',t1,t2)
print(res1.shape)


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