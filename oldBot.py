#!/usr/bin/env python3
# Python 3.6

# Import the Halite SDK, which will let you interact with the game.
import hlt

#import numpy as np
import random

# This library contains constant values.
from hlt import constants

# This library contains direction metadata to better interface with the game.
from hlt.positionals import Direction
from hlt.positionals import Position

# This library allows you to generate random numbers.
# import random


'''
To add
fix when ships get stuck
Ship construction should be a function of game length
cargo hold orders should shorten at the start and lengthen as the game goes on
'''

# Logging allows you to save messages for yourself. This is required because the regular STDOUT
#   (print statements) are reserved for the engine-bot communication.
import logging



# given ship position return where (SAFE) and best halite
def findHigherHalite(pos):
    maxHalite = 0
    location_choices = [pos.directional_offset(x) for x in [Direction.North, Direction.South, Direction.East, Direction.West]]
    safe_moves = [game_map.naive_navigate(ship, x) for x in location_choices]
    
    #logging.info("safe moves : {}".format(safe_moves))
   
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

### Settings ###
shipBuildingTurns = 150
collectingRatio   = 20
returnFlagRatio   = 1.5

logging.info("map information: {}".format(Position(1,1)))




game.ready("MyPythonBot")

# Now that your bot is initialized, save a message to yourself in the log file with some important information.
#   Here, you log here your id, which you can always fetch from the game object by using my_id.
logging.info("Successfully created bot! My Player ID is {}.".format(game.my_id))

""" <<<Game Loop>>> """

ship_status = {}

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

        # build ship status
        if ship.id not in ship_status:
            ship_status[ship.id] = "exploring"
        
        if game_map.calculate_distance(ship.position, me.shipyard.position) >= (constants.MAX_TURNS - game.turn_number) - 5:
            logging.info("Ship {} time to head home: {}".format(ship.id, game_map.calculate_distance(ship.position, me.shipyard.position)))
            ship_status[ship.id] = "returnSuicide"
            
        elif ship_status[ship.id] == "returning":
            if ship.position == me.shipyard.position:
                ship_status[ship.id] = "exploring"
                
        elif ship.halite_amount >= constants.MAX_HALITE / returnFlagRatio:
            ship_status[ship.id] = "returning"
            
        # if time running out head home and suicide. Need to add suicide code


        #logging.info("Ship {} is: {}; ship is this {} far with {} much time".format(ship.id, ship_status[ship.id],game_map.calculate_distance(ship.position, me.shipyard.position),(constants.MAX_TURNS - game.turn_number)))

        # For each of your ships, move randomly if the ship is on a low halite location or the ship is full.
        #   Else, collect halite.
        # check if enough fueld
        if ship.halite_amount < game_map[ship.position].halite_amount * 0.1:
            command_queue.append(ship.stay_still())
            logging.info("Ship {} is low on fueld and staying still".format(ship.id))
        
        elif (game_map[ship.position].halite_amount < constants.MAX_HALITE / collectingRatio or ship.is_full) and ship_status[ship.id] == "exploring":
            # safe random movement
            next_move = findHigherHalite(ship.position)
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

    # If the game is in the first 200 turns and you have enough halite, spawn a ship.
    # Don't spawn a ship if you currently have a ship at port, though - the ships will collide.
    if game.turn_number <= shipBuildingTurns and me.halite_amount >= constants.SHIP_COST and not game_map[me.shipyard].is_occupied:
        command_queue.append(me.shipyard.spawn())

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)

