#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

import random
#import queue

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position
import timeit
import numpy as np

# This library allows you to generate random numbers.
# import random
# helper variables
GLOBAL_DEPO = 0
START_TURN_DEPO = 0
SUICIDE_TURN_FLAG = 6
GLOBAL_DEPO_BUILD_OK = True
SAVE_UP_FOR_DEPO = False
DEPO_ONE_SHIP_AT_A_TIME = False
DEPO_BUILD_THIS_TURN = False
WAIT_TO_BUILD_DEPOT = 15
FIRST_DEPO_BUILT = False
BUILD_DEPO_TIMER = 0


'''
To add later
fix when ships get stuck
Ship construction should be a function of game length
cargo hold orders should shorten at the start and lengthen as the game goes on
'''

'''
TODO
1) improve depo code to move a bit further after it sees an opportunity
2) need to scan area around the home base, if low halite we need a depo early on 
3) Need a smart way to do 4player ship construction
4) Ways to optimize player scores, perhaps combine attacking to algorithm?
5) Want to incorporate percent mined into algorithm
6) 

fix depo building built next to enemy one
fix big maps when u don't trigger a depo by turn 150ish (just force build one at 200)
build depos in a bigger ZoC in 2p

7) for 4p when enemy is on a lot of halite (+bonus) don't expect him to move and hit u
8) when enemy is x units away from big halite zone, reduce dist cost so we move towards it
8) ???
8) Profit?
'''


# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
#logging.basicConfig(level=logging.NOTSET)

# ship construction should be a function of scores, ships, and halite
# assume first number in list is player one
def shipConstructionLogic(playerScores, playerShips, haliteLeft, turnsLeft):
    # don't build ships after this
    turnStopBuilding = 90
    buildShip = False
    playerMultiple = len(playerScores)/2
    shipLead = 10
    shipCompare = playerShips[1]
    totalShips = np.sum(playerShips)
    
    stopFlag = 0.3
    if game_map.width > 50:
        stopFlag = 0.25
    
    if game_map.width <= 40:
        shipLead = 5
    elif game_map.width <= 48:
        shipLead = 8
    
    if totalShips < 1:
        totalShips = 1
    nextTen = 10 * (game_map.miningMA[game_map.turnNumber-1] * 2 - game_map.miningMA[game_map.turnNumber-10])/totalShips
    logging.info("next 10 turns {} one {} two {} flag {}".format(nextTen, game_map.miningMA[game_map.turnNumber-1], game_map.miningMA[game_map.turnNumber-10],nextTen/10 * turnsLeft))
    
    if len(playerScores) == 4:
        shipCompare = np.mean(playerShips[1:3])
        playerMultiple = 1.25
        if game_map.width > 55:
            stopFlag = 0.225
        
    if len(playerScores)==4:
        shipLead += -2
        if nextTen/10 * turnsLeft < 1000*playerMultiple or \
        turnsLeft<turnStopBuilding or \
        playerShips[0] - shipCompare > shipLead or \
        game_map.freeHalite < stopFlag:
            buildShip = False    
        else:
            buildShip = True
    else:
        if (nextTen/10 * turnsLeft > 1000 and turnsLeft > turnStopBuilding):
            buildShip = True
        if turnsLeft < 45 or playerShips[0] - shipCompare > shipLead:
            buildShip = False
    return buildShip

def giveShipOrders(ship, currentOrders, collectingStop):
    # build ship status
    global GLOBAL_DEPO
    global GLOBAL_DEPO_BUILD_OK
    global SAVE_UP_FOR_DEPO
    global DEPO_ONE_SHIP_AT_A_TIME
    global FIRST_DEPO_BUILT
    global WAIT_TO_BUILD_DEPOT
    global ATTACK_CURRENT_HALITE
    global ATTACK_TARGET_HALITE
    global BUILD_DEPO_TIMER
    global DEPO_MIN_SHIPS
    
    moveFlag = False
    
    turns_left = (constants.MAX_TURNS - game.turn_number)
    #logging.info("Ship {} was {}".format(ship, currentOrders))

    # enemy locations, look if they are next to you
    runFlag = False
    attackFlag = False
    
    #logging.info("Enemy ship halite \n {}".format(game_map.enemyShipHalite))
    
    # check to run
    shipX = ship.position.x
    shipY = ship.position.y
    
    dist = game_map.dist1[shipX][shipY]
    enemyInSight = dist * game_map.shipFlag
    #logging.info("ship {} dist {} enemy in sight {}".format(ship.id, dist, enemyInSight))
    
    # is an enemy in zone
    if np.sum(enemyInSight)>0:
        enemyHalite = game_map.enemyShipHalite * dist
        enemyMA = np.ma.masked_equal(enemyHalite, 0, copy=False)
        if len(game.players)==2 or len(game.players)==4:
            fightHalite = dist * (game_map.enemyShipHalite + game_map.shipFlag * game_map.npMap * (0.25 + 0.5 * game_map.negInspirationBonus))
            enemyLoc = np.unravel_index(fightHalite.argmax(),fightHalite.shape)
        else:
            fightHalite = dist * 1
        logging.info("ship {} halite {} max enemy {} enemyMa {} friendly {} enemy {}".format(ship.id, ship.halite_amount, np.max(fightHalite), enemyMA.min(), game_map.friendlyShipCount[shipY,shipX], game_map.enemyShipCount[shipY,shipX]))        
        # check if we should run
        if enemyMA.min() < 300 and \
           ship.halite_amount > 700 and \
           len(game.players) == 2:
            logging.info("ship {} runs!!!".format(ship.id))
            runFlag = True
        elif enemyMA.min() < 500 and \
             ship.halite_amount>900 and \
             len(game.players) == 4 and \
             turns_left < 50:
            runFlag = True
        elif len(game.players) == 2 and \
             (ship.halite_amount + game_map.npMap[shipY,shipX] *(0.25 + 0.5 * game_map.inspirationBonus[shipY,shipX]))>500 and \
             game_map.friendlyShipCount[shipY,shipX] <= game_map.enemyShipCount[shipY,shipX] and \
             enemyMA.min() < 500:
            logging.info("ship {} needs to move!".format(ship.id))
            moveFlag = np.unravel_index(enemyMA.argmin(),enemyMA.shape)
        # check if we should fight
        elif np.max(fightHalite) - 100 > ship.halite_amount and \
             len(game.players)==2 and \
             game_map.friendlyShipCount[enemyLoc] > game_map.enemyShipCount[enemyLoc]:
            #logging.info("ship {} attacks!!!".format(ship.id))
            attackFlag = True
        elif np.max(fightHalite) - 500 > ship.halite_amount and \
             len(game.players)==4 and \
             game_map.friendlyShipCount[enemyLoc] > game_map.enemyShipCount[enemyLoc] + 2 and \
             turns_left < 150:
             #game_map.friendlyShipCount[shipY,shipX] > game_map.enemyShipCount[shipY,shipX] + 2:
            logging.info("ship {} attacks!!!".format(ship.id))
            attackFlag = True
            #logging.info("ship {} attacks friendly \n {} enemy \n {}".format(ship.id,game_map.friendlyShipCount,game_map.enemyShipCount))
        elif np.max(fightHalite) > 750 and \
             ship.halite_amount < 200 and \
             game_map.friendlyShipCount[shipY,shipX] == game_map.enemyShipCount[shipY,shipX] and \
             len(game.players)==2:
            attackFlag = True                 
        
    okToBuildDepo = False
    # we wait if we just built a depo
    if FIRST_DEPO_BUILT == False:
        okToBuildDepo = True
    elif WAIT_TO_BUILD_DEPOT < 1:
        okToBuildDepo = True

    #logging.info("ship {} in max zone {}".format(ship.id, game_map.dropCalc.inMaxZone(ship.position)))
    #logging.info("ship {} friendly count {}".format(ship.id, game_map.returnFriendlyCount(ship.position, 7)))

    status = None
    if currentOrders is None: #new ship
        status = "exploring"
    elif currentOrders == 'build depo' and BUILD_DEPO_TIMER < 45:
        status = 'build depo'
        BUILD_DEPO_TIMER += 1
    elif GLOBAL_DEPO < MAX_DEPO and \
         min(GLOBAL_DEPO+1,2) * 11 < game.me.get_ship_count() and \
         game.turn_number > shipBuildingTurns and \
         game_map.dropCalc.inMaxZone(ship.position) and \
         min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= DEPO_DISTANCE-6 and \
         GLOBAL_DEPO_BUILD_OK == True and \
         ship.position not in game.return_all_drop_locations() and \
         DEPO_ONE_SHIP_AT_A_TIME == False and\
         okToBuildDepo == True and \
         turns_left > 75 and \
         game_map.returnFriendlyCount(ship.position, 7) > DEPO_MIN_SHIPS:
        status = 'build depo'
        SAVE_UP_FOR_DEPO = True
        DEPO_ONE_SHIP_AT_A_TIME = True
    elif ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
        status = 'mining'
    elif min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= turns_left - SUICIDE_TURN_FLAG:
        status = "returnSuicide"
    elif currentOrders == "returning":
        status = "returning"
        if ship.position == me.shipyard.position or ship.position in me.get_dropoff_locations():
            status = "exploring"
    elif ship.halite_amount >= returnHaliteFlag  or runFlag == True:
        status = "returning"
    #elif ship.halite_amount < game_map[ship.position].halite_amount * 0.1 or game_map[ship.position].halite_amount > collectingStop:
    #    status = 'mining'
    #create attack squad near end
    #elif (ship.halite_amount < 50 and game_map.averageHalite < 50 and game_map.width < 48 and len(game.players)==2) or attackFlag == True:
    elif attackFlag == True:
        status = 'attack'
    elif currentOrders == "exploring":
        status = "exploring"
    else:
        status = 'exploring'
    #logging.info("ship {} status is {}".format(ship.id, status))
    return status, moveFlag

#resolve movement function
def resolveMovement(ships, destinations, status, attackTargets, previousDestination):
    global GLOBAL_DEPO
    global GLOBAL_DEPO_BUILD_OK
    global SAVE_UP_FOR_DEPO
    global DEPO_ONE_SHIP_AT_A_TIME
    global DEPO_BUILD_THIS_TURN
    global FIRST_DEPO_BUILT
    global SAVE_UP_FOR_DEPO
    global WAIT_TO_BUILD_DEPOT
    global DEPO_DISTANCE
    global DEPO_DISTANCE_DELTA
    global BUILD_DEPO_TIMER
    
    nextTurnPosition = {}
    orderList = {}
    finalOrder = []

    ###########################
    ### Movement resolution ###
    ###########################
    dropoffs = me.get_all_drop_locations()
    
    enemyLoc = []
    for enemy in game.enemyShips:
        #enemyLoc.append(enemy.position)
        if enemy.halite_amount !=1000 and len(game.players)==2:
            enemyLoc.append(enemy.position)
        elif len(game.players)==4:
            enemyLoc.append(enemy.position)
        else:
            logging.info("1k found")
    #logging.info("enemyLoc {} and adj {}".format(game.enemyShips, game.adjEnemyShips))    
    if len(game.players) > 3:
        enemyLoc.extend(game.adjEnemyShips)
    
    
    #logging.info("ships {} *** dest {} *** dropoffs {}".format(ships, destinations, dropoffs))
    orderList = game_map.findOptimalMoves(ships, destinations, dropoffs, status, enemyLoc)

    # issue final order
    for ship in ships:

        ### BUILD DEPO ###
        if status[ship.id] == 'build depo':
            # if we have enough halite
            if me.halite_amount >= ((GLOBAL_DEPO + 1 - START_TURN_DEPO) * constants.DROPOFF_COST - ship.halite_amount) and \
                min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= DEPO_DISTANCE and \
                game_map.dropCalc.inMaxZone(ship.position) and \
                ship.position not in game.return_all_drop_locations():
                #logging.info("ship {} w/ {} building a depo".format(ship.id, ship.halite_amount))
                finalOrder.append(ship.make_dropoff())        
                GLOBAL_DEPO += 1
                GLOBAL_DEPO_BUILD_OK = False
                SAVE_UP_FOR_DEPO = False
                DEPO_ONE_SHIP_AT_A_TIME = False
                DEPO_BUILD_THIS_TURN = True
                WAIT_TO_BUILD_DEPOT = 25
                BUILD_DEPO_TIMER = 0
                if FIRST_DEPO_BUILT == False:
                    DEPO_DISTANCE += DEPO_DISTANCE_DELTA
                    FIRST_DEPO_BUILT = True
            else:   
                #logging.info("depo ship {} order {}".format(ship.id, orderList[ship.id]))
                finalOrder.append(ship.move(orderList[ship.id]))

        else:
            finalOrder.append(ship.move(orderList[ship.id]))
        nextTurnPosition[ship.id] = game_map.normalize(ship.position.directional_offset(orderList[ship.id]))
        
    #logging.info("order list {}, next turn pos{}".format(orderList, nextTurnPosition))
    return finalOrder, nextTurnPosition


""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

################
### Settings ###
################
shipBuildingTurns = 90 # how many turns to build ships
collectingStop    = 80 # Ignore halite less than this
returnHaliteFlag  = 950 # halite to return to base
DEPO_DISTANCE_DELTA = 0
DEPO_PERCENTILE = 75
DEPO_MIN_SHIPS = 4

#DEPOs
MAX_DEPO          = 3
DEPO_HALITE_LOOK  = 5
DEPO_HALITE       = 100
DEPO_DISTANCE     = 12
DEPO_MIN_HALITE   = 400

#default is 1, 3, 7
RADAR_DEFAULT = 1
RADAR_WIDE = RADAR_DEFAULT + 2
RADAR_MAX = RADAR_DEFAULT + 6

# attack thresholds
ATTACK_CURRENT_HALITE = 250
ATTACK_TARGET_HALITE = 250

#logging.disable(logging.CRITICAL)
logging.info("map size: {}, max turns: {}".format(game.game_map.width, constants.MAX_TURNS))
nearAvg, nearStd = game.game_map.get_near_stats(game.me.shipyard.position, 5)

### Logic for ship building turns ###
if game.game_map.width > 60:
    shipBuildingTurns = 80
    RADAR_MAX = 12
    DEPO_HALITE += 0
    DEPO_DISTANCE  = 12
    DEPO_DISTANCE_DELTA = 5
    SUICIDE_TURN_FLAG = 7
    MAX_DEPO = 7
    collectingStop = 1
    DEPO_HALITE_LOOK  = 3
    DEPO_HALITE = 140
    DEPO_MIN_HALITE = 290
    DEPO_PERCENTILE = 66
    #game.game_map.updateSmoothSize(5)
    DEPO_MIN_SHIPS = 2
elif game.game_map.width > 50:
    shipBuildingTurns = 80
    DEPO_DISTANCE  = 12
    DEPO_DISTANCE_DELTA = 4
    MAX_DEPO = 4
    collectingStop = 1
    DEPO_MIN_HALITE  = 290
    DEPO_PERCENTILE = 66
    #game.game_map.updateSmoothSize(5)
elif game.game_map.width > 41:
    shipBuildingTurns = 80
    collectingStop= 1
    DEPO_DISTANCE  = 15
    MAX_DEPO = 3
    if game.game_map.totalHalite < 200000:
        MAX_DEPO = 1
    DEPO_DISTANCE  = 11
    DEPO_DISTANCE_DELTA = 6
    DEPO_MIN_HALITE   = 350
    DEPO_MIN_SHIPS = 3
elif game.game_map.width > 39:
    shipBuildingTurns = 80
    collectingStop= 1
    DEPO_HALITE = 140
    MAX_DEPO = 2
    DEPO_HALITE_LOOK  = 3
    if game.game_map.totalHalite < 200000:
        MAX_DEPO = 1
    DEPO_DISTANCE  = 11
    DEPO_DISTANCE_DELTA = 6
    DEPO_MIN_HALITE   = 375
elif game.game_map.width < 40 and game.game_map.totalHalite < 200000:
    shipBuildingTurns = 110
    collectingStop = 1
    MAX_DEPO = 1    
    DEPO_DISTANCE  = 12
elif game.game_map.width < 40 and game.game_map.totalHalite < 270000:
    shipBuildingTurns = 90
    collectingStop = 1
    MAX_DEPO = 2
    DEPO_DISTANCE  = 12
elif game.game_map.width < 40 and game.game_map.averageHalite > 250:
    collectingStop = 1
    shipBuildingTurns = 90
else:
    shipBuildingTurns = 90
    collectingStop= 1
    
if game.game_map.width < 40:
    DEPO_DISTANCE  = 9
    DEPO_DISTANCE_DELTA = 3
    DEPO_MIN_HALITE   = 350
    DEPO_MIN_SHIPS = 1

if game.game_map.width < 55:
    DEPO_MIN_SHIPS = 0
    
#elif game.game_map.width < 40 and totalHalite > 300000:
#    shipBuildingTurns = 200
#    collectingStop = 50

if game.game_map.averageHalite > 180:
    logging.info("Build more ships!")
    #shipBuildingTurns += 25
    #collectingStop += 25

#if game.game_map.averageHalite > 240:
#    DEPO_HALITE_LOOK  = 5
#    DEPO_HALITE       = 160
    
    
### 4 player changes ###
if len(game.players) == 4:
    returnHaliteFlag  = 950
    if game.game_map.width < 40:
        #shipBuildingTurns = 100
        MAX_DEPO = 1
        collectingStop= 1
        DEPO_HALITE -= 25
        if game.game_map.totalHalite < 220000:
            MAX_DEPO = 0
    elif game.game_map.width < 42:
        #shipBuildingTurns = 120
        collectingStop= 1
        DEPO_HALITE -= 10
        MAX_DEPO = 2
        if game.game_map.totalHalite < 225000:
            MAX_DEPO = 1
    elif game.game_map.width < 50:
        DEPO_HALITE -= 10
        #shipBuildingTurns = 100
        MAX_DEPO = 2        
        if game.game_map.totalHalite < 260000:
            MAX_DEPO = 1
    elif game.game_map.width < 57:
        DEPO_HALITE -= 25
        #shipBuildingTurns = 75
        MAX_DEPO = 4
    elif game.game_map.width < 80:
        #shipBuildingTurns = 75
        RADAR_MAX = 12
        DEPO_HALITE -= 25
        #DEPO_DISTANCE  = 17
        MAX_DEPO = 5
        DEPO_MIN_HALITE = 270

    
if len(game.players) == 4:
    SUICIDE_TURN_FLAG = 14


logging.info("NEARBY: avg {}, stdev {}".format(nearAvg, nearStd))

# bad spawn, lets get a depo way quicker!
#if nearAvg + 25 < game.game_map.averageHalite:
#    shipBuildingTurns -= 25
#elif nearAvg + 50 < game.game_map.averageHalite:
#    shipBuildingTurns -= 50

game.ready("v65Bot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {} # track what ships want to do
ship_move_flag = {} # track if ship is in danger and should move
ship_destination = {} # track where ships want to go
ship_previous_destination = {} # keep track of past 
ship_previous_status = {}
ship_order_refreshrate = {}

while True:
    start_time = timeit.default_timer()
    game.update_frame()
    logging.info("updateFrame {}".format(timeit.default_timer() - start_time))
    me = game.me
    game_map = game.game_map
    ship_destination = {} # reset destinations
    ship_move_flag = {} # track if ship is in danger and should move
    attack_targets = {} # make sure we don't double target
    START_TURN_DEPO = GLOBAL_DEPO
    turns_left = (constants.MAX_TURNS - game.turn_number)
    game_map.turnsLeft = turns_left
    GLOBAL_DEPO_BUILD_OK = True # only build one depo per turn
    DEPO_BUILD_THIS_TURN = False
    #game_map.dropCalc.updateMinHalite(DEPO_MIN_HALITE)
    game_map.dropCalc.updatePercentile(DEPO_PERCENTILE)

    if game.turn_number > 11:
        haliteChange = game.haliteHistory[-10] - game_map.totalHalite
    #logging.info("Total Halite: {} Average: {} Stdev: {}".format(game_map.totalHalite, game_map.averageHalite, game_map.stdDevHalite))

    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    for ship in me.get_ships():

        ###########################
        ### Set ship priorities ###
        ###########################
        if ship.id not in ship_status: # let function know there are no current orders
            ship_status[ship.id], ship_move_flag[ship.id] = giveShipOrders(ship, None, collectingStop)
        else:
            ship_status[ship.id], ship_move_flag[ship.id] = giveShipOrders(ship, ship_status[ship.id], collectingStop)
            
        
        ###############################
        ### Assign ship destination ###
        ###############################
        
        # assign collection goals
        lookWidth = 15
        if game_map.width > 50:
            lookWidth = 15
        #nearAvg, nearStd = game_map.get_near_stats(ship.position, lookWidth)

        targetSize = 100

        
        # be more aggressive early game
        if game.turn_number < 10 and (game.game_map.width == 40 or game.game_map.width == 32):
            targetSize = nearAvg
        
        #logging.info("Ship {} nAvg P{} nStd {} gAvg {} gStd{}".format(ship.id, nearAvg, nearStd, game_map.averageHalite, game_map.stdDevHalite))
        
        #if turns_left < 125 or game_map.averageHalite < 100:
        #if collectingStop > game_map.averageHalite:
        #    collectingStop = game_map.averageHalite
        
        if ship_status[ship.id] == 'mining':
            ship_destination[ship.id] = ship.execute_mining()
            
        elif ship_status[ship.id] == 'build depo':
            # want ship to move towards highest avg halite if it isn't ready to build
            if game_map.width < 65:
                allDrops = game.return_all_drop_locations()
                ship_destination[ship.id] = game_map.findHighestSmoothHalite(ship, allDrops, DEPO_DISTANCE)
            else:
                ship_destination[ship.id] = ship.position
            #logging.info("ship {} should head to {}".format(ship.id, game_map.findHighestSmoothHalite(ship)))
        
        # If ship should explore now
        elif (game_map[ship.position].halite_amount < collectingStop or ship.is_full) and ship_status[ship.id] == "exploring":
            targetHalite = 100
           
            # idea: 1) look very close for micro locations 2 width or less, look for above nearish avg halite
            # 2) if not found then move towards move halite?
            
            # look for close target
            #ship_destination[ship.id] = game_map.findDynamicHalite(ship, ship_destination, targetSize, lookWidth)
            #logging.info("Ship {} wants to go {}".format(ship.id, ship_destination[ship.id]))
            
        # If ship should return home
        elif ship_status[ship.id] == "returning" or ship_status[ship.id] == "returnSuicide":
            # choose closest depo or shipyard
            possibleLocations = [me.shipyard]
            possibleLocations.extend(me.get_dropoffs())
            closestChoice=  game_map.findClosest(ship, possibleLocations)
            ship_destination[ship.id] = closestChoice

        # If ship is in attack mode
        elif ship_status[ship.id] == 'attack':
            # in two player game attack but in 4 player game choose weakest enemy
            if len(game.players) == 2:
                targetEnemies = game.enemyShips
            else: # find weakest player to attack
                lowScore = 10000000
                weakestPlayer = None
                for player in game.players:
                    if game.players[player].halite_amount < lowScore and player != me.id:
                        lowScore = game.players[player].halite_amount
                        targetEnemies = game.players[player].get_ships()
            ship_destination[ship.id] = game_map.findDynamicEnemy(ship, targetEnemies, 200, 10)
        else: # stay still
            ship_destination[ship.id] = ship.position

        ### COUNTER MEASURES ###
        ### Counter measures check if ship sits on shipyard
        if game_map[me.shipyard.position].is_enemy() and (me.shipyard.position in ship.position.get_surrounding_cardinals()):
            ship_status[ship.id] == "returnSuicide"
            ship_destination[ship.id] = me.shipyard.position


    ### Check if depo ship was killed ###
    shipAlive = False
    if SAVE_UP_FOR_DEPO == True:
        for ship in me.get_ships():
            if ship_status[ship.id] == 'build depo':
                shipAlive = True
    
    if SAVE_UP_FOR_DEPO == True and shipAlive == False:
        SAVE_UP_FOR_DEPO = False
        DEPO_ONE_SHIP_AT_A_TIME = False
                
    

    ###########################
    ### Order Explore Ships ###
    ###########################
    start_time = timeit.default_timer()

    liveShips = me.get_ships()
    liveShipStatus = {}
    shipsExploringFinal = []
    
    for ship in liveShips:
        liveShipStatus[ship.id] = ship_status[ship.id]
            
    shipsExploring = [me.get_ship(k) for k,v in liveShipStatus.items() if v == 'exploring']

    
    shipsExploringFinal = shipsExploring
        
    # reduce the big matrix
    if game_map.width > 60:
        minHaliteSize = -2.5
    else:
        minHaliteSize = collectingStop
    
    #logging.info("final {}".format(shipsExploringFinal))
#    logging.info("Ship exp {}".format(shipsExploring))
    targetRow, targetCol, testOrders = game_map.matchShipsToDest2(shipsExploringFinal, ship_move_flag, minHaliteSize, 'hpt', collectingStop)
#    logging.info("TESTTEST! targ row {}, targ col {}, test orders {}".format(targetRow, targetCol, testOrders))

    for ship in shipsExploring:
        if ship.id in testOrders:
            ship_destination[ship.id] = testOrders[ship.id]
        else:
            ship_destination[ship.id] = ship_previous_destination[ship.id]
    #logging.info("ship destiantions {} ---- {}".format(testOrders, ship_destination))
    logging.info("choose destinations {}".format(timeit.default_timer() - start_time))
    #logging.info("final orders {}".format(ship_destination))
    


    ########################
    ### Resolve movement ###
    ########################
    start_time = timeit.default_timer()
    command_queue, finalDestination = resolveMovement(me.get_ships(), ship_destination, ship_status, attack_targets, ship_previous_destination)
    ship_previous_destination = ship_destination
    ship_previous_status = ship_status
    logging.info("resolve destinations {}".format(timeit.default_timer() - start_time))


    ########################
    ### Ship Build Logic ###
    ########################
    buildLogic = False
    if game.turn_number <= shipBuildingTurns:
        buildLogic = True
    else:
        logicCheck = shipConstructionLogic(game.playerScores, game.shipCountList, game_map.totalHalite, turns_left)
        #logging.info("ship logic {} depo built {} save up {}".format(logicCheck, DEPO_BUILD_THIS_TURN, SAVE_UP_FOR_DEPO))
        if logicCheck and me.halite_amount >= 5000:
            buildLogic = True
            #logging.info("extra ship!")
        elif logicCheck and DEPO_BUILD_THIS_TURN == True:
            if me.halite_amount >= 5000:
                buildLogic = True
        elif logicCheck and SAVE_UP_FOR_DEPO == False:
            buildLogic = True
            #logging.info("extra ship!")            
    
    if FIRST_DEPO_BUILT == True:
        WAIT_TO_BUILD_DEPOT -= 1
    
    #logging.info("first depo {} depo save {}".format(FIRST_DEPO_BUILT, WAIT_TO_BUILD_DEPOT))
    
    if me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()) and buildLogic:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)



