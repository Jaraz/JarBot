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

# This library allows you to generate random numbers.
# import random
# helper variables
GLOBAL_DEPO = 0
START_TURN_DEPO = 0

'''
To add later
fix when ships get stuck
Ship construction should be a function of game length
cargo hold orders should shorten at the start and lengthen as the game goes on
'''

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
#logging.basicConfig(level=logging.NOTSET)

# returns average halite in area based on width, also returns max halite
def getSurroundingHalite(pos, width):
    total = 0
    for i in range(-width,width+1):
        for j in range(-width,width+1):
            total += game_map[pos + Position(i,j)].halite_amount
    return total/((width*2+1)*(width*2+1))


def giveShipOrders(ship, currentOrders):
    # build ship status
    global GLOBAL_DEPO
    turns_left = (constants.MAX_TURNS - game.turn_number)
    #logging.info("Ship {} was {}".format(ship, currentOrders))

    status = None
    if currentOrders is None: #new ship
        status = "exploring"
    elif GLOBAL_DEPO < MAX_DEPO and game.turn_number > shipBuildingTurns and getSurroundingHalite(ship.position, DEPO_HALITE_LOOK) > DEPO_HALITE and me.halite_amount >= (GLOBAL_DEPO + 1 - START_TURN_DEPO) * constants.DROPOFF_COST and min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= DEPO_DISTANCE:
        status = 'build depo'
        GLOBAL_DEPO += 1
    elif min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= turns_left - 5:
        #logging.info("Ship {} time to head home: {}".format(ship.id, game_map.calculate_distance(ship.position, me.shipyard.position)))
        status = "returnSuicide"
    elif currentOrders == "returning":
        status = "returning"
        if ship.position == me.shipyard.position or ship.position in me.get_dropoff_locations():
            status = "exploring"
    elif ship.halite_amount >= returnHaliteFlag:
        status = "returning"
    elif currentOrders == "exploring":
        status = "exploring"
    #logging.info("Ship {} status is {}".format(ship.id, status))
    return status

#resolve movement function
def resolveMovement(ships, destinations, status):
    nextTurnPosition = {}
    orderList = {}
    nextList = {}
    finalOrder = []


    # tell me where everyone wants to go next turn    
    for ship in ships:
        # next move
        nextBest = None
        logging.info("Ship {} at {} wants go to {}".format(ship.id, ship.position, destinations[ship.id]))
        #firstOrder = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
        firstOrder = game_map.get_safe_moves(ship.position, destinations[ship.id])
        #logging.info("Ship {} first order is {}".format(ship.id, firstOrder))
        if not firstOrder: # if no safe moves just stay still
            order = Direction.Still
        else: 
            random.shuffle(firstOrder)
            order = firstOrder[0]
            if len(firstOrder) > 1:
                nextList[ship.id] = firstOrder[1] ### need to fix this 
            #logging.info("ship {}, order {}, nextbest {}".format(ship.id, order, nextBest))
        
        orderList[ship.id] = order
        
        # where next move takes us
        nextTurnPosition[ship.id] = game_map.normalize(ship.position + Position(*orderList[ship.id]))
    
    # resolve movement make 2 passes
    useSecondBest = False
    for x in range(3): # make 2 pases
        for ship in ships:
            for i in ships:
                # check if you need a new move
                # do we end up at the same spot + ensure its not ourselfs + don't choose another if sitting still + is enemy there
                #logging.info("ship {} vs ship {} resolve! Checck1: {} vs {}; check3: {} vs {}".format(ship.id, i.id, nextTurnPosition[ship.id], nextTurnPosition[i.id], ship.position, destinations[ship.id]))
                if nextTurnPosition[ship.id] == nextTurnPosition[i.id] and ship.id != i.id and ship.position != destinations[ship.id]:
                    # first try other unsafe moves, if empty just move so you don't bottleneck
                    #nextBest = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
                    
                    #logging.info("Ship {} has an issue with {}".format(ship.id,i.id))
                    
                    # if you have a second best move
                    if ship.id in nextList: 
                        nextLocation = game_map.normalize(ship.position + Position(*nextList[ship.id]))
                        if nextLocation not in nextTurnPosition.values():
                            #logging.info("Ship {} will use next best to go {}, danger at {}".format(ship,nextLocation,nextTurnPosition.values()))
                            useSecondBest = True
    
                    # IF second best isn't available we need to switch to something random
                    if useSecondBest == True:
                            orderList[ship.id] = nextList[ship.id]
                    else:
                        possibilities = list(map(game_map.normalize, ship.position.get_surrounding_cardinals()))
                        #logging.info("Ship {} surrounding cardinals {}".format(ship.id, possibilities))
                        #logging.info("ship {} sees possiblities {} based on next turn {}".format(ship.id, possibilities, list(nextTurnPosition.values())))
                        possibilities = [x for x in possibilities if x not in list(nextTurnPosition.values())]
    
                        if len(possibilities) == 0:
                            orderList[ship.id] = Direction.Still
                        else:
                            newDirection = game_map.get_safe_moves(ship.position, random.choice(possibilities))
                            #logging.info("Shio {} picked a new direction {}".format(ship.id, newDirection[0]))
                            if newDirection == []:
                                orderList[ship.id] = Direction.Still
                            else:
                                orderList[ship.id] = random.choice(newDirection)
                                #logging.info("ship {} uses random new direction {}".format(ship.id, orderList[ship.id]))
    
                    useSecondBest = False
                    # new position
                    nextTurnPosition[ship.id] = game_map.normalize(ship.position.directional_offset(orderList[ship.id]))
    
            #####################
            #### MISC CHECKS ####
            #####################                
                    
            # check if suicide mission home
            if status[ship.id] == 'returnSuicide' and (me.shipyard.position in ship.position.get_surrounding_cardinals()):
                orderList[ship.id] = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
            elif status[ship.id] == 'returnSuicide':
                #logging.info("Dropoffs {}, surrounding {}".format(me.get_dropoff_locations(),ship.position.get_surrounding_cardinals()))
                dropOffTarget = None
                nextToDrop = False
                surrounding = ship.position.get_surrounding_cardinals()
                for i in me.get_dropoff_locations():
                    if i in surrounding:
                        nextToDrop = True
                        dropOffTarget = i
                if nextToDrop:
                    orderList[ship.id] = game_map.get_unsafe_moves(ship.position, dropOffTarget)[0]        
             
            
            ## Check to ATTACK !!!! ##
            # If you are next to a full ship, and you are low on halite, ATTACK!
            enemyLocations = game_map.return_nearby_enemies(ship.position)
            for loc in enemyLocations:
                if loc: 
                    #logging.info("ship {} at {} looking at enemy loc {} enemyShip {}".format(ship.id, ship.position, loc, loc.enemyShip))
                    if ship.halite_amount < 200 and loc.enemyShip.halite_amount > 800 and ship.halite_amount > game_map[ship.position].halite_amount * 0.1 and len(game.players) == 2:
                        orderList[ship.id] = game_map.get_unsafe_moves(ship.position, loc.position)[0]
                        #logging.info("ATTACK: Ship {} to {} on order {}".format(ship.id, loc, orderList[ship.id]))
    
    # issue final order
    for ship in ships:
        ### BUILD DEPO ###
        if status[ship.id] == 'build depo':
            finalOrder.append(ship.make_dropoff())        
        else:
            finalOrder.append(ship.move(orderList[ship.id]))
        
    #logging.info("order list {}, next turn pos{}".format(orderList, nextTurnPosition))
    return finalOrder, nextTurnPosition
    


""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()
# At this point "game" variable is populated with initial map data.
# This is a good place to do computationally expensive start-up pre-processing.
# As soon as you call "ready" function below, the 2 second per turn timer will start.
#constants.load_constants()

################
### Settings ###
################
shipBuildingTurns = 175 # how many turns to build ships
collectingStop    = 50 # Ignore halite less than this
returnHaliteFlag  = 950 # halite to return to base

#DEPOs
MAX_DEPO          = 2
DEPO_HALITE_LOOK  = 5
DEPO_HALITE       = 125
DEPO_DISTANCE     = 10

#default is 1, 3, 7
RADAR_DEFAULT = 1
RADAR_WIDE = RADAR_DEFAULT + 2
RADAR_MAX = RADAR_DEFAULT + 6

#logging.disable(logging.CRITICAL)
logging.info("map size: {}, max turns: {}".format(game.game_map.width, constants.MAX_TURNS))

### Logic for ship building turns ###
if game.game_map.width > 60:
    shipBuildingTurns = 250
    RADAR_MAX = 12
    DEPO_HALITE += 25
    DEPO_DISTANCE  = 12
elif game.game_map.width > 50:
    shipBuildingTurns = 225
elif game.game_map.width > 40:
    shipBuildingTurns = 200
elif game.game_map.width < 40 and game.game_map.totalHalite < 160000:
    shipBuildingTurns = 155
    collectingStop = 50
#elif game.game_map.width < 40 and totalHalite > 300000:
#    shipBuildingTurns = 200
#    collectingStop = 50
collectingStop = 50

if game.game_map.averageHalite > 180:
    logging.info("Build more ships!")
    shipBuildingTurns += 25
    collectingStop += 25

if game.game_map.averageHalite > 240:
    DEPO_HALITE_LOOK  = 5
    DEPO_HALITE       = 240
    
    
### 4 player changes ###
if len(game.players) == 4:
    if game.game_map.width < 40:
        shipBuildingTurns = 130
    elif game.game_map.width < 50:
        shipBuildingTurns = 180
    elif game.game_map.width < 57:
        shipBuildingTurns = 225
    elif game.game_map.width < 80:
        shipBuildingTurns = 250
        RADAR_MAX = 12
        DEPO_HALITE += 25
        DEPO_DISTANCE  = 12
    

nearAvg, nearStd = game.game_map.get_near_stats(game.me.shipyard.position, 5)
logging.info("NEARBY: avg {}, stdev {}".format(nearAvg, nearStd))

#? DEPO_HALITE = avgHalite +10

game.ready("oldBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {} # track what ships want to do
ship_destination = {} # track where ships want to go

# Track ship yield
totalShipsBuilt = [0]
haliteChange = 1000

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map
    ship_destination = {} # reset destinations
    START_TURN_DEPO = GLOBAL_DEPO
    turns_left = (constants.MAX_TURNS - game.turn_number)

    if game.turn_number > 11:
        haliteChange = game.haliteHistory[-10] - game_map.totalHalite
    #logging.info("Total Halite: {} Average: {} Stdev: {}".format(game_map.totalHalite, game_map.averageHalite, game_map.stdDevHalite))

    # label map w/ enemy ship locations
    enemyShips = []
    for player in game.players:
        if player != me.id:
            enemyShips = game.players[player].get_ships()
        for i in enemyShips:
            game_map[i.position].mark_enemy_ship(i)
            logging.info("Enemy identified {}".format(i))
            
            # ship info
            haliteAtEnemy = game_map[i.position].halite_amount
            haliteOnShip  = i.halite_amount
            
            # guess enemy movement, skip if he is on a lot of halite and empty
            #if len(game.players) > 3 and haliteAtEnemy > game_map.averageHalite and haliteOnShip < 700:
            if len(game.players) >4:
                game_map[game_map.normalize(i.position + Position(1,0))].mark_enemy_ship(i)
                game_map[game_map.normalize(i.position + Position(0,1))].mark_enemy_ship(i)
                game_map[game_map.normalize(i.position + Position(-1,0))].mark_enemy_ship(i)
                game_map[game_map.normalize(i.position + Position(0,-1))].mark_enemy_ship(i)
            
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    for ship in me.get_ships():

        ###########################
        ### Set ship priorities ###
        ###########################
        if ship.id not in ship_status: # let function know there are no current orders
            ship_status[ship.id] = giveShipOrders(ship, None)
        else:
            ship_status[ship.id] = giveShipOrders(ship, ship_status[ship.id])
            
        ###############################
        ### Assign ship destination ###
        ###############################
        #targetSize = game_map.averageHalite
        #if turns_left < 100:
        #    targetSize = game_map.averageHalite
        #    collectingStop = 50
        # If ship is low on fuel don't move
        if ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
            ship_destination[ship.id] = ship.position
        
        # If ship shouldn't mine any more
        elif (game_map[ship.position].halite_amount < collectingStop or ship.is_full) and ship_status[ship.id] == "exploring":
            ship_destination[ship.id] = game_map.findDynamicHalite(ship, ship_destination, 100, 7)
        
        elif ship_status[ship.id] == "returning" or ship_status[ship.id] == "returnSuicide":
            # choose closest depo or shipyard
            possibleLocations = [me.shipyard]
            possibleLocations.extend(me.get_dropoffs())
            closestChoice=  game_map.findClosest(ship, possibleLocations)
            ship_destination[ship.id] = closestChoice
            #logging.info("Ship {} is returning home to {}, choices were {}".format(ship.id, closestChoice, possibleLocations))
            #logging.info("Ship {} is returning home this way {}".format(ship.id, me.shipyard.position))

        else: # stay still
            ship_destination[ship.id] = ship.position

        ### COUNTER MEASURES ###
        ### Counter measures check if ship sits on shipyard
        if game_map[me.shipyard.position].is_enemy() and (me.shipyard.position in ship.position.get_surrounding_cardinals()):
            ship_status[ship.id] == "returnSuicide"
            ship_destination[ship.id] = me.shipyard.position

    ########################
    ### Resolve movement ###
    ########################
    #logging.info("RESOLVE MOVEMENT!!!!!!!")    
    #logging.info("Destination list (pre resolve): {}".format(ship_destination))
    command_queue, finalDestination = resolveMovement(me.get_ships(), ship_destination, ship_status)

    # calculate marginal benefit of a new ship
    numShips = 0
    for player in game.players:
        numShips +=len(game.players[player].get_ships())
    #numShips = len(numShips)
    recentYield = haliteChange/(numShips+0.001)
    projectedEarn = (recentYield/30) * (turns_left - 50) 
    #logging.info("Projected earn: {}".format((projectedEarn)))

    # Ship spawn logic
    #if projectedEarn >= constants.SHIP_COST and me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()):
    if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()):
        command_queue.append(me.shipyard.spawn())
        totalShipsBuilt.append(totalShipsBuilt[-1] + 1)

    minedHalite = max(totalShipsBuilt) * constants.SHIP_COST + me.halite_amount - 5000
    #logging.info("Max ships: {}, Halite mined: {}".format(max(totalShipsBuilt), minedHalite))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

