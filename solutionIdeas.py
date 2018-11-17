# -*- coding: utf-8 -*-
"""
Created on Fri Nov 16 18:35:03 2018

@author: jaycw_000
"""

## Question, what is the optimal number of ships to build?
## Ideas: What do you earn per ship per turn, how do you estimate this?
## Ideas: 
##
import matplotlib.pyplot as plt
plt.rcParams["figure.dpi"] = 300


turns = 400
buildFlag = 300

shipYieldPerTurn = 7
totalHalite = 158000
shipCost = 1000
halite = []
halite.append(5000)
ships = []
ships.append(0)

for i in range(turns):
    halite.append(halite[-1] + ships[-1] * shipYieldPerTurn)
    if halite[-1] > totalHalite - ships[-1] * 1000:
        halite[-1] = totalHalite - ships[-1] * 1000
    
    if i < buildFlag:
        ships.append(ships[-1] + int(halite[-1]/shipCost))
        halite[-1] -= int(halite[-1]/shipCost) * shipCost
    

plt.plot(halite)
