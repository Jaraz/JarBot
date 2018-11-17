# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

Multiprocessor supported test 

@author: jaycw_000
"""

import subprocess
import numpy as np
import multiprocessing

jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 400 --width 32 --height 32 "python MyBot.py" "python oldBot.py"'
argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 430 --width 40 --height 40 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'

newBotScores = []
oldBotScores = []

runSims = 100

def runSim(i):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
    
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    
    return player1, player2

if __name__ == '__main__':
    pool = multiprocessing.Pool(processes = 8)
    for newScore, oldScore in pool.map(runSim, range(runSims)):
        newBotScores.append(newScore)
        oldBotScores.append(oldScore)
    #newBotScores, oldBotScores = map(runSim, range(runSims))
    
    newScores = np.array(newBotScores)
    oldScores = np.array(oldBotScores)
    
    scoreDiff = newScores - oldScores
    print("Win % {}".format(sum(scoreDiff>0)/sum(scoreDiff>-1000000)))
    print("Average Score {}".format(np.mean(scoreDiff)))
    print("Median Score {}".format(np.median(scoreDiff)))
