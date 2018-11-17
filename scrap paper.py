# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import multiprocessing

from os import getpid

def worker(procnum):
    print("I am number {} in process {}".format(procnum, getpid()))
    return getpid()

if __name__ == '__main__':
    pool = multiprocessing.Pool(processes = 4)
    print(pool.map(worker, range(1000)))
