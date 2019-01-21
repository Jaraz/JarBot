import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
from .dropCalc import dropCalc
import logging
import numpy as np
from scipy import optimize
from scipy import ndimage, misc
from collections import deque
import random
import timeit

def get_wrapped(matrix, startX, startY, width):
    m, n = matrix.shape
    rows = []
    cols = []
    for i in range(-1,width*2):
        rows.append(startX-(width-i) % m)
        cols.append(startY-(width-i) % n)
    return matrix[rows][:, cols]


class MapCell:
    """A cell on the game map."""
    def __init__(self, position, halite_amount):
        self.occupado = False
        self.position = position
        self.halite_amount = halite_amount
        self.ship = None
        self.structure = None
        self.enemyShip = None
        self.enemyLikelyHood = 0 # [0,1] odds an enemy steps on this spot next turn
        self.avgHalite = 0

    @property
    def is_empty(self):
        """
        :return: Whether this cell has no ships or structures
        """
        return self.ship is None and self.structure is None

    @property
    def is_occupied(self):
        """
        :return: Whether this cell has any ships
        """
        return self.ship is not None

    @property
    def has_structure(self):
        """
        :return: Whether this cell has any structures
        """
        return self.structure is not None

    @property
    def structure_type(self):
        """
        :return: What is the structure type in this cell
        """
        return None if not self.structure else type(self.structure)

    def mark_unsafe(self, ship):
        """
        Mark this cell as unsafe (occupied) for navigation.

        Use in conjunction with GameMap.naive_navigate.
        """
        self.ship = ship

    def mark_enemy_ship(self,ship):
        self.enemyShip = ship
    
    def is_enemy(self):
        return self.enemyShip is not None

    def __eq__(self, other):
        return self.position == other.position

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return 'MapCell({}, halite={})'.format(self.position, self.halite_amount)


class GameMap:
    """
    The game map.

    Can be indexed by a position, or by a contained entity.
    Coordinates start at 0. Coordinates are normalized for you
    """
    def __init__(self, cells, width, height):
        self.width = width
        self.height = height
        self._cells = cells
        self.totalHalite = 0
        self.haliteRegion = 0
        self.haliteData = [0] * (self.width * self.height)
        self.turnsLeft = 500
        self.turnNumber = 0
        self.optimalDrops = []
        self.numPlayers = 2
        
        # ship map is a simmple 1 or 0 label for which cell has a ship
        self.shipMap = np.zeros([self.width, self.height], dtype=np.int)
        self.shipFlag = np.zeros([self.width, self.height], dtype=np.int)
        self.smoothInspirationMap = np.zeros([self.width, self.height], dtype=np.float)
        self.friendlyShipCount = np.zeros([self.width, self.height], dtype=np.int)
        self.enemyShipCount = np.zeros([self.width, self.height], dtype=np.int)
        self.enemyShipHalite = np.zeros([self.width, self.height], dtype=np.int)
        self.enemyMiningNext = np.zeros([self.width, self.height], dtype=np.int)
        self.inspirationBonus = np.zeros([self.width, self.height], dtype=np.int)
        self.dropOffBonus = np.zeros([self.width, self.height], dtype=np.int)
        self.myShipHalite = np.zeros([self.width, self.height], dtype=np.int)
        
        # variables to avoid some enemies
        self.minedNextTurn = np.zeros([self.width, self.height], dtype=np.int)
        self.enemyMask = np.zeros([self.width, self.height], dtype=np.int) # avoid these zones, risk of attack
        
        # negative inspiration check for 2 player
        # updated once per turn, telling me all cells currently getting the bonus
        self.negInspirationBonus = np.zeros([self.width, self.height], dtype=np.int)
        self.negShipMap = np.zeros([self.width, self.height], dtype=np.int)
        
        # build numpy map
        self.npMap = np.zeros([self.width, self.height], dtype=np.int) 
        self.npMapOld = np.zeros([self.width, self.height], dtype=np.int) 
        for y in range(self.height):
            for x in range(self.width):
                self.npMap[y][x] = self[Position(x,y)].halite_amount
        self.npMapDistance = self.buildDistanceMatrix()
        
        self.startingHalite = np.sum(self.npMap)
        
        self.smoothSize = 3
        self.smoothMap = ndimage.uniform_filter(self.npMap, size = self.smoothSize, mode = 'wrap')
        
        #logging.info("np map {}".format(self.npMap))
        #logging.info("smooth map {}".format(self.smoothMap))
        
        # init drop calc
        self.dropCalc = dropCalc(5, self.npMap, self.smoothMap, 400, 75, 1) 


        self.totalHalite = np.sum(self.npMap)
        self.averageHalite = np.mean(self.npMap)
        self.stdDevHalite = np.std(self.npMap)
        #logging.info("Total {}, avg {}, stdev {}".format(self.totalHalite, self.averageHalite, self.stdDevHalite))
        
        # precompute normalized distances
        self.directionMatrix = np.zeros([self.width, self.height, 4, 2], dtype=np.int)
        directions = [Direction.North, Direction.East, Direction.South, Direction.West]
        for y in range(self.height):
            for x in range(self.width):
                startPos = Position(y,x)
                for i in range(4):
                    endPos = self.normalize(startPos.directional_offset(directions[i]))
                    self.directionMatrix[y][x][i][0] = endPos.x
                    self.directionMatrix[y][x][i][1] = endPos.y

        # precompute start adn end distances [x][y] is start, to [q][p] returns a scalar manhattan distance
        # count space for each part of matrix
        self.matrixID = np.zeros([self.width, self.height], dtype = np.int)
        matrixCount = 0

        self.distanceMatrix = np.zeros([self.width, self.height, self.width, self.height], dtype=np.int)
        for y in range(self.height):
            for x in range(self.width):
                startPos = Position(y,x)
                self.distanceMatrix[y][x] = self.calcDistanceMatrix(startPos)
                self.matrixID[y][x] = matrixCount
                matrixCount += 1
        
        # avoid code to connect search and movement allocation
        self.avoid = np.zeros([1000, self.width, self.height], np.int)
        
        # distances to dropoff locations
        self.dropDistances = np.ones([10, self.width, self.height]) * 200
        self.dropDistancesAll = np.ones([10, self.width, self.height]) * 200
        
        self.distanceMatrixNonZero = self.distanceMatrix.copy()
        self.distanceMatrixNonZero[self.distanceMatrixNonZero==0] = 1
        #self.distanceMatrixNonZero = 1/self.distanceMatrixNonZero
        #logging.info("distanceMatrix {}".format(self.distanceMatrix))

        #logging.info("matrix count {}".format(self.matrixID))
        
        # negative inspiration variables
        self.shiftShipTensor = np.zeros([self.width, self.height, self.width, self.height], dtype=np.int)
        
        # mining
        self.haliteHistory = np.zeros([500])
        self.miningHistory = np.zeros([500])
        self.miningMA = np.zeros([500])
        self.haliteHistory[0] = np.sum(self.npMap)
        
        # how long till spot is inspired (look at one hsip for now)
        #self.waitTillInsp = np.zeros([self.width, self.height], dtype = np.int)
        # check if an enemy is within this distance
        #self.distTillInsp = self.distanceMatrixNonZero.copy()
        #self.distTillInsp = self.distTillInsp.astype(np.float)
        #self.distTillInsp[self.distTillInsp>8] = 0
        #self.distTillInsp[self.distTillInsp<=4] = 0

        
        # precompute 1 distance
        self.dist1 = self.distanceMatrixNonZero.copy()
        self.dist1[self.dist1>1] = 0
                
        # precompute distance for averaging
        self.dist4 = self.distanceMatrixNonZero.copy()
        self.dist4[self.dist4>4] = 0
        
        self.dist4Indicator = self.dist4.copy()
        self.dist4Indicator[self.dist4Indicator>4] = 0
        self.dist4Indicator[self.dist4Indicator>0] = 1

        self.dist4Discount = self.distanceMatrix.copy()
        self.dist4Discount[self.dist4Discount>4] = 0
        self.dist4Discount = self.dist4Discount.astype(np.float)
        self.dist4Discount[self.dist4Discount>0] = 1/(self.dist4Discount[self.dist4Discount>0] * (self.dist4Discount[self.dist4Discount>0]))

        self.dist16Indicator = self.distanceMatrixNonZero.copy()
        self.dist16Indicator[self.dist16Indicator>16] = 0
        self.dist16Indicator[self.dist16Indicator>1] = 1

        self.haliteRegBene4x = 0.25
        self.distaceDenom = 1000
        
        self.haliteCollectionTarget = 1000
        
        #self.negInspWindow = self.width / 8 + 1
        #self.distNegInsp = self.distanceMatrixNonZero.copy()
        #self.distNegInsp[self.distNegInsp > self.negInspWindow] = 0
        #self.distNegInsp[self.distNegInsp > 1] = 1
        
        self.attackThreshold = 0.3
        
        if self.width == 40:
            self.haliteRegBene4x = 0.25
            self.distaceDenom = 950
            self.attackThreshold = 0.275
        elif self.width == 48:
            self.haliteRegBene4x = 0.25
            self.distaceDenom = 900
            self.attackThreshold = 0.25
        elif self.width == 56:
            self.haliteRegBene4x = 0.25
            self.distaceDenom = 850
            self.attackThreshold = 0.225
        elif self.width == 64:
            self.haliteRegBene4x = 0.25
            self.distaceDenom = 800
            self.attackThreshold = 0.2
        
    def __getitem__(self, location):
        """
        Getter for position object or entity objects within the game map
        :param location: the position or entity to access in this map
        :return: the contents housing that cell or entity
        """
        if isinstance(location, Position):
            location = self.normalize(location)
            return self._cells[location.y][location.x]
        elif isinstance(location, Entity):
            return self._cells[location.position.y][location.position.x]
        return None
    
    
    '''    
    def updateOptimalDrops(self, distance):
        cutOff = np.percentile(self.smoothMap,)
        topSpots = self.smoothMap.copy()
        topSpots = topSpots[topSpots>]
        
        return 0
    '''
    def updateSmoothSize(self, smoothSize):
        self.smoothSize = smoothSize
    
    def updateNegativeInspiration(self):
        return 0
    
    def updateNearbyEnemyShips(self):
        '''
        for a given cell this matrix shows teh smallest neighboring enemy
        '''
        self.nearbyEnemyShip = np.zeros([self.width, self.height], dtype=np.int)
        self.nearbyEnemyShipCount = np.zeros([self.width, self.height], dtype=np.int)
        
        tempEnemyHalite = self.enemyShipHalite + self.shipFlag # if no halite, need to make it 1
        
        # find minimum of nearby ships
        north = np.roll(tempEnemyHalite,1,0)
        south = np.roll(tempEnemyHalite,-1,0)
        east = np.roll(tempEnemyHalite,-1,1)
        west = np.roll(tempEnemyHalite,1,1)
        
        north[north==0] = 1000000
        south[south==0] = 1000000
        east[east==0] = 1000000
        west[west==0] = 1000000
        
        self.nearbyEnemyShipCount = np.roll(self.shipFlag,1,0) + np.roll(self.shipFlag,-1,0) + np.roll(self.shipFlag,-1,1) + np.roll(self.shipFlag,1,1)
        self.nearbyEnemyShip = np.minimum(north, np.minimum(south,np.minimum(east,west)))
        self.nearbyEnemyShip[self.nearbyEnemyShip==1000000]=0
        logging.info("nearby enemy ship count {}".format(self.nearbyEnemyShipCount.shape))
    
    def updateInspirationMatrix(self):
        self.enemyShipCount = np.einsum('ijkl,lk',self.dist4Indicator,self.shipFlag)
        res = self.enemyShipCount.copy()
        res[res<=1] = 0
        res[res>1] = 1
        self.inspirationBonus = res
        
        self.miningSpeed = self.inspirationBonus.copy()
        self.miningSpeed = self.miningSpeed.astype(np.float)
        self.miningSpeed[self.miningSpeed<1] = .25
        self.miningSpeed[self.miningSpeed>.99] = .75
        self.dropCalc.updateMiningSpeed(self.miningSpeed)
        #self.smoothInspirationMap = ndimage.uniform_filter(self.npMap*self.miningSpeed, size = 3, mode = 'wrap')
        
        #logging.info("dist2 {}".format(dist2[0][0]))
        #temp = self.npMap*self.miningSpeed
        if self.numPlayers == 2:
            tempSpeed = self.miningSpeed.copy()
            tempSpeed[self.miningSpeed==0.75]=0.75
            tempSpeed[self.miningSpeed==0.25]=0.25
        else:
            tempSpeed = self.miningSpeed.copy()
            tempSpeed[self.miningSpeed==0.25]=self.haliteRegBene4x
        self.smoothInspirationMap = np.einsum('ijkl,lk',self.dist4Discount,self.npMap*tempSpeed)/np.sum(self.dist4Discount[0][0])
        
        
        # calc wait till inspiration, assuming 1 ship enemy distance for now
        '''
        if self.numPlayers==5:
            self.waitTillInsp = np.einsum('ijkl,lk',self.distTillInsp,self.shipFlag)
            self.waitTillInsp[self.waitTillInsp>0] = 1
            self.waitTillInsp[self.inspirationBonus==1] = 0
            #logging.info("wit till insp)
        '''
        #self.smoothInspirationMap = ndimage.gaussian_filter(self.npMap*self.miningSpeed, sigma = 3, mode = 'wrap')
        #temp = self.npMap*self.miningSpeed
        #logging.info("halite map \n {} \n smooth \n {}".format(temp.astype(np.int), self.smoothInspirationMap.astype(np.int)))
       
    def updateNegInspirationMatrix(self):
        ships = self.shipMap.copy()
        ships[ships>1] = 0
        self.friendlyShipCount = np.einsum('ijkl,lk',self.dist4Indicator,ships)
        res = self.friendlyShipCount.copy()
        res[res<=1] = 0
        res[res>1] = 1
        self.negInspirationBonus = res
        #logging.info("Neg inspiration \n{}".format(self.negInspirationBonus))
        
        self.enemyMiningNext = self.shipFlag * self.npMap * (0.25 + 0.5 * self.negInspirationBonus)
        
    def returnFriendlyCount(self, pos, width):
        countMap = self.shipMap.copy()
        dist = self.distanceMatrixNonZero[pos.x][pos.y]
        
        countMap[self.shipMap>1] = 0
        countMap[dist > width] = 0
        return np.sum(countMap)-1
    
    def updateDropOffMatrix(self, drops, bonusDist):
        for drop in drops:
            x = drop.position.x
            y = drop.position.y
            dist = self.distanceMatrixNonZero[y][x].copy()
            dist[dist>bonusDist]=0
            dist[dist>0]=1
            self.dropOffBonus += dist
            
            # cap bonus to one dropoff
            self.dropOffBonus[self.dropOffBonus>1] = 1
            
    def updateDropDistances(self, locations):
        #logging.info("locs {}".format(locations))
        for i in range(len(locations)):
            loc = locations[i]
            self.dropDistances[i] = self.distanceMatrix[loc.x][loc.y]
        #logging.info("drops {}".format(self.dropDistances))
    
    def updateDropDistancesAll(self, locations):
        #logging.info("locs {}".format(locations))
        for i in range(len(locations)):
            loc = locations[i]
            self.dropDistancesAll[i] = self.distanceMatrix[loc.x][loc.y]
    
    def emptyShipMap(self):
        self.shipMap = np.zeros([self.width, self.height], dtype=np.int)
        self.shipFlag = np.zeros([self.width, self.height], dtype=np.int)
        self.inspirationBonus = np.zeros([self.width, self.height], dtype=np.int)
        self.enemyShipHalite = np.zeros([self.width, self.height], dtype=np.int)        
        self.myShipHalite = np.zeros([self.width, self.height], dtype=np.int)

    def buildDistanceMatrix(self):
        '''
        at start of game, create array [x,y] which returns manhattan distance to all points on the map from x,y
        for use in distance heuristic
        '''
        dist = np.zeros((self.width, self.height), dtype=int)
        
        for x in range(self.width):
            for y in range(self.height):
                min_x = min((x - 0) % self.width, (0 - x) % self.width)
                min_y = min((y - 0) % self.height, (0 - y) % self.height)
                dist[x, y] = min_x + min_y
        return dist

    def returnDistanceMatrix(self, source, zeroFlag = False):
        '''
        return distance from source across the entire map
        Zero flag true means don't return a zero when distance is zero, return 1. fix division by zero issue
        '''
        if zeroFlag:
            results = self.distanceMatrixNonZero[source.x][source.y]    
        else:
            results = self.distanceMatrix[source.x][source.y]
        return results
    
    def calcDistanceMatrix(self, source):
        '''
        return distance from source across the entire map
        Zero flag true means don't return a zero when distance is zero, return 1. fix division by zero issue
        '''
        results = np.roll(np.roll(self.npMapDistance,source.x,1), source.y,0)
        return results


    def get_near_stats(self, source, width):
        '''
        return avg and stdev of halite around a source position
        ''' 
        subMatrix = get_wrapped(self.npMap, source.x, source.y, width)
        return np.mean(subMatrix), np.std(subMatrix)
    
    def findOptimalMoves(self, ships, destinations, dropoffs, status, enemyLocs):
        '''
        given a vector of ships and destinations will find optimal moves next turn
        '''
        turnMatrix = np.zeros([len(ships), self.width * self.height])
        moveStatus = ["exploring","returning","returnSuicide", "attack", "build depo"]
        shipPosList = []
        for ship in ships:
            shipPosList.append(ship.position)
        
        issueFlag = True
        loopCounter = 1
        issueList = []
        maxLoop = 5
        if self.width > 60:
            maxLoop = 4
            if self.numPlayers==4:
                maxLoop = 4
            if self.turnsLeft <50:
                maxLoop = 5
        

        while issueFlag and loopCounter < maxLoop:
            #logging.info("loop {}".format(loopCounter))
            #logging.info("issue list {}".format(issueList))

            for i in range(len(ships)):
                shipMap = np.zeros([self.width, self.height], np.int)       
                halite = ships[i].halite_amount
                if halite < 10:
                    halite = 10
                shipID = ships[i].id
                pos = ships[i].position
                x = ships[i].position.x
                y = ships[i].position.y
                
                # should we move
                if status[ships[i].id] in moveStatus:
                    distToDest   = self.distanceMatrix[pos.y][pos.x][destinations[shipID].x][destinations[shipID].y]
                    leftOnly = False
                    rightOnly = False
                    upOnly = False
                    downOnly = False
                    
                    # logic
                    # 1 - for backwards move
                    # 2 = stay still
                    # halite otherwise
                    # if you are on dropoff you are VIP!
                    
                    # Need to get ships off dropoffs
                    if pos in dropoffs:
                        shipMap[y,x] = 1
                        halite = 10000
                    elif destinations[shipID] == pos:
                        shipMap[y,x] = halite
                    # needs safety
                    elif shipID in issueList:
                        logging.info("ship {} trying to survive".format(shipID))
                        halite = 10000
                        shipMap[y,x] = 10000
                    elif status[shipID] == 'build depo' and pos == destinations[shipID]:
                        shipMap[y,x] = 100000
                    # encourage to stay if target destination is empty right now
                    elif destinations[shipID] not in shipPosList:
                        shipMap[y,x] = 6
                    else: 
                        shipMap[y,x] = halite
                        
                    # is goal directly n,s,e,w?
                    up = Position(self.directionMatrix[pos.x][pos.y][0][0],self.directionMatrix[pos.x][pos.y][0][1])
                    right = Position(self.directionMatrix[pos.x][pos.y][1][0],self.directionMatrix[pos.x][pos.y][1][1])
                    down = Position(self.directionMatrix[pos.x][pos.y][2][0],self.directionMatrix[pos.x][pos.y][2][1])
                    left  = Position(self.directionMatrix[pos.x][pos.y][3][0],self.directionMatrix[pos.x][pos.y][3][1])
                    leftDist = self.distanceMatrix[left.y][left.x][destinations[shipID].x][destinations[shipID].y]
                    rightDist = self.distanceMatrix[right.y][right.x][destinations[shipID].x][destinations[shipID].y]
                    upDist = self.distanceMatrix[up.y][up.x][destinations[shipID].x][destinations[shipID].y]
                    downDist = self.distanceMatrix[down.y][down.x][destinations[shipID].x][destinations[shipID].y]
    
                    # Directions
                    if leftDist < distToDest and upDist > distToDest and downDist > distToDest:
                        leftOnly = True
                    elif upDist < distToDest and rightDist > distToDest and leftDist > distToDest:
                        upOnly = True
                    elif rightDist < distToDest and upDist > distToDest and downDist > distToDest:
                        rightOnly = True
                    elif downDist < distToDest and rightDist > distToDest and leftDist > distToDest:
                        downOnly = True
                        
                    # try to reduce movement costs (if possible); now incorporates enemy ship (try to avoid if possible)
                    if status[shipID] == 'returnSuicide' or status[shipID] == 'returning':
                        northHalite = random.randint(1,2) + (10 - self.npMap[(y) % self.width,(x-1) % self.height]/100) - self.nearbyEnemyShip[(y) % self.width,(x-1) % self.height]
                        southHalite = random.randint(1,2) + (10 - self.npMap[(y) % self.width,(x+1) % self.height]/100) - self.nearbyEnemyShip[(y) % self.width,(x+1) % self.height]
                        westHalite = random.randint(1,2) + (10 - self.npMap[(y-1) % self.width,(x) % self.height]/100) - self.nearbyEnemyShip[(y-1) % self.width,(x) % self.height]
                        eastHalite = random.randint(1,2) + (10 - self.npMap[(y+1) % self.width,x % self.height]/100) - self.nearbyEnemyShip[(y+1) % self.width,x % self.height]
                    else:
                        northHalite = random.randint(1,2) - self.nearbyEnemyShip[(y) % self.width,(x-1) % self.height]/1000*2
                        southHalite = random.randint(1,2) - self.nearbyEnemyShip[(y) % self.width,(x+1) % self.height]/1000*2
                        westHalite = random.randint(1,2) - self.nearbyEnemyShip[(y-1) % self.width,(x) % self.height]/1000*2
                        eastHalite = random.randint(1,2) - self.nearbyEnemyShip[(y+1) % self.width,x % self.height]/1000*2

                    #logging.info("ship {}, dist {}, l {}, r {}, u {}, d{}".format(shipID, distToDest, leftDist, rightDist, upDist, downDist))

                    # NORTH
                    if status[shipID] == "attack" and left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 10000
                    elif left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 0
                    elif leftDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + northHalite #random.randint(1,2) 
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + northHalite # random.randint(1,2) 
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x-1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x-1) % self.height] = 2
                    #logging.info("left ship {} map {}".format(ships[i].id, shipMap))
    
                    # SOUTH
                    if status[shipID] == "attack" and right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 10000
                    elif right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 0
                    elif rightDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + southHalite #random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + southHalite # random.randint(1,2)
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x+1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x+1) % self.height] = 2
                    #logging.info("right ship {} map {}".format(ships[i].id, shipMap))
                    
                    # WEST
                    if status[shipID] == "attack" and up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 10000
                    elif up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 0
                    elif upDist < distToDest: # moves us closer 
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + westHalite #random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + westHalite # random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y-1) % self.width,(x) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y-1) % self.width,(x) % self.height] = 2
                    #logging.info("up ship {} map {}".format(ships[i].id, shipMap))
    
                    # EAST
                    if status[shipID] == "attack" and down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 10000
                    elif down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 0
                    elif downDist < distToDest: # moves us closer 
                        shipMap[(y+1) % self.width,x % self.height] = halite + eastHalite #random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y+1) % self.width,x % self.height] = halite + eastHalite #random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y+1) % self.width,x % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y+1) % self.width,x % self.height] = 2
                # or mine and stay still
                else:
                    shipMap[y,x] = 100000
                

                    
                # if you are returning halite and its a 4 player game, avoid all spots neighboring an enemy ship
                if self.numPlayers == 4 and (status[shipID] == 'returnSuicide' or status[shipID] == 'returning'):
                    shipMap -= np.sign(self.nearbyEnemyShip) * 10000
                    shipMap[y,x] += np.sign(self.nearbyEnemyShip[y,x]) * 10000
                    
                    # make sure dropoff is never blocked
                    for drop in dropoffs:
                        shipMap[drop.y,drop.x] += np.sign(self.nearbyEnemyShip[drop.y,drop.x]) * 10000
                    
                    shipMap[shipMap < 0] = 0
                    
                    # if no choice stand still
                    if shipID in issueList:
                        shipMap[y,x] = 50000
                
                if self.numPlayers == 4 and (status[shipID] == 'exploring' or status[shipID] == 'build depo'):
                    # need to ensure avoid only gives locations next to ship
                    shipMap -= self.avoid[shipID] * 10000
                    shipMap[shipMap < 0] = 0
                                                        
                #logging.info("shipo {} shipMap {}".format(shipID, shipMap))
                turnMatrix[i,:] = shipMap.ravel()
                #logging.info("ship {} map {}".format(ships[i].id, shipMap))
    
            # solve for correct moves
            # reduce matrix size
            matrixLabels = self.matrixID.copy().ravel() # which cell teh destination will be 
            #logging.info("matrix label {} ravel {}".format(self.matrixID, matrixLabels))
            #logging.info("turn matrx {}".format(turnMatrix))
            turnColumnSum = turnMatrix.sum(axis=0)
            #logging.info("turn reduced {}".format(turnColumnSum))
            #logging.info("matrixOrig {}".format(matrixLabels[turnColumnSum!=0]))
            matrixLabels[turnColumnSum==0] = 0
            
            solveMatrix = turnMatrix[:, ~np.all(turnMatrix == 0, axis = 0)]
            matrixLabelsFinal = matrixLabels[turnColumnSum!=0]
            #logging.info("matrixLabel {}".format(matrixLabelsFinal))
            
            #logging.info("solve matrix {}".format(solveMatrix))
            row_ind, col_ind = optimize.linear_sum_assignment(-solveMatrix)
            #logging.info("row ind {} ---- col_ind {}".format(row_ind, col_ind))
            
            # check each position to make sure solution is possible if not you have an issue
            
            #logging.info("around list {}".format(aroundList))
            issueFlag = False
            for i in range(len(ships)):
                posCheck = Position(matrixLabelsFinal[col_ind[i]] % self.width, int(matrixLabelsFinal[col_ind[i]]/self.width))
                aroundList = self.get_surrounding_cardinals(posCheck,1)
                if ships[i].position not in aroundList:
                    issueList.append(ships[i].id)
                    issueFlag = True
                    #logging.info("ship {} in danger".format(ships[i].id))
            
            loopCounter += 1
                
        
        # convert to ship orders
        orders = {}
        for i in range(len(ships)):
            pos = ships[i].position
            
            crashLand = False
            dropOffTarget = None
            # help crash at the end
            if status[ships[i].id] == "returnSuicide":
                surrounding = ships[i].position.get_surrounding_cardinals()
                for j in dropoffs:
                        if j in surrounding:
                            crashLand = True
                            dropOffTarget = j
            if crashLand == False:
                nextMove = Position(matrixLabelsFinal[col_ind[i]] % self.width, int(matrixLabelsFinal[col_ind[i]]/self.width))
                #logging.info("ship {} to {}".format(ships[i].id, nextMove))
            else:
                nextMove = dropOffTarget
            #logging.info("ship {} next move to {}".format(ships[i].id, nextMove))
            if nextMove == pos:
                orders[ships[i].id] = Direction.Still
            else:
                orders[ships[i].id] = self.get_unsafe_moves(pos, nextMove)[0]
        return orders
    
    def matchShipsToDest2(self, ships, moveFlag, minHalite= 0, hChoice = 'sqrt', collectingStop=50):
        '''
        The eyes of JarBot
        need to add penalty when another ship is on a spot already
        halite excluded form search if its below minHalite 
        '''
        distMatrix = np.zeros([len(ships), self.width*self.height], dtype=np.int)
        distResults = np.zeros([len(ships), self.width*self.height], dtype=np.int)
        
        # remove taken spots from the solver
        tempMap = self.shipMap.copy()
        if self.numPlayers==2 and self.turnNumber > 100:
            tempMap[self.shipMap==2]=0
        if self.numPlayers==4 and self.turnNumber > 500:
            tempMap[self.shipMap==2]=0
            tempMap[self.shipMap==3]=0
            tempMap[self.shipMap==4]=0
        haliteMap = self.npMap - 1000 * tempMap
        
        #add back 1k ships (assumes they move only for 2p)
        if self.numPlayers==2:
            tempMap2 = self.myShipHalite.copy()
            tempMap2[self.myShipHalite!=1000]=0
            tempMap2[self.myShipHalite==1000]=1
            haliteMap += 1000 * tempMap2
        
        finalMap = haliteMap.copy()
        
        #if self.turnsLeft < 300 and max(self.shipMap.flatten())==4:
        #    haliteMap = haliteMap * (1 + self.inspirationBonus*2)
        
        haliteMap[haliteMap<1] = 1

        # taking into account mining speed
        miningSpeed = self.inspirationBonus.copy()
        miningSpeed = miningSpeed.astype(np.float)
        if self.numPlayers == 2:
            miningSpeed[miningSpeed<1] = .25
            miningSpeed[miningSpeed>.99] = .75
        else:
            miningSpeed[miningSpeed<1] = self.haliteRegBene4x
            miningSpeed[miningSpeed>.99] = .75
        
        if self.numPlayers==2:
            miningSpeed[(self.negInspirationBonus==0) & (self.inspirationBonus==1)]=0.75
            miningSpeed[(self.negInspirationBonus==1) & (self.inspirationBonus==1)]=0.75
        
        #miningSpeed[(self.friendlyShipCount<=1) & (self.inspirationBonus==1)] = 0.75
        #miningSpeed[(self.enemyShipCount>self.friendlyShipCount) & (self.friendlyShipCount>1)]=0.25
        #miningSpeed2 = miningSpeed.copy()
        #miningSpeed2[miningSpeed2==0.75]=0.25
        #if self.turnNumber > 50:
        #    miningSpeed2=0
        #logging.info("miningSpeed2 {}".format(miningSpeed2))
        depoDistAll = self.dropDistancesAll.min(0) # includes yard + depo
        haliteMap = haliteMap - collectingStop
        haliteMap[haliteMap<collectingStop] = 1


        enemyShipMoveAmt = 250
        tempShipMatrix = self.nearbyEnemyShip.copy()
        tempShipMatrix[(self.enemyMiningNext>enemyShipMoveAmt) & (self.nearbyEnemyShipCount == 1)] -= self.nearbyEnemyShip[(self.enemyMiningNext>enemyShipMoveAmt) & (self.nearbyEnemyShipCount == 1)]
        #logging.info("help meh {}".format(self.nearbyEnemyShip[(self.enemyMiningNext>enemyShipMoveAmt) & (self.nearbyEnemyShipCount == 1)]))
        #logging.info("NES {}".format(self.nearbyEnemyShip))
        #logging.info("TSM {}".format(tempShipMatrix))

        # negative inspiration check for 2p
        # this is the penalty if you give a bonus at that square
        #negInspirationPenalty = np.einsum('ijkl,lk',self.dist4Indicator,self.shipFlag * self.npMap) * 0.5
        #negInspirationPenalty[self.negInspirationBonus==1]=0
        #negInspirationPenalty[self.friendlyShipCount<=1]=0

        for i in range(len(ships)):
            shipID = ships[i].id
            shipX = ships[i].position.x
            shipY = ships[i].position.y
            dist = self.distanceMatrix[ships[i].position.x][ships[i].position.y] #+ depoDist
            distNZ = self.distanceMatrixNonZero[ships[i].position.x][ships[i].position.y] #+ depoDist

            # can't see bad inspiration zones from afar
            #miningSpeed[self.dist4Indicator[shipX,shipY]==1]=.25


            # take into account enemy zone of control
            # avoid these spots, you will be killed
            if self.numPlayers==2:
                avoid = 1 * (np.sign(self.nearbyEnemyShip) * (ships[i].halite_amount + self.minedNextTurn) > self.nearbyEnemyShip)
                avoid *= self.enemyZoC
                
                #logging.info("ship {} enemyZoc \n {} \n avoid \n {}".format(shipID, self.enemyZoC, avoid))
            else:
                # avoid spots where enemy is not likely to go b/c:
                #   1) he is making more by staying (vs moving one and mining)
                #   2) our ship has less halite (and thus less to lose) by moving
                
                # set avoid to all neighboring zones
                # check if the enemy won't move b/c of mining
                avoid = np.sign(tempShipMatrix)

                ### (2) ###
                # take into account how much they will mine
                #avoid -= 1 * (self.nearbyEnemyShip - 750*(self.freeHalite-0.4)> ships[i].halite_amount)
                #avoid -= 1 * (self.nearbyEnemyShip + 600*(self.freeHalite-0.6)> ships[i].halite_amount)
                
                if self.width==56:
                    multiplier = 500
                elif self.width==64:
                    multiplier = 500
                else:
                    multiplier = 500

                    
                avoid -= 1 * (self.nearbyEnemyShip - multiplier*(self.freeHalite*self.freeHalite)> ships[i].halite_amount)
                avoid[avoid<0]=0
                avoid = avoid.astype(np.int)
                self.avoid[shipID] = avoid # to be used in resolve movement function

            finalMap = haliteMap.copy()
            finalMap = finalMap.astype(np.float)
            # add back current ship from earlier subtraction of friendlies
            finalMap[shipY, shipX] += self.npMap[shipY, shipX] 
            #finalMap2 = finalMap.copy()
            finalMap *= miningSpeed
            #finalMap2 *= miningSpeed2

            # add costs to other squares
            if self.width > 60:
                ratio = 0.075
            elif self.width > 41:
                ratio = 0.05
            elif self.width > 39:
                ratio = 0.025
            else:
                ratio = 0.025
            finalMap -= dist * self.smoothMap[shipY, shipX] *ratio
            finalMap[(shipY) % self.width,(shipX-1) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap[(shipY) % self.width,(shipX+1) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap[(shipY-1) % self.width,(shipX) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap[(shipY+1) % self.width,(shipX) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            '''
            finalMap2 -= dist * self.smoothMap[shipY, shipX] *ratio
            finalMap2[(shipY) % self.width,(shipX-1) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap2[(shipY) % self.width,(shipX+1) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap2[(shipY-1) % self.width,(shipX) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            finalMap2[(shipY+1) % self.width,(shipX) % self.height] -= self.npMap[shipY, shipX] * 0.1 - self.smoothMap[shipY, shipX] * ratio
            '''    
            finalMap[finalMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount)
            depoDistMarginal = depoDistAll - depoDistAll[shipY][shipX]
            depoDistDecayed = depoDistMarginal*np.minimum(1, ships[i].halite_amount/1000)
            #*(1-ships[i].halite_amount/2000)

            if self.numPlayers==2 and self.width <= 40:
                denom = dist + 1 + depoDistDecayed
                denom[self.inspirationBonus==1] -= 1
                denom[denom<=1] = 1
                
                term1 = finalMap / (denom)
                term2 = np.minimum(self.haliteCollectionTarget - ships[i].halite_amount, self.smoothInspirationMap) / (denom+1)
                h = -(term1 + term2 - 5000*avoid)
                
            elif self.numPlayers==2 and self.width>40 and self.inspirationBonus[shipY][shipX]==1: #and self.negInspirationBonus[shipY][shipX]==1:
                denom = dist + 1 + depoDistDecayed
                denom[(self.inspirationBonus==1)&(self.negInspirationBonus==1)] -= 1
                #denom[self.inspirationBonus==1] -= 1
                denom[denom<=1] = 1
                
                # add negative opportunity cost
                term1 = finalMap / (denom)
                term2 = np.minimum(self.haliteCollectionTarget - ships[i].halite_amount, self.smoothInspirationMap) / (denom+1)
                '''
                term3 = finalMap.copy()
                term3[self.inspirationBonus==1] *= 1/3
                term3[(self.negInspirationBonus==0) | (self.inspirationBonus==0)]=0
                term3 *= 0 / (denom) # neg opp cost
                '''
                h = -(term1 + term2 - 5000*avoid)
                
            elif self.numPlayers == 2:
                denom = dist + 1 + depoDistDecayed
                #denom[self.friendlyShipCount<self.enemyShipCount] += 2
                #denom[(self.inspirationBonus==0)] += -1
                #denom[(self.inspirationBonus==1)&(self.negInspirationBonus==1)] += -1
                #denom[(self.inspirationBonus==1)&(self.negInspirationBonus==0)] += 1
                #denom[denom<1] = 1
                
                mineTurn1 = finalMap / denom
                
                noInspMap = self.npMap * 0.25
                tempCopyMap = noInspMap.copy()
                finalMap[finalMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount)
                '''
                finalMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - tempCopyMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn2 = (1.75 * finalMap) / (denom+1)
                finalMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 1.75*tempCopyMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn3 = (2.3125 * finalMap) / (denom+2)
                finalMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.3125*tempCopyMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn4 = (2.734375 * finalMap) / (denom+3)
                finalMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.734375*tempCopyMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn5 = (3.05 * finalMap) / (denom+4)

                
                '''
                noInspMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - tempCopyMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn2 = (1.75 * noInspMap) / (denom+1)
                noInspMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 1.75*tempCopyMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn3 = (2.3125 * noInspMap) / (denom+2)
                noInspMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.3125*tempCopyMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn4 = (2.734375 * noInspMap) / (denom+3)
                noInspMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.734375*tempCopyMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn5 = (3.05 * noInspMap) / (denom+4)
                
                term1 = np.maximum(mineTurn1, np.maximum(mineTurn2, np.maximum(mineTurn3, np.maximum(mineTurn4,mineTurn5))))
                term2 = np.minimum(self.haliteCollectionTarget - ships[i].halite_amount, self.smoothInspirationMap) / (dist+1+2+depoDistDecayed)
                #term1[(self.inspirationBonus==1)&(self.negInspirationBonus==0)] = mineTurn1[(self.inspirationBonus==1)&(self.negInspirationBonus==0)]

                '''
                term3 = finalMap.copy()
                term3[self.inspirationBonus==1] *= 1/3
                term3[(self.negInspirationBonus==0) | (self.inspirationBonus==0)]=0
                term3 *= 0 / (denom) # neg opp cost
                '''
                term3=0
                if self.numPlayers >= 3:
                    term4 = self.npMap.copy()
                    term4[term3<1]=1
                    turns = (np.log(0.1) - np.log(term4))/np.log(0.75)
                    term4 = -term4/turns*2
                    term4[self.inspirationBonus==1]=0
                else:
                    term4 = 0
                
                h = -(term1 + term2  + term3 + term4 - 5000*avoid)

                '''
                denom = dist + 1 + depoDistDecayed
                denom[self.inspirationBonus==1] -= 1
                denom[denom<=1] = 1
                
                # add negative opportunity cost
                term1 = finalMap / (denom)
                term2 = np.minimum(self.haliteCollectionTarget - ships[i].halite_amount, self.smoothInspirationMap) / (denom+1)
                term3 = finalMap.copy()
                term3[self.inspirationBonus==1] *= 1/3
                term3[(self.negInspirationBonus==0) | (self.inspirationBonus==0)]=0
                term3 *= 1 / (denom) # neg opp cost
                
                if self.numPlayers == 5:
                    term4 = self.npMap.copy()
                    term4[term4<1]=1
                    turns = (np.log(0.1) - np.log(term4))/np.log(0.75)
                    term4 = -term4/turns/2
                    term4[self.inspirationBonus==1]=0
                else:
                    term4 = 0
                    
                h = -(term1 + term2 + term4 - 5000*avoid)
                
                term1 = finalMap / (denom)
                term1a = np.minimum(950 - ships[i].halite_amount-finalMap,1.75 * finalMap) / (denom+1)
                term1Final = np.maximum(term1, term1a)

                term2 = np.minimum(950 - ships[i].halite_amount, self.smoothInspirationMap) / (denom+2)
                
                term3 = finalMap.copy()
                term3[self.inspirationBonus==1] *= 1/3
                term3[(self.negInspirationBonus==0) | (self.inspirationBonus==0)]=0
                term3 *= 2 / (denom+1) # neg opp cost
                
                h = -(term1Final + term2 + term3 - 5000*avoid)
                '''
            else:
                denom = dist + 1 + depoDistDecayed
                denom[(self.inspirationBonus==1)] -= 1
                denom[denom<=1] = 1
                tempCopyMap = finalMap.copy()
                mineTurn1 = finalMap / (denom)
                finalMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - tempCopyMap[1.75*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn2 = (1.75 * finalMap) / (denom+1)
                finalMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 1.75*tempCopyMap[2.3125*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn3 = (2.3125 * finalMap) / (denom+2)
                finalMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.3125*tempCopyMap[2.734375*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn4 = (2.734375 * finalMap) / (denom+3)
                finalMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)] = (self.haliteCollectionTarget - ships[i].halite_amount - 2.734375*tempCopyMap[3.05*tempCopyMap > (self.haliteCollectionTarget - ships[i].halite_amount)])
                mineTurn5 = (3.05 * finalMap) / (denom+4)
                
                term1 = np.maximum(mineTurn1, np.maximum(mineTurn2, np.maximum(mineTurn3, np.maximum(mineTurn4,mineTurn5))))
                #logging.info("ship {} term1 {}".format(shipID, term1.astype(np.int)))
                term2 = np.minimum(self.haliteCollectionTarget - ships[i].halite_amount, self.smoothInspirationMap) / (dist+1+2)
                #term1[(self.inspirationBonus==1)] = mineTurn1[(self.inspirationBonus==1)]
                
                if self.width < 48:
                    term1[(self.inspirationBonus==1)] = mineTurn1[(self.inspirationBonus==1)] #+ term2[(self.inspirationBonus==1)]
                
                term3 = 0
                if self.numPlayers >= 3:
                    term3 = self.npMap * 0.25 # look at per turn
                    term3 *= 2/3 # add bonus, you are taking it before someone gets the inspired bonus
                    term3 = term3/(dist+1)
                    term3[self.inspirationBonus==1]=0
                else:
                    term3 = 0
                    
                h = -(term1 + term2 + term3 - 5000*avoid)
            if self.width > 63:
                h *= self.dist16Indicator[shipX, shipY] # kill far away points
            distMatrix[i,:] = h.ravel()
            distResults[i,:] = dist.ravel()
            
        # shrink targets for 64x
        if self.width >55 and np.sum(distMatrix)>0 and self.turnsLeft > 50:
            # shrink targets
            matrixLabels = self.matrixID.copy().ravel() # which cell the destination will be 
            columnHaliteMean = distMatrix.min(0)
            trueFalseFlag = columnHaliteMean < -2
            if self.turnsLeft < 100:
                trueFalseFlag = columnHaliteMean < np.mean(columnHaliteMean)
            logging.info("len {}".format(np.sum(1*trueFalseFlag)))
            matrixLabelsFinal = matrixLabels[trueFalseFlag]
            solveMatrix = distMatrix[:,trueFalseFlag]
        else:
            solveMatrix = distMatrix
            matrixLabels = self.matrixID.copy().ravel() # which cell teh destination will be 
            matrixLabelsFinal = matrixLabels

        # find closest destination
        row_ind, col_ind = optimize.linear_sum_assignment(solveMatrix)
        
        # convert to ship orders
        orders = {}
        for i in range(len(ships)):
            orders[ships[i].id] = Position(matrixLabelsFinal[col_ind[i]] % self.width,int(matrixLabelsFinal[col_ind[i]]/self.width))

        return row_ind, col_ind, orders
    
    def findHighestSmoothHalite(self, ship, drops, depoDist, maxWidth=12):
        minPlayers = 3
        if self.numPlayers > 2:
            minPlayers = 4
        maxHalite = self.smoothMap[ship.position.y,ship.position.x]
        finalLocation = ship.position
        
        #break b/c the ship can't move
        if ship.halite_amount < self[ship.position].halite_amount * 0.1:
            return finalLocation
        
        if min([self.calculate_distance(ship.position, j) for j in drops]) < depoDist or self.dropCalc.inMaxZone(ship.position)==False:
            #logging.info("ship {} has a problem".format(ship.id))
            maxHalite = -50
        
        # need to be near a friendly ship
        shipLocs = self.shipMap.copy()
        shipLocs[shipLocs != 1] = 0
        #logging.info("ship locs {}".format(shipLocs))
        location_choices = self.get_surrounding_cardinals(ship.position, maxWidth)

        neighborDrops = []
        for drop in drops:
            neighborDrops.extend(self.get_surrounding_cardinals(drop,2))
       
        #find max halite
        for x in location_choices:
            dist = self.distanceMatrixNonZero[x.x][x.y].copy()
            dist[dist>(self.width/4)]=0
            dist[dist>0]=1
            haliteCheck = self.smoothMap[x.y,x.x]
            if haliteCheck > maxHalite and x != ship.position and \
                x not in drops and \
                x not in neighborDrops and \
                min([self.calculate_distance(x, j) for j in drops]) >= depoDist and \
                self.dropCalc.inMaxZone(x) and \
                np.sum(dist*shipLocs)>minPlayers:
                maxHalite = haliteCheck
                finalLocation = self.normalize(x)
                #logging.info("ship build location at".format(x))
        return finalLocation
    
    
    # returns average halite in area based on width, also returns max halite
    def getSurroundingHalite(self, pos, width):
        total = 0
        for i in range(-width,width+1):
            for j in range(-width,width+1):
                total += self[pos + Position(i,j)].halite_amount
        return total/((width*2+1)*(width*2+1))

    def findDynamicEnemy(self, ship, enemyShips, minHalite, maxWidth):
        '''
        return closest enemy ship with minHalite
        '''
        targetLoc = ship.position
        maxHalite = 0
        for i in range(1, maxWidth):
            for enemy in enemyShips:
                if enemy.halite_amount > maxHalite:
                    maxHalite = enemy.halite_amount
                    targetLoc = enemy.position
            if maxHalite > minHalite:
                break
        return targetLoc
    
    def get_normalized_cardinals(self, source):
        surroundings = source.get_surrounding_cardinals()
        return [self.normalize(pos) for pos in surroundings]

    def get_surrounding_cardinals(self, source, width):
        '''
        returns a list of locations around a source
        '''
        locations = []
        for i in range(-width,width+1):
            for j in range(-width,width+1):
                locations.append(self.normalize(source + Position(i,j)))
        return locations

    def calculate_distance(self, source, target, disType = 'manhattan'):
        """
        Compute the Manhattan distance between two locations.
        Accounts for wrap-around.
        :param source: The source from where to calculate
        :param target: The target to where calculate
        :param type: What to return, manhattan, x only, y only
        :return: The distance between these items
        """
        source = self.normalize(source)
        target = self.normalize(target)
        resulting_position = abs(source - target)
        
        manhattan = min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)
            
        x_only = min(resulting_position.x, self.width - resulting_position.x)
        
        y_only = min(resulting_position.y, self.height - resulting_position.y)
        
        if disType == 'manhattan':
            return manhattan
        elif disType == 'x only':
            return x_only
        elif disType == 'y only':
            return y_only
        
        return min(resulting_position.x, self.width - resulting_position.x) + \
            min(resulting_position.y, self.height - resulting_position.y)

    def findClosest(self, ship, targets):
        """
        ChoosesReturn closest from ship to targets w/ manhattan distance.
        :param ship: The ship instance
        :param targets: A list of target locations
        :return: The location of closest dropoff point
        """ 
        closestDist = 10000
        finalLocation = None
        for i in targets:
            dist = self.calculate_distance(ship.position, i.position)
            if dist < closestDist:
                closestDist = dist
                finalLocation = i.position
        return finalLocation

    def normalize(self, position):
        """
        Normalized the position within the bounds of the toroidal map.
        i.e.: Takes a point which may or may not be within width and
        height bounds, and places it within those bounds considering
        wraparound.
        :param position: A position object.
        :return: A normalized position object fitting within the bounds of the map
        """
        return Position(position.x % self.width, position.y % self.height)

    @staticmethod
    def _get_target_direction(source, target):
        """
        Returns where in the cardinality spectrum the target is from source. e.g.: North, East; South, West; etc.
        NOTE: Ignores toroid
        :param source: The source position
        :param target: The target position
        :return: A tuple containing the target Direction. A tuple item (or both) could be None if within same coords
        """
        return (Direction.South if target.y > source.y else Direction.North if target.y < source.y else None,
                Direction.East if target.x > source.x else Direction.West if target.x < source.x else None)

    def return_nearby_enemies(self, source):
        '''
        return in a list form which positions have an enemy ship
        '''
        north = self[self.normalize(source.directional_offset(Direction.North))]
        south = self[self.normalize(source.directional_offset(Direction.South))]
        east  = self[self.normalize(source.directional_offset(Direction.East))]
        west  = self[self.normalize(source.directional_offset(Direction.West))]

        locList = [north, south, east, west]
        enemyList = []
        
        for loc in locList:
            if loc.is_enemy():
                enemyList.append(loc)

        return enemyList

    def return_nearby_ships(self, source, width):
        '''
        return in a list form which positions have an enemy ship
        '''
        location_choices = self.get_surrounding_cardinals(source, width)
        shipList = []
       
        for loc in location_choices:
            if self[loc].occupado:
                shipList.append(loc)
        return shipList

    def get_safe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move accounts for enemy collisions. 
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        unsafeMoves = self.get_unsafe_moves(source,destination)
        finalMoves = unsafeMoves.copy()
        logging.info("unsafe moves {}".format(unsafeMoves))
        for move in unsafeMoves:
            # check if safe
            logging.info("checking move {}".format(move))
            checkLoc = self.normalize(source.directional_offset(move))
            logging.info("loc {} w/ enemy? {}".format(checkLoc, self[checkLoc].is_enemy()))
            if self[checkLoc].is_enemy():
                logging.info("loc {} removed".format(checkLoc))
                finalMoves.remove(move)
        return finalMoves

    def get_unsafe_moves(self, source, destination):
        """
        Return the Direction(s) to move closer to the target point, or empty if the points are the same.
        This move mechanic does not account for collisions. The multiple directions are if both directional movements
        are viable.
        :param source: The starting position
        :param destination: The destination towards which you wish to move your object.
        :return: A list of valid (closest) Directions towards your target.
        """
        source = self.normalize(source)
        destination = self.normalize(destination)
        possible_moves = []
        distance = abs(destination - source)
        y_cardinality, x_cardinality = self._get_target_direction(source, destination)

        if distance.x != 0:
            possible_moves.append(x_cardinality if distance.x < (self.width / 2)
                                  else Direction.invert(x_cardinality))
        if distance.y != 0:
            possible_moves.append(y_cardinality if distance.y < (self.height / 2)
                                  else Direction.invert(y_cardinality))
        return possible_moves

    def naive_navigate(self, ship, destination):
        """
        Returns a singular safe move towards the destination.

        :param ship: The ship to move.
        :param destination: Ending position
        :return: A direction.
        """
        # No need to normalize destination, since get_unsafe_moves
        # does that
        for direction in self.get_unsafe_moves(ship.position, destination):
            target_pos = ship.position.directional_offset(direction)
            if not self[target_pos].is_occupied:
                self[target_pos].mark_unsafe(ship)
                return direction

        return Direction.Still

    def updateEnemyMask(self):
        self.minedNextTurn = self.npMap * (0.25 + 0.5 * self.inspirationBonus) # what will be mined next turn
        self.enemyMineNextTurn = self.npMap * (0.25 + 0.5 * self.negInspirationBonus) # what will be mined next turn
        self.enemyZoC = 1 * (self.enemyShipCount > self.friendlyShipCount) # zones of control; 1 means enemy controls it

        return 0

    @staticmethod
    def _generate():
        """
        Creates a map object from the input given by the game engine
        :return: The map object
        """
        map_width, map_height = map(int, read_input().split())
        game_map = [[None for _ in range(map_width)] for _ in range(map_height)]
        for y_position in range(map_height):
            cells = read_input().split()
            for x_position in range(map_width):
                game_map[y_position][x_position] = MapCell(Position(x_position, y_position),
                                                           int(cells[x_position]))
        return GameMap(game_map, map_width, map_height)

    def _update(self):
        """
        Updates this map object from the input given by the game engine
        :return: nothing
        """
        # Mark cells as safe for navigation (will re-mark unsafe cells
        # later)
        #self.npMapOld = self.npMap.copy()
        
        self.totalHalite = 0
        for _ in range(int(read_input())):
            cell_x, cell_y, cell_energy = map(int, read_input().split())
            self[Position(cell_x, cell_y)].halite_amount = cell_energy

        for y in range(self.height):
            for x in range(self.width):
                self[Position(x, y)].ship = None
                self[Position(x, y)].enemyShip = None
                self[Position(x, y)].enemyLikelyHood = 0
                self.npMap[y][x] = self[Position(x,y)].halite_amount
        self.totalHalite = np.sum(self.npMap)
        self.averageHalite = np.mean(self.npMap)
        self.stdDevHalite = np.std(self.npMap)
        #logging.info('avg halite {}'.format(self.averageHalite))
        
        # update drop distance matrices

        self.smoothMap = ndimage.uniform_filter(self.npMap, size = self.smoothSize, mode = 'wrap')
        self.dropCalc.updateMap(self.npMap, self.smoothMap)
        self.dropCalc.identifyBestDrops()
        self.avoid.fill(0)
        
        self.freeHalite = self.totalHalite / self.startingHalite
        

        if self.turnNumber>0:
            tempMap = self.npMap.copy()
            #logging.info("temp1 {}".format(tempMap))
            tempMap[tempMap>self.npMapOld] = self.npMapOld[tempMap>self.npMapOld]
            #logging.info("temp2 {}".format(tempMap))
            self.miningHistory[self.turnNumber] = - np.sum(tempMap) + self.haliteHistory[self.turnNumber-1]
            self.haliteHistory[self.turnNumber] = np.sum(tempMap)
            self.npMapOld = tempMap
        else:
            self.npMapOld = self.npMap.copy()
            self.miningHistory[self.turnNumber] = 0
            
        if self.turnNumber>20:
            self.miningMA[self.turnNumber] = np.mean(self.miningHistory[self.turnNumber-20:self.turnNumber])
            logging.info("turn {} mining speed {}; MA {}; total {} temp {}".format(self.turnNumber, self.miningHistory[self.turnNumber], self.miningMA[self.turnNumber], np.sum(self.miningHistory),np.sum(tempMap)))
        
        if self.numPlayers == 2:
            self.haliteCollectionTarget = 950 
        else:
            self.haliteCollectionTarget = 750 + 200 * self.freeHalite