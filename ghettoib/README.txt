
ghettoIB 0.2

 _______________________
|=======================|
||""""""""""|  [ --- ]  |
||   o o    |           |
||  ·___·   |    (')    |
||__________|,.         |-.
|------------··---------|  '--.       .---( 0100100001001001 ... 
'"--------------------"-'      '·--__/

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
legacy measurement instruments. Errors in the program controlling the operation of these
devices could have various consequences. It has only been tested with an HP 16500B.


### REQUIREMENTS

- An HP 16500B Logic Analysis System or similar IEEE 488.2 compliant instrument.
- null-modem type physical connection
- pySerial and Python Imaging Library (for screenshots)


### FEATURES

- basic commands (changing menus, reading and setting registers, printing etc.)
- downloading files, configuration and acquisition data from the instrument
- uploading files, configuration and acquisition data to the instrument


### CURRENT STATE

- very limited testing
- nearly nonexistent runtime error checking
- better than nothing


### INTRODUCTION

This Python (written for 2.7.3) class implements the byte-level serial communication and all of
the commands listed in the HP16500B/16501A Logic Analysis System Programmer's Guide' (rev.
April 1994). Their descriptions have been extracted and abbreviated from the same document and
one should refer to the original document (available from Agilent support site) for details on
the commands and the internal parser of the instrument.  The guide also has syntax diagrams for
each subsystem. This README file has a command summary but each of the method definitions in
the main source contains a more detailed description.

Only the HP16500B mainframe commands have been included. These instruments are very complex and
each installed module has its own set of commands and registers available for programming.
There are 63 commands for the mainframe. For details refer to the Programmer's Guides of the
individual modules you have. This library does not attempt to replicate the command parser of
the Logic Analysis System, nor does it implement much of the actual functionality one would
expect in an instrument controller. It should, however, allow at least limited control of the
instrument to automate it, to transfer data back and forth and to provide the minimum tools to
build your own high-level features, such as a GUI or using the instrument's CRT to display
incoming IRC messages.

This was written mostly because I wanted color screenshots from the thing. I tried to look for
an "official" software solution after producing an adapter for the serial port to communicate
with the instrument. Instead I found this Tcl script by Venkat Iyer: http://wiki.tcl.tk/13583
which was probably the most complete *simple* example to actually do anything meaningful with
the instrument, big kudos to him. But unfortunately this method of getting screenshots was very
slow and the resulting picture will be monochromatic, which doesn't do justice for the
instrument.

I did find PyVISA and similar applications that looked promising but they all seemed to require
downloading a ridiculously big (300-700MB!!) Windows software suite from the device vendor's
'register to download' archives, extracting a couple of files from it (redistribution outside
the huge package probably prohibited by license) to provide the soon-to-be-compiled software
the actual capability to do the byte banging, referring to some magic programs that
conveniently are 404 these days, or even suggesting that to speak serial to the ancient
instrument requires some special software, only $490 or so. Not very convenient.

This library is of course not a substitute for the real thing and mostly a quick hack, but it
is self-contained, simple, free to use and open source. It even allows me to get the
screenshots I wanted in the first place and you can make it better.


### PINOUTS

Oh, by the way, it took some effort to figure out what sort of cable is needed since the 16500B
happens to have a female RS-232C connector. You can minimally use a three-wire
interface (I didn't try it):

Pin 7	SGND	(Signal Ground)
Pin 2	TD	(Transmit Data from logic analysis system)	output
Pin 3	RD	(Receive Data into logic analysis system)	input

If you use the three-wire interface, you *must* configure both the instrument and your code to
use the XON/XOFF protocol. When you create an HPLA object you can pass its constructor the
'xonxoff=True' keyword argument to set this option for the serial port. By default RTS/CTS flow
control is used and will be disabled if xonxoff is enabled.

Additional lines for extended interface:

Pin 4	RTS	(Request To Send)	output
Pin 5	CTS	(Clear To Send)		input
Pin 6	DSR	(Data Set Ready)	input
Pin 8	DCD	(Data Carrier Detect)	input
Pin 20	DTR	(Data Terminal Ready)	output

* Pin 20 is always high when the instrument is on.

I use a male DB25 connector wired to a DB9 female connector like a DB25-DB9 null-modem cable
(which I plug into a Belkin F5U103V USB serial adapter connected to a RaspberryPi):

DB9	 		DB25
Pin #	Connects To	Pin #
1	<-------->	20
2	<-------->	2
3	<-------->	3
4	<-------->	6,8
5	<-------->	7
6	<-------->	20
7	<-------->	5
8	<-------->	4
9	<-------->	22

That diagram was borrowed from here:
http://logmett.com/index.php?/quick-tips/rs232-cable-pinouts.html

Another fine resource for cable confusion:
http://www.lammertbies.nl/comm/cable/RS-232.html


### INSTRUMENT SETTINGS

1) set HPIB as the printer interface and RS-232 as the communication interface
2) configure RS-232 to: 19200, 8 bits, NO parity, NO XON/XOFF (unless you use 3-wire!)
3) save the settings and make the instrument autoload them so they'll stay that way


### USAGE

You can run the accompanying 'hp-repl.py' script to get an interactive REPL and a connection to
the instrument. Check that you have chosen the right serial port. The script creates an HPLA
(HP Logic Analyzer) object that you can use to interact with the instrument.

Note that while this class was written for an HP 16500B, it might also work to
some extent with other devices that talk IEEE 488.2 over RS-232. No guarantees.


## Overview

The documentation for the mainframe commands is available in the source code itself. The code
is very simple and in its early stages so the best way to learn it is simply to
browse through the source file.

To create an HPLA object:

>>> hp = ghettoib.HPLA("/dev/ttyUSB0")			# using a USB RS-232 adapter
>>> hp2 = ghettoib.HPLA("/dev/ttyS0", xonxoff=True)	# using 3-wire on plain serial port (not tested!)

The archaic HP-BASIC examples in the Guides are fairly intimidating, but it all boils down to
sending some text and reading it back. To pass simple, arbitrary commands to the instrument's
parser and read answers back, you can:

>>> hp.cmd(":SELECT 3")				# select module in slot 3 (for further commands)
>>> currentcolor = hp.query(":SETC? 5")		# returns '5,57,100,67' (color, hue, sat, lum)

The replies are strings. 'cmd' sends a command without (by default) waiting for an answer, but
'query' returns the answer. You can use the methods provided by this class to get some
meaningful data out of the replies:

>>> hp.main_select(3)
>>> currentcolor = hp.main_setcolor_query(5)	# currentcolor will contain [5, 57, 100, 67]

The IEEE 488.2 methods are categorized to COMMon, MAINframe, SYSTem, MMEMory and INTERmodule
commands according to the Programmer's Guide. The WEIrd caps all over the command descriptions
signify the minimum amount of characters for the instrument's parser to recognize the commands.
The parser doesn't care about command case and it can be mixed, also there is no difference to
typing 'SETC' instead of 'SETCOLOR' except the former needing to transmit four bytes less. Even
'sEtCoL' is ok.


## Filesystem

The instrument refers to mass storage units as "INTernal0" (hard disk) and "INTernal1"
('flexible' disk / floppy), abbreviated INT0 and INT1 respectively. You may need to use the OPC
Query to wait for any file operations to finish. Also be advised that the :MMEM:INIT command
isn't as friendly as it sounds: it formats a storage device. Yes. When a command has an 'msus'
parameter, it refers to Mass Storage Unit Specifier, and you should make sure that the right
one is referenced, INT0 (hard disk) or INT1 (floppy). There are commands to traverse and
manipulate the filesystem and if you know DOS you should feel right at home. You can change your
working directory for each drive and filenames are at most 8+3 characters long, but can
additionally have a 32 character description, but these are not visible for "DOS files".


## Parser syntax

This library doesn't really know or care about the actual properties of the instrument or know
before sending the commands whether the instrument will accept your input without error or if
the command makes any sense to execute.

For valid command syntax refer to the Guides, but in a nutshell, colon ':' is the root of the
parser's command tree, semicolon ';' is the command separator, commands starting with an
asterisk (*CLS etc) can be called at any branch location, there are three subsystems: SYSTem,
MMEMory and INTermodule, branches are preceded by colons, no spaces are allowed
around colons. A newline ends an input. 

Tree traversal rules: 
 1) a leading colon or terminator places the parser at the root 
 2) executing a subsystem command places you in that subsystem until a leading colon or
    terminator is found

This basically means that you can send many commands on one line and if consecutive commands
are for the same subsystem, repeating the command header is not necessary. For example:

>>> hp.cmd(":MMEM:MKDIR 'TEST';CD 'TEST';CD '..';RENAME 'TEST','BEST';PURGE 'BEST'")

instead of:

>>> hp.cmd(":MMEM:MKDIR 'TEST';:MMEM:CD 'TEST';:MMEM:CD '..';:MMEM:RENAME 'TEST','BEST';:MMEM:PURGE 'BEST'")

Many commands have a query form, for example "*ESE <mask>" sets register bits but "*ESE?"
queries the current contents of the register. In the code's current form the queries (usually
commands ending with '?') can be performed with a '_query' method. For example 'comm_ese' vs.
'comm_ese_query'. By default also the 'cmd' method flushes the input buffer in case there's
something the instrument wanted to say, there are also special cases like the catalog listing
that transmits multiline input and cmd attempts to handle each flavour.

Each query attempts to return the data in a format suitable for further processing in Python
where appropriate, ie. strings from the instrument such as one representing a list of numbers
is returned as an integer list.

To send a raw, unadulterated string to the instrument, you can use 'send' and pass it a string
or an unsigned byte array (bytes = array.array('B')) which it will send to the device as-is.
Note that no newline is appended automatically, so you would do:

>>> hp.send(":OPC?" + '\n')	# send OPC query
>>> hp.flush()			# get reply

Excluding description strings and such, case of the string parameters doesn't matter.

To program the instrument by sending it the appropriate command strings and formatting the
results yourself, simply use methods cmd and query. For example: cmd(":SYSTEM:PRINT SCREEN") or
query(":SYS:LONG?").  If you make a mistake, the instrument displays excellent error messages
on its screen, pointing you at the exact error and explaining the cause.


## Simulating

To test output before sending it to the instrument, you can use socat (install
it first if necessary).

The command:

	$ socat -d -d pty,raw,echo=0,b19200 pty,raw,echo=0,b19200
	2013/05/10 00:15:18 socat[18809] N PTY is /dev/pts/1
	2013/05/10 00:15:18 socat[18809] N PTY is /dev/pts/4
	2013/05/10 00:15:18 socat[18809] N starting data transfer loop with FDs [3,3] and [5,5]

will create two dummy serial terminals. The output may differ between
invocations, but in the above case the two device files /dev/pts/1 and
/dev/pts/4 will be connected for as long as socat is running. You can just
start it up and forget it.

Writes to /dev/pts/1 can be read from /dev/pts/4 and vice versa.

	test = ghettoib.HPLA("/dev/pts/1", 19200)
	test.main_beeper()

You can read/simulate the instrument end with a terminal program or simply
screen for example, just remember to use the right device file:

	$ screen /dev/pts/4 19200,cs8

There's also serial sniffer programs to help further, one option is jpnevulator:

	$ jpnevulator --ascii --timing-print --read --tty /dev/pts/1 --tty /dev/pts/4
	2013-05-10 17:42:39.297112: /dev/pts/4
	2A 43 4C 53 0A                                  *CLS.		# hp.comm_cls()
	2013-05-10 17:42:42.010605: /dev/pts/1
	68 65 6C 6C 6F 20 77 6F 72 6C 64 0A             hello world.	# $ echo "hello world">/dev/pts/4


## High-level commands

There aren't many high-level commands due to lack of time but there are some:

put(filename, remotename, desc = "from ghettoIB", type = -5813, msus="INT0")
	- send a file to the instrument
	- by default saved to hard disk and current working directory
	- put("myfile.dat", "remote.dat")
	- put("myfile.dat", "\DIR\remote.dat", desc = "measurement B", msus = "INT1")

get(filename, remotename, msus = "INT0")
	- receive a file from the instrument
	- by default from hard disk's current directory
	- saves remotename into local filename
	- get("myfile.dat", "remote.dat")

save_data(filename = None, module = None)
	- saves acquisition data from the current or specified module to the controller
	- parameters optional, by default the file "module-<n>-data-<date>.dat"
	  will be created
	- save_data("scope.dat")

load_data(filename, module = None)
	- loads acquisition data into the instrument from a file on the controller
	- data will be loaded into the current or specified module
	- load_data("scope.dat")

save_settings(filename = None, module = None)
	- saves settings from the current or specified module to the controller
	- save_settings("scope-evening.set")

load_settings(filename, module = None)
	- loads settings from file on the controller
	- settings will be loaded into the current or specified module
	- load_settings("scope-evening.set")

menumap()
	- creates a map of the available menus on the system
	- content depends on installed modules and their settings
	- returns a list of tuples
	- will spurt errors on the screen while operating because finding the
	  menus involves looping through the possible module/menu values and
	  checking the error queue for an error, only successful transitions
	  are recorded
	- map = menumap()

screenshot_menus(image_basename, menumap)
	- uses return value of menumap to screenshot all of them and transfer the images to the controller
	- image_basename will be used for the screenshots and '_<module>-<menu>.png' will be appended to it
	- screenshot_menus(map)

dimscreen()
	- set all colors to black
	- dimscreen()

togglescreen()
	- toggles screen between black and default colorscheme
	- togglescreen()

synctime()
	- synchronizes instrument RTC with the controller's time
	- synctime()

installed_modules()
	- lists installed modules in human-readable fashion
	- returns a list of tuples containing (module, module_name_string, module_assignment)
	- basically a ':CARDcage?' query that also identifies the modules
	- installed_modules()

screenshot(filename, printfile = None, msus = "INT0", download = True)
	- captures a screenshot in PCX format (default of syst_print)
	- if download is True, also transfers the screenshot immediately to controller
	- saves PNG images
	- screenshot("screeny.png")

flush_errors()
	- flushes the error queue and returns a list of all the accumulated errors
	- flush_errors()



To send an arbitrary command that doesn't contain block data, you can use cmd:

cmd(string, wait = None, multiline = None)
	- the optional wait parameter will specify a timeout value to wait for an answer
	- multiline means that block data is read, this is used with the catalog query (directory listing)
	- cmd("*ESE 0")

Or if you're interested in the reply, there are query methods:

query(string, timeout = 0.2)
	- just calls cmd with a timeout
query_num(string, timeout = 0.2)
	- same as above but instead of a string returns a number
query_numlist(string, timeout = 0.2)
	- as above but assumes string is a numeric list, returns a list

The rest of the commands are just to implement the above.



Next a command summary for the mainframe, listing both the IEEE 488.2 syntax for
the actual instrument and the Python methods to send them:

Common commands:

*CLS		Clear Status
		'*CLS'
		- clears all event status registers etc.
		* comm_cls()

*ESE		Event Status Enable
		'*ESE <mask>'
		'*ESE?'
		- set and read the Standard Event Status Enable Register
		* comm_ese(mask)	-- mask: byte
		* comm_ese_query()	-- returns: byte

*ESR		Event Status Register
		'*ESR?'
		- read the Standard Event Status Register
		* comm_esr_query()	-- returns: byte

*IDN		Identification Number
		'*IDN?'
		- read the ID string of the instrument
		- "HEWLETT-PACKARD,16500B,0,REV <revision_code>"
		* comm_idn_query()	-- returns: string

*IST		Individual Status
		'*IST?'
		- read current state of IEEE 488.1 defined "ist" local message
		* comm_ist_query()	-- returns: 0 or 1

*OPC		Operation Complete
		'*OPC'
		'*OPC?'
		- set operation complete bit in the Standard Event Status Register
		  when pending operations have finished
		- query makes the instrument send a "1" when operations have finished
		- comm_opc_query can be used to wait until eg. disk write has been done
		  before continuing with the program (wait for the "1")
		* comm_opc()
		* comm_opc_query()	-- returns: 1

*OPT		Option Identification
		'*OPT?'
		- lists installed options
		* comm_opt_query()	-- returns: list of nine strings

*PRE		Parallel Poll Enable Register Enable
		'*PRE <mask>'
		- set and read the Parallel Poll Enable Register Enable bits
		* comm_pre(mask)	-- mask: 0-65535
		* comm_pre_query()	-- returns: 0-65535 

*RST		Reset
		'*RST'
		- not implemented on HP16500B: allowed command but has no effect
		* comm_rst()

*SRE		Service Request Enable
		'*SRE <mask>'
		'*SRE?'
		- set and read the Service Request Enable Register bits
		* comm_sre(mask)	-- mask: byte
		* comm_sre_query()	-- returns: byte

*STB		Status Byte
		'*STB?'
		- read the current status byte
		* comm_stb_query()	-- returns: byte

*TRG		Trigger
		'*TRG'
		- Group Execute Trigger, if no intermodule configuration, no effect
		* comm_trg()

*TST		Test
		'*TST?'
		- returns the results of power-up self-tests
		* comm_tst_query()	-- returns: integer, 0-511

*WAI		Wait
		'*WAI'
		- causes the device to wait for overlapped commands to finish
		* comm_wait()



Mainframe commands:

:BEEPer		Beeper
		':BEEPer [{ON|1}|{OFF|0}]'
		- beeps with no arguments, 0 or 1 disable/enable beeper
		* main_beeper(setting)		-- (optional) setting: 1/"1"/"ON" or 0/"0"/"OFF"

:CAPability?	Capability Query
		':CAPability?'
		- returns IEEE 488.1 interface capability set
		* main_capability_query()	-- returns: numeric list

:CARDcage?	CARDcage Query
		':CARDcage?'
		- identifies installed modules
		* main_cardcage_query()		-- returns: numeric list

:CESE		CESE (Combined Event Status Enable)
		':CESE <value>'
		':CESE?'
		- set and read the Combined Event Status Enable register bits
		* main_cese(value)		-- value: 0-65535
		* main_cese_query()		-- returns: 0-65535

:CESR?		CESR (Combined Event Status register)
		':CESR?'
		- read the Combined Event Status register
		* main_cesr_query()		-- returns: 0-65535

:EOI		EOI (End Or Identify)
		':EOI {{ON|1}|{OFF|0}}'
		':EOI?'
		- turn EOI on or off (last byte of reply send with EOI bus control line set or not)
		* main_eoi(setting)		-- setting: 1/"1"/"ON" or 0/"0"/"OFF"
		* main_eoi_query()		-- returns: 1 or 0
		
:LER?		LER (LCL Event Register)
		':LER?'
		- reads LCL Event Register, register is cleared after reading
		- 1 = remote-to-local transition has taken place, 0 = has not taken place
		* main_ler_query()

:LOCKout	LOCKout
		':LOCKout {{ON|1}|{OFF|0}}'
		':LOCKout?'
		- locks out or restores front panel operation
		* main_lockout(setting)		-- setting: 1/"1"/"ON" or 0/"0"/"OFF"
		* main_lockout_query()		-- returns: 1 or 0 

:MENU		MENU
		':MENU <module>[,<menu>]'
		':MENU?'
		- puts a menu of a module on display or tells the current one
		* main_menu(module, menu)	-- module: integer, -2 to 10
						-- menu: integer, range module-specific
		* main_menu_query()		-- returns 

:MESE<N>	MESE<N> (Module Event Status Enable)
		':MESE<N> <enable_value>'
		':MESE<N>?'
		- set and read the Module Event Status Enable register
		- enable register for MESR, <N> is the module index
		* main_mese(n, value)		-- n: integer, 0 to 10
						-- value: byte
		* main_mese_query(n)		-- n: integer, 0 to 10

:RMODe		RMODe
		':RMODe {SINGle|REPetitive}'
		':RMODe?'
		- specifies the run mode for selected module (or Intermodule if selected)
		* main_rmode(mode)		-- mode: string, "single" or "repetitive"
		* main_rmode_query()		-- returns: string

:RTC		RTC (Real-time Clock)
		':RTC <day>,<month>,<year>,<hour>,<minute>,<second>'
		':RTC?'
		- set and query the real-time clock
		* main_rtc(datetime)		-- datetime: datetime object
		* main_rtc_query()		-- returns: datetime object

:SELect		SELect
		':SELect <module>'
		':SELect?'
		- selects which module or system has parser control
		- the appropriate module must be selected before any module or system
		  specific commands can be sent
		- 0 = System/IM, 1-10 = slots A-J, -1 and -2 = software options 1 and 2
		* main_select(module)		-- module: integer, -2 to 10
		* main_select_query()		-- returns: integer, -2 to 10

:SETColor	SETColor
		':SETColor {<color>,<hue>,<sat>,<lum>|DEFault}'
		':SETColor? <color>'
		- modify palette colors, except color number 0
		* main_setcolor(color, hue, sat, lum)
			-- color: integer, 1 to 7
			-- hue/sat/lum: integer, 0 to 100
		* main_setcolor_query(color)	-- color: integer, 1 to 7
						-- returns: numeric list, [c,h,s,l]

:STARt		STARt
		':STARt'
		- starts the selected module running in the specified run mode
		- overlapped command
		* main_start()

:STOP		STOP
		':STOP'
		- stops the selected module
		- overlapped command
		* main_stop()

:XWINdow	XWINdow
		':XWINdow {OFF|0}'
		':XWINdow {ON|1}[,<display name>]'
		- opens or closes a window on an X server (requires networking capability)
		- saves display name in non-volatile memory
		* main_xwindow(mode, display)	-- mode: 1/"1"/"ON" or 0/"0"/"OFF"
						-- display: (optional) string, eg. "192.168.1.50:0.0"



SYSTem subsystem commands:

:DATA		DATA
		':SYSTem:DATA <block_data>'
		':SYSTem:DATA?'
		- send and receive acquired data in block form
		- refer to modules' Programmer's Guides
		* syst_data(blockdata)		-- blockdata: binary string or unsigned byte array
		* syst_data_query()		-- returns: block data

:DSP		DSP (Display)
		':SYSTem:DSP <string>'
		- display a message (up to 5 at a time) on the CRT
		- up to 68 characters
		* syst_dsp(string)		-- string: string, message to display

:ERRor		ERRor
		':SYSTem:ERRor?	[NUMeric|STRing]'
		- dequeue and return oldest message in the error queue
		- if NUM or no parameter, only number is returned
		* syst_error_query(string)	-- returns: tuple(errno, string)
		* flush_errors()		-- returns: list of tuple(errno, string)
						-- flushes all errors from the queue

:HEADer		HEADer
		':SYSTem:HEADer {{ON|1}|{OFF|0}}'
		':SYSTem:HEADer?'
		- when set to ON, all query responses include the command header
		- shouldn't be enabled, unnecessary chatter
		* syst_header(mode)		-- mode: 1/"1"/"ON" or 0/"0"/"OFF"
		* syst_header_query()		-- returns: 1 or 0

:LONGform	LONGform
		':SYSTem:LONGform {{ON|1}|{OFF|0}}'
		':SYSTem:LONGform?'
		- if set to OFF, command headers and alpha arguments are sent in abbreviated form
		- doesn't do much unless HEADer is enabled
		* syst_longform(mode)		-- mode: 1/"1"/"ON" or 0/"0"/"OFF"
		* syst_longform_query()		-- returns: 1 or 0

:PRINt		PRINt
		':SYSTem:PRINt ALL[,DISK,<pathname>[,<msus>]]'
		':SYSTem:PRINt PARTial,<start>,<end>[,DISK,<pathname>[,<msus>]]'
		':SYSTem:PRINt SCReen[,DISK,<pathname>[,<msus>],{BTIF|CTIF,PCX,EPS}]
		- prints the screen or listing buffer to printer or disk
		- BTIF = B/W TIF, CTIF = color TIF, PCX = color PCX, EPS = Encapsulated Postscript
		- instrument will append the correct extension if it is not specified
		- many arguments are optional, defaults print to hard disk as PCX
		* syst_print(mode, pathname, msus, disk, start, end, filetype)
						-- mode: string, "all" / "partial" / "screen"
						-- pathname: (optional) string
						-- msus: (optional) string
						-- start: (optional) integer, state number
						-- end: (optional) integer, state number
						-- filetype: (optional) string, "BTIF"/"CTIF"/"PCX"/"EPS"

:SETup		SETup
		':SYSTem:SETup <block_data>'
		':SYSTem:SETup?'
		- configures the system and reads the configuration in binary block data
		- see module specific Programmer's Guides
		* syst_setup(blockdata)		-- blockdata: binary string or array of unsigned bytes
		* syst_setup_query()		-- returns: current configuration as block data




MMEMory subsystem commands:

:AUToload	AUToload
		':MMEMory:AUToload {{OFF|0}|{<auto_file>}}[,<msus>]'
		':MMEMory:AUToload?'
		- set or query current autoload file, or disable autoload
		* mmem_autoload(auto_file, msus)	-- auto_file: string
							-- msus: (optional) string
		* mmem_autoload_query()			-- returns: string

:CATalog	CATalog
		':MMEMory:CATalog? [[All,][<msus>]]'
		- provides a directory listing in long (71 chars) or short mode (50 chars)
		* mmem_catalog_query(all, msus)		-- all: (optional) string "all" or nothing
							-- msus: (optional) string
		

:CD		CD (Change Directory)
		':MMEMory:CD <directory_name> [,<msus>]'
		- change current directory
		* mmem_cd(dirname, msus)		-- dirname: string, directory name
							-- msus: (optional) string

:COPY		COPY
		':MMEMory:COPY <name>[,<msus>],<new_name>[,<msus>]'
		- copy a file
		* mmem_copy(name, newname, srcmsus, dstmsus)
							-- name: string
							-- newname: string
							-- srcmsus: (optional) string
							-- dstmsus: (optional) string

:DOWNload	DOWNload
		':MMEMory:DOWNload <name>[,<msus>],<description>,<type>,<block_data>'
		- creates a file on the instrument's storage device from block data sent to it
		- note: download = from controller to instrument, upload = from instrument to controller
		- see method definition for table of datatypes
		* mmem_download(name, description, datatype, blockdata, msus)
							-- name: string
							-- description: string
							-- datatype: negative integer
							-- blockdata: binary string or array of unsigned bytes
							-- msus: (optional) string

:INITialize	INITialize
		':MMEMory:INITialize [{LIF|DOS}[,<msus>]]'
		- formats the disk in LIF or DOS format
		- make sure you have the right msus selected!
		- for "safety", by default floppy is selected
		* mmem_initialize(format, msus)		-- format: string, "LIF" or "DOS"
							-- msus: (optional) string

:LOAD		:LOAD[:CONFIG]
		':MMEMory:LOAD[:CONfig] <name>[,<msus>][,<module>]'
		- loads a configuration from the disk
		* mmem_load_config(name, msus, module)	-- name: string
							-- msus: (optional) string
							-- module: (optional) integer, -2 to 10

:LOAD		:LOAD:IASSembler
		':MMEMory:LOAD:IASSembler <IA_name>[,<msus>],{1|2}[,<module>]'
		- loads inverse assembler files into state analysis modules
		* mmem_load_iassembler(ia_name, machine, msus, module)
							-- ia_name: string
							-- machine: 1 or 2
							-- msus: (optional) string
							-- module: (optional) integer

:MKDir		MKDir (Make Directory)
		':MMEMory:MKDir <directory_name>[,<msus>]'
		- creates a directory
		* mmem_mkdir(dirname, msus)		-- dirname: string
							-- msus: (optional) string

:MSI		MSI (Mass Storage Is)
		':MMEMory:MSI [<msus>]'
		':MMEMory:MSI?'
		- select a default mass storage device (msus)
		- see method docstring for note on msus parameter
		* mmem_msi(msus)			-- msus: (optional) string
		* mmem_msi_query()			-- returns: string

:PACK		PACK
		':MMEMory:PACK [<msus>]'
		- packs files on the LIF disk in the drive, no action on DOS disks
		* mmem_pack(msus)			-- msus: (optional) string

:PURGe		PURGe
		':MMEMory:PURGe <name>[,<msus>]'
		- deletes a file
		* mmem_purge(name, msus)		-- name: string
							-- msus: (optional) string

:PWD		PWD (Present Working Directory)
		':MMEMory:PWD? [<msus>]'
		- return present working directory for the specified drive
		* mmem_pwd_query(msus)			-- msus: (optional) string

:REName		REName
		':MMEMory:REName <name>[,<msus>],<new_name>'
		- rename a file
		* mmem_rename(name, newname, msus)	-- name: string
							-- newname: string
							-- msus: (optional) string

:STORe		STORe[:CONFig]
		':MMEMory:STORe[:CONFIG] <name>[,<msus>],description[,<module>]'
		- stores module or system configurations on disk
		* mmem_store(name, description, msus, module)
							-- name: string
							-- description: string
							-- msus: (optional) string
							-- module: (optional) integer, 1 to 10

:UPLoad		UPLoad
		':MMEMory:UPLoad? <name>[,<msus>]'
		- upload a file (send it to controller) in block data form
		* mmem_upload_query(name, msus)		-- name: string
							-- msus: (optional) string

:VOLume		VOLume
		':MMEMory:VOLume? [<msus>]'
		- returns the volume type of the disk
		* mmem_volume_query(msus)		-- msus: (optional) string
							-- returns: string, "DOS", "LIF" or "???"



INTermodule subsystem commands:

:DELete		DELete
		':INTermodule:DELete {ALL|OUT|<module>}'
		- delete a module, PORT OUT or the entire intermodule tree
		* inter_delete(module)			-- module: integer, 1 to 10
		
:HTIMe		HTIMe
		':INTermodule:HTIMe?'
		- returns internal hardware skew in the Intermodule configuration
		* inter_htime_query()			-- returns: numeric list (real values)

:INPort		INPort
		':INTermodule:INPort {{ON|1}|{OFF|0}}'
		':INTermodule:INPort?'
		- causes intermodule acquisitions to be armed from the Input port
		* inter_inport(setting)			-- setting: 1/"1"/"ON" or 0/"0"/"OFF"
		* inter_inport_query()			-- returns: 1 or 0

:INSert		INSert
		':INTermodule:INSert {<module>|OUT},{GROUP|<module>}'
		- adds module or PORT OUT to Intermodule configuration
		* inter_insert(module, location)	-- module: string, "OUT" or integer, 1 to 10
							-- location: string, "GROUP" or integer, 1 to 10

:PORTEDGE	PORTEDGE
		':INTermodule:PORTEDGE <edge_spec>'
		':INTermodule:PORTEDGE?'
		- set the port input BNC to respond to either rising/falling edge for an external trigger
		- 1 = rising edge, 0 = falling edge
		* inter_portedge(edge_spec)		-- 1/"1"/"ON" or 0/"0"/"OFF"
		* inter_portedge_query()		-- returns: 1 or 0
		
:PORTLEV	PORTLEV
		':INTermodule:PORTLEV {TTL|ECL|<user_lev>}'
		':INTermodule:PORTLEV?'
		- set input BNC threshold level for intermodule trigger
		- level is a real number from -4.0 to +5.0 volts, in 0.02 volt increments
		* inter_portlev(level)			-- level: "TTL", "ECL" or real number
		* inter_portlev_query()			-- returns: "TTL", "ECL" or real number

:SKEW<N>	SKEW<N>
		':INTermodule:SKEW<N> <setting>'
		':INTermodule:SKEW<N>?'
		- set or read skew value for a module
		- N is module index, setting is the skew value in seconds, -1.0 to 1.0
		* inter_skew(n, setting)		-- n: integer, 1 to 10
							-- setting: real number
		* inter_skew_query(n)			-- n: integer, 1 to 10
							-- returns: real number

:TREE		TREE
		':INTermodule:TREE <module>,<module>,<module>,<module>,<module>,<module>'
		':INTermodule:TREE?'
		- allows an intermodule setup to be specified in one command
		- -1 = module not in intermodule tree, 0 = module armed from Group run
		- positive value = indicates module is armed by another module indicated by the slot number
		- first parameter: intermodule arm for module A (logic analyzer)
		- second parameter: intermodule arm for PORT OUT
		* inter_tree(modulelist)		-- modulelist: list of integers
		* inter_tree_query()			-- returns: numeric list

:TTIMe?		TTIMe
		':INTermodule:TTIMe?'
		- returns absolute intermodule trigger time for all modules in the Intermodule configuration
		- 9.9e37 = no module installed / not time correlated / did not trigger
		* inter_ttime_query()			-- returns: numeric list

