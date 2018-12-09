import queue

from . import constants
from .entity import Entity, Shipyard, Ship, Dropoff
from .player import Player
from .positionals import Direction, Position
from .common import read_input
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
        
        # ship map is a simmple 1 or 0 label for which cell has a ship
        self.shipMap = np.zeros([self.width, self.height], dtype=np.int)
        
        # build numpy map
        self.npMap = np.zeros([self.width, self.height], dtype=np.int)
        for y in range(self.height):
            for x in range(self.width):
                self.npMap[y][x] = self[Position(x,y)].halite_amount
        self.npMapDistance = self.buildDistanceMatrix()
        
        self.smoothMap = ndimage.uniform_filter(self.npMap, size = 5, mode = 'wrap')
        
        #logging.info("np map {}".format(self.npMap))
        #logging.info("smooth map {}".format(self.smoothMap))
        
        


        self.totalHalite = np.sum(self.npMap)
        self.averageHalite = np.mean(self.npMap)
        self.stdDevHalite = np.std(self.npMap)
        logging.info("Total {}, avg {}, stdev {}".format(self.totalHalite, self.averageHalite, self.stdDevHalite))
        
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
        self.distanceMatrix = np.zeros([self.width, self.height, self.width, self.height], dtype=np.int)
        for y in range(self.height):
            for x in range(self.width):
                startPos = Position(y,x)
                self.distanceMatrix[y][x] = self.calcDistanceMatrix(startPos)
        
        self.distanceMatrixNonZero = np.sqrt(self.distanceMatrix.copy())
        self.distanceMatrixNonZero[self.distanceMatrixNonZero==0] = 1
        self.distanceMatrixNonZero = 1/self.distanceMatrixNonZero
        #logging.info("distanceMatrix {}".format(self.distanceMatrix))
        
        # count space for each part of matrix
        self.matrixID = np.zeros([self.width, self.height], dtype = np.int)
        matrixCount = 0
        for y in range(self.height):
            for x in range(self.width):
                self.matrixID[y][x] = matrixCount
                matrixCount += 1
        #logging.info("matrix count {}".format(self.matrixID))
        
        # setup row column labels to keep track of positions later
        

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
    
    # basic logic if we should keep building ships
    # should be a function of my ships, enemy ships, my halite, his halite
    def shipBuild(self):
        return 0
    
    def emptyShipMap(self):
        self.shipMap = np.zeros([self.width, self.height], dtype=np.int)

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

    def get_map_split(self, source):
        '''
        evenly divide the map into quarters. Return odds for next move
        '''
        breakPoint = self.width/2 - 1 # since python starts at 0
        haliteSplit = {}
        
        for x in range(2):
            for y in range(2):
                for i in range(breakPoint):
                    for j in range(breakPoint):
                        haliteSplit[x,y] = self[self.normalize(source + Position(i,j))].halite_amount
                
        return 0

    def get_ship_surroundings(self, ships, width, minHalite):
        '''
        return a list of possible surrounding spots, unique, that pass min Halite threshold
        '''
        targets = []
        for ship in ships:
            for nearby in self.get_surrounding_cardinals(ship.position, width):
                if self[nearby].halite_amount > minHalite and nearby not in targets:
                    targets.append(nearby)
        return targets

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
        turnMatrix = np.zeros([len(ships), self.width * self.height], dtype=np.int)
        moveStatus = ["exploring","returning","returnSuicide", "attack", "build depo"]
        shipPosList = []
        for ship in ships:
            shipPosList.append(ship.position)
        
        issueFlag = True
        loopCounter = 1
        issueList = []
        maxLoop = 5
        if self.width > 60:
            maxLoop = 3
            if self.turnsLeft <30:
                maxLoop = 3
        

        while issueFlag and loopCounter < maxLoop:
            logging.info("loop {}".format(loopCounter))
            logging.info("issue list {}".format(issueList))

            for i in range(len(ships)):
                shipMap = np.zeros([self.width, self.height], dtype=np.int)       
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
                        shipMap[y,x] = 1
                        
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
    
                    # need to add logic to sit still if ship just moved in front
    
                    if status[shipID] == "attack" and left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 10000
                    elif left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 0
                    elif leftDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + random.randint(1,2) 
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + random.randint(1,2) 
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x-1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x-1) % self.height] = 2
                    #logging.info("left ship {} map {}".format(ships[i].id, shipMap))
    
                    if status[shipID] == "attack" and right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 10000
                    elif right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 0
                    elif rightDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + random.randint(1,2)
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x+1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x+1) % self.height] = 2
                    #logging.info("right ship {} map {}".format(ships[i].id, shipMap))
                    
                    if status[shipID] == "attack" and up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 10000
                    elif up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 0
                    elif upDist < distToDest: # moves us closer 
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y-1) % self.width,(x) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y-1) % self.width,(x) % self.height] = 2
                    #logging.info("up ship {} map {}".format(ships[i].id, shipMap))
    
                    if status[shipID] == "attack" and down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 10000
                    elif down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 0
                    elif downDist < distToDest: # moves us closer 
                        shipMap[(y+1) % self.width,x % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y+1) % self.width,x % self.height] = halite + random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y+1) % self.width,x % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y+1) % self.width,x % self.height] = 2
                # or mine and stay still
                else:
                    shipMap[y,x] = 100000
                
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
    
    def matchShipsToDest2(self, ships, minHalite= 0, hChoice = 'sqrt'):
        '''
        The eyes of JarBot
        need to add penalty when another ship is on a spot already
        halite excluded form search if its below minHalite
        '''
        distMatrix = np.zeros([len(ships), self.width*self.height], dtype=np.int)
        
        # remove taken spots from the solver
        tempMap = self.shipMap.copy()
        tempMap[self.shipMap==2]=0
        if max(self.shipMap.flatten())==4:
            tempMap[self.shipMap==3]=0
            tempMap[self.shipMap==4]=0
        haliteMap = self.npMap - 1000 * tempMap
        ### FIX THIS ####

        for i in range(len(ships)):
            #dist = self.distanceMatrixNonZero[ships[i].position.x][ships[i].position.y] 
            #dist[dist==0] = 1
            if hChoice == 'sqrt':
                h = -haliteMap * self.distanceMatrixNonZero[ships[i].position.x][ships[i].position.y] 
            elif hChoice == 'sqrt2':
                h = -haliteMap / np.sqrt(dist * 2)
            elif hChoice == 'fourthRoot':
                h = -haliteMap / np.sqrt(np.sqrt(dist))
            elif hChoice == 'quad':
                h = -haliteMap / (dist * dist)
            elif hChoice == 'linear':
                h = -haliteMap / dist
            elif hChoice == "nThird":
                h = -haliteMap / (dist * dist / np.sqrt(dist))
            elif hChoice == 'maxHalite':
                h = -haliteMap         
            distMatrix[i,:] = h.ravel()

        if self.width >60 and len(distMatrix)>0:
            # shrink targets
            matrixLabels = self.matrixID.copy().ravel() # which cell teh destination will be 
            columnHaliteMean = distMatrix.mean(axis=0)
            #logging.info("dist {} - len {}".format(distMatrix, distMatrix.shape))
            #logging.info("mlabels {} - len {}".format(matrixLabels, len(matrixLabels)))
            #logging.info("mean {}".format(columnHaliteMean))
            trueFalseFlag = columnHaliteMean < minHalite # filter out destinations that i don't care about
        
            # if map is over mined can lead to an error
            if sum(trueFalseFlag) < len(ships):
                trueFalseFlag = columnHaliteMean < minHalite + 5
                if sum(trueFalseFlag) < len(ships):
                    trueFalseFlag = columnHaliteMean < 0
            matrixLabelsFinal = matrixLabels[trueFalseFlag]
            #logging.info("equality {} - len {}".format(columnHaliteMean < minHalite, len(columnHaliteMean < minHalite)))
            #logging.info("mlabel reduced {} - len {}".format(matrixLabelsFinal, len(matrixLabelsFinal)))
                
            solveMatrix = distMatrix[:,trueFalseFlag]
            #logging.info("dist {} - len {}".format(solveMatrix, solveMatrix.shape))
        else:
            solveMatrix = distMatrix
            matrixLabels = self.matrixID.copy().ravel() # which cell teh destination will be 
            matrixLabelsFinal = matrixLabels

        # find closest destination
        distMatrix = distMatrix.astype(np.int, copy=False)
        row_ind, col_ind = optimize.linear_sum_assignment(solveMatrix)
        #logging.info("row {}, col {}, colLen".format(distMatrix, row_ind, col_ind, len(col_ind)))
        
        # convert to ship orders
        orders = {}
        for i in range(len(ships)):
            orders[ships[i].id] = Position(matrixLabelsFinal[col_ind[i]] % self.width,int(matrixLabelsFinal[col_ind[i]]/self.width))
        return row_ind, col_ind, orders
    
    def matchShipsToDest(self, ships, destinations):
        distMatrix = np.zeros([len(ships), len(destinations)])
        for i in range(len(ships)):
            for j in range(len(destinations)):
                distCalc = self.calculate_distance(ships[i].position, destinations[j])
                if distCalc == 0:
                    distCalc = 1000
                distMatrix[i,j] = -self[destinations[j]].halite_amount / (np.sqrt(2 * distCalc))
            
        # find closest destination
        row_ind, col_ind = optimize.linear_sum_assignment(distMatrix)
        logging.info("distMatrix {}, row {}, col {}".format(distMatrix, row_ind, col_ind))
        
        # convert to ship
        orders = {}
        for i in range(len(ships)):
            orders[ships[i].id] = destinations[col_ind[i]]
        return row_ind, col_ind, orders
    
    def findHighestSmoothHalite(self, ship, maxWidth=2):
        maxHalite = self.smoothMap[ship.position.y,ship.position.x]
        finalLocation = ship.position
        
        for i in range(1, maxWidth+1):
            location_choices = self.get_surrounding_cardinals(ship.position, i)
        
            #find max halite
            for x in location_choices:
                haliteCheck = self.smoothMap[x.y,x.x]
                if haliteCheck > maxHalite and x != ship.position:
                    maxHalite = haliteCheck
                    finalLocation = self.normalize(x)
        return finalLocation
    
    def findDynamicHalite(self, ship, destinations, minHalite, maxWidth):
        '''
        returns the location of highest halite near a source, widens 
        search until minHalite is reached up to timeout from maxWidth
        :param source: The source from where to search
        :param destinations: excludes these points
        :param minHalite: break once this size is found
        :param maxWidth: cutoff where it will no longer search
        :return: The location
        '''
        maxHalite = 0 
        finalLocation = ship.position
    
        for i in range(1, maxWidth + 1):
            location_choices = self.get_surrounding_cardinals(ship.position, i)
        
            #find max halite
            for x in location_choices:
                haliteCheck = self[x].halite_amount
                if haliteCheck > maxHalite and x != ship.position and not (x in destinations.values()):
                    maxHalite = haliteCheck
                    finalLocation = self.normalize(x)
        
            if maxHalite > minHalite:
                break
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

    def findOptimalMoves_old(self, ships, destinations, dropoffs, status, enemyLocs):
        '''
        given a vector of ships and destinations will find optimal moves next turn
        '''
        turnMatrix = np.zeros([len(ships), self.width * self.height], dtype=np.int)
        moveStatus = ["exploring","returning","returnSuicide", "attack"]
        shipPosList = []
        for ship in ships:
            shipPosList.append(ship.position)
        
        issueList = []
        issueFlag = True
        loopCounter = 1
        maxLoop = 4
        if self.width > 60:
            maxLoop = 3
            if self.turnsLeft <30:
                maxLoop = 2
        

        while issueFlag and loopCounter < maxLoop:
            for i in range(len(ships)):
                shipMap = np.zeros([self.width, self.height], dtype=np.int)       
                halite = ships[i].halite_amount
                if halite < 10:
                    halite = 10
                shipID = ships[i].id
                pos = ships[i].position
                x = ships[i].position.x
                y = ships[i].position.y
                
                # should we move
                if status[ships[i].id] in moveStatus:
                    distToDest   = self.calculate_distance(pos,destinations[shipID])
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
                    # needs safety
                    elif shipID in issueList:
                        logging.info("ship {} trying to survive".format(shipID))
                        halite = 10000
                        shipMap[y,x] = 10000
                    # encourage to stay if target destination is empty right now
                    elif destinations[shipID] not in shipPosList:
                        shipMap[y,x] = 6
                    else: 
                        shipMap[y,x] = 1
                        
                    # is goal directly n,s,e,w?
                    left = self.normalize(pos.directional_offset(Direction.West))
                    right = self.normalize(pos.directional_offset(Direction.East))
                    up = self.normalize(pos.directional_offset(Direction.North))
                    down = self.normalize(pos.directional_offset(Direction.South))
                    leftDist = self.calculate_distance(left, destinations[shipID])                
                    rightDist = self.calculate_distance(right, destinations[shipID])                
                    upDist = self.calculate_distance(up, destinations[shipID])
                    downDist = self.calculate_distance(down, destinations[shipID])
    
                    # Directions
                    if leftDist < distToDest and upDist > distToDest and downDist > distToDest:
                        leftOnly = True
                    elif upDist < distToDest and rightDist > distToDest and leftDist > distToDest:
                        upOnly = True
                    elif rightDist < distToDest and upDist > distToDest and downDist > distToDest:
                        rightOnly = True
                    elif downDist < distToDest and rightDist > distToDest and leftDist > distToDest:
                        downOnly = True
    
                    # need to add logic to sit still if ship just moved in front
    
                    if status[shipID] == "attack" and left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 10000
                    elif left in enemyLocs:
                        shipMap[(y) % self.width,(x-1) % self.height] = 0
                    elif leftDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + random.randint(1,2) 
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x-1) % self.height] = halite + random.randint(1,2) 
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x-1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x-1) % self.height] = 2
                    #logging.info("left ship {} map {}".format(ships[i].id, shipMap))
    
                    if status[shipID] == "attack" and right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 10000
                    elif right in enemyLocs:
                        shipMap[(y) % self.width,(x+1) % self.height] = 0
                    elif rightDist < distToDest: # moves us closer 
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y) % self.width,(x+1) % self.height] = halite + random.randint(1,2)
                    elif upOnly or downOnly:
                        shipMap[(y) % self.width,(x+1) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y) % self.width,(x+1) % self.height] = 2
                    #logging.info("right ship {} map {}".format(ships[i].id, shipMap))
                    
                    if status[shipID] == "attack" and up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 10000
                    elif up in enemyLocs:
                        shipMap[(y-1) % self.width,(x) % self.height] = 0
                    elif upDist < distToDest: # moves us closer 
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y-1) % self.width,(x) % self.height] = halite + random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y-1) % self.width,(x) % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y-1) % self.width,(x) % self.height] = 2
                    #logging.info("up ship {} map {}".format(ships[i].id, shipMap))
    
                    if status[shipID] == "attack" and down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 10000
                    elif down in enemyLocs:
                        shipMap[(y+1) % self.width,x % self.height] = 0
                    elif downDist < distToDest: # moves us closer 
                        shipMap[(y+1) % self.width,x % self.height] = halite + random.randint(1,2)
                    elif shipID in issueList:
                        shipMap[(y+1) % self.width,x % self.height] = halite + random.randint(1,2)
                    elif rightOnly or leftOnly:
                        shipMap[(y+1) % self.width,x % self.height] = 3 + random.randint(1,2)
                    else:
                        shipMap[(y+1) % self.width,x % self.height] = 2
                # or mine and stay still
                else:
                    shipMap[y,x] = 100000
                
                turnMatrix[i,:] = shipMap.ravel()
                #logging.info("ship {} map {}".format(ships[i].id, shipMap))
    
            # solve for correct moves
            row_ind, col_ind = optimize.linear_sum_assignment(-turnMatrix)
            #logging.info("row {}, col {}".format(row_ind, col_ind))
            
            # look for issues
            issueFlag = False
            aroundList = self.get_surrounding_cardinals(Position(0,0),1)
            for i in range(len(ships)):
                if col_ind[i] == 0 and ships[i].position not in aroundList:
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
                nextMove = Position(col_ind[i] % self.width, int(col_ind[i]/self.width))
            else:
                nextMove = dropOffTarget
            #logging.info("ship {} next move to {}".format(ships[i].id, nextMove))
            if nextMove == pos:
                orders[ships[i].id] = Direction.Still
            else:
                orders[ships[i].id] = self.get_unsafe_moves(pos, nextMove)[0]
        return orders

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

        self.smoothMap = ndimage.uniform_filter(self.npMap, size = 5, mode = 'wrap')