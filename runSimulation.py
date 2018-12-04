# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

Multiprocessor supported test 

@author: jaycw_000
"""

import subprocess
import numpy as np
import multiprocessing
import timeit


jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv  "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 8 --height 8 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 48 --height 48 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 --seed 1543318434 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 56 --height 56 "python MyBot.py" "python oldBot.py"'
argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v22 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 64 --height 64 --seed 1543794944 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v22 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" '
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 400 --width 32 --height 32 "python MyBot.py" "python oldBot.py" '
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'

# low halite seed
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 32 --height 32 --seed 1542549748 "python MyBot.py" "python oldBot.py" '

newBotScores = []
oldBotScores = []
seedArray = []

runSims = 100
def runSim(i):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
    
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    
    return player1, player2, seed

if __name__ == '__main__':
    start_time = timeit.default_timer()
    pool = multiprocessing.Pool(processes = 4)
    for newScore, oldScore, seed in pool.map(runSim, range(runSims)):
        newBotScores.append(newScore)
        oldBotScores.append(oldScore)
        seedArray.append(seed)
    #newBotScores, oldBotScores = map(runSim, range(runSims))
    
    newScores = np.array(newBotScores)
    oldScores = np.array(oldBotScores)
    seedTracker = np.array(seedArray)
    
    scoreDiff = newScores - oldScores
    print("Win % {}".format(sum(scoreDiff>0)/sum(scoreDiff>-1000000)))
    print("Average Score {}".format(np.mean(scoreDiff)))
    print("Median Score {}".format(np.median(scoreDiff)))
    print("Minimum Score {}".format(np.min(newScores)))
    print("Bad seeds {}".format(seedTracker[newScores<1]))
    print((timeit.default_timer() - start_time)/runSims)