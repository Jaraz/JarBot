import json
import logging
import sys

from .common import read_input
from . import constants
from .game_map import GameMap, Player
from .positionals import Direction, Position


class Game:
    """
    The game object holds all metadata pertinent to the game and all its contents
    """
    def __init__(self):
        """
        Initiates a game object collecting all start-state instances for the contained items for pre-game.
        Also sets up basic logging.
        """
        self.turn_number = 0

        # Grab constants JSON
        raw_constants = read_input()
        constants.load_constants(json.loads(raw_constants))

        num_players, self.my_id = map(int, read_input().split())

        logging.basicConfig(
            filename="bot-{}.log".format(self.my_id),
            filemode="w",
            level=logging.DEBUG,
        )

        self.players = {}
        for player in range(num_players):
            self.players[player] = Player._generate()
        self.me = self.players[self.my_id]
        self.game_map = GameMap._generate()
        self.haliteHistory = [self.game_map.totalHalite]
        self.allShips = None
        self.enemyShips = None
        self.shipCountList = None
        
        self.game_map.numPlayers = num_players
        self.game_map.dropCalc.numPlayers = num_players
        if num_players == 4:
            self.game_map.dropCalc.minHalite *= 1.5
        
    def ready(self, name):
        """
        Indicate that your bot is ready to play.
        :param name: The name of your bot
        """
        send_commands([name])

    def return_all_drop_locations(self):
        '''
        returns dropoff location for all players
        '''
        dropLocs = []
        for player in self.players:
            dropLocs.extend(self.players[player].get_all_drop_locations())
        return dropLocs

    def update_frame(self):
        """
        Updates the game object's state.
        :returns: nothing.
        """
        self.turn_number = int(read_input())
        logging.info("=============== TURN {:03} ================".format(self.turn_number))

        for _ in range(len(self.players)):
            player, num_ships, num_dropoffs, halite = map(int, read_input().split())
            self.players[player]._update(num_ships, num_dropoffs, halite)

        self.game_map._update()
        self.haliteHistory.append(self.game_map.totalHalite)

        # Mark cells with ships as unsafe for navigation
        self.game_map.emptyShipMap()
        # first populate with your own ships
        for ship in self.me.get_ships():
            self.game_map[ship.position].mark_unsafe(ship)
            self.game_map.shipMap[ship.position.y, ship.position.x] = 1
            self.game_map.myShipHalite[ship.position.y, ship.position.x] = ship.halite_amount
            self.game_map.negShipMap[ship.position.y, ship.position.x] = 1
        
        playerCount = 2
        for player in self.players.values():
            if player.id != self.me.id:
                for ship in player.get_ships():
                    self.game_map[ship.position].mark_unsafe(ship)
                    self.game_map.shipMap[ship.position.y, ship.position.x] = playerCount
                    self.game_map.enemyShipHalite[ship.position.y, ship.position.x] = ship.halite_amount
    
                self.game_map[player.shipyard.position].structure = player.shipyard
                for dropoff in player.get_dropoffs():
                    self.game_map[dropoff.position].structure = dropoff
                playerCount += 1

        #flag for enemy ships
        self.game_map.shipFlag=self.game_map.shipMap.copy()
        self.game_map.shipFlag[self.game_map.shipMap==1]=0
        self.game_map.shipFlag[self.game_map.shipMap==2]=1
        self.game_map.shipFlag[self.game_map.shipMap==3]=1
        self.game_map.shipFlag[self.game_map.shipMap==4]=1
        
        self.game_map.updateInspirationMatrix()
        if len(self.players.values())>1:
            self.game_map.updateNegInspirationMatrix()
        else:
            self.game_map.enemyShipCount = self.game_map.shipMap.copy()
        
        
        #logging.info("Ship locations {}".format(self.game_map.shipMap))
        #logging.info("Enemy flag {}".format(self.game_map.shipFlag))
        #logging.info("Inspiration {}".format(self.game_map.inspirationBonus))
        
        # Update enemy ships and all ships
        self.enemyShips = []
        self.playerScores = []
        self.playerScores.append(self.me.halite_amount)
        
        self.shipCountList = []
        self.shipCountList.append(self.me.get_ship_count())
        
        for player in self.players:
            for i in self.players[player].get_ships():
                self.game_map[i.position].occupado = True
            if player != self.me.id:
                self.playerScores.append(self.players[player].halite_amount)
                self.shipCountList.append(self.players[player].get_ship_count())
                self.enemyShips.extend([i for i in self.players[player].get_ships() if i.position not in self.players[self.my_id].get_all_drop_locations()])
        #logging.info("player scores".format(self.playerScores))
        
        self.adjEnemyShips = []
        
        # update drop distances
        #self.game_map.updateDropDistances(self.players[self.my_id].get_all_drop_locations())
        self.game_map.updateDropDistances(self.players[self.my_id].get_dropoff_locations())
        self.game_map.updateDropDistancesAll(self.players[self.my_id].get_all_drop_locations())
        
        # update dropoff bonus matrix
        self.game_map.updateDropOffMatrix(self.players[self.my_id].get_dropoffs(), 7)
        #logging.info("drop it {}".format(self.game_map.dropOffBonus.tolist()))

        # update enemy mask
        if len(self.players)==2 or len(self.players)==4:
            self.game_map.updateNearbyEnemyShips()
            self.game_map.updateEnemyMask()
            #logging.info("nearbyEnemy {}".format(self.game_map.nearbyEnemyShip))

        self.game_map.turnNumber = self.turn_number

    @staticmethod
    def end_turn(commands):
        """
        Method to send all commands to the game engine, effectively ending your turn.
        :param commands: Array of commands to send to engine
        :return: nothing.
        """
        send_commands(commands)


def send_commands(commands):
    """
    Sends a list of commands to the engine.
    :param commands: The list of commands to send.
    :return: nothing.
    """
    print(" ".join(commands))
    sys.stdout.flush()
