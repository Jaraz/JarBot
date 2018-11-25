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
SUICIDE_TURN_FLAG = 6
GLOBAL_DEPO_BUILD_OK = True

'''
To add later
fix when ships get stuck
Ship construction should be a function of game length
cargo hold orders should shorten at the start and lengthen as the game goes on
'''

'''
TODO
1) improve depo code to move a bit further after it sees an opportunity
2) make sure we have optimal allocation of targets and ships
3) make the bot more aggro in small maps and small 4 player games
4) Tweak depo building in 4 player games, esp 48 and under maps, maybe only build 1 depo max
5) tweak depo in bigger maps like 56x, wider distance
6) 
7) ???
8) Profit?
'''


# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging
#logging.basicConfig(level=logging.NOTSET)

def giveShipOrders(ship, currentOrders, collectingStop):
    # build ship status
    global GLOBAL_DEPO
    global GLOBAL_DEPO_BUILD_OK
    turns_left = (constants.MAX_TURNS - game.turn_number)
    #logging.info("Ship {} was {}".format(ship, currentOrders))

    status = None
    if currentOrders is None: #new ship
        status = "exploring"
    elif GLOBAL_DEPO < MAX_DEPO and \
         game.turn_number > shipBuildingTurns and \
         game_map.getSurroundingHalite(ship.position, DEPO_HALITE_LOOK) > DEPO_HALITE and \
         me.halite_amount >= (GLOBAL_DEPO + 1 - START_TURN_DEPO) * constants.DROPOFF_COST and \
         min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= DEPO_DISTANCE and \
         GLOBAL_DEPO_BUILD_OK == True:
        status = 'build depo'
        GLOBAL_DEPO += 1
        GLOBAL_DEPO_BUILD_OK = False
    elif min([game_map.calculate_distance(ship.position, i) for i in me.get_all_drop_locations()]) >= turns_left - SUICIDE_TURN_FLAG:
        status = "returnSuicide"
    elif currentOrders == "returning":
        status = "returning"
        if ship.position == me.shipyard.position or ship.position in me.get_dropoff_locations():
            status = "exploring"
    elif ship.halite_amount >= returnHaliteFlag:
        status = "returning"
    elif ship.halite_amount < game_map[ship.position].halite_amount * 0.1 or game_map[ship.position].halite_amount > collectingStop:
        status = 'mining'
    #create attack squad near end
    elif ship.halite_amount < 50 and game_map.averageHalite < 50 and game_map.width < 48:
        status = 'attack'
    elif currentOrders == "exploring":
        status = "exploring"
    else:
        status = 'exploring'
    logging.info("ship {} status is {}".format(ship.id, status))
    return status

#resolve movement function
def resolveMovement(ships, destinations, status, attackTargets):
    nextTurnPosition = {}
    orderList = {}
    nextList = {}
    finalOrder = []


    # tell me which direction everyone wants to go next turn    
    for ship in ships:
        # next move
        #firstOrder = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
        firstOrder = game_map.get_safe_moves(ship.position, destinations[ship.id])
        if not firstOrder: # if no safe moves just stay still
            order = Direction.Still
        else: 
            random.shuffle(firstOrder)
            order = firstOrder[0]
            if len(firstOrder) > 1:
                nextList[ship.id] = firstOrder[1] ### need to fix this 
        
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
                    
                    logging.info("Ship {} has an issue with {}".format(ship.id,i.id))
                    
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
                        logging.info("ship {} sees possiblities {} based on next turn {}".format(ship.id, possibilities, list(nextTurnPosition.values())))
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
             
            ##########################
            ## Check to ATTACK !!!! ##
            ##########################
            # If you are next to a full ship, and you are low on halite, ATTACK!
            enemyLocations = game_map.return_nearby_enemies(ship.position)
            for loc in enemyLocations:
                if loc: 
                    #logging.info("ship {} at {} looking at enemy loc {} enemyShip {}".format(ship.id, ship.position, loc, loc.enemyShip))
                    if ((ship.halite_amount < 200 and \
                        loc.enemyShip.halite_amount > 600 and \
                        ship.halite_amount > game_map[ship.position].halite_amount * 0.1 and \
                        len(game.players) == 2) or status[ship.id] == 'attack') and \
                        (loc.position.x,loc.position.y) not in attackTargets:
                        logging.info("ATTACK TEST{}".format((loc.position.x,loc.position.y)))
                        attackTargets[(loc.position.x,loc.position.y)] = 'targeted'
                        orderList[ship.id] = game_map.get_unsafe_moves(ship.position, loc.position)[0]
                        logging.info("ATTACK: Ship {} to {} on order {}".format(ship.id, loc, orderList[ship.id]))
    
    # issue final order
    for ship in ships:
        ### BUILD DEPO ###
        if status[ship.id] == 'build depo':
            finalOrder.append(ship.make_dropoff())        
        else:
            finalOrder.append(ship.move(orderList[ship.id]))
        
    logging.info("order list {}, next turn pos{}".format(orderList, nextTurnPosition))
    return finalOrder, nextTurnPosition


""" <<<Game Begin>>> """

# This game object contains the initial game state.
game = hlt.Game()

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
    DEPO_DISTANCE  = 20
    SUICIDE_TURN_FLAG = 7
    MAX_DEPO = 3
elif game.game_map.width > 50:
    shipBuildingTurns = 225
    DEPO_DISTANCE  = 20
elif game.game_map.width > 39:
    shipBuildingTurns = 200
    collectingStop= 50
elif game.game_map.width < 40 and game.game_map.totalHalite < 160000:
    shipBuildingTurns = 155
    collectingStop = 50
    MAX_DEPO = 1    
elif game.game_map.width < 40 and game.game_map.averageHalite > 250:
    collectingStop = 50
else:
    collectingStop= 50
#elif game.game_map.width < 40 and totalHalite > 300000:
#    shipBuildingTurns = 200
#    collectingStop = 50

if game.game_map.averageHalite > 180:
    logging.info("Build more ships!")
    shipBuildingTurns += 25
    collectingStop += 25

if game.game_map.averageHalite > 240:
    DEPO_HALITE_LOOK  = 5
    DEPO_HALITE       = 180
    
    
### 4 player changes ###
if len(game.players) == 4:
    if game.game_map.width < 40:
        shipBuildingTurns = 130
        MAX_DEPO = 1
        collectingStop= 100
    elif game.game_map.width < 42:
        shipBuildingTurns = 150
        collectingStop= 100
    elif game.game_map.width < 50:
        shipBuildingTurns = 180
    elif game.game_map.width < 57:
        shipBuildingTurns = 225
    elif game.game_map.width < 80:
        shipBuildingTurns = 250
        RADAR_MAX = 12
        DEPO_HALITE += 25
        DEPO_DISTANCE  = 15
    
if len(game.players) == 4:
    SUICIDE_TURN_FLAG = 14

nearAvg, nearStd = game.game_map.get_near_stats(game.me.shipyard.position, 5)
logging.info("NEARBY: avg {}, stdev {}".format(nearAvg, nearStd))

game.ready("JarBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {} # track what ships want to do
ship_destination = {} # track where ships want to go

while True:
    game.update_frame()
    me = game.me
    game_map = game.game_map
    ship_destination = {} # reset destinations
    attack_targets = {} # make sure we don't double target
    START_TURN_DEPO = GLOBAL_DEPO
    turns_left = (constants.MAX_TURNS - game.turn_number)
    GLOBAL_DEPO_BUILD_OK = True # only build one depo per turn

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
            ship_status[ship.id] = giveShipOrders(ship, None, collectingStop)
        else:
            ship_status[ship.id] = giveShipOrders(ship, ship_status[ship.id], collectingStop)
            
        ###############################
        ### Assign ship destination ###
        ###############################
        
        # assign collection goals
        lookWidth = 15
        if game_map.width > 50:
            lookWidth = 15
        nearAvg, nearStd = game_map.get_near_stats(ship.position, lookWidth)

        targetSize = 100

        
        # be more aggressive early game
        if game.turn_number < 10 and (game.game_map.width == 40 or game.game_map.width == 32):
            targetSize = nearAvg
        
        logging.info("Ship {} nAvg P{} nStd {} gAvg {} gStd{}".format(ship.id, nearAvg, nearStd, game_map.averageHalite, game_map.stdDevHalite))
        
        if turns_left < 100 or game_map.averageHalite < 100:
            collectingStop = game_map.averageHalite
        
        if ship_status[ship.id] == 'mining':
            ship_destination[ship.id] = ship.execute_mining()
        
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

    # Test movement 2.0
    # ships set to explore
    liveShips = me.get_ships()
    liveShipStatus = {}
    for ship in liveShips:
        liveShipStatus[ship.id] = ship_status[ship.id]
    shipsExploring = [me.get_ship(k) for k,v in liveShipStatus.items() if v == 'exploring']
#    logging.info("Ship exp {}".format(shipsExploring))
    targetRow, targetCol, testOrders = game_map.matchShipsToDest2(shipsExploring, hChoice = 'linear')    
#    logging.info("TESTTEST! targ row {}, targ col {}, test orders {}".format(targetRow, targetCol, testOrders))

    for ship in shipsExploring:
        ship_destination[ship.id] = testOrders[ship.id]
    logging.info("final orders {}".format(ship_destination))
    


    ########################
    ### Resolve movement ###
    ########################
    command_queue, finalDestination = resolveMovement(me.get_ships(), ship_destination, ship_status, attack_targets)

    # Ship spawn logic
    if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()):
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

