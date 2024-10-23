# i75W MVG Farhinfo

Micropython code for Pimoroni's Interstate 75w RP2040 board to display departure times of Munich public transport.
It uses MVG API to fetch departure information for a predetermined set of stations

The code was developed for [Pimoroni's Interstate 75 W (Pico W Aboard) - RGB LED Matrix Driver](https://shop.pimoroni.com/products/interstate-75-w?variant=40453881299027) and uses [Pimoroni's Micropython libraries](https://github.com/pimoroni/pimoroni-pico) to drive a generic RGB LED Madrix Panel

You can also use a RP Pico W directly connected to the LED Panel, check [this](https://cdn.shopify.com/s/files/1/0174/1800/files/interstate_w_schematic.pdf?v=1675859802) schema for the connections

This code was developed using a 64x32 pixels panel, but other panel sizes (compositions) are also possible (hopefully with minimal changes)

## Setup

 - Check [these](https://learn.pimoroni.com/article/getting-started-with-interstate-75) instructions to setup your board with Pimoroni's Micropython libraries
 - Include your WIFI and desired stations information in `CONFIG.py`
 - Move `main.py`, `network_manager.py` and `CONFIG.py` to pico's flash memory using Thonny

Now everytime the board is turned on it will automatically run the code

## Customizing

### Selecting Stations

The code will update the departure information for the predetermined stations in the `CONFIG.py` file

You can append multiple stations to the `stations` list with the station information that you want to display (be aware of the memory limitations of rp pico w)

 - Get station information from https://www.mvg.de/.rest/zdm/stations

```
stations.append( # First station
    {
        "id": ["de:09162:2"],               #station IDs, used to fetch departures
        "name": "Marienplatz",              #station name, not used
        "tariffZones":"m",                  #tariffZones (m, m+1, etc..), not used
        "products":["UBAHN","BUS","SBAHN"], #transportation type, used in the station screen
        "abbreviation":"MP",                #short name, used in the station screen             "filter":["S8","S1"],               #only show departures with these labels (if present)
        "departures": initial_departures    #structure that will hold departure data
    })

stations.append( # Second station
    {....}
)
```

It is possible to include more than one `id` in the station information. This will make the configured station to display departure information for multiple stations. In this case, you can use an `abbreviation` name that makes sense for you.

You can use the onboard button A of i75w to change between the available stations.

### Changing delays

There are multiple variables controling the behaviour regarding delays. These are the most important ones:

 - `DEPARTURES_UPDATE_DELAY`: How often should we update departure information using the MVG API
 - `STATION_DEFAULT_WAIT`: How long the station screen should be visible after startup and during station change (button A)
 - `DEPARTURES_DEFAULT_WAIT`: How long before every departure screen refresh
 - `OFFSET_DEFAULT_WAIT`: How long to wait before scrolling the departure name (for long departure names)

### Other Parameters

 - `DISABLE_SCROLL`: Disables the scrolling of the departure name totally

## Example

![station](https://github.com/rafael747/i75w-mvg-farhinfo/assets/3441126/97d6902d-82e9-4ae3-86d1-73860434e6ce)

https://github.com/rafael747/i75w-mvg-farhinfo/assets/3441126/878e0836-b371-4c74-9605-dce73c2667e6

## Credits

- [MVG](https://mvg.de) for the API.
- [FaisalBinAhmed/MVGFahrinfo](https://github.com/FaisalBinAhmed/MVGFahrinfo) for the inspiration for this project

## License

MIT

### Limitations

Due to the hardware limitations of pico w, the board will soft reset itself when facing any issues (when connecting to the wifi, when connecting to the API, etc..)
Luckily, the current station will be preserved between the resets.

