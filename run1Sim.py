# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

Multiprocessor supported test 

@author: jaycw_000
"""

import timeit
import subprocess

jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
#argum = ' --replay-directory replays/ -vvv --width 40 --height 40 --seed 1542910796 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 8 --height 8 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 64 --height 64 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v22 & python MyBot.py"'
argum = ' --replay-directory replays/ -vvv --width 64 --height 64 --seed 1543795037 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v22 & python MyBot.py"'
argum = ' --replay-directory replays/ -vvv --width 64 --height 64 --seed 1543795037 "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 32 "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 64 --height 64 "python MyBot.py" "python oldBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 64 --height 64 --seed 1543749785 "python MyBot.py" "python myBot.py" '
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ --no-logs --no-replay  -vvv --turn-limit 500 --width 64 --height 64 "python MyBot.py" "python oldBot.py" "python oldBot.py" "python oldBot.py"'

start_time = timeit.default_timer()

rng = 1

for i in range(rng):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
        
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    
    if player1 - player2 < -20000:
        break
    
print((timeit.default_timer() - start_time)/rng)

