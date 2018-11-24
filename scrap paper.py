# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""


def get_wrapped(matrix, startX, startY, width):
    m, n = matrix.shape
    rows = []
    cols = []
    for i in range(-1,width*2):
        rows.append(startX-(width-i) % m)
        cols.append(startY-(width-i) % n)
    return matrix[rows][:, cols]

print(y)

print(get_wrapped(y, 5,2, 2))