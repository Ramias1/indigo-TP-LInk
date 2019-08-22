#! /usr/bin/env python
# -*- coding: utf-8 -*-
####################
# Copyright (c) 2014, Perceptive Automation, LLC. All rights reserved.
# http://www.indigodomo.com

import indigo

import os
import sys
import json
import time

from tplink_smartplug import tplink_smartplug

# Note the "indigo" module is automatically imported and made available inside
# our global name space by the host process.

################################################################################
class Plugin(indigo.PluginBase):
	########################################
	def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
		super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
		self.debug = pluginPrefs.get("showDebugInfo", False)
		self.interval = None
		self.deviceList = []


	########################################
	def startup(self):
		self.logger.debug(u"startup called")
		self.closedPrefsConfigUi(None, None)

	def shutdown(self):
		self.logger.debug(u"shutdown called")

	########################################
	def validateDeviceConfigUi(self, valuesDict, typeId, devId):
		return (True, valuesDict)

	########################################
	# Relay / Dimmer Action callback
	######################
	def actionControlDimmerRelay(self, action, dev):
		if dev.model == "SmartPlug":
			addr = dev.address
			childID = None
			deviceID = None
		else:
			addr = dev.ownerProps['addr']
			childID = dev.ownerProps['outlet']
			deviceID = dev.ownerProps['deviceID']
		
		port = 9999
		self.logger.debug("TPlink name={}, addr={}, action={}".format(dev.name, addr, action))
		tplink_dev = tplink_smartplug (addr, port, deviceID, childID)

		###### TURN ON ######
		if action.deviceAction == indigo.kDimmerRelayAction.TurnOn:
			# Command hardware module (dev) to turn ON here:
			cmd = "on"
		###### TURN OFF ######
		elif action.deviceAction == indigo.kDimmerRelayAction.TurnOff:
			# Command hardware module (dev) to turn OFF here:
			cmd = "off"
		###### TOGGLE ######
		elif action.deviceAction == indigo.kDimmerRelayAction.Toggle:
			# Command hardware module (dev) to toggle here:
			if dev.onState:
				cmd = "off"
			else:
				cmd = "on"
			newOnState = not dev.onState
		else:
			self.logger.error("Unknown command: {}".format(indigo.kDimmerRelayAction))
			return

		result = tplink_dev.send(cmd)
		sendSuccess = False
		try:
			result_dict = json.loads(result)
			error_code = result_dict["system"]["set_relay_state"]["err_code"]
			if error_code == 0:
				sendSuccess = True
			else:
				self.logger.error("turn {} command failed (error code: {})".format(cmd, error_code))
		except:
			pass

		if sendSuccess:
			# If success then log that the command was successfully sent.
			self.logger.info(u'sent "{}" {}'.format(dev.name, cmd))

			# And then tell the Indigo Server to update the state.
			dev.updateStateOnServer("onOffState", cmd)
		else:
			# Else log failure but do NOT update state on Indigo Server.
			self.logger.error(u'send "{}" {} failed with result "{}"'.format(dev.name, cmd, result))

	########################################
	# General Action callback
	######################
	def actionControlGeneral(self, action, dev):
		if action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
			self.getInfo(action, dev)
		else:
			self.logger.error(u'unsupported Action callback "{}" {}'.format(dev.name, action))

	########################################
	# Energy checking option for SmartStrip
	######################
	def getEnergyInfo(self, pluginAction, dev):
		keyValueList = []
		self.logger.debug("sent '{}' status request".format(dev.name))
		if dev.model == "SmartPlug": addr = dev.address
		else: addr = dev.ownerProps['addr']
		port = 9999
		self.logger.debug("getInfo name={}, addr={}".format(dev.name, addr, ) )
		tplink_dev = tplink_smartplug (addr, port, dev.ownerProps['deviceID'], dev.ownerProps['outlet'])
		result = tplink_dev.send("energy")

		try:
			# pretty print the json result
			json_result = json.loads(result)
			power_mw = json_result["emeter"]["get_realtime"]['power_mw']
			self.logger.debug("Power in MW is " + str(power_mw))
			
			# Set curEnergyLevel value
			curEnergyLevel = power_mw / float(1000)
			self.logger.debug("Current energy is " + str(curEnergyLevel))
			keyValueList.append ({'key':"curEnergyLevel", 'value':curEnergyLevel, 'uiValue':str(curEnergyLevel) + "w"})
			dev.updateStatesOnServer(keyValueList)
		except ValueError as e:
				self.logger.error("JSON value error: {} on {}".format(e, result))

	########################################
	# Custom Plugin Action callbacks (defined in Actions.xml)
	######################
	def getInfo(self, pluginAction, dev):
		self.logger.debug("sent '{}' status request".format(dev.name))
		if dev.model == "SmartPlug": addr = dev.address
		else: addr = dev.ownerProps['addr']
		port = 9999
		self.logger.debug("getInfo name={}, addr={}".format(dev.name, addr, ) )
		tplink_dev = tplink_smartplug (addr, port)

		if dev.model == "SmartPlug": 
			result = tplink_dev.send("info")
			try:
				# pretty print the json result
				json_result = json.loads(result)
				# Get the device state from the JSON
				
				# Parse JSON for device state
				if json_result["system"]["get_sysinfo"]["relay_state"] == 1:
					state = "on"
				else:
					state = "off"
				
				# Update Indigo's device state
				dev.updateStateOnServer("onOffState", state)
				self.logger.debug("getInfo result JSON:\n{}".format(json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': '))))
			except ValueError as e:
				self.logger.error("JSON value error: {} on {}".format(e, result))

		# If a SmartStrip or DualPlug
		else:
			result = tplink_dev.send("info")
			try:
				# pretty print the json result
				json_result = json.loads(result)
				
				# Parse JSON for device state
				plug_num = dev.ownerProps['outlet']
				target_plug = [plug for plug in json_result["system"]["get_sysinfo"]['children'] if plug['id'] == dev.ownerProps['deviceID'] + str(int(plug_num)).zfill(2)]
				state_val = target_plug[0]['state']
				
				if state_val == 1:
					state = "on"
				else:
					state = "off"
				
				# Update Indigo's device state
				dev.updateStateOnServer("onOffState", state)
				self.logger.debug("getInfo result JSON:\n{}".format(json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': '))))
			except ValueError as e:
				self.logger.error("JSON value error: {} on {}".format(e, result))
			
			if dev.model == "SmartStrip" : self.getEnergyInfo("", dev)

	########################################
	# Menu callbacks defined in MenuItems.xml
	########################################
	def toggleDebugging(self):
		if self.debug:
			self.logger.info("Turning off debug logging")
			self.pluginPrefs["showDebugInfo"] = False
		else:
			self.logger.info("Turning on debug logging")
			self.pluginPrefs["showDebugInfo"] = True
		self.debug = not self.debug

	########################################
	# Added by Ramias
	########################################

	def getAlias(self, dev):
		self.logger.debug("sent '{}' status request".format(dev.name))
		if dev.model == "SmartPlug": addr = dev.address
		else: addr = dev.ownerProps['addr']
		port = 9999
		self.logger.debug("Getting alias for ={}, addr={}".format(dev.name, addr, ) )
		tplink_dev = tplink_smartplug (addr, port)

		if dev.model == "SmartPlug": 
			result = tplink_dev.send("info")
			try:
				# pretty print the json result
				json_result = json.loads(result)
				
				# Parse JSON for Alias
				alias = json_result["system"]["get_sysinfo"]['alias']

			except ValueError as e:
				self.logger.error("Error updating device alias.")

		# If a SmartStrip or DualPlug
		else:
			result = tplink_dev.send("info")
			try:
				# pretty print the json result
				json_result = json.loads(result)
				
				# Parse JSON for Alias
				plug_num = dev.ownerProps['outlet']
				target_plug = [plug for plug in json_result["system"]["get_sysinfo"]['children'] if plug['id'] == str(int(plug_num)).zfill(2)]
				alias = target_plug[0]['alias']

			except ValueError as e:
				self.logger.error("Error updating device alias.")

		# Update Indigo's device description/Notes field
		self.logger.debug("Updating device description with " + alias)
		dev.description = str(alias)
		dev.replaceOnServer()
	
	########################################
	def update_device_property(self, device, propertyname, new_value = ""):
	        self.logger.debug("Updating Device Properties for property named " + propertyname + " with value " + new_value)
	        newProps = device.pluginProps
	        newProps.update( {propertyname : new_value} )
	        device.replacePluginPropsOnServer(newProps)

	########################################
	# Initialize SmartStrip
	########################################
	def smartStripInit(self, device):
		self.logger.debug("Top of smartStripInit")
		port = 9999
		addr = device.address.split(":")[0]
		childID = int(device.address.split(":")[1]) - 1
		
		self.logger.debug("Smart strip or plug found.  IP Address is: " + str(addr) + " and Outlet index ID is " + str(childID))
		
		self.update_device_property(device, "addr", addr)
		self.update_device_property(device, "outlet", str(childID))
		
		tplink_dev = tplink_smartplug (addr, port)
		json_result = tplink_dev.send("info")
		json_result = json.loads(json_result)
		deviceID = json_result["system"]["get_sysinfo"]["deviceId"]
		
		self.logger.debug("DeviceID is detected "+ deviceID)
		
		self.update_device_property(device, "deviceID", deviceID)
		
		if device.model == "SmartStrip" : 
			keyValueList = [
			{'key':'curEnergyLevel', 'value':''}]
			device.updateStatesOnServer(keyValueList)

########################################
########################################
	def deviceStartComm(self, device):
		self.debugLog("Starting device: " + device.name)
		if device.id not in self.deviceList:
			self.deviceList.append(device.id)
			device.stateListOrDisplayStateIdChanged()
			self.logger.debug("Device address is " + device.address)
			
			if device.model != "SmartPlug":
				self.smartStripInit(device)

			if not device.description:
				self.getAlias(device)
			else:
				self.logger.debug("Description field already populated.  Not updating.")

	########################################
	def deviceStopComm(self, device):
		self.debugLog("Stopping device: " + device.name)
		if device.id in self.deviceList:
			self.deviceList.remove(device.id)

	def didDeviceCommPropertyChange(self, origDev, newDev):
	   # Return True if a plugin related property changed from
	   # origDev to newDev. Examples would be serial port,
	   # IP address, etc. By default we assume all properties
	   # are comm related, but plugin can subclass to provide
	   # more specific/optimized testing. The return val of
	   # this method will effect when deviceStartComm() and
	   # deviceStopComm() are called.
	   if origDev.pluginProps != newDev.pluginProps:
	      return False
	   return False

	def closedPrefsConfigUi(self, valuesDict, userCancelled):
		if not userCancelled:
			self.debugLog(u"[%s] Getting plugin preferences." % time.asctime())

			try:		
				self.debug = self.pluginPrefs[u'showDebugInfo']
			except:
				self.debug = False

			try:
				if self.interval != self.pluginPrefs["interval"]:
					self.interval = self.pluginPrefs["interval"]
					indigo.server.log ("Polling Interval: " + str(self.interval))
			except:
				self.plugin.errorLog("[%s] Could not retrieve Polling Interval." % time.asctime())

	########################################
	def runConcurrentThread(self):
		self.debugLog("Starting concurrent thread")
		try:
			while True:
				for deviceId in self.deviceList:
					dev = indigo.devices[deviceId]
					self.getInfo("", dev)
				self.sleep(int(self.interval))
		except self.StopThread:
			return
		except Exception as e:
			self.logger.error("runConcurrentThread error: \n%s" % traceback.format_exc(10))
	
	########################################

	########################################
	# General Action callback
	######################
	def actionControlUniversal(self, action, dev):

		###### ENERGY UPDATE ######
		if action.deviceAction == indigo.kUniversalAction.EnergyUpdate:
			# Request hardware module (dev) for its most recent meter data here:
			# ** IMPLEMENT ME **
			if dev.model == "SmartStrip" :
				self.logger.info("Energy Status Update Requested for " + dev.name)
				self.getEnergyInfo("", dev)

		###### STATUS REQUEST ######
		elif action.deviceAction == indigo.kUniversalAction.RequestStatus:
			# Query hardware module (dev) for its current status here:
			# ** IMPLEMENT ME **
			self.getInfo("", dev)