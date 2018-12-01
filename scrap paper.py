# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import numpy as np
from scipy import optimize
from scipy.spatial import distance

a = np.array([[4, 1, 1, 2, 0, 0, 4],
              [3, 4, 3, 1, 4, 0, 4],
              [1, 4, 3, 1, 0, 0, 0],
              [0, 0, 0, 0, 0, 0, 0],
              [0, 4, 4, 0, 4, 0, 3]])

test = a[:, ~np.all(a == 0, axis = 0)]
print(test)