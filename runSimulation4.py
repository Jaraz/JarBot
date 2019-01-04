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
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 32 --height 32 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'
argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --width 48 --height 48 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v50 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v50 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v50 & python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'

newBotScores = []
oldBotScores1 = []
oldBotScores2 = []
oldBotScores3 = []
seedArray = []

runSims = 24

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
    start_time = timeit.default_timer()
    pool = multiprocessing.Pool(processes = 6)
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
    totalScores = np.array([newScores,oldScores1,oldScores2,oldScores3])
    
    results = []
    second = []
    third = []
    fourth = []
    for i in range(runSims):
        if newScores[i] > oldScores1[i] and newScores[i] > oldScores2[i] and newScores[i] > oldScores3[i]:
            results.append(1)
            second.append(0)
            third.append(0)
            fourth.append(0)
        else:
            results.append(0)
            if (newScores[i] > oldScores1[i] and newScores[i] > oldScores2[i]) or (newScores[i] > oldScores2[i] and newScores[i] > oldScores3[i]) or (newScores[i] > oldScores1[i] and newScores[i] > oldScores3[i]):
                second.append(1)
                third.append(0)
                fourth.append(0)
            else:
                second.append(0)
                if newScores[i] > oldScores1[i] or newScores[i] > oldScores2[i] or newScores[i] > oldScores3[i]:
                    third.append(1)
                    fourth.append(0)
                else:
                    third.append(0)
                    fourth.append(1)
        
    print("Run {}".format(argum))
    print("Sims {}".format(runSims))
    print("Win %: {}".format(np.mean(results)))
    print("Second %: {}".format(np.mean(second)))
    print("Third %: {}".format(np.mean(third)))
    print("Fourth %: {}".format(np.mean(fourth)))
    print((timeit.default_timer() - start_time)/runSims)
