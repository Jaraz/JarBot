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


RADAR_WIDTH = 1

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
    halite = []
    for i in range(-width,width+1):
        for j in range(-width,width+1):
            halite.append(game_map[pos + Position(i,j)].halite_amount)
    return sum(halite)/len(halite)


def giveShipOrders(ship, currentOrders):
    # build ship status

    logging.info("Ship {} was {}".format(ship, currentOrders))

    status = None
    if currentOrders is None:
        status = "exploring"
    elif game_map.calculate_distance(ship.position, me.shipyard.position) >= (constants.MAX_TURNS - game.turn_number) - 5:
        logging.info("Ship {} time to head home: {}".format(ship.id, game_map.calculate_distance(ship.position, me.shipyard.position)))
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
        order = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
        if not order:
            order = Direction.Still
        else: 
            order = order[0]
        
        orderList[ship.id] = order
        
        # where next move takes us
        nextTurnPosition[ship.id] = game_map.normalize(ship.position + Position(*orderList[ship.id]))
    
    # resolve movement    
    useSecondBest = False
    for ship in ships:
        for i in ships:
            # check if you need a new move
            if nextTurnPosition[ship.id] == nextTurnPosition[i.id] and ship.id != i.id and ship.position != destinations[ship.id]:
                # first try other unsafe moves, if empty just move so you don't bottleneck
                nextBest = game_map.get_unsafe_moves(ship.position, destinations[ship.id])
                
                if len(nextBest) > 1:
                    nextLocation = game_map.normalize(ship.position + Position(*nextBest[1]))
                    if nextLocation not in nextTurnPosition.values():
                        logging.info("Ship {} will use next best to go {}, danger at {}nextTurnPostiion.values()".format(ship,nextLocation,nextTurnPosition.values()))
                        useSecondBest = True

                # IF second best isn't available we need to switch to something random
                if useSecondBest == True:
                        orderList[ship.id] = nextBest[1]
                else:
                    possibilities = ship.position.get_surrounding_cardinals()
                    logging.info("ship {} sees possiblities {} based on next turn {}".format(ship.id, possibilities, list(nextTurnPosition.values())))
                    possibilities = [x for x in possibilities if x not in list(nextTurnPosition.values())]

                    if len(possibilities) == 0:
                        orderList[ship.id] = Direction.Still
                    else:
                        newDirection = game_map.get_unsafe_moves(ship.position, random.choice(possibilities))
                        logging.info("Shio {} picked a new direction {}".format(ship.id, newDirection[0]))
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
            locations.append(pos + Position(i,j))
    return locations

# version 2
# returns location of higher halite in radar
def findHigherHalite2(ship, destinations, width = RADAR_WIDTH):
    pos = ship.position
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
            finalLocation = x
    logging.info("For {} location_choices are {}, we chose highest halite {}".format(pos,location_choices, finalLocation))
    
    # if highest halite is current pos just chose something random
    if finalLocation == pos:
        finalLocation = pos + game_map.get_unsafe_moves(pos, random.choice(ship.position.get_surrounding_cardinals()))
    return finalLocation
    

# given ship position return where (SAFE) and best halite
def findHigherHalite(pos):
    maxHalite = 0
    
    # neighbor scanner
    location_choices = pos.get_surrounding_cardinals()
    safe_moves = [game_map.naive_navigate(ship, x) for x in location_choices]
    
    logging.info("cardinal check : {}".format(pos.get_surrounding_cardinals()))
   
    # only look at actual moves
    moves = list(filter(((0,0)).__ne__,safe_moves))
    
    if moves == []:
        finalMove = random.choice(safe_moves)
    else:
        finalMove = random.choice(moves)
        
    for x in moves:
        haliteCheck = game_map[pos + Position(*x)].halite_amount
        #logging.info("Check it out ! : {}".format(Position(*x)))
        if haliteCheck > maxHalite and x != (0,0):
            maxHalite = haliteCheck
            finalMove = x
    
    return finalMove

# returns how far away ship object is
#def shipDistanceToHome(pos1, pos2):
#    game_map.calculate_distance(ship, me.shipyard.position)
#    return 0

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
returnFlagRatio   = 1.5 # higher means it returns earlier, ratio to 1000


#logging.disable(logging.CRITICAL)
logging.info("map information: {}".format(Position(1,1)))




game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {} # track what ships want to do
ship_destination = {} # track where ships want to go

while True:
    # This loop handles each turn of the game. The game object changes every turn, and you refresh that state by
    #   running update_frame().
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

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
        logging.info("Ship {} is {} currently at {}".format(ship.id, ship_status[ship.id], ship.position))

        ###############################
        ### Assign ship destination ###
        ###############################
        # If ship is low on fuel don't move
        if ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
            ship_destination[ship.id] = ship.position
            logging.info("Ship {} is low on fuel and staying still".format(ship.id))
        
        # If ship shouldn't mine any more
        # in theory you shoudl start with a high threshold and then move lower near end game
        elif (game_map[ship.position].halite_amount < constants.MAX_HALITE / collectingRatio or ship.is_full) and ship_status[ship.id] == "exploring":
            # i want the ship to see if its in a halite deadzone and then widen the window
            # if not in deadzone
            logging.info("Ship {} sees {} avg halite".format(ship.id,int(getSurroundingHalite(ship.position,1))))
            
            if getSurroundingHalite(ship.position,1) < 100 and game.turn_number < 400:
                haliteScanWidth =  RADAR_WIDTH + 2
            #elif getSurroundingHalite(ship.position,3) < 100:
            #    haliteScanWidth =  RADAR_WIDTH + 6
            else:
                haliteScanWidth =  RADAR_WIDTH
            
            ship_destination[ship.id] = findHigherHalite2(ship, ship_destination, width = haliteScanWidth)
            logging.info("Ship {} next move is {}".format(ship.id, ship_destination[ship.id]))
        
        elif ship_status[ship.id] == "returning":
            ship_destination[ship.id] = me.shipyard.position
            logging.info("Ship {} is returning home this way {}".format(ship.id, me.shipyard.position))
        
        elif ship_status[ship.id] == "returnSuicide":
            logging.info("Ship {} is returning home for its last journey".format(ship.id))
            ship_destination[ship.id] = me.shipyard.position
        
        else:
            ship_destination[ship.id] = ship.position
            logging.info("Ship {} has no other choice but to stay still".format(ship.id))

    ########################
    ### Resolve movement ###
    ########################
    logging.info("Current position: {}".format(ship_destination))    
    logging.info("Destination list (pre resolve): {}".format(ship_destination))
    command_queue, finalDestination = resolveMovement(me.get_ships(), ship_destination, ship_status)

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    #if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied and not (me.shipyard.position in finalDestination.values()):
    if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not (me.shipyard.position in finalDestination.values()):
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)



####### Structure ideas ########
# 1) Set ship priorities
# 2) Set ship movement goals
# 3) issue commands to all ships

'''
        if ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
            command_queue.append(ship.stay_still())
            logging.info("Ship {} is low on fueld and staying still".format(ship.id))
        
        elif (game_map[ship.position].halite_amount < constants.MAX_HALITE / collectingRatio or ship.is_full) and ship_status[ship.id] == "exploring":
            # safe random movement
            next_move = findHigherHalite2(ship.position)
            command_queue.append(ship.move(next_move))
            logging.info("Ship {} next safe move is {}".format(ship.id, next_move))
        
        elif ship_status[ship.id] == "returning":
            move = game_map.naive_navigate(ship, me.shipyard.position)
            command_queue.append(ship.move(move))
            logging.info("Ship {} is returning home this way {}".format(ship.id, move))
        
        elif ship_status[ship.id] == "returnSuicide":
            #if you are next to station, suicide!!!!
            if me.shipyard.position in ship.position.get_surrounding_cardinals():
                move = game_map.get_unsafe_moves(ship.position, me.shipyard.position)[0]
            else:
                move = game_map.naive_navigate(ship, me.shipyard.position)

            logging.info("Ship {} is returning home for its last journey {}".format(ship.id, move))
            command_queue.append(ship.move(move))
            logging.info("Ship {} is surrounded by {}".format(ship.id, ship.position.get_surrounding_cardinals()))
        
        else:
            command_queue.append(ship.stay_still())
            logging.info("Ship {} has no other choice but to stay still".format(ship.id))

'''
