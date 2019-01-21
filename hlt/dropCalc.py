# -*- coding: utf-8 -*-
"""
Created on Fri Dec 21 15:37:13 2018

@author: jaycw_000
"""

from scipy import ndimage, misc
#from skimage.feature import peak_local_max
import numpy as np
import logging
np.set_printoptions(threshold=np.nan)
np.set_printoptions(linewidth = 300)

class dropCalc:
    """
    Class which identifies the best dropoff locations
    """
    def __init__(self, maxDrops, haliteMap, smoothMap, minHalite, percentile, miningSpeed):
        self.maxDrops = maxDrops
        self.haliteMap = haliteMap
        self.smoothMap = smoothMap
        self.length = len(self.haliteMap)
        self.minHalite =  minHalite
        self.percentileFlag = percentile
        self.miningSpeed = miningSpeed
        self.minHalite = 10000/(8 * 8)
        self.percentileFlag = 50
        self.numPlayers = 2
        self.width = 32
        logging.info("minHalite {}, lenght {}, denom {}".format(self.minHalite, self.length, (self.length/4 * self.length/4)))

    def updateMap(self, haliteMap, smoothMap):
        self.haliteMap = haliteMap
        self.smoothMap = smoothMap
        
    def updateMinHalite(self, minHalite):
        self.minHalite = minHalite
        
    def updateMiningSpeed(self, miningSpeed):
        self.miningSpeed = miningSpeed
        
    def updatePercentile(self, percentile):
        self.percentileFlag = percentile
        
    def identifyBestDrops(self):
        targetMap = self.haliteMap
        if self.numPlayers == 4 and self.width == 32:
            targetMap = self.haliteMap * self.miningSpeed * 4
        self.filteredMap = ndimage.uniform_filter(targetMap, size = 8, mode = 'wrap')
        #self.filteredMap = ndimage.maximum_filter(self.smoothMap, size = self.length / 4, mode = 'wrap')
        #self.peakMaxima = peak_local_max(self.smoothMap, min_distance = 1)
        self.maxZones = self.filteredMap
        #self.maxZones[self.filteredMap < np.percentile(self.filteredMap, self.percentileFlag)]=0
        self.maxZones[self.maxZones<self.minHalite] = 0
        #logging.info("raw map\n {}".format(self.haliteMap))
        #logging.info("filter map\n {}".format(self.filteredMap))
        #logging.info("peak Max\n {}".format(self.maxZones))
        #logging.info("peak Max\n {}".format(self.peakMaxima))

    def inMaxZone(self, pos):
        '''
        returns if position is in a max zone
        '''
        
        return self.maxZones[pos.y,pos.x] > 0
    


     
        
'''
            finalMapClose = -finalMap / (dist+1)
            
            # hpt for further squares
            finalMapFar[haliteMap > (950 - ships[i].halite_amount)] = (950 - ships[i].halite_amount)
            finalMapFar = finalMapFar.astype(np.float)
            #finalMapFar -= dist * self.smoothMap[shipY, shipX] * 0.025
            finalMapFar[finalMapFar<1] = 1
            miningTurns = np.log(100/finalMapFar)/np.log(.75)
            miningTurns[miningTurns<0] = np.log(50/100) / np.log(.75)
            miningTurns[miningTurns<0] = np.log(25/50) / np.log(.75)
            miningTurns[miningTurns<0] = np.log(1/25) / np.log(.75)
            finalMapFar = -(finalMapFar) / (dist+miningTurns+depoDist)
            finalMapFar[shipY,shipX] = 0
            finalMapFar[(shipY) % self.width,(shipX-1) % self.height] = 0
            finalMapFar[(shipY) % self.width,(shipX+1) % self.height] = 0
            finalMapFar[(shipY-1) % self.width,(shipX) % self.height] = 0
            finalMapFar[(shipY+1) % self.width,(shipX) % self.height] = 0
'''

        # what you can make on avg next two turns
        #tempMap = self.npMap * .25 * 1.75
        #finalMapFar = ndimage.uniform_filter(tempMap, size = 3, mode = 'wrap') * 9/1.5 
       
        #finalMapFar2[finalMapFar2 > (850 - ships[i].halite_amount)] = (850 - ships[i].halite_amount)
        #finalMapFar2[shipY,shipX] = 0
        #haliteMap[haliteMap<collectingStop] = 1
        #logging.info("ship {} final map {}".format(ships[i].id, finalMap))
            
        #h2 = (finalMapFar2 - 5000 * avoid) / (dist+14)
        #h = -np.maximum(h1,h2)