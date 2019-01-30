# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 06:05:59 2018

Multiprocessor supported test 

@author: jaycw_000
"""

import timeit
import subprocess

jarBotFolder = "C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\halite.exe"
argum = ' --replay-directory replays/ -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 --seed 1548065954 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 40 --height 40 --seed 1548064240 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 56 --height 56 --seed 1548029511 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 64 --height 64 --seed 1548018889 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 56 --height 56 --seed 1548036337 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 32 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v74 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v74 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v74 & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 32 "python MyBot.py" "python MyBot.py" "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 56 --height 56 --seed 1547845080 "python MyBot.py" "python MyBot.py" "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 24 --height 24 "python MyBot.py" "python MyBot.py" "python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 56 --height 56 --seed 1547845080 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75 & python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 40 --height 40 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 --seed 1548018735 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 48 --height 48 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75 & python MyBot.py" "python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 32 --height 32 --seed 1547934087 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v75\\ & python MyBot.py"'
#argum = ' --replay-directory replays/ -vvv --width 64 --height 64 --seed 1548082979 "python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "cd C:\\Users\\jaycw_000\\Documents\\GitHub\\JarBot\\v76 & python MyBot.py" "python MyBot.py"'

start_time = timeit.default_timer()

rng = 1

for i in range(rng):
    res = subprocess.Popen(jarBotFolder + argum, shell = True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,bufsize=1, universal_newlines=True)
        
    results = res.communicate()[1]
    lineSplit = results.split("\n")
    seed = lineSplit[0].split()[4]
    player1 = int(results.split("[info] Player 0")[1].split()[6])
    player2 = int(results.split("[info] Player 1")[1].split()[6])
    #player3 = int(results.split("[info] Player 2")[1].split()[6])
    #player4 = int(results.split("[info] Player 3")[1].split()[6])
    
    if player1 == 0 or player2 ==0:
        break
    
print((timeit.default_timer() - start_time)/rng)
#print(lineSplit)
print(player1)
print(player2)
#print(player3)
#print(player4)

