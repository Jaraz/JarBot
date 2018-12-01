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
        
    def ready(self, name):
        """
        Indicate that your bot is ready to play.
        :param name: The name of your bot
        """
        send_commands([name])

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
        for player in self.players.values():
            for ship in player.get_ships():
                self.game_map[ship.position].mark_unsafe(ship)
                self.game_map.shipMap[ship.position.y, ship.position.x] = player.id + 1

            self.game_map[player.shipyard.position].structure = player.shipyard
            for dropoff in player.get_dropoffs():
                self.game_map[dropoff.position].structure = dropoff

        #logging.info("Ship locations {}".format(self.game_map.shipMap))
        
        # Update enemy ships and all ships
        self.enemyShips = []
        for player in self.players:
            for i in self.players[player].get_ships():
                self.game_map[i.position].occupado = True
            if player != self.me.id:
                self.enemyShips.extend(self.players[player].get_ships())
        for i in self.enemyShips:
            self.game_map[i.position].mark_enemy_ship(i)
            #logging.info("Enemy identified {}".format(i))
            
            # ship info
            haliteAtEnemy = self.game_map[i.position].halite_amount
                
            # guess enemy movement, skip if he is on a lot of halite and empty
            if len(self.players) > 3 and haliteAtEnemy < self.game_map.averageHalite:
                self.game_map[self.game_map.normalize(i.position + Position(1,0))].mark_enemy_ship(i)
                self.game_map[self.game_map.normalize(i.position + Position(0,1))].mark_enemy_ship(i)
                self.game_map[self.game_map.normalize(i.position + Position(-1,0))].mark_enemy_ship(i)
                self.game_map[self.game_map.normalize(i.position + Position(0,-1))].mark_enemy_ship(i)
                

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
