#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

#import numpy as np
import random
#import queue

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position

# This library allows you to generate random numbers.
# import random



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

# return map halite
def getMapHalite():
    width = game.game_map.width
    totalH = 0 
    for i in range(width):
        for j in range(width):
            totalH +=game.game_map[Position(i,j)].halite_amount
    return totalH

# returns average halite in area based on width, also returns max halite
def getSurroundingHalite(pos, width):
    halite = []
    for i in range(-width,width+1):
        for j in range(-width,width+1):
            halite.append(game_map[pos + Position(i,j)].halite_amount)
    return sum(halite)/len(halite)


def giveShipOrders(ship, currentOrders):
    # build ship status

    #logging.info("Ship {} was {}".format(ship, currentOrders))

    status = None
    if currentOrders is None:
        status = "exploring"
    elif game_map.calculate_distance(ship.position, me.shipyard.position) >= (constants.MAX_TURNS - game.turn_number) - 5:
        #logging.info("Ship {} time to head home: {}".format(ship.id, game_map.calculate_distance(ship.position, me.shipyard.position)))
        status = "returnSuicide"
    elif currentOrders == "returning":
        status = "returning"
        if ship.position == me.shipyard.position:
            status = "exploring"
    elif ship.halite_amount >= constants.MAX_HALITE / returnFlagRatio:
        status = "returning"
    elif currentOrders == "exploring":
        status = "exploring"
    
    return status

#resolve movement function
def resolveMovement(ships, destinations, status):
    nextTurnPosition = {}
    orderList = {}
    finalOrder = []

    # tell me where everyone wants to go next turn    
    for ship in ships:
        # next move
        #logging.info("Ship {} at {} wants go to {}".format(ship.id, ship.position, destinations[ship.id]))
        #firstOrder = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
        firstOrder = game_map.get_safe_moves(ship.position, destinations[ship.id])
        if not firstOrder:
            order = Direction.Still
        else: 
            order = random.choice(firstOrder)
            nextBest = None
            if len(firstOrder) > 1:
                firstOrder.pop(firstOrder.index(order))
                nextBest = random.choice(firstOrder) ### need to fix this 
        
        orderList[ship.id] = order
        
        # where next move takes us
        nextTurnPosition[ship.id] = game_map.normalize(ship.position + Position(*orderList[ship.id]))
    
    # resolve movement    
    useSecondBest = False
    for ship in ships:
        for i in ships:
            # check if you need a new move
            # do we end up at the same spot + ensure its not ourselfs + don't choose another if sitting still + is enemy there
            #logging.info("ship {} vs ship {} resolve! Checck1: {} vs {}; check3: {} vs {}".format(ship.id, i.id, nextTurnPosition[ship.id], nextTurnPosition[i.id], ship.position, destinations[ship.id]))
            if nextTurnPosition[ship.id] == nextTurnPosition[i.id] and ship.id != i.id and ship.position != destinations[ship.id]:
                # first try other unsafe moves, if empty just move so you don't bottleneck
                #nextBest = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
                
                if nextBest is not None:
                    nextLocation = game_map.normalize(ship.position + Position(*nextBest))
                    if nextLocation not in nextTurnPosition.values():
                        #logging.info("Ship {} will use next best to go {}, danger at {}".format(ship,nextLocation,nextTurnPosition.values()))
                        useSecondBest = True

                # IF second best isn't available we need to switch to something random
                if useSecondBest == True:
                        orderList[ship.id] = nextBest
                else:
                    possibilities = list(map(game_map.normalize, ship.position.get_surrounding_cardinals()))
                    #logging.info("Ship {} surrounding cardinals {}".format(ship.id, possibilities))
                    #logging.info("ship {} sees possiblities {} based on next turn {}".format(ship.id, possibilities, list(nextTurnPosition.values())))
                    possibilities = [x for x in possibilities if x not in list(nextTurnPosition.values())]

                    if len(possibilities) == 0:
                        orderList[ship.id] = Direction.Still
                    else:
                        newDirection = game_map.get_unsafe_moves(ship.position, random.choice(possibilities))
                        #logging.info("Shio {} picked a new direction {}".format(ship.id, newDirection[0]))
                        orderList[ship.id] = newDirection[0]
                
                useSecondBest = False
                # new position
                nextTurnPosition[ship.id] = game_map.normalize(ship.position.directional_offset(orderList[ship.id]))
                
        # check if suicide mission home
        if status[ship.id] == 'returnSuicide' and (me.shipyard.position in ship.position.get_surrounding_cardinals()):
            orderList[ship.id] = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
        finalOrder.append(ship.move(orderList[ship.id]))
        
    logging.info("order list {}, next turn pos{}".format(orderList, nextTurnPosition))
    return finalOrder, nextTurnPosition
    
#return all surrounding cardinals
def get_surrounding_cardinals2(pos, width):
    locations = []
    for i in range(-width,width+1):
        for j in range(-width,width+1):
            #locations.append(game_map.normalize(pos) + game_map.normalize(Position(i,j)))
            locations.append(game_map.normalize(pos + Position(i,j)))
    return locations

# version 2
# returns location of higher halite in radar
def findHigherHalite2(ship, destinations, width = 1):
    pos = game_map.normalize(ship.position)
    maxHalite = 0 
    location_choices = get_surrounding_cardinals2(pos, width)

    #find max halite
    finalLocation = pos
    for x in location_choices:
        haliteCheck = game_map[x].halite_amount
        #logging.info("Check it out ! : {}".format(Position(*x)))
        otherDest = destinations.copy()
        if ship.id in otherDest:
            otherDest.pop(ship.id)
            
        if haliteCheck > maxHalite and x != pos and not (x in otherDest.values()):
            maxHalite = haliteCheck
            finalLocation = game_map.normalize(x)
    #logging.info("For ship {} at {} location_choices are {}, we chose highest halite {}".format(ship.id, pos,location_choices, finalLocation))
    
    return finalLocation
    


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
collectingRatio   = 10 # higher means you move less frequently to next halite
returnFlagRatio   = 1 # higher means it returns earlier, ratio to 1000
totalHalite       = getMapHalite()

RADAR_DEFAULT = 1
RADAR_WIDE = 3
RADAR_MAX = 7

#logging.disable(logging.CRITICAL)
logging.info("map size: {}, max turns: {}, halite: {}".format(game.game_map.width, constants.MAX_TURNS, totalHalite))

### Logic for ship building turns ###
if game.game_map.width > 60:
    shipBuildingTurns = 250
    RADAR_MAX = 12
elif game.game_map.width > 50:
    shipBuildingTurns = 225
elif game.game_map.width > 40:
    shipBuildingTurns = 185

game.ready("oldBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {} # track what ships want to do
ship_destination = {} # track where ships want to go

# Track ship yield
totalShipsBuilt = [0]

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # label map w/ enemy ship locations
    enemyShips = []
    ships = []
    for player in game.players:
        if player != me.id:
            ships = game.players[player].get_ships()
        for i in ships:
            game_map[i.position].mark_enemy_ship(i)
            
    # A command queue holds all the commands you will run this turn. You build this list up and submit it at the
    #   end of the turn.
    command_queue = []
    for ship in me.get_ships():

        ###########################
        ### Set ship priorities ###
        ###########################
        if ship.id not in ship_status:
            ship_status[ship.id] = giveShipOrders(ship, None)
        else:
            ship_status[ship.id] = giveShipOrders(ship, ship_status[ship.id])
            
        # if time running out head home and suicide. Need to add suicide code
        #logging.info("Ship {} is {} currently at {}".format(ship.id, ship_status[ship.id], ship.position))

        ###############################
        ### Assign ship destination ###
        ###############################
        # If ship is low on fuel don't move
        if ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
            ship_destination[ship.id] = ship.position
            #logging.info("Ship {} is low on fuel and staying still".format(ship.id))
        
        # If ship shouldn't mine any more
        # in theory you shoudl start with a high threshold and then move lower near end game
        elif (game_map[ship.position].halite_amount < constants.MAX_HALITE / collectingRatio or ship.is_full) and ship_status[ship.id] == "exploring":
            # i want the ship to see if its in a halite deadzone and then widen the window
            # if not in deadzone
            #logging.info("Ship {} sees {} avg halite".format(ship.id,int(getSurroundingHalite(ship.position,1))))
            
            if getSurroundingHalite(ship.position,1) < 100 and game.turn_number < 300:
                haliteScanWidth =  RADAR_WIDE
            elif getSurroundingHalite(ship.position,3) < 100:
                haliteScanWidth =  RADAR_MAX
            else:
                haliteScanWidth =  RADAR_DEFAULT
            
            ship_destination[ship.id] = findHigherHalite2(ship, ship_destination, width = haliteScanWidth)
            #logging.info("Ship {} next move is {}".format(ship.id, ship_destination[ship.id]))
        
        elif ship_status[ship.id] == "returning":
            ship_destination[ship.id] = me.shipyard.position
            #logging.info("Ship {} is returning home this way {}".format(ship.id, me.shipyard.position))
        
        elif ship_status[ship.id] == "returnSuicide":
            #logging.info("Ship {} is returning home for its last journey".format(ship.id))
            ship_destination[ship.id] = me.shipyard.position
        
        else:
            ship_destination[ship.id] = ship.position
            #logging.info("Ship {} has no other choice but to stay still".format(ship.id))

    ########################
    ### Resolve movement ###
    ########################
    #logging.info("RESOLVE MOVEMENT!!!!!!!")    
    #logging.info("Destination list (pre resolve): {}".format(ship_destination))
    command_queue, finalDestination = resolveMovement(me.get_ships(), ship_destination, ship_status)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    #if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and not (me.shipyard.position in finalDestination.values()):
    if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()):
        command_queue.append(me.shipyard.spawn())
        totalShipsBuilt.append(totalShipsBuilt[-1] + 1)

    minedHalite = max(totalShipsBuilt) * constants.SHIP_COST + me.halite_amount - 5000
    logging.info("Max ships: {}, Halite mined: {}, shipYieldPerTurn: {}".format(max(totalShipsBuilt), minedHalite, minedHalite/max(totalShipsBuilt)/game.turn_number))

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

