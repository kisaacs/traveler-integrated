# Imports
import copy

import numpy as np
import json
from .loggers import logToConsole
from profiling_tools._cCalcBin import ffi, lib

class SparseUtilizationList():
    def __init__(self):
        self.locationDict = dict()
        self.cLocationDict = dict()

    def getCLocation(self, loc):
        return self.cLocationDict[loc]

    def setCLocation(self, loc, val):
        self.cLocationDict[loc] = copy.deepcopy(val)

    def sortAtLoc(self, loc):
        self.locationDict[loc].sort(key=lambda x: x['index'])

    def calcCurrentUtil(self, index, prior):
        if prior is None:
            last = {'index': 0, 'counter': 0, 'util': 0}
        else:
            last = prior

        return (((index - last['index']) * last['counter'])+last['util'])

    def setIntervalAtLocation(self, edgeUtilObj, location):
        # check if array exists
        if location not in self.locationDict:
            self.locationDict[location] = []

        self.locationDict[location].append(edgeUtilObj)
        return

    # Calculates utilization histogram for all intervals regardless of location
    def calcGanttHistogram(self, bins=100, begin=None, end=None):
        listOfLocations = []

        for location in self.locationDict:
            temp = self.calcUtilizationForLocation(bins, begin, end, location)
            listOfLocations.append({"location":location, "histogram":temp})

        return listOfLocations

    # Calculates utilization histogram for all intervals regardless of location
    def calcUtilizationHistogram(self, bins=100, begin=None, end=None, isInterval=True):
        array = []
        isFirst = True
        for location in self.locationDict:
            temp = self.calcUtilizationForLocation(bins, begin, end, location, isInterval)
            if isFirst is True:
                isFirst = False
                array = temp
            for i in range(bins):
                array[i] = array[i] + temp[i]

        return array

    # Calculates metric histogram
    def calcMetricHistogram(self, bins=100, begin=None, end=None, location=None):
        array = []
        isFirst = True
        if location is not None:
            return self.calcUtilizationForLocation(bins, begin, end, location, False)
        for location in self.locationDict:
            temp = self.calcUtilizationForLocation(bins, begin, end, location, False)
            if isFirst is True:
                isFirst = False
                array = temp
            for i in range(bins):
                array = array + temp

        return array

    # Calculates histogram for interval duration
    def calcIntervalHistogram(self, bins=100, begin=None, end=None):
        return self.calcUtilizationForLocation(bins, begin, end, 1, False)

    # Calulates utilization for one location in a Gantt chart
    # Location designates a particular CPU or Thread and denotes the y-axis on the Gantt Chart
    def calcUtilizationForLocation(self, bins=100, begin=None, end=None, Location=None, isInterval=True):
        rangePerBin = (end-begin)/bins

        # caclulates the beginning of each each bin evenly divided over the range of
        # time indicies and stores them as critical points
        criticalPts = np.empty(bins + 1, dtype=np.int64)
        critical_length = len(criticalPts)
        critical_points = ffi.new("long long[]", critical_length)
        for i in range(0, bins):
            criticalPts[i] = (i * rangePerBin) + begin
            critical_points[i] = int((i * rangePerBin) + begin)
        criticalPts[len(criticalPts)-1] = end
        critical_points[len(criticalPts)-1] = end

        # searches
        histogram = np.empty_like(criticalPts, dtype=object)
        location = self.locationDict[Location]
        length = len(location)
        histogram_length = len(histogram)

        histogram_index = ffi.new("long long[]", histogram_length)
        histogram_counter = ffi.new("long long[]", histogram_length)
        histogram_util = ffi.new("double[]", histogram_length)

        cLocationStruct = self.getCLocation(Location)
        location_index = ffi.cast("long long*", cLocationStruct['index'].ctypes.data)
        location_counter = ffi.cast("long long*", cLocationStruct['counter'].ctypes.data)
        location_util = ffi.cast("double*", cLocationStruct['util'].ctypes.data)

        lib.calcHistogram(histogram_counter, histogram_length, histogram_index, histogram_util, critical_points, critical_length, location_index, length-1, location_counter, location_util)
        histogram[0] = {'integral': 0, 'index': histogram_index[0], 'util': histogram_util[0], 'counter': histogram_counter[0]}
        prev = histogram[0]
        prettyHistogram = []
        for i in range(1, len(histogram)):
            histogram[i] = {'index': histogram_index[i], 'util': histogram_util[i], 'counter': histogram_counter[i]}
            current = histogram[i]
            val = current['util']
            if isInterval:
                val = (current['util'] - prev['util']) / (current['index'] - prev['index'])
            current['integral'] = val
            prev = current
            prettyHistogram.append(histogram[i]['integral'])
        return prettyHistogram
