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
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "python myBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 24 --height 24 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v38\\ & python MyBot.py"'
argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v35 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v28 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" '
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 400 --width 32 --height 32 "python MyBot.py" "python oldBot.py" '
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 64 --height 64 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 40 --height 40 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v23 & python MyBot.py"'

# low halite seed
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 32 --height 32 --seed 1542549748 "python MyBot.py" "python oldBot.py" '

newBotScores = []
oldBotScores = []
seedArray = []
lineSplitArray = []

runSims = 128
def runSim(i):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
    
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    
    return player1, player2, seed, lineSplit

if __name__ == '__main__':
    start_time = timeit.default_timer()
    pool = multiprocessing.Pool(processes = 6)
    totalWin = 0
    for newScore, oldScore, seed, linesplt in pool.map(runSim, range(runSims)):
        newBotScores.append(newScore)
        oldBotScores.append(oldScore)
        seedArray.append(seed)
        lineSplitArray.append(linesplt)
    #newBotScores, oldBotScores = map(runSim, range(runSims))
    
    newScores = np.array(newBotScores)
    oldScores = np.array(oldBotScores)
    seedTracker = np.array(seedArray)
    
    scoreDiff = newScores - oldScores
    print("Run {}".format(argum))
    print("Sims {}".format(runSims))
    print("Win % {}".format(sum(scoreDiff>0)/sum(scoreDiff>-1000000)))
    print("Average Score {}".format(np.mean(scoreDiff)))
    print("Median Score {}".format(np.median(scoreDiff)))
    print("Stdev Score {}".format(np.std(scoreDiff)))
    print("Minimum Score {}".format(np.min(newScores)))
    print("Bad seeds {}".format(seedTracker[newScores<1]))
    print((timeit.default_timer() - start_time)/runSims)
