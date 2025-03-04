#!/usr/bin/env python
#
# TP-Link Wi-Fi Smart Plug Protocol Client
# For use with TP-Link HS-100 or HS-110
#
# by Lubomir Stroetmann
# Copyright 2016 softScheck GmbH
#  from: https://github.com/softScheck/tplink-smartplug/blob/master/tplink_smartplug.py
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Also incorporates the send_udp code from https://github.com/p-doyle/Python-KasaSmartPowerStrip
# and the associated decrypt and encrypt functions used for UDP devices.

import json
import struct
import socket
import argparse
from struct import pack

version = 0.2

debug = False

# Predefined Smart Plug Commands
# For a full list of commands, consult tplink_commands.txt
commands = {'info'     : '{"system":{"get_sysinfo":{}}}',
			'on'       : '{"system":{"set_relay_state":{"state":1}}}',
			'off'      : '{"system":{"set_relay_state":{"state":0}}}',
			'cloudinfo': '{"cnCloud":{"get_info":{}}}',
			'wlanscan' : '{"netif":{"get_scaninfo":{"refresh":0}}}',
			'time'     : '{"time":{"get_time":{}}}',
			'schedule' : '{"schedule":{"get_rules":{}}}',
			'countdown': '{"count_down":{"get_rules":{}}}',
			'antitheft': '{"anti_theft":{"get_rules":{}}}',
			'reboot'   : '{"system":{"reboot":{"delay":1}}}',
			'reset'    : '{"system":{"reset":{"delay":1}}}',
			'energy'   : '{"emeter":{"get_realtime":{}}}'
}

# Encryption and Decryption of TP-Link Smart Home Protocol
# XOR Autokey Cipher with starting key = 171
def encrypt(string):
	key = 171
	result = pack('>I', len(string))
	for i in string:
		a = key ^ ord(i)
		key = a
		result += chr(a)
	return result

def decrypt(string):
	key = 171
	result = ""
	for i in string:
		a = key ^ ord(i)
		key = ord(i)
		result += chr(a)
	return result

# def _encrypt_udp(string, prepend_length=True):

#     key = 171
#     result = ''

#     # when sending get_sysinfo using udp the length of the command is not needed but
#     #  with all other commands using tcp it is
#     if prepend_length:
#         result = struct.pack('>I', len(string))

#     for i in string:
#         a = key ^ ord(i)
#         key = a
#         result += chr(a)
#     return result

# def _decrypt_udp(string):

#     key = 171
#     result = ''
#     for i in string:
#         a = key ^ ord(i)
#         key = ord(i)
#         result += chr(a)
#     return result

########################
# the class has an optional deviceID string, used by power Strip devices (and others???)
# and the send command has an optional childID representing the socket on the power Strip
class tplink_smartplug():
	def __init__(self, ip, port, deviceID = None, childID = None):
		self.ip = ip
		self.port = port

		# both or neither deviceID and childID should be set
		if (deviceID is not None and childID is not None) or (deviceID is None and childID is None):
			pass # both combinations are ok
		else:
			quit("ERROR: both deviceID and childID must be set together")

		self.deviceID = deviceID
		self.childID = childID
		if debug:
			print("init with host=%s, port=%s" % ( ip, port) )
		return

	# Send command and receive reply
	def send(self, cmd):
		if cmd in commands:
			cmd = commands[cmd]
		else:
			quit("ERROR: unknown command: %s" % (cmd, ))

		# if both deviceID and childID are set, { context... } is prepended to the command
		if self.deviceID is not None and self.childID is not None:
			context = '{"context":{"child_ids":["' + self.deviceID + "{:02d}".format(int(self.childID)) +'"]},'
			# now replace the initial '{' of the command with that string
			cmd = context + cmd[1:]
		# note error checking on deviceID and childID is done in __init__

		if debug:
			print ("send cmd=%s" % (cmd, ))
		try:
			sock_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock_tcp.connect((self.ip, self.port))
			sock_tcp.settimeout(2)
		except socket.error:
			quit("ERROR: Cound not connect to host " + self.ip + ":" + str(self.port))

		sock_tcp.send(encrypt(cmd))

		data = ""
		while True:
			try:
				new_data = sock_tcp.recv(1024)
				data = data + new_data

			except socket.timeout:
				break
			except socket.error:
				quit("ERROR: Socket error e: " + str(e))

		sock_tcp.close()

		result = decrypt(data)
		return '{' + result[5:]


	# Send command and receive reply
	# def send_udp(self, cmd):
	# 	timeout = 2.0
	# 	if cmd in commands:
	# 		cmd = commands[cmd]
	# 	else:
	# 		quit("ERROR: unknown command: %s" % (cmd, ))

	# 	# if both deviceID and childID are set, { context... } is prepended to the command
	# 	if self.deviceID is not None and self.childID is not None:
	# 		context = '{"context":{"child_ids":["' + self.deviceID + "{:02d}".format(int(self.childID)) +'"]},'
	# 		# now replace the initial '{' of the command with that string
	# 		cmd = context + cmd[1:]
	# 	# note error checking on deviceID and childID is done in __init__

	# 	if debug:
	# 		print ("send cmd=%s" % (cmd, ))

	# 	client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# 	client_socket.settimeout(timeout)

	# 	addr = (self.ip, self.port)

	# 	client_socket.sendto(_encrypt_udp(cmd, prepend_length=False), addr)

	# 	data, server = client_socket.recvfrom(1024)

	# 	result = _decrypt_udp(data)
	# 	client_socket.close()
	# 	return result

# Check if hostname is valid
def validHostname(hostname):
	try:
		socket.gethostbyname(hostname)
	except socket.error:
		parser.error("Invalid hostname.")
	return hostname

########################
# for debugging
def main():
	try:
		import json
	except ImportError:
		print ("using simplejson")
		import simplejson as json

	global debug
	# Parse commandline arguments
	parser = argparse.ArgumentParser(description="TP-Link Wi-Fi Smart Plug Client v" + str(version))
	parser.add_argument("-t", "--target", metavar="<hostname>", required=True, help="Target hostname or IP address", type=validHostname)
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument("-c", "--command", metavar="<command>", help="Preset command to send. Choices are: "+", ".join(commands), choices=commands)
	group.add_argument("-C", "--CMD", metavar="<command>", help="unvalidated Command")
	# group.add_argument("-j", "--json", metavar="<JSON string>", help="Full JSON string of command to send")
	parser.add_argument("-d", "--deviceID", metavar="<deviceID>", required=False, help="device ID for testing powerstrip")
	parser.add_argument("-p", "--childID", metavar="<childID>", required=False, help="port on device", type=int)

	args = parser.parse_args()

#	if (args.deviceID is None) ^ (args.childID is None):
#		# this is true if one is set and the other isn't
#		# we need BOTH to be set or both NOT set
#		print "both device and port must be set or not set"
#		exit(1)

	debug = True
	if args.deviceID:
		my_target = tplink_smartplug(args.target, 9999, deviceID=args.deviceID, childID=args.childID)
	else:
		my_target = tplink_smartplug(args.target, 9999)

#	if args.command is None:
#		cmd = args.json
#	else:
#		cmd = commands[args.command]

	print "Sent:     ", args.command
	if args.childID:
		data = my_target.send(args.command)
	else:
		data = my_target.send(args.command)

	# data[0] = "{"
	try:
		# pretty print the json result
		json_result = json.loads(data)
		print "Received: ", json.dumps(json_result, sort_keys=True, indent=2, separators=(',', ': '))
	except ValueError, e:
		print ("Json value error: %s on %s" % (e, data) )


###### main for testing #####
if __name__ == '__main__' :
	main()
