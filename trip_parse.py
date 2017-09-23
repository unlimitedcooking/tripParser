#!/usr/bin/python

from datetime import datetime
import os
import sys
import time
import pprint 

import csv
import fnmatch

MIN_THRESHOLD = 10
STATE_MOVING = 0
STATE_STOPPED = 1

def epochToTime(time):
	return datetime.fromtimestamp(int(time) / 1000).strftime('%Y-%m-%d %H:%M:%S')
	
def milliToTime(time):
	time /= 1000
	seconds = int(time % 60)
	if seconds < 10:
		seconds = "0" + str(seconds)
	
	time /= 60
	minutes = int(time % 60)
	if minutes < 10:
		minutes = "0" + str(minutes)
	
	time /= 60
	hours = int(time % 24)
	if hours < 10:
		hours = "0" + str(hours)
	
	return str(hours) + "h:" + str(minutes) + "m:" + str(seconds) + "s"



class tripNode():
	def __init__(self, time, lat, lng, speed):
		self.time = time
		self.lat = lat
		self.lng = lng
		self.speed = speed
	
	def __str__(self):
		return "%s %s %s %s" % (self.time, self.lat, self.lng, self.speed)	
	
class subtrip():
	def __init__(self, state):
		self.data = []
		self.prev_time_delta = 0
		self.state = state
		
	def __len__(self):
		return len(self.data)
	
	def add(self, newNode):
		self.data.append(newNode)
		
	def size(self):
		return len(self.data)
		
	def toString(self):
		for node in data:
			print(node)
			
	def getLastNode(self):
		if len(self.data) > 0:
			return self.data[len(self.data) - 1]
			
	def getStartTime(self):
		if len(self.data) > 0:
			return int(self.data[0].time)
		return 0
	
	def getStartTimeString(self):
		return epochToTime(self.getStartTime())
	
	def getEndTime(self):
		if len(self.data) > 0:
			return int(self.data[len(self.data) - 1].time)
		return 0
		
	def getEndTimeString(self):
		return epochToTime(self.getEndTime())
		
	def getDuration(self):
		return int(self.getEndTime() - self.getStartTime())
		
	def getDurationString(self):
		return milliToTime(self.getDuration())
	
	def getMaxSpeed(self):
		maxSpeed = 0
		for node in self.data:
			currSpeed = float(node.speed)
			if currSpeed > maxSpeed:
				maxSpeed = currSpeed
		return maxSpeed
		
	def addList(self, mList):
		for element in mList:
			self.data.append(element)
		
	def printInfo(self):
		return ("Entries = %s. Start = %s (%s). Stop = %s (%s). Duration = %s. Max Speed = %s" % 
			(self.size(),
			self.getStartTimeString(),
			self.getStartTime(), 
			self.getEndTimeString(),
			self.getEndTime(), 
			milliToTime(self.getDuration()),
			self.getMaxSpeed()))
			
class stateMachine():
	def __init__(self):
		self.currTrip = None
		self.trips = []
		self.storage = []
		
	def updateState(self, node):
		if self.currTrip == None:
			if float(node.speed) > MIN_THRESHOLD:
				self.currTrip = subtrip(STATE_MOVING)
			else:
				self.currTrip = subtrip(STATE_STOPPED)
	
		if self.currTrip.state == STATE_MOVING:
			if float(node.speed) > MIN_THRESHOLD:
				self.currTrip.addList(self.storage)
				self.currTrip.add(node)
				self.storage = []
			else:
				self.storage.append(node)
				if len(self.storage) > 20 or (int(node.time) - self.currTrip.getEndTime()) > 60000:
					print("Trip #%s(M). %s" % (len(self.trips), self.currTrip.printInfo()))
					print
					self.trips.append(self.currTrip)
					self.currTrip = subtrip(STATE_STOPPED)
					self.currTrip.addList(self.storage)
					self.storage = []
		elif self.currTrip.state == STATE_STOPPED:
			if float(node.speed) > MIN_THRESHOLD:
				self.storage.append(node)
				if len(self.storage) > 20:
					if len(self.trips) > 0:
						prevTrip = self.trips[len(self.trips) - 1]
						self.currTrip.prev_time_delta = int(node.time) - prevTrip.getEndTime()
					else:
						prevTrip = subtrip(STATE_STOPPED)
						self.currTrip.prev_time_delta = 0
					print("Trip #%s(S). Stopped for %s, from %s (%s) to %s (%s). Entries = %s" % 
						(len(self.trips),
						milliToTime(self.currTrip.prev_time_delta),
						self.currTrip.getStartTimeString(),
						self.currTrip.getStartTime(),
						self.currTrip.getEndTimeString(),
						self.currTrip.getEndTime(),
						len(self.currTrip)))
					print
					self.trips.append(self.currTrip)
					self.currTrip = subtrip(STATE_MOVING)
					self.currTrip.addList(self.storage)
					self.storage = []
			else:
				self.currTrip.addList(self.storage)
				self.currTrip.add(node)
				self.storage = []
				#print(node.speed)
			
	def getLastTime(self):
		if len(self.trips) is 0:
			return 0
		subtrip = self.trips[len(self.trips) - 1]
		if subtrip is None:
			return 0
		lastNode = subtrip.getLastNode()
		if lastNode is None:
			return 0
		return int(lastNode.time)
		
	def lastUpdate(self):
		if self.currTrip.size() > 0: #end case where the file ends while car still moving
			self.trips.append(self.currTrip)
			
	def getTripsInfo(self):
		return self.trips

def findGreatestSpeed(trips):
	maxSpeed = 0
	tripNum = 0
	maxSpeedTime = 0
	
	for i in range(0, len(trips) - 1):
		currTrip = trips[i]
		for node in currTrip.data:
			currSpeed = float(node.speed)
			if currSpeed > float(maxSpeed):
				maxSpeed = currSpeed
				tripNum = i + 1
				maxSpeedTime = node.time
				
	return ("Max speed = %s at %s, found in trip #%s" % (maxSpeed, epochToTime(maxSpeedTime), tripNum))
	
def findLongestDuration(trips):
	mMaxDuration = 0
	mMaxDurationTripNum = 0
	
	sMaxDuration = 0
	sMaxDurationTripNum = 0
	
	for i in range(0, len(trips) - 1):
		currTrip = trips[i]
		if currTrip.size() > 0:
			mCurrDuration = int(currTrip.getDuration())
			if mCurrDuration > int(mMaxDuration):
				mMaxDuration = mCurrDuration
				mMaxDurationTripNum = i + 1
		else:
			sCurrDuration = int(currTrip.prev_time_delta)
			if sCurrDuration > int(sMaxDuration):
				sMaxDuration = sCurrDuration
				sMaxDurationTripNum = i + 1
	
	return ("Longest moving duration = %s, in trip#%s. Longest stopped duration = %s, in trip#%s" % 
		(milliToTime(mMaxDuration),
		mMaxDurationTripNum,
		milliToTime(sMaxDuration),
		sMaxDurationTripNum))
			
def printTripsInfo(trips):
	print("STATISTICS:")
	print("Total of %s trips recorded." % len(trips))
	print(findGreatestSpeed(trips))
	print(findLongestDuration(trips))
	
def parse_file(filepath):
	stateTracker = stateMachine()
	
	with open(filepath) as csvfile:
		fieldnames = ['TIME', 'LAT', 'LNG', 'SPD']
		reader = csv.DictReader(csvfile, fieldnames = fieldnames)
		for row in reader:
			currTime = row['TIME'].split(":")[1]
			UTC_time = epochToTime(int(currTime))
			
			lat = row['LAT']
			lng = row['LNG']
			speed = row['SPD']
			
			node = tripNode(currTime, lat, lng, speed)
			
			stateTracker.updateState(node)
				
	stateTracker.lastUpdate()
	print
	print
	print
	printTripsInfo(stateTracker.getTripsInfo())


if len(sys.argv) == 2:
	fileName = sys.argv[1]
	parse_file(fileName)










