# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

import random

x = [5, 8, 10, 3]

rc = random.choice(x)
print(rc)
x.pop(x.index(rc))