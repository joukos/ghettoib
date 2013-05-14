# -*- coding: utf8 -*-
import serial
import array
import io
import sys
import time
import Image
import cStringIO
import struct
import inspect
from datetime import datetime

"""

ghettoIB 0.2


### MIT LICENSE / DISCLAIMER

Copyright (c) 2013 Jouko Strömmer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### NOTE

This software allows a computer with a suitable RS-232 serial connection to crudely control
legacy electrical measurement instruments. Errors in the program controlling the operation of
these devices could have various consequences. It has only been tested with a HP 16500B.

Read the included README.txt for usage information and command summary.

"""



class HPLA:
	"""Control HP 16500B Logic Analyzer Mainframe via RS-232"""
	
	# Constructor

	def __init__(self, tty = "/dev/ttyUSB0", speed = 19200, timeout = None, debug = True, color = True, screenshotfile = "\HP16500.PCX", xonxoff=False, rtscts = True):
		"""Set serial port parameters and initialize connection."""
		self.tty = tty
		self.speed = speed
		self.timeout = timeout
		self.debug = debug
		self.color = color
		self.blank = False
		self.screenshotfile = screenshotfile
		self.xonxoff = xonxoff
		self.rtscts = rtscts
		self.initialize()
	
	def dbg(self, msg, color = None):
		"""Print debug messages."""
		c = dict(cyan = '\033[96m',
			 magenta= '\033[95m', 
			 blue = '\033[94m', 
			 yellow = '\033[93m',
			 green = '\033[92m',
			 red = '\033[91m',
			 end = '\033[0m')
		source = inspect.stack()[1][3] # didn't benchmark but using inspect seemed to make startup much slower
		if self.debug:
			print "["+str(time.time())+"\t"+source+"]\t" + ((c[color] + msg + c['end']) if (c.has_key(color) and self.color) else msg)


	# High-level functionality 

#	def dir(self, pat

	def save_data(self, filename = None, module = None):
		"""Save acquisition data of the current or specified module into a file."""
		if not module:
			module = self.main_menu_query()[0]
		if not filename:
			filename = "module-" + str(module) + "-data-" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + ".dat"
		self.dbg("Saving acquisition data of module " + str(module) + " into " + str(filename), "cyan")
		self.main_select(module)
		self.save(self.syst_data_query(), filename)

	def load_data(self, filename, module = None):
		"""Load acquisition data from a file to current or specified module."""
		if not module:
			module = self.main_menu_query()[0]
		self.dbg("Loading acquisition data from file " + str(filename) + " to module " + str(module), "cyan")
		self.main_select(module)
		self.syst_data(self.load(filename))

	def save_settings(self, filename = None, module = None):
		"""Save current or specified module settings into a file."""
		if not module:
			module = self.main_menu_query()[0]
		if not filename:
			filename = "module-" + str(module) + "-settings-" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + ".dat"
		self.dbg("Saving settings data of module " + str(module) + " into " + str(filename), "cyan")
		self.main_select(module)
		self.save(self.syst_setup_query(), filename)
			
	def load_settings(self, filename, module = None):
		"""Load settings into current (visible) or specified module."""
		if not module:
			module = self.main_menu_query()[0]
		self.dbg("Loading settings data from file " + str(filename) + " to module " + str(module), "cyan")
		self.main_select(module)
		self.syst_setup(self.load(filename))

	def menumap (self):
		"""Map the available menus on the instrument. Iterate through reasonable
		numbers and save all the menus that didn't give the error (-211, "Legal comman").

		Returns:
		A list of tuples: [ (module_index, [menu1, menu2, ...]), (module_index,[menu1, ... ]) ]

		Example:
		[(0, [0, 1, 2, 3, 4, 5]), (3, [0, 1, 2, 3, 4, 5]), (4, [0, 1, 2, 3, 4, 5]), (5, [0, 1, 3, 5, 7, 9])]

		"""
		self.serialport.timeout = 5
		self.flush_errors()
		beeper = self.main_beeper_query()
		self.main_beeper(0)
		available_menus = []
		self.dbg("Searching for available menus...", "cyan")
		for module in range(-2,11): # -2 to 10
			module_menus = []
			for menu in range(16): # should be enough?
				self.main_menu(module, menu)
				self.comm_opc_query()
				err = self.syst_error_query()
				if err[0] == 0:
					self.dbg("Found menu " + str(module) + "," + str(menu), "green")
					module_menus += [menu]
				time.sleep(0.1)
			if module_menus:
				available_menus += [(module, module_menus)]
		time.sleep(0.5)
		self.main_beeper(beeper)
		self.serialport.timeout = self.timeout
		return available_menus

	def screenshot_menus(self, image_basename, menumap):
		"""Screenshot all menus in the menumap list."""
		current = self.mmem_msi_query()
		for module_menus in menumap:
			module, menulist = module_menus
			for menu in menulist:
				floppy = module == 0 and menu == 2
				self.dbg("Screenshotting menu " + str(module) + "," + str(menu), "cyan")
				self.main_menu(module, menu)
				self.comm_opc_query()
				self.screenshot(image_basename + "_" + str(module) + "-" + str(menu) + ".png", msus=("INT1" if floppy else current))
				self.comm_opc_query()
				time.sleep(1)
		return menumap
				
	def dimscreen (self):
		"""Set all colors black, one by one."""
		self.dbg("Dimming screen...", "cyan")
		for c in range(1,8):
			self.main_setcolor(c, 0, 0, 0)
	
	def togglescreen(self):
		"""Toggle between black and default colors."""
		self.blank = not self.blank
		if self.blank:
			self.dimscreen()
		else:
			# instead of resetting to default colors, one could
			# add color scheme support and things like 
			# palette = savecolors()
			self.dbg("Resetting screen colors...", "cyan")
			self.main_setcolor_default()

	def synctime (self):
		"""Sets instrument RTC to current date and time."""
		self.dbg("Synchronizing instrument RTC with current time...", "cyan")
		self.main_rtc(datetime.now())
	
	def installed_modules(self):
		"""Returns a list of (slot, module-name, master) tuples of each installed module.
		modulelist is the result list of the module query (":CARDCAGE?").
		Names associated with ID numbers are from 'HP16500B/16501A Logic Analysis System 
		Programmer's Guide' (rev. April 1994). Refer to CARDcage query documentation for details.

		"""
		self.dbg("Querying installed modules...", "cyan")
		modulelist = self.main_cardcage_query()
		numslots = len(modulelist)/2
		slots = []
		idnumbers = {	1:"HP 16515A 1 GHz Timing Master Card",
				2:"HP 16516A 1 GHz Timing Expansion Card",

				11:"HP 16530A Oscilloscope Timebase Card",
				12:"HP 16531A Oscilloscope Acquisition Card",
				13:"HP 16532A Oscilloscope Card",
				21:"HP 16520A Pattern Generator Master Card",
				22:"HP 16521A Pattern Generator Expansion Card",
				30:"HP 16511B Logic Analyzer Card",
				31:"HP 16510A or B Logic Analyzer Card",
				32:"HP 16550A Logic Analyzer Master Card",
				33:"HP 16550A Logic Analyzer Expansion Card",
				40:"HP 16540A Logic Analyzer Card",
				41:"HP 16541A Logic Analyzer Card",
				42:"HP 16542A Logic Analyzer Master Card",
				43:"HP 16542A Logic Analyzer Expansion Card"}
		masterlist = modulelist[numslots:]
		for index, idnum in enumerate(modulelist[0:numslots]):
			if int(idnum) >= 0:
				slots.append((index + 1, idnumbers[int(idnum)], masterlist[index]))
		return slots
	
	def screenshot(self, filename, printfile = None, msus = "INT0", download = True):
		"""Capture color screenshot and save as PNG.
		First saves the screenshot in PCX format to the instrument's internal
		hard disk, then uploads the image data to be written into a PNG file.
		
		"""
		if not printfile:
			printfile = self.screenshotfile
		self.dbg("Capturing screen shot as " + printfile, "cyan")
		self.syst_print("SCREEN", printfile, msus = msus)
		self.dbg("Waiting for disk operation to finish...", "cyan")
		self.comm_opc_query()
		if download:
			self.dbg("Transferring screen shot...", "cyan")
			imagedata = cStringIO.StringIO(self.mmem_upload_query(printfile, msus = msus))
			im = Image.open(imagedata)
			self.dbg("Saving screen shot as " + filename, "cyan")
			im.save(filename, "PNG")
			
	def flush_errors(self):
		"""Return a list of all errors in the instrument's error queue."""
		self.dbg("Flushing error queue...", "cyan")
		errors = []
		while 1:
			e = self.syst_error_query()
			if type(e) != tuple:
				break;
			if e[0] == 0: # 0 = 'No errors'
				break;
			errors += [e]
		return errors


	# File methods

	def readblock (self, timeout = 0.5): # adjust timeout?
		"""Read definite-length block data from instrument.
		Response is in the form '#<number of digits in block length><block length><data>',
		for example "#800000075<75 bytes of data>", where '#8' means the next 8 digits represent
		the length of the block, ie. 00000075 = 75 bytes.
		"""
		self.serialport.timeout=timeout
		blockpound = self.serialport.read(1) # read block header
		data = ""
		if blockpound == '#':
			numdigits = int(self.serialport.read())
			numdata = int(self.serialport.read(numdigits))
			self.dbg("Receiving block of " + str(numdata) + " bytes", "cyan")
			data = self.serialport.read(numdata)
			self.dbg("Received " + str(len(data)) + " bytes.", "cyan")
		self.serialport.timeout=self.timeout
		if not data:
			self.dbg("Didn't receive anything.", "yellow")
		self.serialport.flushInput() # for eating extra newlines and such (upload_query...)
		return data
	
	def save(self, data, filename):
		"""Saves data into a file."""
		with open(filename, 'wb') as f:
			self.dbg("Writing " + str(len(data)) + " bytes to file " + filename, "cyan")
			f.write(data)

	def load(self, filename):
		"""Returns contents of a file."""
		with open(filename, 'rb') as f:
			self.dbg("Opened file " + filename, "cyan")
			return f.read()
	
	def put(self, filename, remotename, desc = "from ghettoIB", type = -5813, msus="INT0"):            
		"""Transfer a file from the controller to the instrument. By default the file
		type is DOS (-5813) and the file is saved on the hard disk."""
	        self.dbg("Sending file " + str(filename) + " to file " + str(remotename) + ", description: '" + str(desc) + "', type " + str(type) + ", msus: " + str(msus), "cyan")
		self.mmem_download(remotename, desc, type, self.load(filename), msus = msus)
		self.comm_opc_query()
		
	def get(self, filename, remotename, msus = "INT0"):
		"""Transfer a file from the instrument to the controller, by default from the
		hard disk."""
	        self.dbg("Downloading file " + str(remotename) + " to file " + str(filename) + " from msus: " + str(msus), "cyan")
	        self.save(self.mmem_upload_query(remotename, msus = msus), filename)
		self.comm_opc_query()


	# Serial comms

	def initialize(self):
		"""Create serial stream for IO."""
		if self.xonxoff:
			self.rtscts = False
		self.serialport = serial.Serial(self.tty, self.speed, timeout = self.timeout, xonxoff = self.xonxoff, rtscts = self.rtscts)
		if self.serialport:
			self.dbg("Opened serial port " + self.tty, "green")

	def close(self):
		"""Close serial port."""
		self.serialport.close()
		self.dbg("Closed serial port.", "green")
			
	def sendblock(self, buffer):
		"""Formats a data block (array.array of integers) with a header and sends it to
		the instrument.
		"""
		ar = array.array('B')
		self.dbg("Sending datablock (" + str(len(buffer)) + " bytes)", "blue")
		ar.fromstring("#8" + "%08d" % (len(buffer)))
		ar.fromstring(buffer + "\n"*32) # Magic newlines to apparently pad the output
		self.send(ar)
		self.dbg("Send finished.", "blue")
	
	def flush(self, timeout = 1):
		"""Flush the input buffer.

		"""
		self.dbg("Flushing input...", "blue")
		self.serialport.timeout=timeout
		buf = self.serialport.read(8192*1024) # up to 8MB
		self.serialport.timeout=self.timeout
		return buf
	
	def send(self, data, newline = None, flush = True):
		"""Simply send data as-is immediately."""
		self.serialport.timeout = None
		self.dbg("Sending data of type: " + str(type(data)), "blue")
		if type(data) == array.array:
			sent = 0
			ar = array.array('B')
			length = len(data)
			for b in data:
				sent += 1
				ar.extend([b])
				if sent % 4096 == 0:
					self.dbg("Progress: " + str(sent) + " / " + str(length-42) + " + 10 + 32 bytes...", "blue")
				self.serialport.write(ar)
				ar.pop()
		else:
			self.serialport.write(data)
		self.serialport.timeout = self.timeout
		if flush:
			return self.flush()
		else:
			return
	
	def cmd (self, string, wait = None, multiline = None):
		"""Send a command to the instrument. If wait = True, block until there is a response,
		otherwise don't wait.

		"""
		self.dbg("Sending command: '" + string + "'", "blue")
		self.serialport.write(string + "\n")
		self.serialport.flush()
		buffer = ""
		if wait:
			if multiline == True:
				self.dbg("Reading multiline reply...", "blue")
				return self.readblock()
			else: 
				self.dbg("Reading reply...", "blue")
				while True:
					self.serialport.timeout = wait
					byte = self.serialport.read(1)
					if byte:
						buffer += byte
					else:
						break
					if '\n' in buffer:
						break
		self.serialport.timeout = self.timeout
		numbytes = len(buffer)
		if numbytes > 0:
			self.dbg("Read " + str(numbytes) + " bytes.", "blue")
		return buffer.rstrip()
	
	def query (self, string, timeout = 0.2):
		"""Shorthand to send a command and return a single-line answer from the instrument."""
		return self.cmd(string, wait = timeout)

	def query_num (self, string, timeout = 0.2):
		"""Turn query result into a number."""
		r = self.query(string, timeout = timeout)
		if str(r):
			return self.number(r)

	def query_numlist (self, string, timeout = 0.2):
		"""Parse a number list from string ("1,2,3,4,...") and return a proper list."""
		return [self.number(e) for e in self.query(string, timeout = timeout).split(',')]

	def quote(self, string):
		"""Just quote an argument if there is any."""
		return "'" + string + "'" if string else ""

	def opts(self, *args):
		"""Simplistic command line builder."""
		if len(args) > 0:
			s = " " # space between command and first argument
			for o in args:
				if o == None: # skip if None
					continue
				s += str(o) + "," if str(o) else "" # separate with commas
			return s[:-1] # get rid of the trailing one
		else:
			return ""

	def number(self, string):
		"""Turn a string representing an integer or a real number to their proper data types."""
		return ("." in string and [float(string)] or [int(string)])[0] if string else ""
	

	# 
	# IEEE 488.2 Commands and their abbreviated documentation
	#
	# starting from here to end of file.
	#



	# Common commands

	def comm_cls(self):
		"""*CLS (Clear Status)

		*CLS
			
		Clear all event status registers, queues and data structures, including
		the device defined error queue and status byte.

		"""
		self.cmd("*CLS")

	def comm_ese(self, mask):
		"""*ESE (Event Status Enable)

		*ESE <mask>

		Set the Standard Event Status Enable Register bits.

		Arguments:
		mask	-- integer from 0 to 255

		Contents of register:
		Bit position	Bit weight	Enables
		7		128		PON - Power On
		6		64		URQ - User Request
		5		32		CME - Command Error
		4		16		EXE - Execution Error
		3		8		DDE - Device Dependent Error
		2		4		QYE - Query Error
		1		2		RQC - Request Control
		0		1		OPC - Operation Complete

		"""
		self.cmd("*ESE " + str(mask))

	def comm_ese_query(self):
		"""*ESE (Event Status Enable) Query

		*ESE?

		Returns:
		Integer from 0 to 255 -- the current contents of the enable register

		"""
		return self.query_num("*ESE?")

	def comm_esr_query(self):
		"""*ESR (Event Status Register) Query

		*ESR?
		
		Queries the contents of the Standard Event Status Register. Reading the
		register clears the Standard Event Status Register.

		Returns:
		Integer from 0 to 255 -- the current contents of the event status register

		Contents of register:
		Bit position	Bit weight	Bit name	Condition
		7		128		PON		0 = register read - not in power up mode
								1 = power up
		6		64		URQ		0 = user request - not used - always zero
		5		32		CME		0 = no command errors
								1 = a command error has been detected
		4		16		EXE		0 = no execution errors
								1 = an execution error has been detected
		3		8		DDE		0 = no device dependent error has been detected
								1 = a device dependent error has been detected
		2		4		QYE		0 = no query errors
								1 = a query error has been detected
		1		2		RQC		0 = request control - not used - always zero
		0		1		OPC		0 = operation is not complete
								1 = operation is complete


		"""
		return self.query_num("*ESR?")

	def comm_idn_query(self):
		"""*IDN (Identification Number)

		*IDN?
			
		Allows the instrument to identify itself. 
		
		Returns: 
		String "HEWLETT-PACKARD,16500B,0,REV <revision_code>". 
		
		<revision_code> is a four digit code in the format XX.XX representing 
		the current ROM revision.
		
		"""
		return self.query("*IDN?")

	def comm_ist_query(self):
		"""*IST (Individual Status)

		*IST?

		Allows the instrument to identify itself during parallel poll by allowing the
		controller to read the current state of the IEEE 488.1 defined "ist" local
		message in the instrument.

		Returns:
		Integer 0 or 1

		1 -- indicates the "ist" local message is false
		0 -- indicates the "ist" local message is true
		
		"""
		return self.query_num("*IST?")

	def comm_opc(self):
		"""*OPC (Operation Complete)
		
		*OPC

		Will cause the instrument to set the operation complete bit in the Standard
		Event Status Register when all pending device operations have finished.

		"""
		self.cmd("*OPC")
	
	def comm_opc_query(self, timeout = 900):
		"""*OPC (Operation Complete)

		*OPC?
		
		The query places an ASCII "1" in the output queue when all pending device
		operations have been completed.

		Useful for waiting for an operation (eg. disk write) to complete.

		"""
		return self.query_num("*OPC?", timeout = timeout)

	def comm_opt_query(self):
		"""*OPT (Option Identification)

		*OPT?

		Identifies the software installed in the HP 16500B. This query returns nine
		parameters.

		Returns:
		List of names of installed software options and software installed in modules.

		"""
		return [str(o) for o in self.query("*OPT?").split(',')]

	def comm_pre(self, mask):
		"""*PRE (Parallel Poll Enable Register Enable)

		*PRE <mask>

		Sets the parallel poll register enable bits. The Parallel Poll Enable Register
		contains a mask value that is ANDed with the bits in the Status Bit Register to
		enable an "ist" during a parallel poll.

		Arguments:
		mask	-- integer from 0 to 65535

		Contents of register:
		Bit position	Bit weight	Enables
		15-8				Not used
		7		128		Not used
		6		64		MSS - Master Summary Status
		5		32		ESB - Event Status
		4		16		MAV - Message Available
		3		8		LCL - Local
		2		4		Not used
		1		2		Not used
		0		1		MSB - Module Summary

		
		"""
		self.cmd("*PRE " + str(mask))

	def comm_pre_query(self):
		"""*PRE (Parallel Poll Enable Register Enable) Query

		*PRE?

		Returns:
		Integer from 0 to 65535 -- the current value of the register

		"""
		return self.query_num("*PRE?")

	def comm_rst(self):
		"""*RST (Reset)

		*RST

		Not implemented on the HP 16500B. The HP 16500B will accept this command, but
		the command has no effect on the system.
		
		"""
		self.cmd("*RST")

	def comm_sre(self, mask):
		"""*SRE (Service Request Enable)

		*SRE <mask>
		
		Sets the Service Request Enable Register bits. The Service Request Enable Register
		contains a mask value for the bits to be enabled in the Status Byte Register. A
		one in the Service Request Enable Register will enable the corresponding bit in
		the Status Byte Register. A zero will disable the bit.

		Arguments:
		mask	-- integer from 0 to 255

		Contents of register:
		Bit position	Bit weight	Enables
		15-8				not used
		7		128		not used
		6		64		MSS - Master Summary Status (always 0)
		5		32		ESB - Event Status
		4		16		MAV - Message Available
		3		8		LCL - Local
		2		4		not used
		1		2		not used
		0		1		MSB - Module Summary


		"""
		self.cmd("*SRE " + str(mask))

	def comm_sre_query(self):
		"""*SRE (Service Request Enable) Query

		*SRE?

		Returns:
		Integer from 0 to 255 -- the current value

		"""
		return self.query_num("*SRE?")

	def comm_stb_query(self):
		"""*STB (Status Byte)

		*STB?

		Returns:
		Integer from 0 to 255 -- the current value of the instrument's status byte

		Contents of register:
		Bit position	Bit weight	Bit name	Condition
		7		128				0 = not used
		6		64		MSS		0 = instrument has no reason for service
								1 = instrument is requesting service
		5		32		ESB		0 = no event status conditions have occurred
								1 = an enabled event status condition has occurred
		4		16		MAV		0 = no output messages are ready
								1 = an output message is ready
		3		8		LCL		0 = a remote-to-local transition has not occurred
								1 = a remote-to-local transition has occurret
		2		4				not used
		1		2				not used
		0		1		MSB		0 = a module or the system has activity to report
								1 = no activity to report

		"""
		return self.query_num("*STB?")

	def comm_trg(self):
		"""*TRG (Trigger)

		*TRG

		The *TRG command has the same effect as a Group Execute Trigger (GET). If no
		modules are configured in the Intermodule menu, this command has no effect.

		"""
		self.cmd("*TRG")

	def comm_tst_query(self):
		"""*TST (Test) Query

		*TST?

		The *TST query returns the results of the power-up self-test. The result of that
		test is a 9-bit mapped value. A one in the corresponding bit means that the test
		failed and a zero means that the test passed.

		Returns:
		Integer from 0 to 511 -- power-up self-test results

		Bits returned by *TST? Query (Power-Up Test Results):
		Bit position	Bit weight	Test
		8		256		Disk Test
		7		128		not used
		6		64		not used
		5		32		Front-panel Test
		4		16		HIL Test
		3		8		Display Test
		2		4		Interrupt Test
		1		2		RAM Test
		0		1		ROM Test


		"""
		return self.query_num("*TST?")

	def comm_wai(self):
		"""*WAI (Wait)

		*WAI

		Causes the device to wait until completing all of the overlapped commands
		before executing any further commands or queries. An overlapped command is a
		command that allows execution of subsequent commands while the device operations
		initiated by the overlapped command are still in progress. Some example of
		overlapped commands for the HP 16500B are STARt and STOP.

		"""
		self.cmd("*WAI")
		

	# Mainframe commands
	
	def main_beeper(self, setting = None):
		"""BEEPer

		:BEEPer [{ON|1}|{OFF|0}]

		Sets the beeper mode, which turns the beeper sound of the instrument on and off.
		When BEEPer is sent with no argument, the beeper will be sounded without affecting
		the current mode.

		Arguments:
		setting	-- mode value: 1/"1"/"ON" or 0/"0"/"OFF"
	
		"""
		
		self.cmd(":BEEP" + self.opts(setting))
	
	def main_beeper_query(self):
		"""BEEPer Query

		:BEEPer?

		Returns:
		Integer 1 or 0 - currently selected mode
	
		"""
		
		return self.query_num(":BEEP?")

	def main_capability_query(self):
		"""CAPability Query

		:CAPability?

		The CAPability query returns the IEEE 488.1 "Interface Requirements for Devices"
		capability sets implemented in the device.

		Returns:
		Implemented capability set as a list.

		Sets implemented in the HP 16500B:
		IEEE488,1987,SH1,AH1,T5,L4,SR1,RL1,PP1,DC1,DT1,C0,E2

		HP 16500B Capability Sets:
		Mnemonic	Capability Name				Implementations
		SH		Source Handshake			SH1
		AH		Acceptor Handshake			AH1
		T		Talker (or TE - Extended Talker)	T5
		L		Listener (or LE - Extended Listener)	L4
		SR		Service Request				SR1
		RL		Remote Local				RL1
		PP		Parallel Poll				PP1
		DC		Device Clear				DC1
		DT		Device Trigger				DT1
		C		Any Controller				C0
		E		Electrical Characteristic		E2

		"""
		return [str(c) for c in self.query(":CAP?").split(',')]
	
	def main_cardcage_query(self):
		"""CARDcage Query

		:CARDcage?

		Identifies the modules that are installed in the mainframe.

		Returns:
		A list of integers, first half are identification numbers and the rest module
		assignment for each card. Length of the list will be 10 elements, or 20 if 
		HP 16501A is connected.

		(see docstring for installed_modules() for table of ID numbers)

		"""
		return self.query_numlist(":CARDCAGE?")

	def main_cese(self, value):
		"""CESE (Combined Event Status Enable)

		:CESE <value>

		Sets the Combined Event Status Enable register. This register is the enable
		register for the CESR register and contains the combined status of all of the
		MESE (Module Event Status Eable) register of the HP 16500B.

		Arguments:
		value	-- integer from 0 to 65535

		Contents of register:
		Bit	Weight		Enables
		11-15			not used
		10	1024		Module in slot J
		9	512		Module in slot I
		8	256		Module in slot H
		7	128		Module in slot G
		6	64		Module in slot F
		5	32		Module in slot E
		4	16		Module in slot D
		3	8		Module in slot C
		2	4		Module in slot B
		1	2		Module in slot A
		0	1		Intermodule

		"""
		self.cmd(":CESE " + str(value))

	def main_cese_query(self):
		"""CESE (Combined Event Status Enable) Query

		:CESE?

		Returns:
		Integer from 0 to 65535	-- the current setting

		"""
		return self.query_num(":CESE?")

	def main_cesr_query(self):
		"""CESR (Combined Event Status Register) Query

		:CESR?

		Returns the contents of the Combined Event Status register. This register
		contains the combined status of all of the MESRs (Module Event Status Registers)
		of the HP 16500B System.

		Returns:
		Integer from 0 to 65535

		Contents of register:
		Bit	Bit weight	Bit name	Condition
		11-15					0 = not used
		10	1024		Module J	0 = No new status
							1 = Status to report
		9	512		Module I	0 = No new status
							1 = Status to report
		8	256		Module H	0 = No new status
							1 = Status to report
		7	128		Module G	0 = No new status
							1 = Status to report
		6	64		Module F	0 = No new status
							1 = Status to report
		5	32		Module E	0 = No new status
							1 = Status to report
		4	16		Module D	0 = No new status
							1 = Status to report
		3	8		Module C	0 = No new status
							1 = Status to report
		2	4		Module B	0 = No new status
							1 = Status to report
		1	2		Module A	0 = No new status
							1 = Status to report
		0	1		Intermodule	0 = No new status
							1 = Status to report

		"""
		return self.query_num(":CESR?")

	def main_eoi(self, setting):
		"""EOI (End Or Identify)

		:EOI {{ON|1}|{OFF|0}}

		Specifies whether or not the last byte of a reply from the instrument is to be
		sent with the EOI bus control line set true or not. If EOI is turned off, the
		logic analyzer will no longer be sending IEEE 488.2 compliant responses.

		Arguments:
		setting	-- 1/"1"/"ON" or 0/"0"/"OFF"

		"""
		self.cmd(":EOI " + str(setting))

	def main_eoi_query(self):
		"""EOI (End Or Identify) Query

		:EOI?

		Returns:
		Integer 0 or 1 -- current status of EOI

		"""
		return self.query_num(":EOI?")

	def main_ler_query(self):
		"""LER (LCL Event Register) Query

		:LER?

		The LER query allows the LCL Event Register to be read. After the LCL Event
		Register is read, it is cleared. A one indicates a remote-to-local transition
		has taken place. A zero indicates a remote-to-local transition has not taken
		place.

		Returns:
		Integer 0 or 1

		"""
		return self.query_num(":LER?")

	def main_lockout(self, setting):
		"""LOCKout

		:LOCKout {{ON|1}|{OFF|0}}

		Locks out or restores front panel operation. When this function is on, all
		controls (except the power switch) are entirely locked out.

		Arguments:
		setting	-- 1/"1"/"ON" or 0/"0"/"OFF"

		"""
		self.cmd(":LOCK" + self.opts(setting))

	def main_lockout_query(self):
		"""LOCKout Query

		:LOCKout?

		Returns:
		Integer 0 or 1	-- current status of the LOCKout command

		"""
		return self.query_num(":LOCK?")

	def main_menu(self, module, menu = 0):
		"""MENU

		:MENU <module>[,<menu>]

		Puts a menu on the display. The first parameter specifies the desired module.
		The optional second parameter specifies the desired menu in the module (defaults
		to 0).

		Arguments:
		module	-- module to select (from -2 to 5, or up to 10 if HP 16501A is connected)
		menu	-- desired menu in the module (starting from 0)

		First Parameter Values:
		Parameter	Menu
		0		System/Intermodule
		1		Module in slot A
		2		Module in slot B
		3		Module in slot C
		4		Module in slot D
		5		Module in slot E
		-1		Software option 1
		-2		Software option 2
		Available when an HP 16501A is connected:
		6		Module in slot F
		7		Module in slot G
		8		Module in slot H
		9		Module in slot I
		10		Module in slot J

		System Menu Values:
		Menu Command Parameters		Menu
		MENU 0,0			System Configuration menu
		MENU 0,1			Hard disk menu
		MENU 0,2			Flexible disk menu
		MENU 0,3			Utilities menu
		MENU 0,4			Test menu
		MENU 0,5			Intermodule menu
		
		"""
		self.cmd(":MENU" + self.opts(module, menu))

	def main_menu_query(self):
		"""MENU Query

		:MENU?

		Returns:
		Tuple (module, menu)	-- current menu selection

		"""
		r = self.query(":MENU?")
		if str(r):
			return tuple(int(m) for m in r.split(','))

	def main_mese(self, n, value):
		"""MESE<N> (Module Event Status Enable)

		:MESE<N> <enable_value>	

		Sets the Module Event Status Enable register. This register is the enable register
		for the MESR register. The <N> index specifies the module, and the parameter
		specifies the enable value. For the HP 16500B alone, the <N> index 0 through 5
		refers to system and modules 1 through 5 respectively. With an HP 16501A connected,
		the <N> index 6 through 10 refers to modules 6 through 10 respectively.

		Arguments:
		n	-- integer from 0 to 10, the <N> value
		value	-- integer from 0 to 255, the enable value

		HP 16500B Mainframe (Intermodule) Module Event Status Enable Register
		Bit position	Bit weight	Enables
		7		128		not used
		6		64		not used
		5		32		not used
		4		16		not used
		3		8		not used
		2		4		not used
		1		2		RNT - Intermodule Run Until Satisfied
		0		1		MC - Intermodule Measurement Complete


		"""
		self.cmd(":MESE" + str(n) + " " + str(value))

	def main_mese_query(self, n):
		"""MESE<N> (Module Event Status Enable) Query

		:MESE<N>?

		Arguments:
		n	-- integer from 0 to 10, the <N> value

		Returns:
		Integer from 0 to 255	-- the enable value

		"""
		return self.query_num(":MESE" + str(n) + "?")

	def main_mesr_query(self, n):
		"""MESR<N> (Module Event Status Register) Query

		:MESR<N>?

		Returns the contents of the Module Event Status register. The <N> index
		specifies the module.

		Arguments:
		n	-- integer from 0 to 10, the <N> value

		Returns:
		Integer from 0 to 255	-- the enable value

		HP 16500B Mainframe Module Event Status Register:
		Bit	Bit weight	Bit Name	Condition
		7	128				0 = not used
		6	64				0 = not used
		5	32				0 = not used
		4	16				0 = not used
		3	8				0 = not used
		2	4				0 = not used
		1	2		RNT		0 = Intermodule Run until not satisfied
							1 = Intermodule Run until satisfied
		0	1		MC		0 = Intermodule Measurement not satisfied
							1 = Intermodule Measurement satisfied


		"""
		return self.query_num(":MESR" + str(n) + "?")

	def main_rmode(self, mode):
		"""RMODe

		:RMODe {SINGle|REPetitive}

		Specifies the run mode for the selected module (or Intermodule). If the
		selected module is in the intermodule configuration, then the intermodule
		run mode will be set by this command.

		After specifying the run mode, use the STARt command to start the acquisition.

		Arguments:
		mode	-- "SINGLE" or "REPETITIVE" for single and repetitive mode respectively

		"""
		self.cmd(":RMODE " + mode)

	def main_rmode_query(self):
		"""RMODe Query

		:RMODe?

		Returns:
		String	-- current setting ("SINGLE"/"REPETITIVE")

		"""
		return self.query(":RMODE?")

	def main_rtc(self, datetime):
		"""RTC (Real-time Clock)

		:RTC <day>,<month>,<year>,<hour>,<minute>,<second>

		Sets the real-time clock to given date and time.

		Arguments:
		datetime	-- a datetime object

		"""
		self.cmd(":RTC "+ str(datetime.day) + "," + str(datetime.month) + "," + str(datetime.year) + "," + str(datetime.hour) + "," + str(datetime.minute) + "," + str(datetime.second))

	def main_rtc_query(self):
		"""RTC (Real-time Clock) Query

		:RTC?

		Returns:
		datetime object	-- Real-time clock settings

		"""
		t = self.query_numlist(":RTC?")
		if len(t) == 6:
			return datetime(t[2], t[1], t[0], t[3], t[4], t[5])

	def main_select(self, module):
		"""SELect

		:SELect <module>

		Selects which module (or system) will have parser control. The appropriate
		module (or system) must be selected before any module (or system) specific
		commands can be sent. SELECT 0 selects System, SELECT 1 through 5 selects
		modules A through E in an HP 16500B only. SELECT 1 through 10 selects
		modules A through J when an HP 16501A is connected. -1 and -2 selects
		software options 1 and 2 respectively.

		When a module is selected, the parser recognizes the module's commands and
		the System/Intermodule commands. When SELECT 0 is used, only the System/
		Intermodule commands are recognized by the parser.

		Arguments:
		module	-- integer from -2 to 10, module index to select

		"""
		self.cmd(":SELECT " + str(module))

	def main_select_query(self):
		"""SELect Query

		:SELect?

		Returns:
		Integer from -2 to 10	-- the current module selection

		"""
		return self.query_num(":SELECT?")

	def main_setcolor(self, color, hue, sat, lum):
		"""SETColor

		:SETColor {<color>,<hue>,<sat>,<lum>|DEFault}

		(* note: for setting the default colors, use main_setcolor_default())

		Used to change one of the color selections on the CRT. Color number 0
		cannot be changed.

		Arguments:
		color	-- integer from 1 to 7, color number
		hue	-- integer from 0 to 100, hue
		sat	-- integer from 0 to 100, saturation
		lum	-- integer from 0 to 100, luminosity

		"""
		self.cmd(":SETC " + ",".join(map(str, [color, hue, sat, lum])))

	def main_setcolor_default(self):
		"""SETColor default

		Resets the default screen colors.

		"""
		self.cmd(":SETC DEFAULT")

	def main_setcolor_query(self, color):
		"""SETColor Query

		:SETColor? <color>

		Returns:
		List of four integers	-- color, hue, saturation and luminosity. If you
		request color number 0, the instrument will beep and return the values for
		color number 1.


		"""
		return self.query_numlist(":SETC? " + str(color))
	
	def main_start(self):
		"""STARt

		:STARt

		Starts the selected module (or Intermodule) running in the specified run
		mode (see RMODe). If the specified module is in the Intermodule configuration,
		then the Intermodule run will be started.

		The STARt command is an overlapped command (allows execution of subsequent
		commands while the device operations initiated by the overlapped command are
		still in progress).


		"""
		self.cmd(":START")

	def main_stop(self):
		"""STOP

		:STOP

		Stops the selected module (or Intermodule). If the specified module is in
		the Intermodule configuration, then the Intermodule run will be stopped.

		The STOP command is an overlapped command.


		"""
		self.cmd(":STOP")

	def main_xwindow(self, mode, display = None):
		"""XWINdow

		:XWINdow {OFF|0}
		:XWINdow {ON|1}[,<display name>]

		Opens or closes a windows on an X Window display server. The XWINdow ON command
		opens a window. If no display name is specified, the display name already stored
		in the HP 16500B X Window configuration menu is used. If a display name is
		specified, that name is used. The specified display name also is stored in non-
		volatile memory in the HP 16500B.

		(* note: If the instrument doesn't have a network interface for this to actually
		 work, it seems to just freeze with the message about opening the window. Not sure
		 if there is some timeout.)

		Arguments:
		mode	-- 1/"1"/"ON" or 0/"0"/"OFF"
		display	-- a string containing an IP optionally followed by display and screen
			   specifier: "12.3.47.11" or "12.3.47.11:0.0"

		"""
		self.cmd(":XWINDOW" + self.opts(mode, display))

	
	# SYSTem subsystem commands

	def syst_data(self, blockdata):
		"""DATA

		:SYSTem:DATA <block_data>

		Allows you to send and receive acquired data to and from a controller in block
		form. The format and length of block data depends on the instruction being used
		and the configuration of the instrument. DATA commands and queries vary for
		individual modules, a complete chapter is dedicated to the DATA command and
		query in each of the module Programmer's Guides.

		Arguments:
		blockdata	-- block of data to be sent (binary string)
		
		"""
		self.send(":SYST:DATA ", flush = False) # instead of cmd, use send to avoid newline
		self.sendblock(blockdata)

	def syst_data_query(self):
		"""DATA? Query

		:SYSTem:DATA?

		Returns the block data. The data sent by the SYSTem:DATA query reflects the
		configuration of a selected module when the last acquisition was performed.
		Any changes made since then through either front-panel operations or programming
		commands do not affect the stored data. Since the mainframe does not acquire data,
		refer to the appropriate module Programmer's Guide for more details.

		Returns:
		Block data
		
		"""
		self.send(":SYST:DATA?" + '\n', flush = False) # don't immediately read the answer
		return self.readblock()
		
	def syst_dsp(self, string):
		"""DSP (Display)

		:SYSTem:DSP <string>

		Writes the specified quoted string to a device-dependent portion of the
		instrument display.

		(* note: The display on the 16500B stacks up to five messages until the oldest
		 is pushed out.)

		Arguments:
		string	-- A string of up to 68 alphanumeric characters.

		"""
		self.cmd(":SYST:DSP " + self.quote(string))

	def syst_error_query(self, string = True):
		"""ERRor Query

		:SYSTem:ERRor? [NUMeric|STRing]
		
		Returns the oldest error from the error queue. The optional parameter determines
		whether the error string should be returned along with the error number. If no
		parameter is received or it's False ("NUMeric") , only the error number is returned. 
		Otherwise a tuple containing the error number and the string is returned.

		Arguments:
		string	-- if True, a string representation of the error is included

		Returns:
		Tuple containing the error number and optionally error string.

		HP 16500B Error Messages:

		Device Dependent Errors:
		
		200	Label not found
		201	Pattern string invalid
		202	Qualified invalid
		203	Data not available
		300	RS-232C error

		Command Errors

		-100	Command error (unknown command)(generic error)
		-101	Invalid character received
		-110	Command header error
		-111	Header delimiter error
		-120	Numeric argument error
		-121	Wrong data type (numeric expected)
		-123	Numeric overflow
		-129	Missing numeric argument
		-130	Non numeric argument error (character, string, or block)
		-131	Wrong data type (character expected)
		-132	Wrong data type (string expected)
		-133	Wrong data type (block type #D required)
		-134	Data overflow (string or block too long)
		-139	Missing non numeric argument
		-142	Too many arguments
		-143	Argument delimiter error
		-144	Invalid message unit delimiter

		Execution Errors

		-200	Can Not Do (generic execution error)
		-201	Not executable in Local Mode
		-202	Settings lost due to return-to-local or power on
		-203	Trigger ignored
		-211	Legal command, but settings conflict
		-212	Argument out of range
		-221	Busy doing something else
		-222	Insufficient capability or configuration
		-232	Output buffer full or overflow
		-240	Mass Memory error (generic)
		-241	Mass storage device not present
		-242	No media
		-243	Bad media
		-244	Media full
		-245	Directory full
		-246	File name not found
		-247	Duplicate file name
		-248	Media protected

		Internal Errors

		-300	Device Failure (generic hardware error)
		-301	Interrupt fault
		-302	System Error
		-303	Time out
		-310	RAM error
		-311	RAM failure (hardware error)
		-312	RAM data loss (software error)
		-313	Calibration data loss
		-320	ROM error
		-321	ROM checksum
		-322	Hardware and Firmware incompatible
		-330	Power on test failed
		-340	Self Test failed
		-350	Too Many Errors (Error queue overflow)

		Query Errors

		-400	Query Error (generic)
		-410	Query INTERRUPTED
		-420	Query UNTERMINATED
		-421	Query received. Indefinite block response in progress
		-422	Addressed to Talk, Nothing to Say
		-430	Query DEADLOCKED

		"""
		reply = filter(None, self.query(":SYST:ERR?" + (" STR" if string else "")).split(','))
		if len(reply) > 1:
			return tuple([int(reply[0]), reply[1][1:-1]])
		elif len(reply) == 1:
			return tuple([int(reply[0])])
		else:
			return ""
		
	def syst_header(self, mode):
		"""HEADer

		:SYSTem:HEADer {{ON|1}|{OFF|0}}

		Tells the instrument whether or not to output a header for query responses.
		When HEADer is set to ON, query responses include the command header.

		(* note: ALL query methods assume that HEADer and LONGform are NOT ON! Don't
		 turn headers on if you want to use them!)

		Arguments:
		mode	-- 1/"1"/"ON" or 0/"0"/"OFF"

		"""
		self.cmd(":SYST:HEAD " + str(mode))
		
	def syst_header_query(self):
		"""HEADer Query

		:SYSTem:HEADer?

		Returns:
		Integer 0 or 1	-- current state of the HEADer command

		"""
		return self.query_num(":SYST:HEAD?")

	def syst_longform(self, mode):
		"""LONGform

		:SYSTem:LONGform {{ON|1}|{OFF|0}}

		Sets the long form variable, which tells the instrument how to format query
		responses. If the LONGform command is set to OFF, command headers and alpha
		arguments are sent from the instrument in the abbreviated form. If the
		LONGform command is set to ON, the whole word will be output. This command
		has no effect on the input data messages to the instrument. Headers and
		arguments may be input in either the long form or short form regardless of
		how the LONGform command is set.

		(* note: like with HEADer, this is not yet handled gracefully!)

		Arguments:
		mode	-- 1/"1"/"ON" or 0/"0"/"OFF"

		"""
		self.cmd(":SYST:LONG " + str(mode))

	def syst_longform_query(self):
		"""LONGForm Query

		:SYSTem:LONGform?

		Returns:
		Integer 0 or 1	-- current status of the LONGform command

		"""
		return self.query_num(":SYST:LONG?")

	def syst_print(self, mode, pathname = "\PRINTED", msus = "INT0", disk = True, start = None, end = None, filetype="PCX"):
		"""PRINt

		:SYSTem:PRINt ALL[,DISK,<pathname>[,<msus>]]
		:SYSTem:PRINt PARTial,<start>,<end>[,DISK,<pathname>[,<msus>]]
		:SYSTem:PRINt SCReen[,DISK,<pathname>[,<msus>],{BTIF|CTIF|PCX|EPS}]

		* Python note: since the mainframe switches the printer communication interface
		* to HP-IB when RS-232C is selected as the serial communication interface and I
		* doubt most people have a printer with a HP-IB interface around, I've chosen
		* to print a color PCX to hard disk by default. To override this, just pass the 
		* argument disk = False.

		Initiates a print of the screen or listing buffer over the current PRINTER
		communication interface to the printer or to a file on the disk. The PRINT
		SCREEN option allows you to specify a graphics type.

		Graphics types available:
		- BTIF (B/W TIF)
		- CTIF (Color TIF)
		- PCX  (Color PCX)
		- EPS  (Encapsulated PostScript format)	

		If a file name extension is not specified in the command, the correct
		extension will be appended to the file name automatically. Both BTIF and
		CTIF will have a .TIF extension.

		The PRINT PARTial command is valid in certain listing menus. It allows you
		to specify a starting and ending state number so you can print a portion of
		the listing to the printer or to a disk file.

		Arguments:
		mode		-- string: "all", "partial" or "screen"
		pathname	-- a string of up to 10 alphanumeric characters for LIF:
				   NNNNNNNNNN
				   or
				   a string of up to 64 alphanumeric characters for DOS:
				   either NNNNNNNN.NNN (file resides in current directory)
				   or \NAME_DIR\FILENAME (file outside working directory)
		msus		-- string: "INTernal0" = hard disk, "INTernal1" = floppy
		disk		-- boolean: if True, print to disk instead of printer and
				   requires pathname argument.
		start		-- integer: if mode is "partial", defines the starting state number
		end		-- integer: if mode is "partial", defines the ending state number
		filetype	-- string: "btif", "ctif", "pcx" or "eps"

		"""
		diskarg = rangearg = typearg = ""
		if disk and pathname:
			diskarg = ",DISK,'" + str(pathname) + "'" + ("," + str(msus) if msus != None else "")
		if mode.lower() == "partial":
			if not (type(start) is int and type(end) is int):
				raise Exception("Range not defined for partial print, use start= and end=.")
			rangearg = "," + str(start) + "," + str(end)
		if mode.lower() == "screen":
			if not filetype:
				raise Exception("No filetype defined for printing.")
			typearg = "," + filetype
		self.cmd(":SYST:PRIN " + mode + rangearg + diskarg + typearg)
		self.comm_opc_query()

	def syst_print_query(self, mode):
		"""PRINt Query

		:SYSTem:PRINt? {SCReen|ALL}

		Sends the screen or listing buffer data over the current CONTROLLER
		communication interface to the controller. The print query should NOT be
		sent in conjunction with any other command or query on the same command line.
		The print query never returns a header. Also, since response data from a print
		query may be sent directly to a printer without modification, the data is not
		returned in block mode.

		PRINT? ALL is only available in menus that have the "Print All" option available
		on the front panel.

		(* note: apparently this commands dumps the screen as PCL data suitable for
		 printing)

		Arguments:
		mode	-- string: "screen" or "all"

		"""
		self.send(":SYST:PRIN?" + " " + str(mode) + "\n", flush = False)
		return self.flush()

	def syst_setup(self, blockdata):
		"""SETup

		:SYSTem:SETup <block_data>

		Configures the logic analysis system as defined by the block data sent by
		the controller. Because of the capabilities and importance of the Setup command
		and query for individual modules, a complete chapter is dedicated to it in each
		of the module Programmer's Guides. The dedicated chapter is called "DATA and
		SETup Commands".

		Arguments:
		blockdata	-- binary string

		"""
		self.send(":SYST:SET ")
		self.sendblock(blockdata)

	def syst_setup_query(self):
		"""SETup Query

		:SYSTem:SETup?

		Returns:
	        A block of data that contains the current configuration to the controller.

		"""
		self.send(":SYST:SET?" + '\n', flush = None)
		return self.readblock()


	# MMEMory subsystem commands

	def mmem_autoload(self, auto_file, msus = None):
		"""AUToload

		:MMEMory:AUToload {{OFF|0}|{<auto_file>}}[,<msus>]

		Controls the autoload feature which designates a set of configuration files
		to be loaded automatically the next time the instrumment is turned on. The
		OFF parameter (or 0) disables the autoload feature. A string parameter may
		be specified instead to represent the desired autoload file. If the file is
		on the current drive, the autoload feature is enabled to the specified file.
		The configuration files specified must reside in the root directory of the
		current drive.

		Arguments:
		auto_file	-- A string of up to 10 alphanumeric characters for LIF:
				   NNNNNNNNNN
				   or
				   a string of up to 12 alphanumeric characters for DOS:
				   NNNNNNNN.NNN
				   or
				   the string "OFF"
		msus		-- string: Mass Storage Unit Specifier, "INTernal0" for
				   hard disk, "INTernal1" for floppy

		"""
		if auto_file.lower() != "off":
			filearg = self.opts( self.quote(auto_file), msus )
		else:
			filearg = "OFF"
		self.cmd(":MMEM:AUT " + filearg)

	def mmem_autoload_query(self):
		"""AUToload Query

		:MMEMory:AUToload?

		* Python note: always returns a string.

		Returns 0 if the autoload feature is disabled. If the autoload feature is
		enabled, the query returns a string parameter that specifies the current
		autoload file.

		Returns:
		String	-- "0" or the selected autoload file name

		"""
		return self.query(":MMEM:AUT?")

	def mmem_catalog_query(self, all = None, msus = None):
		"""CATalog Query

		:MMEMory:CATalog? [[All,][<msus>]]

		Returns the directory of the disk in one of two block data formats. The
		directory consists of a 51 character string for each file on the disk
		when the ALL option is not used. Each file entry is formatted as follows:

		"NNNNNNNNNN TTTTTTT FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF"

		where N is the filename, T is the file type and F is the file description.

		The optional parameter ALL returns the directory of the disk in a 70-
		character string as follows:
		
		"NNNNNNNNNNNN TTTTTTT FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF DDMMMYY HH:MM:SS"

		where N is the filename, T is the file type, F is the file description, and
		D, M, Y and HH:MM:SS are the date, month, year and time respectively in 24-
		hour format.

		If you don't use the ALL option with a DOS disk, each filename entry will
		be truncated at 51 characters.

		Arguments:
		all	-- (optional) if not None, print in long format
		msus	-- (optional) string: Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		
		fmtstring = '10s1x7s1x32s' # 51 char input
		n = 51
		if all:
			fmtstring = '12s1x7s1x32s1x7s1x8s' # 70 char input
			n = 70
			all = "All"
		parse = struct.Struct(fmtstring).unpack_from
		listing = self.cmd(":MMEM:CAT?" + self.opts(all, msus), wait = 0.5, multiline = True)
		# flush extra newline after input
		self.flush()
		if all:
			mapfun = lambda x: tuple([x[0], int(x[1]), x[2], x[3]])
		else:
			mapfun = lambda x: tuple([x[0], int(x[1]), x[2]])
		return map(mapfun, map(parse, map(''.join, zip(*[iter(listing)]*n)))) 

	def mmem_cd(self, dirname, msus = None):
		"""CD (Change Directory)

		:MMEMory:CD <directory_name>[,<msus>]

		Allows you to change the current working directory on the hard disk or
		a DOS flexible disk. The command allows you to send path names of up to
		64 characters for DOS format. Separators can be either the slash (/) or
		backslash (\) character. Both the slash and backslash characters are
		equivalent and are used as directory separators. The string containing
		double periods (..) represents the parent of the directory.

		Arguments:
		dirname	-- string of up to 64 characters for DOS disks ending in the new
			   directory name
		msus	-- (optional) string: Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		self.cmd(":MMEM:CD" + self.opts(self.quote(dirname), msus))
	
	def mmem_copy(self, name, newname, srcmsus = None, dstmsus = None):
		"""COPY

		:MMEMory:COPY <name>[,<msus>],<new_name>[,<msus>]

		Copies one file to a new file or an entire disk's contents to another disk.
		The two <name> parameters are the filenames. The first pair of parameters
		specifies the source file which must reside in the present working
		directory. The second pair specifies the destination file. An error is
		generated if the source file doesn't exist, or if the destination file
		already exists.

		Arguments:
		name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   or
			   A string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file resides outside working directory
			   (* note: I think there's a typo in the guide and it should say
			    "up to 64 alphanumeric characters" for pathnames like it does
			    for the new_name argument)
		newname	-- same as above, 64 characters maximum length of string
		srcmsus	-- string, source file Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy
		dstmsus	-- same as srcmsus but for the destination file

		"""
		self.cmd(":MMEM:COPY" + self.opts(self.quote(name), srcmsus, self.quote(newname), dstmsus))

	def mmem_download(self, name, description, datatype, blockdata, msus = None):
		"""DOWNload

		:MMEMory:DOWNload <name>[,<msus>],<description>,<type>,<block_data>

		Downloads a file to the mass storage device. The <name> parameter specifies
		the filename, the <description> parameter specifies the file description,
		and the <block_data> contains the contents of the file to be downloaded.

		Arguments:
		name		-- string of up to 10 alphanumeric characters for LIF:
				   NNNNNNNNNN
				   or
				   string of up to 12 alphanumeric characters for DOS:
				   NNNNNNNN.NNN when file resides in present working directory
				   or
				   \NAME_DIR\FILENAME when file is outside working directory
		description	-- string of up to 32 alphanumeric characters
		datatype	-- integer defining the file type:
				   
				   HP 16500B System Software			-15603
				   HP 16500B Option Software			-15602
				   HP 16500A or HP 16500B System Configuration	-16127
				   Autoload File				-15615
				   Inverse Assembler				-15614
				   DOS file (from Print To Disk)		-5813
				   HP 16510A/B Configuration			-16097
				   HP 16511B Configuration			-16098
				   HP 16515A Configuration			-16127
				   HP 16516A Configuration			-16126
				   HP 16520A Configuration			-16107
				   HP 16521A Configuration			-16106
				   HP 16530A Configuration			-16117
				   HP 16531A Configuration			-16116
				   HP 16532A Configuration			-16115
				   HP 16540A Configuration			-16088
				   HP 16541A Configuration			-16087
				   HP 16542A Master Card Configuration		-16086
				   HP 16542A Expansion Card Configuration	-16085
				   HP 16550A Master Card Configuration		-16096
				   HP 16550A Expansion Card Configuration	-16095
		blockdata	-- contents of file as a binary string
		msus		-- string, Mass Storage Unit Specifier, "INTernal0" for hard
				   disk, "INTernal1" for floppy

		"""
		self.send(":MMEM:DOWN" + self.opts(self.quote(name), msus, self.quote(description), datatype) + ",")
		self.sendblock(blockdata)

	def mmem_initialize(self, format = None, msus = "INTernal1"):
		"""INITialize

		:MMEMory:INITialize [{LIF|DOS}[,<msus>]]

		Formats the disk in DOS (Disk Operating System) on the hard drive or
		either DOS or LIF (Logical Information Format) on the floppy drive. If no
		format is specified, then the initialize command will format the disk in
		the DOS format. LIF format is not allowed on the hard drive.

		* Once executed, the initialize command formats the specified disk,
		* permanently erasing all existing information from the disk. After that,
		* there is no way to retrieve the original information.

		* (* note: the manual doesn't say what happens when msus is undefined,
		*  but assuming it picks INTernal0 (the hard disk) by default, this method
		*  uses the default of INTernal1 to avoid accidentally wiping out the hard
		*  disk. Be careful with this command!! Also see command mmem_msi.)

		Arguments:
		format	-- string (optional), "LIF" or "DOS"
		msus	-- string (optional), Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		# asks for confirmation to avoid accidents
		confirm = raw_input("Are you sure you want to FORMAT the disk " + str(msus) + "? Type Yes to confirm: ")
		if confirm == "Yes":
			self.dbg("Formatting disk " + str(msus) + "...")
			self.cmd(":MMEM:INIT" + self.opts(format, msus))
			self.comm_opc_query()
			self.dbg("Format finished.")
		else:
			self.dbg("Aborted format.")	
		return

	def mmem_load_config(self, name, msus = None, module = None):
		"""LOAD[:CONFig]

		:MMEMory:LOAD[:CONFig] <name>[,<msus>][,<module>]
		
		Loads a configuration file from the disk into the modules, software options,
		or the system. The <name> parameter specifies the filename from the disk.
		The optional <module> parameter specifies which module(s) to load the file
		into. The accepted values are -2 through 10. Not specifying the <module>
		parameter is equivalent to performing 'LOAD ALL' from the front panel which
		loads the appropriate files for both the system and the modules, and any
		software option.

		Arguments:
		name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   of
			   string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file outside working directory
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy
		module	-- (optional) integer, from -2 to 5 for the HP 16500B alone, -2 to
			   10 with the HP 16501A connected
		
		"""
		self.cmd(":MMEM:LOAD:CONFIG" + self.opts(self.quote(name), msus, module))

	def mmem_load_iassembler(self, ia_name, machine, msus = None, module = None):
		"""LOAD :IASSembler

		:MMEMory:LOAD:IASSembler <IA_name>[,<msus>],{1|2},[,<module>]

		This variation of the LOAD command allows inverse assembler files to be
		loaded into a module that performs state analysis. The <IA_name> parameter
		specifies the inverse assembler filename from the desired <msus>. The
		parameter after the optional <msus> specifies which machine to load the
		inverse assembler into. For example, a 1 following <msus> specifies that
		the inverse assembler files will be loaded into MACHINE 1 of the specified
		module.  

		Arguments:
		ia_name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   of
			   string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file outside working directory
		machine	-- integer 1 or 2, specifies which machine to load the file into
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy
		module	-- (optional) integer, from 1 to 5 for the HP 16500B alone, 1 to
			   10 with an HP 16501A connected
		
		"""
		self.cmd(":MMEM:LOAD:IASS" + self.opts(self.quote(ia_name), msus, machine, module))

	def mmem_mkdir(self, dirname, msus = None):
		"""MKDir (Make Directory)

		:MMEMory:MKDir <directory_name>[,<msus>]

		Allows you to make a directory on the hard drive and a DOS disk in the
		floppy drive. Directories cannot be made on LIF disks. Make directory will
		make a directory under the present working directory on the current drive
		if the optional path is not specified. Separators can be either the slash
		(/) or backslash (\) character. Both the slash and backslash characters are
		equivalent and are used as directory separators. The string containing two
		periods (..) represents the parent of the present working directory.

		Arguments:
		dirname	-- string of up to 64 characters for DOS disks ending in the new
		           directory name
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		self.cmd(":MMEM:MKD" + self.opts(self.quote(dirname), msus))

	def mmem_msi(self, msus):
		"""MSI (Mass Storage Is)

		:MMEMory:MSI [<msus>]

		Selects a default mass storage device. INTernal0 selects the hard disk
		drive and INTernal1 selects the floppy disk drive. Once the MSI is
		selected it remains the default drive until another MSI command is sent
		to the system.

		(* note: the manual states <msus> parameter is optional but doesn't state
		 what the command does if it's not specified. This method requires the
		 parameter.)

		Arguments:
		msus	-- string, Mass Storage Unit Specifier, "INTernal0" for hard disk, 
			   "INTernal1" for floppy

		"""
		self.cmd(":MMEM:MSI " + msus)

	def mmem_msi_query(self):
		"""MSI (Mass Storage Is) Query

		:MMEMory:MSI?

		Returns:
		String	-- current MSI setting

		"""
		return self.query(":MMEM:MSI?")

	def mmem_pack(self, msus = None):
		"""PACK

		:MMEMory:PACK [<msus>]

		Packs the files on the LIF disk in the drive. If a DOS disk is in the
		drive when the PACK command is sent, no action is taken.

		Arguments:
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy
		
		"""
		self.cmd(":MMEM:PACK" + self.opts(msus))

	def mmem_purge(self, name, msus = None):
		"""PURGe

		:MMEMory:PURGe <name>[,<msus>]

		Deletes files and directories from the disk in the specified drive. The
		PURGe command only purges directories when the directory is empty. If the
		PURGe command is send with a directory name and the directory contains
		files, the message "Directory contains files" is displayed and the
		command is ignored. The <name> parameter specifies the file name to be
		deleted.

		Once executed, the purge command permanently erases all the existing
		information about the specified file. After that, there is no way to
		retrieve the original information.

		Arguments:
		name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   of
			   string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file outside working directory
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		self.cmd(":MMEM:PURG" + self.opts(self.quote(name), msus))

	def mmem_pwd_query(self, msus = None):
		"""PWD (Present Working Directory)

		:MMEMory:PWD? [<msus>]

		Returns the present working directory for the specified drive. If the
		<msus> option is not sent, the present directory will be returned for
		the current drive.

		Arguments:
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		Returns:
		Tuple containing (current_directory, msus).

		"""
		return tuple(self.query(":MMEM:PWD?" + self.opts(msus)).split(','))

	def mmem_rename(self, name, newname, msus = None):
		"""REName

		:MMEMory:REName <name>[,<msus>],<new_name>

		Renames a file on the disk in the drive. The <name> parameter specifies
		the filename to be changed and the <new_name> parameter specifies the
		new filename.

		You cannot rename a file to an already existing filename.

		Arguments:
		name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   of
			   string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file outside working directory
		newname	-- string, format same as above
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		self.cmd(":MMEM:REN" + self.opts(self.quote(name), msus, self.quote(newname)))

	def mmem_store(self, name, description, msus = None, module = None):
		"""STORe[:CONFig]

		:MMEMory:STORe[:CONFig]<name>[,<msus>],<description>[,<module>]

		Stores module or system configurations onto a disk. The [:CONFig] specifier
		is optional and has no effect on the command. The <name> parameter specifies
		the file on the disk. The <description> parameter describes the contents of
		the file. The optional <module> parameter allows you to store the configuration
		for either the system or the modules. 0 refers to the system. 1 through 5
		refers to the modules in the mainframe alone and 1 through 10 refers to the
		mainframe with an expansion frame connected.

		If the optional <module> parameter is not specified, the configurations for
		both the system and logic analyzer are stored.

		Arguments:
		name		-- string of up to 10 alphanumeric characters for LIF:
				   NNNNNNNNNN
				   of
				   string of up to 12 alphanumeric characters for DOS:
				   NNNNNNNN.NNN when file resides in present working directory
				   or
				   \NAME_DIR\FILENAME when file outside working directory
		description	-- string of up to 32 alphanumeric characters
		msus		-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
				   hard disk, "INTernal1" for floppy
		module		-- (optional) integer, from 1 to 5 for the HP 16500B alone, 1 to
				   10 with an HP 16501A connected

		"""
		self.cmd(":MMEM:STOR" + self.opts(self.quote(name), msus, self.quote(description), module))

	def mmem_upload_query(self, name, msus = None):
		"""UPLoad Query

		:MMEMory:UPLoad? <name>[,<msus>]

		Uploads a file. The <name> parameter specifies the file to be uploaded
		from the disk. The contents of the file are sent out of the instrument
		in block data form.

		This command should only be used for HP 16550A configuration files.

		(* note: bollocks, this can be used just fine to get any file from the
		 instrument, PCX for example)

		Arguments:
		name	-- string of up to 10 alphanumeric characters for LIF:
			   NNNNNNNNNN
			   of
			   string of up to 12 alphanumeric characters for DOS:
			   NNNNNNNN.NNN when file resides in present working directory
			   or
			   \NAME_DIR\FILENAME when file outside working directory
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		"""
		self.send(":MMEM:UPL?" + self.opts(self.quote(name), msus) + '\n', flush = False)
		# wait for transfer to begin
		while 1:
			if self.serialport.inWaiting() > 1:
				break
		return self.readblock(timeout=3)

	def mmem_volume_query(self, msus = None):
		"""VOLume Query

		:MMEMory:VOLume? [<msus>]

		Returns the volume type of the disk. The volume types are DOS and LIF. Question
		marks (???) are returned if there is no disk, if the disk is not formatted, or
		if a disk has a format other than DOS or LIF.

		Arguments:
		msus	-- (optional) string, Mass Storage Unit Specifier, "INTernal0" for
			   hard disk, "INTernal1" for floppy

		Returns:
		String	-- type of volume ("DOS", "LIF" or "???")

		"""
		return self.query(":MMEM:VOL?" + self.opts(msus))


	# INTermodule subsystem commands

	def inter_delete(self, module):
		"""DELete

		:INTermodule:DELete {ALL|OUT|<module>}
		
		Used to delete a module, PORT OUT, or an entire intermodule tree. The <module>
		parameter sent with the delete command refers to the slot location of the
		module.

		Arguments:
		module	-- integer from 1 to 5 for HP 16500B alone, 1 to 10 with the HP 16501A
			   connected or strings "all" or "out"

		"""
		self.cmd(":INT:DEL " + str(module))

	def inter_htime_query(self):
		"""HTIMe Query

		:INTermodule:HTIMe?

		Returns a value representing the internal hardware skew in the Intermodule
		configuration. If there is no internal skew, 9.9E37 is returned.

		The internal hardware skew is only a display adjustment for time-correlated
		waveforms. The value returned is the average propagation delay of the trigger
		lines through the intermodule bus circuitry. These values are for reference
		only because the values returned by TTIMe include the internal hardware skew
		represented by HTIMe.

		Returns:
		List of real numbers	-- skew for each module slot (A through J)

		"""
		return self.query_numlist(":INT:HTIM?")

	def inter_inport(self, setting):
		"""INPort

		:INTermodule:INPort {{ON|1}}|{OFF|0}}

		Causes intermodule acquisitions to be armed from the input port.

		Arguments:
		setting	-- 1/"1"/"ON" or 0/"0"/"OFF"

		"""
		self.cmd(":INT:INP " + str(setting))

	def inter_inport_query(self):
		"""INPort Query

		:INTermodule:INPort?

		Returns:
		Integer	-- 1 or 0, the current setting

		"""
		return self.query_num(":INT:INP?")

	def inter_insert(self, module, location):
		"""INSert

		:INTermodule:INSert {<module>|OUT},{GROUP|<module>}

		Adds PORT OUT to the Intermodule configuration. The first parameter
		selects the module or PORT OUT to be added to the intermodule configuration,
		and the second parameter tells the instrument where the module or PORT
		OUT will be located. 1 through 5 corresponds to the slot location of the
		modules A through E for the HP 16500B alone and 1 through 10 corresponds to
		slot location of modules A through J when an HP 16501A is connected.

		Arguments:
		module		-- integer, 1 through 5 for HP 16500B alone, 1 through 10 
				   with the HP 16501A connected, or string "OUT"
		location	-- as above, integer 1 through 5 or 10, or string "GROUP"

		"""
		self.cmd(":INT:INS" + self.opts(module, location))

	def inter_portedge(self, edge_spec):
		"""PORTEDGE

		:INTermodule:PORTEDGE <edge_spec>

		Sets the port input BNC to respond to either a rising edge or falling edge
		for a trigger from an external source. The threshold level of the input
		signal is set by the PORTLEV command.

		Arguments:
		edge_spec	-- 1/"1"/"ON" for rising edge or 0/"0"/"OFF" for falling
				   edge

		"""
		self.cmd(":INT:PORTEDGE" + self.opts(edge_spec))

	def inter_portedge_query(self):
		"""PORTEDGE Query

		:INTermodule:PORTEDGE?

		Returns:
		Integer	-- 1 or 0, current edge setting (1 for rising, 0 for falling)

		"""
		return self.query_num(":INT:PORTEDGE?")

	def inter_portlev(self, level):
		"""PORTLEV

		:INTermodule:PORTLEV {TTL|ECL|<user_lev>}

		Sets the threshold level at which the input BNC responds and produces
		an intermodule trigger. The preset levels are TTL and ECL. The user
		defined level is -4.0 volts to +5.0 volts.

		Arguments:
		level	-- real number from -4.0 to +5.0 volts in 0.02 volt increments
			   or "TTL" or "ECL"

		"""
		self.cmd(":INT:PORTLEV" + self.opts(level))

	def inter_portlev_query(self):
		"""PORTLEV Query

		:INTermodule:PORTLEV?

		Returns:
		float	-- the current BNC threshold setting
	
		"""
		r = self.query(":INT:PORTLEV?")
		if "L" in r:	## if TTL or ECL, return the string
			return r.replace('"','')
		else:
			return self.number(r.replace('"','')[:-1]) ## remove quotes and trailing 'V'

	def inter_skew(self, n, setting):
		"""SKEW<N>

		:INTermodule:SKEW<N> <setting>

		Sets the skew value for a module. The <N> index value is the module
		number (1 though 5 corresponds to the slot location of the modules A
		through E for the HP 16500B alone and 1 through 10 corresponds to slot
		location of modules A through J when an HP 16501A is connected). The
		<setting> parameter is the skew setting (- 1.0 to 1.0) in seconds.

		Arguments:
		n	-- integer, 1 through 5 for HP 16500B alone or 1 through 10 with
			   the HP 16501A connected
		setting	-- real number from -1.0 to 1.0 seconds

		"""
		self.cmd(":INT:SKEW" + str(n) + " " + str(setting))

	def inter_skew_query(self, n):
		"""SKEW<N> Query

		:INTermodule:SKEW<N>?

		Arguments:
		n	-- integer, 1 through 5 for HP 16500B alone or 1 through 10 with
			   the HP 16501A connected

		Returns:
		float	-- the user defined skew setting

		"""
		return self.number(self.query(":INT:SKEW" + str(n) + "?"))

	def inter_tree(self, modulelist):
		"""TREE

		:INTermodule:TREE <module>,<module>,<module>,<module>,<module>,<module>

		Allows an intermodule setup to be specified in one command. The first
		parameter is the intermodule arm value for module A (logic analyzer). The
		second parameter corresponds to the intermodule arm value for PORT OUT. A
		-1 means the module is not in the intermodule tree, a 0 value means the
		module is armed from the Intermodule run button (Group run), and a
		positive value indicates the module is being armed by another module
		with the slot location 1 to 10. 1 through 10 corresponds to slots A
		through J.

		Arguments:
		modulelist -- list of integers, possible values -1 through 5 for an HP 
		              16500B alone, -1 through 10 with the HP 16501A connected

		"""
		if len(modulelist) == 6:
			self.cmd(":INT:TREE " + ",".join(str(m) for m in modulelist))
		else:
			self.dbg("Invalid length for intermodule tree module list (should be 6): " + str(modulelist))

	def inter_tree_query(self):
		"""TREE Query

		:INTermodule:TREE?

		Returns a list of integers representing the intermodule tree. A -1 means
		the module is not in the intermodule tree, a 0 value means the module is
		armed from the Intermodule run button (Group run), and a positive value
		indicates the module is being armed by another module with the slot
		location 1 to 10. 1 through 10 corresponds to the slots A through J.

		Returns:
		List of integers	-- current intermodule tree

		"""
		return self.query_numlist(":INT:TREE?")

	def inter_ttime_query(self):
		"""TTIMe Query

		:INTermodule:TTIMe?

		Returns five values (HP 16500B alone) representing the absolute intermodule
		trigger time for all of the modules in the Intermodule configuration. When
		an HP 16501A is connected, the TTIMe query returns 10 values. The first
		value is the trigger time for the module in slot A, the second value is
		for the module in slot B, the third value is for slot C, etc.

		The value 9.9E37 is returned when:
		* No module is installed in the corresponding slot;
		* The module in the corresponding slot is not time correlated; or
		* A time correlatable module did not trigger

		Returns:
		List of real numbers	-- corresponding to trigger time for each slot A
					   through E or A through J.

		"""
		return self.query_numlist(":INT:TTIM?")
	
