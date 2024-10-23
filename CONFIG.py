# Wifi Configuration
SSID = "your-ssid-here"
PSK = "your-wifi-password-here"
COUNTRY = "GB"

# Structures that will hold all the station and departures info
stations = []

# Get station information from https://www.mvg.de/.rest/zdm/stations
stations.append(
        {
            "id": ["de:09162:2"],               #station IDs, used to fetch departures
            "name": "Marienplatz",              #station name, not used
            "tariffZones":"m",                  #tariffZones (m, m+1, etc..), not used
            "products":["UBAHN","BUS","SBAHN"], #transportation type, used in the station screen
            "abbreviation":"MP",                #short name, used in the station screen
            "filter":["S8","S1"],               #only show depart. with these labels (if present)
            "departures": ""                    #structure that will hold departure data
        })

# Add more stations as needed (be aware of the memory limitations of rp pico w)
