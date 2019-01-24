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


# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging

# ship construction should be a function of scores, ships, and halite
# assume first number in list is player one
def shipConstructionLogic(playerScores, playerShips, haliteLeft, turnsLeft):
    turnStopBuilding = 90 # don't build ships after this
    buildShip = False # assume we are saying no
    shipLead = 10
    shipCompare = playerShips[1]
    totalShips = np.sum(playerShips)
    
    stopFlag = 0.28 # stop if map is below this % of halite
    if game_map.width > 50:
        stopFlag = 0.25
    
    if game_map.width <= 40:
        shipLead = 5
    elif game_map.width <= 48:
        shipLead = 8
    
    if totalShips < 1:
        totalShips = 1 # random bug fix at start of game
        
    # take a moving average of halite being mined by everyone (doesn't count insp nor dead ship recovery) 
    nextTen = 10 * (game_map.miningMA[game_map.turnNumber-1] * 2 - game_map.miningMA[game_map.turnNumber-10])/totalShips
    
    if len(playerScores) == 4:
        shipCompare = np.mean(playerShips[1:3]) # don't build too many ships vs everyone
        playerMultiple = 1.15
        if game_map.width > 55:
            stopFlag = 0.225
        
    if len(playerScores)==4:
        shipLead += 5
        # can we make back 1k on ship cost
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
        if turnsLeft > 100 and playerScores[0] < playerScores[1] and playerShips[0] < playerShips[1]:
            buildShip = True
    return buildShip

# gives high level macro orders
def giveShipOrders(ship, currentOrders, collectingStop):
    # i have no idea how python works so i just jam global everywhere lolz
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

    # flags to run or attack
    runFlag = False
    attackFlag = False
    
    #logging.info("Enemy ship halite \n {}".format(game_map.enemyShipHalite))
    
    shipX = ship.position.x
    shipY = ship.position.y
    
    dist = game_map.dist1[shipX][shipY] # matrix of 1's next to current ship
    enemyInSight = dist * game_map.shipFlag # ship flag is a matrix of enemy ship locations
    #logging.info("ship {} dist {} enemy in sight {}".format(ship.id, dist, enemyInSight))
    
    # is an enemy in zone
    if np.sum(enemyInSight)>0:
        enemyHalite = game_map.enemyShipHalite * dist
        enemyMA = np.ma.masked_equal(enemyHalite, 0, copy=False)

        # matrix of how much halite enemy ships are carrying + will mine next turn
        fightHalite = dist * (game_map.enemyShipHalite + game_map.enemyMiningNext)
        
        # returns highest halit eneighbor
        enemyLoc = np.unravel_index(fightHalite.argmax(),fightHalite.shape)

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
        # check if we should fight, do we control the area, based on 4 dist from enemy location
        elif np.max(fightHalite) - 100 > ship.halite_amount and \
             len(game.players)==2 and \
             game_map.friendlyShipCount[enemyLoc] > game_map.enemyShipCount[enemyLoc]:
            #logging.info("ship {} attacks!!!".format(ship.id))
            attackFlag = True
        elif np.max(fightHalite) - 200 > ship.halite_amount and \
             len(game.players)==4 and \
             game_map.friendlyShipCount[enemyLoc] >= game_map.enemyShipCount[enemyLoc] + 2 and \
             game_map.freeHalite < game_map.attackThreshold:
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
    # gross depo code, plz don't read
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
    elif ship.halite_amount < game_map[ship.position].halite_amount * 0.1 and game_map[ship.position].halite_amount >= 10:
        status = 'mining'
    elif min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= turns_left - SUICIDE_TURN_FLAG:
        status = "returnSuicide"
    elif currentOrders == "returning":
        status = "returning"
        if ship.position == me.shipyard.position or ship.position in me.get_dropoff_locations():
            status = "exploring"
    elif (ship.halite_amount >= game_map.haliteCollectionTarget)  or (runFlag == True) or (ship.halite_amount >=900 and min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) <= 2):
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

# prep work before we assign which direction teh ship should move
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
    # if an enemy already has 1k in a 2p game, he is gonna move so don't plan him to stay still
    for enemy in game.enemyShips:
        #enemyLoc.append(enemy.position)
        if enemy.halite_amount !=1000 and len(game.players)==2:
            enemyLoc.append(enemy.position)
        elif len(game.players)==4:
            enemyLoc.append(enemy.position)
        else:
            logging.info("1k found")
    
    
    #logging.info("ships {} *** dest {} *** dropoffs {}".format(ships, destinations, dropoffs))
    # this resolves movement givne ship orders
    orderList = game_map.findOptimalMoves(ships, destinations, dropoffs, status, enemyLoc)

    # issue final order
    for ship in ships:

        ### BUILD DEPO ###
        if status[ship.id] == 'build depo':
            # always avoid reading depo code
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
returnHaliteFlag  = 950 # halite to return to base
DEPO_DISTANCE_DELTA = 0
DEPO_PERCENTILE = 75
DEPO_MIN_SHIPS = 4

#DEPOs
MAX_DEPO          = 3
DEPO_HALITE_LOOK  = 5
DEPO_HALITE       = 100
DEPO_DISTANCE     = 14

#logging.disable(logging.CRITICAL)
logging.info("map size: {}, max turns: {}".format(game.game_map.width, constants.MAX_TURNS))
nearAvg, nearStd = game.game_map.get_near_stats(game.me.shipyard.position, 5)

### Logic for ship building turns ###
if game.game_map.width > 60:
    shipBuildingTurns = 50
    DEPO_HALITE += 0
    DEPO_DISTANCE  = 14
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
    shipBuildingTurns = 50
    DEPO_DISTANCE  = 13
    DEPO_DISTANCE_DELTA = 4
    MAX_DEPO = 6
    collectingStop = 1
    DEPO_MIN_HALITE  = 290
    DEPO_PERCENTILE = 66
    #game.game_map.updateSmoothSize(5)
elif game.game_map.width > 41:
    shipBuildingTurns = 50
    collectingStop= 1
    DEPO_DISTANCE  = 15
    MAX_DEPO = 4
    if game.game_map.totalHalite < 200000:
        MAX_DEPO = 1
    DEPO_DISTANCE  = 13
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
    DEPO_DISTANCE  = 13
    DEPO_DISTANCE_DELTA = 6
    DEPO_MIN_HALITE   = 375
elif game.game_map.width < 40 and game.game_map.totalHalite < 200000:
    shipBuildingTurns = 110
    collectingStop = 1
    MAX_DEPO = 1    
    DEPO_DISTANCE  = 13
elif game.game_map.width < 40 and game.game_map.totalHalite < 270000:
    shipBuildingTurns = 90
    collectingStop = 1
    MAX_DEPO = 2
    DEPO_DISTANCE  = 13
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
    returnHaliteFlag  = 850
    if game.game_map.width < 40:
        MAX_DEPO = 1
        collectingStop= 1
        DEPO_HALITE -= 25
        if game.game_map.totalHalite < 220000:
            MAX_DEPO = 0
    elif game.game_map.width < 42:
        collectingStop= 1
        DEPO_HALITE -= 10
        MAX_DEPO = 2
        if game.game_map.totalHalite < 225000:
            MAX_DEPO = 1
    elif game.game_map.width < 50:
        DEPO_HALITE -= 10
        MAX_DEPO = 2        
        if game.game_map.totalHalite < 260000:
            MAX_DEPO = 1
    elif game.game_map.width < 57:
        DEPO_HALITE -= 25
        MAX_DEPO = 4
    elif game.game_map.width < 80:
        DEPO_HALITE -= 25
        #DEPO_DISTANCE  = 17
        MAX_DEPO = 5
        DEPO_MIN_HALITE = 270

    
if len(game.players) == 4:
    SUICIDE_TURN_FLAG = 14
    DEPO_DISTANCE += 1


logging.info("NEARBY: avg {}, stdev {}".format(nearAvg, nearStd))

# bad spawn, lets get a depo way quicker!
#if nearAvg + 25 < game.game_map.averageHalite:
#    shipBuildingTurns -= 25
#elif nearAvg + 50 < game.game_map.averageHalite:
#    shipBuildingTurns -= 50

game.ready("JarBot")

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
        
        # If ship should return home
        elif ship_status[ship.id] == "returning" or ship_status[ship.id] == "returnSuicide":
            # choose closest depo or shipyard
            possibleLocations = [me.shipyard]
            possibleLocations.extend(me.get_dropoffs())
            closestChoice=  game_map.findClosest(ship, possibleLocations)
            ship_destination[ship.id] = closestChoice

        else: # stay still
            ship_destination[ship.id] = ship.position

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
    
    # this is the halite search function, only reason i made diamond
    targetRow, targetCol, testOrders = game_map.matchShipsToDest2(shipsExploringFinal, ship_move_flag, minHaliteSize, 'hpt', collectingStop)

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



