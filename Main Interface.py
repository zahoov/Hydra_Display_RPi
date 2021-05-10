"""
AUTHOR: Xavier Biancardi

        Portions that deal with receiving CAN messages have been adapted from Calvin Lefebvre's code

PURPOSE: This is an app to be used on small 5" touch screen displays inside Hydra's trucks. It is used to display information gathered from the truck monitoring scripts in an easy to read
         touch screen GUI. It (currently) consists of 7 pages: Main Menu, H2 Fuel Gauge, H2 Injection Rate, Tank Pressure and Temperature, Fault Information, Leakage Information, and the Screen Saver.
         The pages' functions/purposes are described below. The app automatically runs on the boot up of the Raspberry Pi computer it is loaded on as long as the appropriate scripts/files are added as described
         in the README. The app requires a few files to run properly, these include the 2 image files "cadran.png" which is the gauge and "needle.png" which is the needle on the gauge. The entire app is built with Kivy
         via Python 3.7 and requires an up to date Python 3.7 as well as Kivy install to work. The file paths are currently set up for the Raspberry Pi computer that the app was built for but can be easily changed to
         fit any computer OS or file path.

Page Descriptions:

         Main Menu: This page is where the app initially loads to and consists of 5 buttons that each take you to the individual information pages. In the top left of the page is an area where in the case of a system fault
         a red message saying "FAULT" as well as the fault number code will be displayed. In the top right of the page is an area where the current mode of the truck (Hydrogen or Diesel) is displayed.

         H2 Fuel Gauge: This is the page that shows the current Hydrogen fuel level in the truck. It displays the percentage as a number in the bottom of the page as well as graphically in the form of the fuel gauge itself.
         In the bottom left of the page is a button that says "BACK" which when pressed takes the user back to the Main Menu page. As with all of the screens/pages the top left displays any faults and the top right displays
         the current engine mode of the truck

         H2 Injection Rate: Very similar in appearance to the H2 Fuel Gauge screen, this page shows the current instantaneous Hydrogen injection rate into the engine. It is displayed graphically as a percentage of the maximum
         injection rate on the gauge as well as the specific value in kg/h in the bottom of the page. This screen includes the same "BACK" button, Fault, and engine mode displays as all the other pages.

         Tank Pressure and Temperature: This page shows the current temperatures of all of the Hydrogen tanks in addition to the readings from the 2 in-line pressure sensors. Includes the same buttons and corner displays as
         the other screens

         Fault Information: This page provides more in depth information about the fault (if any) occurring within the truck. On the left it shows the fault code and on the right has the brief description of what the fault is.
         This is mainly for the driver to be able to inform the technician(s) and thus the fault description is brief and requires knowledge of the fault codes/messages to understand. Has the same "BACK" button and engine mode
         display however does not include a Fault display in the top left as that would be redundant since the page already displays that information

         Leakage Information: This page provides information on the status/severity of any Hydrogen leaks occurring in the truck. Includes the same corner buttons and displays as the other screens.

         Screen Saver: There is no direct button to access this screen. If there is no user interaction on any of the pages for a designated amount of time (controlled by the variable 'delay') then the app will automatically
         change to this page. To avoid burn in the Hydra logo is animated to slowly bounce around

Any reference to the Kivy back end or the Kivy code relates to the code held within the "fuelgauge.kv" file -- it will/needs to be in the same folder as this code for the app to work

"""
"""
    Outside References:
    - For the dusk screen dimming system the https://sunrise-sunset.org/api was used, this provided a very useful list of sunset times
    

"""

import time
import can
import os
from threading import Thread

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.properties import NumericProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.dropdown import DropDown

# The conversion factor is used to convert the raw numerical data into degrees to move the needle
# default is 1.8 which works for a 0-100 slider, this is because when the needle is pointing straight up (at the 50) it is at 0˚ and since
# the maximum angles for the needle will be 50 points on the dial either way to get this as +/- 90˚ you multiply the value by 1.8.
# To put it more simply 50 * 1.8 = 90, the needle has to be able to rotate 180˚ total and the gauge is from 0-100, 100 * 1.8 = 180
# cf = conversion_factor
cf = 1.8
# The delay is how long the app goes without user input before it changes to the screen saver
delay = 2000
# '/Users/Xavier Biancardi/PycharmProjects/Display_rep/'
display_code_dir = '/Users/Xavier Biancardi/PycharmProjects/Display_rep/'

_canIdTank123 = "cff3d17"
_canIdTank456 = "cff4017"
_canIdNira3 = "cff3e17"
_canIdWheelSpeed = "18fef100"


# This next block of functions are all derived from Calvin's PI data logging code, the main differences between them in this code and his are where the variables send their contents
#################################################################################################################

def msg_receiving():
    '''outDir = sys.argv[1]  # "/home/pi/rough/logger-rbp-python-out/lomack150_"
    numCAN = int(sys.argv[2])  # 2
    bRate = int(sys.argv[3])  # 250000 or 500000
    CANtype = sys.argv[4]  # OCAN or ACAN
    numTank = int(sys.argv[5])
    volumeStr = sys.argv[6]'''

    outDir = "/Users/Xavier Biancardi/PycharmProjects/Display_rep/"
    # Display_rep/out/hydraFL
    # "/home/pi/rough/logger-rbp-python-out/lomack150_"
    numCAN = 1  # 2
    bRate = 250000  # 250000 or 500000
    CANtype = "RBP15"  # OCAN or ACAN
    numTank = 5
    volumeStr = "202,202,202,202,148"

    volumeL = [float(x) for x in volumeStr.split(",")]

    os.system("sudo /sbin/ip link set can0 down")
    if numCAN == 2:
        os.system("sudo /sbin/ip link set can1 down")

    # Make CAN interface to 250 or 500kbps
    setCANbaudRate(numCAN, bRate)

    # Connect to Bus
    bus0 = connectToLogger('can0')
    if numCAN == 2:
        bus1 = connectToLogger('can1')

    # Continually recieved messages
    readwriteMessageThread(bus0, outDir, numCAN, bRate, CANtype, numTank, volumeL)
    # if numCAN == 2:
    #    readwriteMessageThread(bus1, outDir, numCAN, bRate, CANtype + "1", numTank, volumeL)

    # Continually write readMessages
    try:
        while True:
            pass

    except KeyboardInterrupt:
        # Catch keyboard interrupt
        os.system("sudo /sbin/ip link set can0 down")
        if numCAN == 2:
            os.system("sudo /sbin/ip link set can1 down")
        print('\n\rKeyboard interrtupt')


def readwriteMessageThread(bus, outDir, numCAN, bRate, CANv, numTank, volumeL):
    """
    In seperate thread continually recieve messages from CAN logger
    """
    # Start receive thread
    t = Thread(target=can_rx_task, args=(bus, outDir, numCAN, bRate, CANv, numTank, volumeL))
    t.start()


def can_rx_task(bus, outDir, numCAN, bRate, CANv, numTank, volumeL):
    """
    CAN receive thread
    """
    curFname = None
    outF = None
    prevTime = ("-1", "-1", "-1")

    livefeedNiraErrorFname = "_".join([outDir, CANv, "liveUpdate-NiraError.txt"])
    livefeedHmassFname = "_".join([outDir, CANv, "liveUpdate-Hmass.txt"])

    prevNiraError = None

    tempL = []
    maxNumTanks = 6
    for i in range(maxNumTanks): tempL.append(None)
    presT1 = None
    wheelSpeed = None
    railPressure = None

    prevSec = None

    curVarL = [railPressure, presT1, wheelSpeed]

    while True:
        # recieve message and extract info
        (outstr, timeDateV) = createLogLine(bus.recv())

        (ymdFV, hourV, ymdBV, hmsfV) = timeDateV

        prevYmdBV = ymdBV
        prevHmsfV = hmsfV
        prevHour = hourV
        prevTime = (prevYmdBV, prevHmsfV, prevHour)

        (prevNiraError, tempL, curVarL, prevSec) = liveUpdateTruck(outstr, livefeedNiraErrorFname,
                                                                   livefeedHmassFname,
                                                                   prevNiraError, prevTime, tempL,
                                                                   curVarL, volumeL, numTank,
                                                                   maxNumTanks, prevSec)
        # if not(HtotalMass == None):
        #     WRITE CODE HERE ... use HtotalMass


def createLogLine(message):
    """
    Format the CAN message
    """
    # Time Stamp
    (ymdFV, hmsfV, hourV, ymdBV) = extractTimeFromEpoch(message.timestamp)

    # PGN
    pgnV = '0x{:02x}'.format(message.arbitration_id)

    # Hex
    hexV = ''
    for i in range(message.dlc):
        hexV += '{0:x} '.format(message.data[i])

    outstr = " ".join([hmsfV, "Rx", "1", pgnV, "x", str(message.dlc), hexV]) + " "
    timeDateV = (ymdFV, hourV, ymdBV, hmsfV)
    return (outstr, timeDateV)


def extractTimeFromEpoch(timeStamp):
    """
    Extract all the relative time and date info from CAN timestamp
    """
    ymdFV = time.strftime('%Y%m%d', time.localtime(timeStamp))
    ymdBV = time.strftime('%d:%m:%Y', time.localtime(timeStamp))
    hmsV = time.strftime('%H:%M:%S', time.localtime(timeStamp))
    hourV = time.strftime('%H', time.localtime(timeStamp))
    millsecondV = str(timeStamp).split(".")[1][:3]
    return (ymdFV, hmsV + ":" + millsecondV, hourV, ymdBV)


def liveUpdateTruck(outstr, livefeedNiraErrorFname, livefeedHmassFname, prevNiraError, YDM,
                    tempL, curVarL, volumeL, numTank, maxNumTanks, prevSec):
    """
    ...
    """

    app = App.get_running_app()

    splt = outstr.strip().split(" ")

    # Timestamp with date
    monthNumToChar = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
                      9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    [dayV, monthV, yearV] = YDM[0].split(":")
    hmsStr = ":".join(YDM[1].split(":")[:3])
    outDate = " ".join([dayV, monthNumToChar[int(monthV)], yearV, hmsStr])

    [railPressure, presT1, wheelSpeed] = curVarL
    # date, can ID, hex value
    if (outstr[0] != "*"):
        try:
            dateV = splt[0]
            idV = splt[3].lower()[2:]
            hexVsplt = splt[6:]
            hexV = ""
            for h in hexVsplt:
                if len(h) == 1:
                    hexV += "0" + h
                elif len(h) == 2:
                    hexV += h
        except IndexError:
            hexV = ""
            idV = ""

        if len(hexV) == 16:
            #######################################################################################
            # Nirai7LastFaultNumber_spnPropB_3E
            if (idV == _canIdNira3):
                dateCond0 = (len(splt[0]) != 12)
                dateCond1 = ((len(splt[0]) == 13) and (len(splt[0].split(":")[-1]) == 4))

                piCcond = ((len(hexV) != 16) or (dateCond0 and not (dateCond1)))

                if piCcond:
                    pass
                else:
                    nirai7LastFaultNumber = (enforceMaxV(((int(hexV[6:8], 16))), 255) * 1.0)

                    app.error_code = str(int(nirai7LastFaultNumber))

                    if prevNiraError == None:
                        prevNiraError = nirai7LastFaultNumber
                    elif nirai7LastFaultNumber != prevNiraError:

                        'INSERT CODE HERE'

            #######################################################################################
            # Temperature and Pressure T1-T3
            if (idV == _canIdTank123):
                presT1 = (enforceMaxV(((int(hexV[0:2], 16)) +
                                       ((int(hexV[2:4], 16) & 0b00001111) << 8)), 4015) * 0.1)
                presT2 = (enforceMaxV((((int(hexV[2:4], 16) & 0b11110000) >> 4) +
                                       ((int(hexV[4:6], 16)) << 4)), 4015) * 0.1)
                tempL[0] = (enforceMaxV(((int(hexV[10:12], 16))), 250) * 1.0) - 40.0
                tempL[1] = (enforceMaxV(((int(hexV[12:14], 16))), 250) * 1.0) - 40.0
                tempL[2] = (enforceMaxV(((int(hexV[14:16], 16))), 250) * 1.0) - 40.0

                app.pressures[0] = str("%.2f" % presT1) + ' bar'

                app.temps[0] = str("%.2f" % tempL[0]) + '˚C'
                app.temps[1] = str("%.2f" % tempL[1]) + '˚C'
                app.temps[2] = str("%.2f" % tempL[2]) + '˚C'

            #######################################################################################
            # Temperature and Pressure T4-T6
            elif (idV == _canIdTank456):
                tempL[3] = (enforceMaxV(((int(hexV[10:12], 16))), 250) * 1.0) - 40.0
                tempL[4] = (enforceMaxV(((int(hexV[12:14], 16))), 250) * 1.0) - 40.0
                tempL[5] = (enforceMaxV(((int(hexV[14:16], 16))), 250) * 1.0) - 40.0

                app.temps[3] = str("%.2f" % tempL[3]) + '˚C'
                app.temps[4] = str("%.2f" % tempL[4]) + '˚C'
                app.temps[5] = str("%.2f" % tempL[5]) + '˚C'



            #######################################################################################
            # Rail pressure
            elif (idV == _canIdNira3):
                railPressure = (enforceMaxV(((int(hexV[12:14], 16))), 4015) * 0.1)

                app.pressures[1] = str('%.2f' % railPressure) + ' bar'

            #######################################################################################
            # Wheel-Based Vehicle Speed
            elif (idV == _canIdWheelSpeed):
                wheelSpeed = (enforceMaxV(((int(hexV[2:4], 16)) + ((int(hexV[4:6], 16)) << 8)),
                                          64259) * 0.003906)
            #######################################################################################
            # Hydrogen injection rate
            elif ((idV == "cff3f28") or (idV == "cff3ffa")):
                app.HinjectionV = (enforceMaxV(((int(hexV[12:14], 16)) + ((int(hexV[14:16], 16)) << 8)), 64255) * 0.02)

            #######################################################################################
            # Hydrogen leakage

            elif ((idV == "cff3e28") or (idV == "cff3efa")):
                app.Hleakage = (enforceMaxV(((int(hexV[2:4], 16))), 250) * 0.4)

            # Coolant temperature
            elif (idV == "18feee00"):
                coolant_temp = str((enforceMaxV(((int(hexV[0:2], 16))), 250) * 1.0) - 40.0)  # Unit = °C

                if coolant_temp is not '':
                    app.coolant_temp = coolant_temp + u' \u00BAC'

            # Diagnostic Message 1 -- Active DTCs
            elif (idV == "18feca00"):
                DM1 = (enforceMaxV((((int(hexV[0:2], 16) & 0b11000000) >> 6)), 3) * 1.0)  # Unit = bit

                if DM1 == 0:
                    app.mil_light = 'Lamp Off'
                else:
                    app.mil_light = 'Lamp On'

            # Diesel particulate filter
            elif (idV == "18fd7c00"):

                dpf = (enforceMaxV((((int(hexV[2:4], 16) & 0b00001100) >> 2)), 3) * 1.0)  # Unit = bit

                if dpf == 0:
                    app.dpf_status = 'Not Active'
                elif dpf == 1:
                    app.dpf_status = 'Active'
                elif dpf == 2:
                    app.dpf_status = 'Regen Needed'
                else:
                    app.dpf_status = 'Not Available'

            # Mode requests
            elif idV == 'cff3c17':

                mode_being_requested = (enforceMaxV(((int(hexV[0:2], 16) & 0b00000011)), 3) * 1.0)  # Unit = bit
                mode_num = (enforceMaxV((((int(hexV[0:2], 16) & 0b00001100) >> 2)), 3) * 1.0)  # Unit = bit

                if (mode_num == 0) or (mode_num == 1):
                    app.current_mode = 'Hydrogen'
                    # app.mode_num = str(mode_num)
                elif mode_num == 2:
                    app.current_mode = 'Diesel'
                    # app.mode_num = str(mode_num)

                # print(app.mode_being_requested)

                if (mode_being_requested) == 0 or (mode_being_requested == 1):

                    app.truck_reqd = u'H\u2082 Mode '
                    # app.mode_color = [235 / 255, 150 / 255, 72 / 255, 1]

                elif mode_being_requested == 2:

                    app.truck_reqd = 'Diesel Mode'
                    # app.mode_color = [0.431, 0.431, 0.431, 1]

                else:

                    app.truck_reqd = 'Missing'
                    app.mode_color = [1, 0, 0, 1]

                # if (app.mode_num == '0') or (app.mode_num == '1'):
                #    app.engine_mode = u'H\u2082 Mode '
                #    app.mode_color = [235 / 255, 150 / 255, 72 / 255, 1]
                # elif app.mode_num == '2':
                #    app.engine_mode = 'Diesel Mode'
                #    app.mode_color = [0.431, 0.431, 0.431, 1]

            #######################################################################################
            # curHr = int(dateV.split(":")[1])
            # if ((curHr in [0, 15, 30, 45]) and (curHr != lastQuarterHour)):
            curSec = int(dateV.split(":")[2])
            if curSec != prevSec:
                ###################################################################################
                # H mass calculation
                HtotalMass = None
                if (not (None in tempL) and (presT1 != None)):
                    HtotalMassL = []
                    for t in range(numTank):
                        # Only consider tank 1 hydrogen pressure
                        currHtotalMassT = hydrogenMassEq2(presT1, tempL[t], volumeL[t])
                        HtotalMassL.append(currHtotalMassT)

                    HtotalMass = round(sum(HtotalMassL), 1)
                    app.hMass = HtotalMass

                tempL = []
                for i in range(maxNumTanks): tempL.append(None)
                presT1 = None
                railPressure = None
                wheelSpeed = None

                prevSec = curSec
                # lastQuarterHour = curHr

    curVarL = [railPressure, presT1, wheelSpeed]

    return (prevNiraError, tempL, curVarL, prevSec)


def connectToLogger(canV):
    """
    Connect to Bus
    """

    app = App.get_running_app()

    try:
        app.bus = can.interface.Bus(channel=canV, bustype='socketcan_native')
    except OSError:
        print('Cannot find PiCAN board.')
        exit()
    return app.bus


def setCANbaudRate(numCAN, bRate):
    """
    Make CAN interface to 250 or 500 kbps
    """
    os.system("sudo /sbin/ip link set can0 up type can bitrate " + str(bRate))
    if numCAN == 2:
        os.system("sudo /sbin/ip link set can1 up type can bitrate " + str(bRate))
    time.sleep(0.1)


def hydrogenMassEq2(pressureV, tempV, volumeV):
    """
    Calculate the hydrogen mass using more complex equation
    Value returns in unit kilo grams
    """

    var1 = 0.000000001348034
    var2 = 0.000000267013
    var3 = 0.00004247859
    var4 = 0.000001195678
    var5 = 0.0003204561
    var6 = 0.0867471

    component1 = (((-var1 * (tempV ** 2)) + (var2 * tempV) - var3) * (pressureV ** 2))
    component2 = ((var4 * (tempV ** 2)) - (var5 * tempV) + var6) * pressureV

    HmassTotal = (component1 + component2) * volumeV
    HmassTotalKg = HmassTotal / 1000.0

    return HmassTotalKg


def enforceMaxV(origV, maxV):
    """
    ...
    """
    if origV < maxV:
        return origV
    else:
        return maxV


#################################################################################################################


# The following functions are all used for the displays operation
#################################################################################################################

# This function checks the value read by modeReader and checks what it is -- if it is 0 or 1 it sets the engine_mode string variable to 'H2\nMODE' which is just H2 MODE on separate lines, otherwise it sets the variable
# to 'DIESEL\nMODE'. It also then changes the color of the text to either green or grey
def truckEngineMode(dt):
    app = App.get_running_app()

    if (app.mode_num == '0') or (app.mode_num == '1'):
        app.engine_mode = u'H\u2082 Mode '
        app.mode_color = [235 / 255, 150 / 255, 72 / 255, 1]
        app.alignment = 'right'
    elif app.mode_num == '2':
        app.engine_mode = 'Diesel Mode'
        app.alignment = 'center'
        app.mode_color = [0.431, 0.431, 0.431, 1]


def stateUpdate(dt):
    app = App.get_running_app()


# This checks what value the error_code variable has and if it has no value or is 255 then since there is no fault the function sets the error_base string variable to ' ' which is just blank
# If error_code is any other number it then changes the error_base variable to a couple different things. This function is called repeatedly every 2s so it checks to see what error_base is currently
# if it is blank it changes it to 'FAULT' if it says 'FAULT' it changes it to the error code, and if it is the error code it changes it to 'FAULT' essentially flipping between displaying 'FAULT' and
# the error code every 2s
def errorMsg(dt):
    app = App.get_running_app()

    if (app.error_code == '255') or (app.error_code == ''):
        app.error_base = ''
    else:
        if app.error_base == '':
            app.error_base = 'FAULT'
        elif app.error_base == 'FAULT':
            app.error_base = '#' + app.error_code
        elif app.error_base == '#' + app.error_code:
            app.error_base = 'FAULT'


# This function just changes the current page to the 'third' which is what the screen saver page is defined as in the Kivy back end
def callback(dt):
    app = App.get_running_app()
    # app.root.current just calls the the Kivy ScreenManger class that handles all of the screens and changes it to the screen defined as 'third'
    app.root.current = 'third'


# Is called every 10s and checks to see if the current time is equal to the stored dusk time -- If it is, and if the screen is not currently dimmed this will
# proceed to set pin 18 to PWM and reduce it to 512 out of 1024
def isDusk(dt):
    app = App.get_running_app()

    dusk_today = app.dusk_time
    now = time.strftime('%I:%m')
    dimmed = app.screen_dim
    print(now)

    if (not dimmed) and (now == dusk_today):

        try:
            os.system('gpio -g pwm 18 75')
        except OSError:
            exit()

        app.screen_dim = True


# This function is called when the display first starts up -- it reads the stored sunset/dusk data file then extracts and stores the sunset time for the current day
def getDuskTime():
    dusk_file = open(display_code_dir + '2021PrinceGeorgeSunsets.txt', 'r')

    dusk_list = dusk_file.readlines()

    this_month = time.strftime('%m')
    real_today = time.strftime('%d')

    # Storing the sunset time for every day of the year would be a lot to sort through -- to speed things up only 5 days a month are used and the display assigns a
    # 'sudo today' which is the closest stored date to the current day
    if int(real_today) <= 3:
        sudo_today = '1'
    elif int(real_today) <= 10:
        sudo_today = '7'
    elif int(real_today) <= 17:
        sudo_today = '14'
    elif int(real_today) <= 23:
        sudo_today = '20'
    else:
        sudo_today = '26'

    for line in dusk_list:

        dusk_month = line.split('>')[0].split('-')[1]
        dusk_day = line.split('>')[0].split('-')[2]

        if dusk_month == this_month:

            dusk_time = line.split('>')[1].strip('\n')

            if dusk_day == sudo_today:

                if (int(this_month) > 3) or (int(this_month) < 11):
                    DST = True

                elif (int(this_month == 3)) and (int(real_today) >= 14):
                    DST = True

                elif (int(this_month == 11)) and (int(real_today) < 7):
                    DST = True
                else:
                    DST = False

                if DST == True:
                    dhour = int(dusk_time.split(':')[0]) + 1
                    dmin = int(dusk_time.split(':')[1])
                    if dhour < 10:
                        dusk_time = '0' + str(dhour) + ':' + str(dmin)
                    else:
                        dusk_time = str(dhour) + ':' + str(dmin)

                print(dusk_time)

                dusk_file.close()
                return dusk_time


def bus_activator(dt):
    app = App.get_running_app()

    try:
        app.bus = can.interface.Bus(channel='can0', bustype='socketcan_native')
        print('Found PiCAN board!')
    except OSError:
        print('Cannot find PiCAN board')
        Clock.schedule_once(bus_activator, 2)
        return
    try:
        print('made it past setting up bus now trying to send the toggle msg')
        app.task = app.bus.send_periodic(app.toggle_msg, 0.2)
        print('Toggle Message Successfully Sending')
    except NameError:
        Clock.schedule_once(bus_activator, 2)
        return


#################################################################################################################


# The following code are all of the classes that make up the main body and backend of the display app
#################################################################################################################
# This is the screen saver page -- for its design/visual setup look in the Kivy back end code (in the 'root_widget')
class ScreenSaver(Screen):
    # Sets the speed that the logo will travel at based on the size of the screen
    velocity = ListProperty([Window.width / 200, Window.height / 200])
    screen_pos = ListProperty([0, 0])

    # Updates the position of the Hydra logo (animates it)
    def update(self, dt):
        self.screen_pos[0] += self.velocity[0]
        self.screen_pos[1] += self.velocity[1]
        if self.screen_pos[0] < 0 or self.screen_pos[0] > ((Window.width * 2 / 3)):
            self.velocity[0] *= -1
        # or (self.screen_pos[1] + self.height) > Window.height
        if self.screen_pos[1] < 0 or self.screen_pos[1] > (Window.height * (1 - (1.8 * (2.5 / 12)))):
            self.velocity[1] *= -1

    app = App.get_running_app()

    def on_enter(self):
        Clock.unschedule(callback)
        Clock.schedule_interval(self.update, 1 / 120)

    # Special Kivy function that runs its code when the user touches the screen and releases
    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            # Since this page is the screen saver there is no timer/delay to reset, however when the user touches the screen saver and 'wakes' the device the app will return to the main menu
            self.manager.current = 'menu'

    def on_leave(self):
        Clock.unschedule(self.update)


# This is the fuel gauge screen that displays the current Hydrogen fuel level
class FuelGaugeLayout(Screen):
    # This (dash_val) value is the value that the dashboard/fuel gauge uses and starts at
    dash_val = NumericProperty(0.00)
    dash_label = StringProperty()
    percent_label = StringProperty()

    def mass_reader(self, dt):
        app = App.get_running_app()
        # Divides the current hydrogen mass by the maximum possible then multiplies by 100 to get a percentage
        # then assigns this value to the 'dash_val' variable
        self.dash_val = ((app.hMass / 20.7) * 100)

        self.percent_label = '%.2f' % self.dash_val

        self.dash_label = '%.2f' % app.hMass

    # Kivy function runs code on entering the page
    def on_enter(self):
        Clock.schedule_once(self.mass_reader)
        Clock.schedule_once(callback, delay)
        Clock.schedule_interval(self.mass_reader, 0.2)

    # Kivy function runs code when the user touches and releases on the screen. This is the delay reset for the screen saver
    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    # Same as in the other classes
    def on_leave(self):
        Clock.unschedule(callback)


# FuelInjectionLayout is the second screen and does what it says on the tin -- it displays the current H2 injection rate
class FuelInjectionLayout(Screen):
    # This variable is what is used to display injection reading at the bottom of the page, is a string property to allow the Kivy back end to read it even when it changes
    hInjection = StringProperty()
    leak_display = StringProperty()

    # Same as in the other classes, calls functions as the user enters the page. Upon_entering has the same function as upon_entering_mass and just calls the functions after a 0.5s
    # delay to avoid any issues
    def on_enter(self):
        Clock.schedule_once(self.injection_reader)
        Clock.schedule_interval(self.injection_reader, 0.2)
        # Same as in fuel gauge screen
        Clock.schedule_once(callback, delay)
        # Ticker is what checks to see if the time is at a 15min +1 time interval

    # Kivy function that runs code after the user touches the screen
    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    # This function opens the file that contains the data about the injection rate, reads it and sets it to some variables
    def injection_reader(self, dt):
        app = App.get_running_app()

        # hInj -- This is the variable that contains the injection rate value

        self.hInjection = '%.2f' % app.HinjectionV

        leakAmt = app.Hleakage
        self.leak_display = '%.2f' % app.Hleakage

    # Same as in the other classes
    def on_leave(self):
        Clock.unschedule(callback)
        Clock.unschedule(self.injection_reader)


# This is the page that displays the Fault code and its corresponding message
class ErrorPage(Screen):
    error_expl = StringProperty('Missing')

    # Same as in the other classes
    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    # Same as in the other classes, apart from the bottom bit
    def code_checker(self, dt):
        app = App.get_running_app()

        # This part checks to see if the error code is 255 as this means that there is no fault or if the code is greater than 233 as this is out of the possible range of
        # fault codes, if it is 255 it sets the message to 'Everything is running as expected' and if the code is greater than 233 it sets it as 'ERROR: Code outside of range'
        try:
            e_c = int(app.error_code)
        except ValueError:
            return ()

        if e_c == 255:
            self.error_expl = 'Running as expected'
        elif int(app.error_code) >= 233:
            self.error_expl = 'Invalid Code'
        else:
            self.error_expl = app.error_list[e_c]

    # Same as in the other class
    def on_enter(self):
        Clock.schedule_once(self.code_checker)
        Clock.schedule_interval(self.code_checker, 0.2)
        Clock.schedule_once(callback, delay)

    def on_leave(self):
        Clock.unschedule(self.code_checker)
        Clock.unschedule(callback)


# This is the screen that displays the temperatures and pressures of the tanks and lines from the tanks
class TankTempPress(Screen):

    # Nothing fancy happens on this page, all of the data collection/displaying is handled by the main app class in addition to the kivy code file (fuelgauge.kv)

    def on_enter(self):
        Clock.schedule_once(callback, delay)

    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    def on_leave(self):
        Clock.unschedule(callback)


# This is the screen manager that holds all of the other pages together
class MyScreenManager(ScreenManager):
    pass


# Screen that shows the leakage rate
class Mode(Screen):

    def on_enter(self):
        app = App.get_running_app()

        # app.title_changer('Engine Mode')

        Clock.schedule_once(callback, delay)

    # Kivy function runs code when the user touches and releases on the screen. This is the delay reset for the screen saver
    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    # Same as in the other classes
    def on_leave(self):
        Clock.unschedule(callback)


# This is the lock screen where technicians can lock or unlock the engine mode toggle button -- accessed by hitting the engine mode descriptor
class ModeLocking(Screen):
    # This is the correct password/pin
    password = '1234'

    # This is the descriptor text that says either 'Locked' or 'Unlocked'
    status = StringProperty()

    def on_enter(self):
        # When the user enters the screen checks the current lock status
        Clock.schedule_once(self.launch_status)
        Clock.schedule_once(callback, delay)

    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    def on_leave(self):
        Clock.unschedule(callback)

    # Checks the current lock status and sets the descriptor text accordingly
    def launch_status(self, dt):
        app = App.get_running_app()

        if app.lock_status == '0':
            self.status = 'Unlocked'
        else:
            self.status = 'Locked'

    # Sets the default color of the submit button
    wrong_password_ind = ListProperty([44 / 255, 49 / 255, 107 / 255, 1])

    # Called when the user submits their password
    def code_tester(self, text):

        # Allows this function to reference variables/functions from the main app class
        app = App.get_running_app()

        # Checks if the entered password matches the correct one
        if text == self.password:

            # Changes the color of the submit button to Green in order to show the correct password was entered
            self.wrong_password_ind = [0, 1, 0, 1]

            # Checks the current lock status
            if app.lock_status == '1':
                # Toggles the lock status to unlocked
                app.lock_status = '0'
                self.status = 'Unlocked'
            else:
                # Toggles the lock status to locked
                app.lock_status = '1'
                self.status = 'Locked'

            # Writes the current lock status to lock_file.txt to save it across sessions
            fin = open(display_code_dir + "lock_file.txt", "wt")
            fin.write(app.lock_status)
            fin.close()

        else:
            # Changes the color of the submit button to Red in order to show an incorrect password was entered
            self.wrong_password_ind = [1, 0, 0, 1]


class Message_settings(Screen):
    def on_enter(self):
        Clock.schedule_once(callback, delay)

    # Kivy function runs code when the user touches and releases on the screen. This is the delay reset for the screen saver
    def on_touch_up(self, touch):
        Clock.unschedule(callback)
        Clock.schedule_once(callback, delay)

    # Same as in the other classes
    def on_leave(self):
        Clock.unschedule(callback)


# The main app class that everything runs off of
class FuelGaugeApp(App):
    os.system('gpio -g mode 18 pwm')
    os.system('gpio -g pwm 18 1024')

    ####################################################################################################
    # Variable declarations
    ####################################################################################################
    temps = ListProperty(['NA', 'NA', 'NA', 'NA', 'NA', 'NA'])
    pressures = ListProperty(['NA', 'NA'])
    font_file = StringProperty(display_code_dir + 'Montserrat-Regular.ttf')
    bold_font_file = StringProperty(display_code_dir + 'Montserrat-Bold.ttf')
    current_page = StringProperty('Fuel Gauge')
    dropdown_list = ListProperty(
        ['Fuel Gauge', 'Injection Rate', 'Engine Mode', 'Temp & Press', 'Fault Info', 'CAN Settings'])
    mode_being_requested = int
    error_list = []
    mode_num = str
    error_code_list = []
    screen_dim = False
    Hleakage = NumericProperty()
    HinjectionV = NumericProperty()
    mil_light = StringProperty('Missing')
    coolant_temp = StringProperty('Missing')
    dpf_status = StringProperty('Missing')
    current_mode = StringProperty('Missing')
    truck_reqd = StringProperty()
    # The 0 inside the brackets is providing an initial value for hMass -- required or else something breaks
    hMass = NumericProperty(0)
    # error_code is a string variable that is used to temporarily store the current error code taken from the text document it is stored in. It is a string because after coming from the .txt the data is a string and
    # must be converted into a float or int to be used as a number
    error_code = StringProperty('Missing')
    # error_base is the text that is displayed in the top left hand of most screens -- if there is a fault this variable becomes "FAULT" and then the error code and flips between them
    # It is a StringProperty() which is a Kivy variable type the essentially tells the Kivy back end code to keep checking what its value is/if it changes
    error_base = StringProperty()
    # The conversion factor is for changing the discrete data values into a specific angle of rotation for the gauges
    conversion_factor = cf
    dusk_time = getDuskTime()

    ####################################################################################################
    # Extracting data from the stored text files
    ####################################################################################################

    # Opens the NIRA error code file and saves th error codes to error_code_list
    with open(display_code_dir + 'faultmessages.txt',
              'r') as f:
        lines = f.readlines()
        # Goes line by line and adds the error codes to the 'error_code_list' list
        for l in lines:
            error_code_list.append(l.split(',')[0])
        f.close()

    # Opens the NIRA error code file and saves the fault code descriptions to error_list
    with open(display_code_dir + 'faultmessages.txt',
              'r') as f:
        lines = f.readlines()
        # Goes line by line and adds the error messages to the 'error_list' list
        for l in lines:
            error_list.append(l.split(',')[2])
        f.close()

    # lock_file.txt and fuel_file.txt contains and holds the lock and engine mode statuses so they are saved after the screen is turned off
    # Tries to open the file -- if it isn't there it creates it with a default value
    if os.path.isfile(display_code_dir + "lock_file.txt"):
        fin = open(display_code_dir + "lock_file.txt", "rt")
        lock_status = fin.read()
        fin.close()
    else:
        fin = open(display_code_dir + "lock_file.txt", "w")
        fin.write('0')
        lock_status = '0'
        fin.close()

    if os.path.isfile(display_code_dir + "fuel_file.txt"):
        fin = open(display_code_dir + "fuel_file.txt", "rt")
        mode_num = fin.read().strip('\n')
        fin.close()
    else:
        fin = open(display_code_dir + "fuel_file.txt", "w")
        fin.write('2')
        mode_num = '2'
        fin.close()

    if os.path.isfile(display_code_dir + "arbitration_file.txt"):
        fin = open(display_code_dir + "arbitration_file.txt", "r+")

        stored_id = fin.read()

        if stored_id == '':
            arb_id = '0xCFF41F2'
            arb_address = StringProperty(arb_id)
            fin.write(arb_id)
            fin.close()
        else:
            arb_id = stored_id
            arb_address = StringProperty(arb_id)
            fin.close()
    else:
        fin = open(display_code_dir + "arbitration_file.txt", "w")
        arb_id = '0xCFF41F2'
        fin.write(arb_id)
        arb_address = StringProperty(arb_id)
        fin.close()

    # Declaring variables and giving them data from the stored/extracted text files
    source_id = StringProperty(arb_id[7:9])
    dest_id = StringProperty(arb_id[5:7])

    ####################################################################################################
    # Determines what the current engine mode is (H2 or Diesel) and sets the initial value for the top right corner display zone
    ####################################################################################################
    if (mode_num == '0') or (mode_num == '1'):
        engine_mode = StringProperty(u'H\u2082 Mode ')
        alignment = StringProperty('right')
        mode_color = ListProperty([235 / 255, 150 / 255, 72 / 255, 1])
        msg_data = [1, 0, 0, 0, 0, 0, 0, 0]
    elif mode_num == '2':
        engine_mode = StringProperty('Diesel Mode')
        alignment = StringProperty('center')
        mode_color = ListProperty([0.431, 0.431, 0.431, 1])
        msg_data = [0, 0, 0, 0, 0, 0, 0, 0]

    ####################################################################################################
    # These are the scheduled functions -- functions that are called every delay (###, delay) seconds
    ####################################################################################################
    # This calls errorMsg every 2 seconds to constantly change the error notification text from "FAULT" to the error code, or if there is no error it sets the text to blank
    Clock.schedule_interval(errorMsg, 2)
    Clock.schedule_interval(isDusk, 5)
    # This checks the value of the engine mode number every 2 seconds and changes the notification text if needed
    Clock.schedule_interval(truckEngineMode, 2)
    # Starts Calvin's CAN message reading code in another thread so that it is constantly reading while the display is active
    a = Thread(target=msg_receiving)
    a.start()

    try:
        bus = can.interface.Bus(channel='can0', bustype='socketcan_native')
    except OSError:
        print('Cannot find PiCAN board.')
        Clock.schedule_once(bus_activator)
        pass

    toggle_msg = can.Message(arbitration_id=0xCFF41F2, data=msg_data, is_extended_id=True)

    try:
        task = bus.send_periodic(toggle_msg, 0.2)
    except NameError:
        Clock.schedule_once(bus_activator)
        pass

    ####################################################################################################
    # These are the functions that are used by the kivy side of the app -- they are defined here so that they can be accessed by the
    # .kv file
    ####################################################################################################

    # Runs the screen manager that sets everything in motion
    def build(self):
        # Clock.schedule_once(self.bus_activator)
        return MyScreenManager()

    # Called when the user hits the 'Truck Engine Mode' button
    def ModeSender(self):
        print(self.lock_status)
        print(self.mode_num)
        prev_mode = self.mode_num
        prev_data = self.msg_data

        # Clock.unschedule(self.toggle_try)

        # If the display is unlocked (lock_status == '0') it checks to see what the current engine mode is
        if self.lock_status == '0':

            # Depending on the current mode the CAN msg data is set to either 1 or 0 (for H2 mode and Diesel mode respectively)
            if self.mode_num == '2':

                self.msg_data = [1, 0, 0, 0, 0, 0, 0, 0]
                # Then it changes what the current mode number is (ie. it toggles the engine mode for the next time the button is pressed)
                self.mode_num = '0'

            else:
                self.msg_data = [0, 0, 0, 0, 0, 0, 0, 0]
                self.mode_num = '2'

            self.toggle_msg.data = self.msg_data
            self.toggle_msg.dlc = 8

            try:
                self.task.modify_data(self.toggle_msg)
            except AttributeError:
                print('Unable to Change Message, Please Try Again')
                self.mode_num = prev_mode
                self.msg_data = prev_data
                return

            # Writing the current engine mode to a text file so that it is saved when the display is shut off
            fin = open(display_code_dir + "fuel_file.txt", "wt")
            fin.write(self.mode_num)
            fin.close()

            # Clock.schedule_once(truckEngineMode)

    def source_changer(self, new_id):

        if new_id == '':
            return

        try:
            int(new_id)
        except ValueError:
            print('This is not an integer value')
        else:

            no_caps = str(self.arb_id)[0:2]
            wo_source = str(self.arb_id)[2:7]

            if int(new_id) > 255:
                print('Inputted value is too high, 255 is the max input')
                return
            else:

                new_id = str(hex(int(new_id)))[2:]

                self.arb_id = (no_caps + wo_source.upper() + new_id.upper())
                self.source_id = new_id

                fin = open(display_code_dir + "arbitration_file.txt", "wt")
                fin.write(self.arb_id)
                fin.close()

                self.arb_address = self.arb_id

                self.task.stop()
                self.toggle_msg = can.Message(arbitration_id=int(self.arb_id, 16), data=self.msg_data)
                self.task = self.bus.send_periodic(self.toggle_msg, 0.2)

    def destination_changer(self, new_id):

        cap = 2 ** 29

        try:
            int(new_id)
        except ValueError:
            print('This is not an integer value')
        else:
            print('Input accepted')

            check = int(new_id)

            if check > (cap - 255):
                print('That was too large a number. The max input is: ' + str(cap - 255))
                return
            else:

                self.dest_id = str(hex(int(new_id)))[2:]

                front_mid = self.arb_id[2:5]
                rear = self.arb_id[7:9]
                no_caps = self.arb_id[0:2]
                new_id = (str(hex(check)))[2:]

                self.arb_id = (no_caps + front_mid.upper() + new_id.upper() + rear.upper())
                self.arb_address = self.arb_id

                fin = open(display_code_dir + "arbitration_file.txt", "wt")
                fin.write(self.arb_id)
                fin.close()

                self.task.stop()
                self.toggle_msg = can.Message(arbitration_id=int(self.arb_id, 16), data=self.msg_data)
                self.task = self.bus.send_periodic(self.toggle_msg, 0.2)

    def title_changer(self, cur_page):
        self.current_page = cur_page


# Makes everything start
if __name__ == '__main__':
    # Tells KIVY to open in fullscreen mode
    Config.set('graphics', 'fullscreen', '0')
    # Tells KIVY what keyboard to use (systemanddock is both physical and onscreen keyboards)
    Config.set('kivy', 'keyboard_mode', 'systemanddock')
    # Tells KIVY to use the custom keyboard layout named pinpad.json and located in the kivy data files
    Config.set('kivy', 'keyboard_layout', 'pinpad')
    # Actually sends all of the previously set config options to the KIVY config controller
    Config.write()
    # Runs the app class that controls the screen
    FuelGaugeApp().run()
