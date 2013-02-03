# Linux port of the NunchukMouse_release.py script (Windows version by Gabriel Bianconi)
# as advertised in Make Magazine issue 33 (http://blog.makezine.com/projects/make-33/wii-nunchuk-mouse/).
#
# Change Log:
#  2013-01-31 by Aaron Mitchell (ajmitc at gmail)
#    - Added command line arguments
#    - Cursor Speed is no longer a constant, now it is a function to scale the 
#      speed with nunchuk movement
#    - Replaced win32* function calls with pymouse function calls
#    - Added error checking
#    - Added signal handler for clean shutdown
#    - Added "joystick cursor" which will allow the analog stick to move the cursor and ignores
#      any movement by the nunchuk itself
#
# Usage: python NunchukMouse_linux.py [port]

# This script depends on the pymouse and pyserial libraries available at:
#    https://github.com/pepijndevos/PyMouse
# and
#    sudo apt-get install python-serial

# Import the required libraries for this script
import math, string, time, serial, sys
from optparse import OptionParser
from signal import signal, SIGINT
from pymouse import PyMouse

parser = OptionParser()
parser.add_option( "-p", "--port", dest='port', help="Port to read nunchuk data from", default="/dev/ttyACM0" )
parser.add_option( "-b", "--baud", dest="baudrate", help="Set the serial port baud rate", default=19200, type="int" )
parser.add_option( "-i", "--invert-y", dest="inverty", help="Invert the Y-Axis", default=False, action="store_true" )
parser.add_option( "-s", "--sensitivity", dest="cursorSensitivity", help="Ignore nunchuk movements less than this value", default=20, type="int" )
parser.add_option( "-v", "--verbose", dest="verbose", help="Print debug messages to the console", default=False, action="store_true" )
parser.add_option( "-j", "--joystick-cursor", dest="joycursor", help="Use the joystick (analog stick) to move mouse cursor (Recommend -i)", default=False, action="store_true" )
parser.add_option( "-c", "--calibrate", dest="calibrate", help="Calibrate mid-points", default=False, action="store_true" )
options, args = parser.parse_args()


def verbose( text ):
    """Print out the given text only if the --verbose option was given"""
    global options
    if options.verbose:
        print text


m = PyMouse()
def mousemove( dx, dy ):
    """Move the mouse cursor relative to the current position"""
    pos = m.position()
    m.move( pos[ 0 ] + dx, pos[ 1 ] + dy )

# Mouse button constants.  The PyMouse documentation says MIDDLE=2 and RIGHT=3,
# but that's not correct.  At least, not for me...
LEFT = 1
RIGHT = 2
MIDDLE = 3
WHEEL_UP = 4
WHEEL_DOWN = 5

def mouseclick( button ):
    """Perform a mouse click.  Currently not used, but here for robustness"""
    pos = m.position()
    m.click( pos[ 0 ], pos[ 1 ], button )

def mousepress( button ):
    """Perform a mouse press"""
    pos = m.position()
    m.press( pos[ 0 ], pos[ 1 ], button )

def mouserelease( button ):
    """Perform a mouse release"""
    pos = m.position()
    m.release( pos[ 0 ], pos[ 1 ], button )


mouseWheelSensitivity = 5
def mousewheel( val ):
    """Perform a mouse wheel action"""
    global mouseWheelSensitivity
    pos = m.position()
    if val < mouseWheelSensitivity and val > -mouseWheelSensitivity:
        return
    if val > 0:
        m.click( pos[ 0 ], pos[ 1 ], WHEEL_UP, n=val / 10 )
    elif val < 0:
        m.click( pos[ 0 ], pos[ 1 ], WHEEL_DOWN, n=(val * -1) / 10 )


def getCursorSpeed( offset ):
    """Get the cursor speed based on the x/y axis offset"""
    if options.joycursor:
        return abs( offset ) / 2
    return abs( offset ) / 4


# Variables indicating whether the mouse buttons are pressed or not
leftDown = False
rightDown = False

# Variables indicating the center position (no movement) of the controller
midAccelX = 530 # Accelerometer X
midAccelY = 510 # Accelerometer Y
midAnalogX = 129 # Analog X
midAnalogY = 131 # Analog Y


# Serial interface variable
ser = None

# setup signal handler to exit cleanly
def handle_signal( signum, frame ):
    if ser is not None:
        ser.close()
    sys.exit( 0 )
signal( SIGINT, handle_signal )


# Open serial port
verbose( "Opening serial port %s" % options.port )
try:
    ser = serial.Serial( options.port, options.baudrate, timeout = 1 )
except Exception, e:
    print str(e)
    sys.exit( 1 )


# Wait 1s for things to stabilize
if options.calibrate:
    print "Calibration will start in 3 seconds.  Hold Nunchuk upright and still.  Make sure joystick is centered"
    time.sleep( 3 )
else:
    time.sleep(1)


# While the serial port is open
while ser.isOpen():

    # Read one line
    line = ser.readline()

    # Strip the ending (\r\n)
    line = string.strip(line, '\r\n')

    # Split the string into an array containing the data from the Wii Nunchuk
    line = string.split(line, ' ')

    analogX = 0
    analogY = 0
    accelX  = 0
    accelY  = 0
    accelZ  = 0
    zButton = 0
    cButton = 0

    try:
        # Set variables for each of the values
        analogX = int(line[0])
        analogY = int(line[1])
        accelX  = int(line[2])
        accelY  = int(line[3])
        accelZ  = int(line[4])
        zButton = int(line[5])
        cButton = int(line[6])
    except Exception, e:
        verbose( str(e) )
        continue

    if options.calibrate:
        midAccelX = accelX
        midAccelY = accelY
        midAnalogX = analogX
        midAnalogY = analogY
        print "Calibration complete"
        options.calibrate = False
        verbose( "New Values:" )
        verbose( "midAccelX: %d" % midAccelX )
        verbose( "midAccelY: %d" % midAccelY )
        verbose( "midAnalogX: %d" % midAnalogX )
        verbose( "midAnalogY: %d" % midAnalogY )


    # Left Mouse Button
    # If the Wii Nunchuk Z Button is pressed, but wasn't previously
    if zButton and not leftDown:
        leftDown = True
        mousepress( LEFT )
    elif leftDown and not zButton:
        leftDown = False
        mouserelease( LEFT )

    # Right Mouse Button
    # Do the same with the C Button, simulating the right mouse button
    if cButton and not rightDown:
        rightDown = True
        mousepress( RIGHT )
    elif rightDown and not cButton:
        rightDown = False
        mouserelease( RIGHT )
        

    # Mouse Wheel
    # If the analog stick is not centered
    if options.joycursor:
        dx = 0
        dy = 0
        if abs(analogX - midAccelX) > options.cursorSensitivity:
            offset = analogX - midAnalogX
            speed = getCursorSpeed( offset )
            dx = int(math.floor( offset * speed / 400 ))
        if abs(analogY - midAccelY) > options.cursorSensitivity:
            offset = analogY - midAnalogY
            speed = getCursorSpeed( offset )
            dy = int(math.floor( offset * speed / 400 ))
            if options.inverty:
                dy = dy*-1
        mousemove( dx, dy )
        continue
        
    if abs(analogY - midAnalogY) > 5:
        # Simulate a mouse wheel movement
        mousewheel( int(math.floor( (analogY - midAnalogY) / 2 )) )


    # Mouse Movement
    # Create variables indicating how much the mouse cursor should move in each direction
    dx = 0
    dy = 0

    # If the Wii Nunchuk is rotated around the x-axis
    if abs(accelX - midAccelX) > options.cursorSensitivity:
        # Calculate how much the cursor should move horizontally
        offset = accelX - midAccelX
        speed = getCursorSpeed( offset )
        dx = int(math.floor( offset * speed / 400 ))

    # If the Wii Nunchuk is rotated around the y-axis
    if abs(accelY - midAccelY) > options.cursorSensitivity:
        # Calculate how much the cursor should move vertically
        offset = accelY - midAccelY
        speed = getCursorSpeed( offset )
        dy = int(math.floor( offset * speed / 400 ))
        # Invert the y-axis
        if options.inverty:
            dy = dy*-1

    # Simulate mouse movement with the values calculated above
    mousemove( dx, dy )
    

# After the program is over, close the serial port connection
ser.close()

