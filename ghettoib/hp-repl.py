#!/usr/bin/python -i
"""

HP 16500B/16501A Logic Analysis System interactive Read-eval-print loop


"""

import ghettoib

hp = ghettoib.HPLA("/dev/ttyUSB0", 19200)
#hp2 = ghettoib.HPLA("/dev/ttyS0", 19200, xonxoff = True)
#test = ghettoib.HPLA("/dev/pts/1", 19200)

#### Add your own control functions below!
