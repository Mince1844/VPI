# VScript-Python Interface
# Server

# Made by Mince (STEAM_0:0:41588292)

import os
import datetime
import time
import math
import json
import asyncio
import importlib
from   random import randint

import vpi_config
import vpi_interfaces

###################################################################################################

# {
#		"<host>": {
#			"restart_modtime": <num>,
#			"paths": {
#				"<filepath>": {
#					"modtime": <num>,
#					"async": [ {...}, {...} ],
#					"chain": [
#						[ {...}, {...} ],
#						[ {...}, {...} ],
#					]
#				}
#			}
#		}
# }
calls = {}


# {
#	  "<host>": {
#		  "<token>": <response>
#	  }
# }
callbacks = {}

# Handle some types not handled by the json module
class Encoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, bytes):
			if (o == b"\x00"):	 return False
			elif (o == b"\x01"): return True
			else:				 return o.decode("ascii")
		elif isinstance(o, (datetime.date, datetime.datetime, datetime.time)):
			return o.isoformat()
		elif isinstance(o, datetime.timedelta):
			return str(o)
		else:
			return super().default(o)

# Emulate behavior of modulus in C / Squirrel
def mod(a, b):
    return (a % b + b) % b

# Simple encryption algorithm based on timestamp, time, and a key
def Encrypt(string):
	timestamp = int(round(time.time()))

	# Add a bit of randomness
	t = mod(timestamp, 1024)        # Sin doesn't give good output for large values, keep things small
	f = math.fabs(math.sin(16 * t)) # Give our time a bit of variance
	h = math.floor(f * 127 + 0.5)   # Get a hash value from 0 - 127 (really this could be any number though)

	# Initialization vector to provide true randomness since we always use the same key
	# Without this the output tends to repeat quite often
	iv = ""
	for ch in string:
		iv += chr(randint(35, 126))

	enc = ""
	for i, ch in enumerate(string):
		key_index = mod(i, len(vpi_config.SECRET)) # Corresponding index in our key, loop if necessary
		key_char  = vpi_config.SECRET[key_index]

		# Encode the character; shifted using hash and key_char; limited to 32 - 127 ASCII
		enc += chr(32 + mod(ord(ch) + h + ord(iv[i]) + ord(key_char), 95))

	return {
		"enc"       : enc,
		"iv"        : iv,
		"timestamp" : timestamp,
		"ticks"     : 0,
	}

# Decryption
def Decrypt(enc, iv, timestamp, ticks):
	t = mod(timestamp + ticks, 1024)
	f = math.fabs(math.sin(16 * t))
	h = math.floor(f * 127 + 0.5)

	dec = ""
	for i, ch in enumerate(enc):
		key_index = mod(i, len(vpi_config.SECRET))
		key_char  = vpi_config.SECRET[key_index]

		dec_char = mod(ord(ch) - 32 - h - ord(iv[i]) - ord(key_char), 95)
		if (dec_char < 32):
			dec_char += 95 * math.ceil((32 - dec_char) / 95.0)
		dec += chr(dec_char)

	return dec

# Grab the hostname from a path
def GetHostname(path):
	host = os.path.basename(path) # Remove the path to the file
	sep	 = host.find("_vpi_")	  # The client separates hostname from the rest of the filename with _vpi_

	if (sep < 0): return
	return host[:sep]

# Write responses from interface functions to file
MAX_FILE_SIZE = 16000
def WriteCallbacksToFile():
	# Hosts to delete
	delete = []

	for host, info in callbacks.items():
		path = os.path.join(vpi_config.SCRIPTDATA_DIR, f"{host}_vpi_input.interface")
		with open(path, "a+") as f:
			# "a+" file mode seeks to the end of the file, need to go back to the beginning
			f.seek(0)
			# and then read
			contents = f.read()

			# Client hasn't handled our previous write, don't overwrite
			if (len(contents) > 0 and not contents.isspace() and contents != "\x00"):
				continue

			# Wipe the file
			f.truncate(0)

			table = {"Calls": info}
			table["Identity"] = Encrypt(vpi_config.SECRET)

			string   = json.dumps(table, cls=Encoder)
			overflow = {}

			if (len(string) >= MAX_FILE_SIZE):
				# Sort responses by size
				cbs = [[token, response] for token, response in info.items()]
				for l in cbs: l.append(len(json.dumps(l)))
				cbs.sort(key=lambda l: l[2])

				# Loop through and get as many as can fit
				totalsize = 0
				fits = {}
				for l in cbs:
					token, response, size = l

					# Client expects error responses to start with [VPI ERROR]
					if (size >= MAX_FILE_SIZE):
						response = "[VPI ERROR] (token) :: Response size exceeds maximum"
						size = len(json.dumps(response, cls=Encoder))

					if (totalsize + size < MAX_FILE_SIZE):
						totalsize   += size
						fits[token] =  response
					else:
						overflow[token] = response

				table["Calls"] = fits
				string = json.dumps(table, cls=Encoder)

			# Store what we can't fit from our buffer back into callbacks
			if (len(overflow)):
				callbacks[host] = overflow
			# Exhausted all callbacks
			else:
				delete.append(host)

			if (not len(string)): continue

			f.write(string)

	for host in delete:
		del callbacks[host]

# Gather and execute interface functions from calls dict
async def ExecCalls():
	tasks	 = [] # Tasks to gather
	contexts = [] # Needed context for parsing task results

	# Execute calls in call chain synchronously
	async def ExecCallChain(call_chain):
		result = None
		for call in call_chain:
			func = call["func"]
			if (not func.startswith("VPI_")): continue
			try:
				func = getattr(vpi_interfaces, func)
				result = await func(call)
			except:
				continue

		return result

	# Prepare calls
	for host, t1 in calls.items():
		restart_modtime = t1["restart_modtime"]
		for path, t2 in t1["paths"].items():
			modtime = t2["modtime"]
			# Async calls can just be added to tasks directly
			for call in t2["async"]:
				func = call["func"]
				if (not func.startswith("VPI_")): continue
				try:
					func = getattr(vpi_interfaces, func)
					tasks.append(func(call))
					contexts.append({"host":host, "call":call} if (modtime >= restart_modtime) else None)
				except:
					continue

			# Calls in call chains should be executed synchronously, but still add that to tasks
			for call_chain in t2["chain"]:
				if (not len(call_chain)): continue
				last = call_chain[-1]
				tasks.append(ExecCallChain(call_chain))
				contexts.append({"host":host, "call":last} if (modtime >= restart_modtime) else None)

	# Go
	results = await asyncio.gather(*tasks)

	# Set callbacks (to return results to client later)
	for result, context in zip(results, contexts):
		# We don't send a response to client for calls from stale files
		if (context is None): continue

		host  = context["host"]
		call  = context["call"]
		token = call["token"]

		if call["callback"] and token:
			if host not in callbacks:
				callbacks[host] = {}
			callbacks[host][token] = result

# Parse JSON from client output file
def ExtractCallsFromFile(path):
	try:
		with open(path, "r+") as f:
			contents = f.read()

			# StringToFile in VScript ends files with a null byte, which python's json parser doesn't like
			if (contents.endswith("\x00")):
				contents = contents[:-1]

			data = json.loads(contents)

			ident = Decrypt(**data["Identity"])
			if (ident != vpi_config.SECRET):
				print(f"Invalid identification received from client in \"{path}\"")
				return

			host = GetHostname(path)

			calls[host]["paths"][path]["async"].extend(data["Calls"]["async"])
			calls[host]["paths"][path]["chain"].extend(data["Calls"]["chain"])

	except Exception as e:
		print(f"Invalid input received from client in: \"{path}\"")


async def main():
	if (vpi_config.DB_SUPPORT):
		if (vpi_config.DB_TYPE == "MySQL"):
			vpi_config.DB = await vpi_config.aiomysql.create_pool(host=vpi_config.DB_HOST, user=vpi_config.DB_USER, password=vpi_config.DB_PASSWORD, port=vpi_config.DB_PORT, db=vpi_config.DB_DATABASE, autocommit=False)
		elif (vpi_config.DB_TYPE == "SQLite"):
			vpi_config.DB = await vpi_config.aiosqlite.connect(vpi_config.DB_LITE)
		print(str(vpi_config.DB) + "\n")

	global calls
	global callbacks

	last_interface_modtime = os.path.getmtime("vpi_interfaces.py")

	# Watchdog loop
	while True:
		time.sleep(0.2)

		# Watch for changes to vpi_interfaces.py and reload the module if necessary
		# This allows server owners to hotload new interface functions without restarting vpi.py
		last_modtime = os.path.getmtime("vpi_interfaces.py")
		if (last_modtime != last_interface_modtime):
			last_interface_modtime = last_modtime
			try:
				importlib.reload(vpi_interfaces)
			except:
				print("INVALID INTERFACE MODULE CODE!")


		files = os.listdir(vpi_config.SCRIPTDATA_DIR)

		for file in files:
			path = os.path.join(vpi_config.SCRIPTDATA_DIR, file)
			host = GetHostname(path)
			if (not host): continue

			if (host not in calls):
				calls[host] = { "restart_modtime": 0, "paths": {} }

			path_mtime = os.path.getmtime(path)

			# Client tells us our callbacks list is outdated (e.g. map change)
			if (file.endswith("_restart.interface")):
				mtime = calls[host]["restart_modtime"]

				if (path_mtime >= mtime):
					calls[host]["restart_modtime"] = path_mtime

				if (host in callbacks): del callbacks[host]
				os.remove(path)

			# Grab info from clients
			elif (file.endswith("_output.interface")):
				if (path not in calls[host]["paths"]):
					calls[host]["paths"][path] = { "modtime": path_mtime, "async": [], "chain": [] }

				ExtractCallsFromFile(path)
				os.remove(path)

		# Execute interface functions if appropriate and populate callbacks with results
		await ExecCalls()

		# Send results to clients
		WriteCallbacksToFile()

		calls = {}


asyncio.run(main())