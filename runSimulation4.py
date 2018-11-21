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
argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 430 --width 40 --height 40 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'

newBotScores = []
oldBotScores1 = []
oldBotScores2 = []
oldBotScores3 = []
seedArray = []

runSims = 100

def runSim(i):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
    
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    player3 = int(results.split("[info] Player 2")[1].split()[6])
    player4 = int(results.split("[info] Player 3")[1].split()[6])
    
    return player1, player2, player3, player4, seed

if __name__ == '__main__':
    pool = multiprocessing.Pool(processes = 4)
    for newScore, oldScore1, oldScore2, oldScore3, seed in pool.map(runSim, range(runSims)):
        newBotScores.append(newScore)
        oldBotScores1.append(oldScore1)
        oldBotScores2.append(oldScore2)
        oldBotScores3.append(oldScore3)
        seedArray.append(seed)
    #newBotScores, oldBotScores = map(runSim, range(runSims))
    
    newScores = np.array(newBotScores)
    oldScores1 = np.array(oldBotScores1)
    oldScores2 = np.array(oldBotScores2)
    oldScores3 = np.array(oldBotScores3)
    
    results = []
    for i in range(runSims):
        if newScores[i] > oldScores1[i] and newScores[i] > oldScores2[i] and newScores[i] > oldScores3[i]:
            results.append(1)
        else:
            results.append(0)
        
    print("Win %: {}".format(np.mean(results)))
        
        
    