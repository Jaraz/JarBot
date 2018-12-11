# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

Multiprocessor supported test 

@author: jaycw_000
"""

import timeit
import subprocess

jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
argum = ' --replay-directory replays/ -vvv --width 64 --height 64 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v30 & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 325 "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v30 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v30 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v30 & python MyBot.py"'

start_time = timeit.default_timer()

rng = 1

for i in range(rng):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
        
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    
    if player1 == 0 or player2 ==0:
        break
    
print((timeit.default_timer() - start_time)/rng)
#print(lineSplit)
print(player1)
print(player2)


