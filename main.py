import _thread
import time
import uasyncio
import requests
import machine
import ntptime

from interstate75 import Interstate75, DISPLAY_INTERSTATE75_64X32
from pimoroni import Button

import WIFI_CONFIG
from network_manager import NetworkManager

# Panel related configuration
i75 = Interstate75(display=DISPLAY_INTERSTATE75_64X32)

graphics = i75.display
graphics.set_font("bitmap8")
i75.set_led(0, 0, 0) # turn off onboard led
WIDTH = i75.width
HEIGHT = i75.height

# Max number of lines to draw in the panel
MAX_LINES = int(HEIGHT/8) # we need 8 lines for each line

# Max departure name size to display
MAX_DEST_NAME_SIZE = (WIDTH-15-8)//5 #15 for the label, 8 for ETA.

# Button used to switch between stations
# using the button A, in the back of interstate 75 W
BUTTON_A = Button(14, invert=True)

# Some colours to draw with
WHITE = graphics.create_pen(80, 80, 80)
YELLOW = graphics.create_pen(100, 100, 50)
BLACK = graphics.create_pen(0, 0, 0)

# Product related colours 
BUS = graphics.create_pen(17, 93, 111)
UBAHN = graphics.create_pen(29, 43, 83)
TRAM = graphics.create_pen(120, 0, 1)
SBAHN = graphics.create_pen(0, 120, 0)

# Departures endpoint
DEPARTURES_URL = 'https://www.mvg.de/api/fib/v2/departure?globalId={}'
DEPARTURES_UPDATE_DELAY = 60 #how often should we update departure info

# Structures that will hold all the station and departures info
stations = []

# Using Watchdog Scratch register 0 to store ActiveStating between resets
active_station = machine.mem32[0x40058000+0xc] # defaults to 0 on poweron

# Placeholder to display while the departures are loaded
initial_departures = [
        {
            'transportType': 'XX',                  #something random, to force a yellow label
            'realtimeDepartureTime': 3141592653589, #some high value, to force "++" in the ETA
            'label': '++ ',                         #label in the beginning of the line
            'destination': 'Loading'                #placeholder, while the stations are fetched
        }
    ]

# Get station information from https://www.mvg.de/.rest/zdm/stations

stations.append(
        {
            "id": ["de:09162:2"],               #station IDs, used to fetch departures
            "name": "Marienplatz",              #station name, not used
            "tariffZones":"m",                  #tariffZones (m, m+1, etc..), not used
            "products":["UBAHN","BUS","SBAHN"], #transportation type, used in the station screen
            "abbreviation":"MP",                #short name, used in the station screen
            "filter":["S8","S1"],               #only show depart. with these labels (if present)
            "departures": initial_departures    #structure that will hold departure data
        })

# Add more stations as needed (be aware of the memory limitations of rp pico w)

# Timing Configuration (delays, etc..)
GLOBAL_SLEEP = 0.2 # time increment for every step

# Time to wait while showing station info
STATION_DEFAULT_WAIT = 1
station_wait = STATION_DEFAULT_WAIT

# Time to wait while showing departure info (use low values when scrolling)
DEPARTURES_DEFAULT_WAIT = 0.2
departures_wait = DEPARTURES_DEFAULT_WAIT

# Scrolling variables
DISABLE_SCROLL = 0
# Wait time before starting scrolling, then it will scroll at "DEPARTURES_DEFAULT_WAIT" speed
OFFSET_DEFAULT_WAIT = 2
# One string offset for each line (max 4 lines in a 64x32 panel)
offset = [ 0 for x in range (MAX_LINES) ]
offset_wait = [ OFFSET_DEFAULT_WAIT for x in range (MAX_LINES) ]

def status_handler(mode, status, ip):
    """Handler function for WIFI connection step"""
    graphics.set_pen(BLACK)
    graphics.clear()
    graphics.set_pen(WHITE)
    graphics.text("{}".format(WIFI_CONFIG.SSID), 2, 2, scale=1)
    status_text = "Connecting..."
    if status is not None:
        if status:
            status_text = "successful!"
        else:
            status_text = "failed!"
            machine.reset() #reset the board in case of issues

    graphics.text(status_text, 2, 12, scale=1)
    graphics.text("{}".format(ip), 0, 22, scale=1)
    i75.update(graphics)

def draw_station():
    """Function to draw station info in a single page (no scrolling)"""
    global station_wait, departures_wait
    global active_station
    global offset, offset_wait

    if station_wait > 0:
        graphics.set_pen(BLACK)
        graphics.clear()
        graphics.set_pen(WHITE)

        # Draw a box around the abbreviation
        graphics.line(10, 4, WIDTH-10, 4)
        graphics.line(10, 4, 10, 14)
        graphics.line(10, 14, WIDTH-10, 14)
        graphics.line(WIDTH-10, 4, WIDTH-10, 15)

        #taking measures to center it
        abbreviation_size = graphics.measure_text(stations[active_station]["abbreviation"], scale=1)
        graphics.text(stations[active_station]["abbreviation"],
                      (WIDTH//2)-(abbreviation_size//2), #center of display - half of abbr size
                      6, scale=1)

        # Draw a list of products avaialble in the station
        product_offset = WIDTH//2 - 27 #where to start writing the products, in pixels
        for product in stations[active_station]["products"]:
            if product == "BUS":
                graphics.set_pen(BUS)
                graphics.rectangle(product_offset, 19, 16, 9) #make a background with product colour
                graphics.set_pen(BLACK)
                graphics.text(product, product_offset+1, 20, scale=1)
                product_offset+=17 #space needed to write the product name
            elif product == "UBAHN":
                graphics.set_pen(UBAHN)
                graphics.rectangle(product_offset, 19, 6, 9)
                graphics.set_pen(BLACK)
                graphics.text("U", product_offset+1, 20, scale=1)
                product_offset+=7
            elif product == "TRAM":
                graphics.set_pen(TRAM)
                graphics.rectangle(product_offset, 19, 23, 9)
                graphics.set_pen(BLACK)
                graphics.text("TRAM", product_offset+1, 20, scale=1)
                product_offset+=24
            elif product == "SBAHN":
                graphics.set_pen(SBAHN)
                graphics.rectangle(product_offset, 19, 6, 9)
                graphics.set_pen(BLACK)
                graphics.text("S", product_offset+1, 20, scale=1)
                product_offset+=7
        i75.update(graphics)
        station_wait -= GLOBAL_SLEEP

    # Handle the change of stations, with an additional check to prevent "double" click
    if BUTTON_A.is_pressed and station_wait < STATION_DEFAULT_WAIT - GLOBAL_SLEEP :
        station_wait = STATION_DEFAULT_WAIT #make the station screen visible
        departures_wait = 0 #make the departure screen visible after showing the station screen
        offset = [ 0 for x in range(MAX_LINES) ] #reset all string offsets
        offset_wait = [ OFFSET_DEFAULT_WAIT for x in range(MAX_LINES) ] #and also the wait time
        if active_station + 1 == len(stations):
            active_station = 0
        else:
            active_station += 1
        # Save active_station in WD Scratch register
        machine.mem32[0x40058000+0xc] = active_station

def draw_departures():
    """Function to draw the departures info"""
    global departures_wait
    global offset, offset_wait

    if station_wait > 0: #if showing the station screen, do nothing
        return
    if departures_wait > 0:
        departures_wait -= GLOBAL_SLEEP #decrement until it is time to refresh
        return
    departures_wait = DEPARTURES_DEFAULT_WAIT
    current_line = 1 # in pixels
    current_item = 0 # in items
    graphics.set_pen(BLACK)
    graphics.clear()

    # for each departure in the current selected station, ordering by "realtimeDepartureTime"
    for departure in sorted(
            stations[active_station]["departures"],
            key=lambda x: x["realtimeDepartureTime"]):

        # choosing the colour for the label
        if departure["transportType"] == "BUS":
            graphics.set_pen(BUS)
        elif departure["transportType"] == "UBAHN":
            graphics.set_pen(UBAHN)
        elif departure["transportType"] == "TRAM":
            graphics.set_pen(TRAM)
        elif departure["transportType"] == "SBAHN":
            graphics.set_pen(SBAHN)
        else:
            graphics.set_pen(YELLOW) #default colour, also used in the initial or no departures

        ## Label 0 - 14
        label_size = graphics.measure_text(departure["label"],scale=1)
        graphics.text(departure["label"], 15-label_size, current_line, scale=1)

        ## Destination 15 - (WIDTH-8)
        graphics.set_pen(WHITE)
        #get MAX_DEST_NAME_SIZE chars from the destination starting from offset[current_item]
        destination = departure["destination"][offset[current_item]:
                                               offset[current_item]+MAX_DEST_NAME_SIZE]
        graphics.text(destination, 15, current_line, scale=1)

        #scrolling logic
        if offset_wait[current_item] > 0: #delay before starting to scroll
            offset_wait[current_item] -= GLOBAL_SLEEP
        elif DISABLE_SCROLL == 0:
            if (len(departure["destination"]) > MAX_DEST_NAME_SIZE and
                    len(departure["destination"]) > offset[current_item]):
                offset[current_item]+=1
            else:
                offset[current_item]=0
                offset_wait[current_item] = OFFSET_DEFAULT_WAIT

        # ETA (WIDTH-8) - WIDTH
        graphics.set_pen(YELLOW)

        # calculate the ETA in minutes (ms - ms / (ms * 60s))
        eta = int((departure["realtimeDepartureTime"] - int(time.time()*1000)) / (1000*60))

        if int(eta) > 99: #if more than 99min, print something in 2 chars
            eta = "++"
        else:
            eta = str(eta)

        eta_size = graphics.measure_text(eta, scale=1)
        graphics.text(eta, WIDTH-eta_size+1, current_line, scale=1)

        current_line += 8 #each line takes 8 pixels
        current_item += 1
        if current_item > MAX_LINES-1: # Only printing MAX_LINES items
            break

    i75.update(graphics) # finally updating the display

def draw_loop():
    """Loop function to draw stations and departures"""
    while True:
        draw_station() #draw current station on demand
        draw_departures() #draw departure info continuously
        time.sleep(GLOBAL_SLEEP)

def update_departures():
    """Function to update departure information using mvg api"""
    global stations
    timestamp = int(time.time()*1000) #get the current timestamp in ms
    print("updating departures")
    i75.set_led(0, 0, 50) #change the onboard led to blue, for debugging
    for station in stations:
        departures = [] #new structure for the departures
        for sid in station["id"]:
            resp = requests.get(url=DEPARTURES_URL.format(sid))
            data = resp.json()
            resp.close()
            count = 0 # we only need MAX_LINES departures
            for departure in data:
                #if filter is defined, skip departures that the label doesn't match the filter
                if station["filter"] and departure["label"] not in station["filter"]:
                    continue
                #check for valid departures (happening in the future and not cancelled)
                if departure["realtimeDepartureTime"] > timestamp and not departure["cancelled"]:
                    departures.append({
                            "transportType": departure["transportType"],
                            "label": departure["label"],
                            "destination": departure["destination"],
                            "realtimeDepartureTime": departure["realtimeDepartureTime"]
                            }
                        )
                    count+=1
                    if count > MAX_LINES-1: #only getting necessary entries
                        break
        if len(departures) == 0: #if there are no departures available to show
            departures.append({
                    "transportType": "XX", # just to show in yellow
                    "label": "++ ",
                    "destination": "No departures available",
                    "realtimeDepartureTime": 3141592653589,
                    }
                )
        station["departures"] = departures #update with the fetched departures
    print("departures updated!")
    i75.set_led(0, 50, 0) #set led to green

# Connect to WIFI
try:
    network_manager = NetworkManager(WIFI_CONFIG.COUNTRY, status_handler=status_handler)
    uasyncio.get_event_loop().run_until_complete(
        network_manager.client(WIFI_CONFIG.SSID, WIFI_CONFIG.PSK))
    ntptime.settime() # Adjusting the RTC time
except Exception as e:
    print(e)
    machine.reset() #reset the board in case of issues

# Use the secound cpu to handle all the drawing
second_thread = _thread.start_new_thread(draw_loop, ())

# Use the first cpu to update departure info
while True:
    try:
        update_departures()
    except Exception as e:
        print(e)
        machine.reset() #reset the board in case of issues
    time.sleep(DEPARTURES_UPDATE_DELAY)
