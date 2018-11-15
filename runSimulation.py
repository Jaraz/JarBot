# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

@author: jaycw_000
"""

import subprocess
import numpy as np

jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
argum = ' --replay-directory replays/ -vvv --turn-limit 400 --width 32 --height 32 "python MyBot.py" "python oldBot.py"'

newBotScores = []
oldBotScores = []

runSims = 10

for i in range(0, runSims):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
    
    results = res.communicate()[1]
    q1 = results.split("\n")
    q2 = results.split("[info] Player 0")[1].split()
    q3 = results.split("[info] Player 1")[1].split()
    
    newBotScores.append(int(q2[6]))
    oldBotScores.append(int(q3[6]))

newScores = np.array(newBotScores)
oldScores = np.array(oldBotScores)

scoreDiff = newScores - oldScores
print("Win % {}".format(sum(scoreDiff>0)/sum(scoreDiff>-1000000)))
print("Average Score {}".format(np.mean(scoreDiff)))
print("Median Score {}".format(np.median(scoreDiff)))
