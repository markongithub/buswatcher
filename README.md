# NJ BusWatcher
v2.0
**2 mar 2019**

---
# ROADMAP TO COMPLETION

###1 finish core
- **route.html** 
    - row 2
        - period picker bar (daily, monthly, history, specific date) 
        -- using [bootstrap-datepicker](https://bootstrap-datepicker.readthedocs.io/en/latest/#) [installation instructions](https://stackoverflow.com/questions/29001753/bootstrap-datetimepicker-installation)
  

- **wwwAPI**
    - REFACTOR: period='daily' to period='today' everywhere
    - RouteReport.get_get_headway **DEBUGGING**
    - RouteReport.get_travel_time
    - RouteReport.get_bunching_badboys
    - RouteReport.get_grade

- **route.html**
    - row 3
        - period = 'now'
            - 'On the Road' can’t tell what is controlling the order of the busses on the road now. But I think if I was looking at this I might want to be able to quickly see busses going east-west or north-south so I could find the bus I usually ride in the morning, or whatever.
        - period != 'now'
            - left
                - hourly table summarizing **Average Headway.** (e.g. time between arrivals)
            - right
                - hourly table summarizing **Average Travel Time.**
           

- **stop.html** NEW DESIGN 
    - basically the same as Route view but narrower scope
    - different set of grade descriptions, e.g. "THIS STATION USUALLY HAS DECENT SERVICE or THIS STATION HAS GOOD SERVICE TODAY" or something like that.
    - stop-only additional panes (in grade box):
        - **average travel time to end of route from here** (by hour of day?)
        - **Average travel speed** - we can calculate this at every observed position with New Localizer.
      
#### Index View
- **index.html**
    - can you add a ranking somewhere of all the routes?  if you want to use this as an advocacy tool it may be useful to expose a ranking like that.
    - add the petition link to your footer next to CODE and API
- **route_config.py**
    - short and long descriptions for the new lines

#### Tripwatcher Q.C.
- **tripwatcher.py**
    - error trapping for disconnected operation (dying now?)
    - `approach assignment`: 3+ position seems to still be having problems...
    - `Interpolate+log missed stops` after scanning each trip and logging any new arrivals, run a function that interpolates arrival times for any stops in between arrivals in the trip card -- theoretically there shouldn't be a lot though if the trip card is correct since we are grabbing positions every 30 seconds.
    - `Boomerang buses (Case E)`: any other indeterminate cases?
   
#### Static Content
- **route_config.py**
    - complete descriptions for all lines
    - fix frequency for new lines
- **/static/images**
    - add images for 2,6,10, 123, tk
- **about.html** 
- **faq.html** 
- **api.html** 
    - write content
- **error_API_down.html** 
    - replace old template with new base.html template


#### Deployment
- check AWS time zones
- reduce image size to fit on micro instance?
- split tripwatcher, and / or map layers API into another instance to keep small+free


###099 someday

- **static/maps/**
    - busmap-index.js
        - add zoom to extent of vehicles_json layer
    - busmap-route.js
        - add zoom to extent of waypoints_json layer
    - busmap-stop.js
        - limit stop layer to single stop (w/ stops_json source set to '/api/v1/maps?layer=stops&rt=119&stop_id=30189') 
        - add zoom to extent of stops_json layer
     
- **stop.html**
    - period picker toggles -  (rush hour, owl, weekdays)
    -`arrival histogram visualization`
    - dot graph showing how many buses arrived at stop during each 30 minute bin, modeled after [Nobel prize D3 viz](https://github.com/Kyrand/dataviz-with-python-and-js/tree/master/nobel_viz_D3_V4) from Python+JS book
        - implementation: concatenate the 3 nobel scripts (core,main,time)
        - 30 minute bins
        - use chart.js, or rough,js
    - optional: show all buses on all routes arriving, each route different color? (would require add/rewrite lib.StopReport) 
- **Localizer.py**
    - `More accurate distance conversion`:  at least verify how far off we are. current method is using a crude assumption (1 degree = 69 miles = 364,320 feet). more accurate method - "If CRS of geodfs are EPSG 4326 (lat/lon) then returned 'dist' will be in degrees. To meters or ft either first convert both gdf to appropriate CRS proj for your location using .to_crs() or convert from degrees [link](https://t.co/FODrAWskNH)".
- **Databases.py** 
    - `relationships! use them!` `children_ScheduledStops` and `parent_Trip` are incredibly use attributes any record i pull from the db will have now. use them to extend the query sets we get back!!!!
    - `Exception handler`: smarter check in get_session on table creation --> try if table exists == False:
- **GTFS Integration**
    - This is a big deal but a major headache. Working with GTFS in [Jupyter](http://simplistic.me/playing-with-gtfs.html).
    - What's needed:
        - module to create lookup table GTFS:Clever_Devices - timestamp_hr_min+run_id --> gtfs: trip_id+start_time so we can match routelog.run to gtfs.trip_id
        - GTFS integration:  write a routine to match gtfs trip_id, start_time :: timestamp,run for first observation of a v in routelog series (e.g. map run to trip_id) -- either a machine learning model or something simpler 
- **Trip Playback**
    - Generate a list of runs, linked to 'playback' pages via an API call that spits out geojson for all points in routelog for a single run, on a specific date, and display on a page using mapbox live update [tutorial](https://www.mapbox.com/mapbox-gl-js/example/live-update-feature/).
- **map improvements**
    - show bus symbol as circle with route # in center (especially on closer zooms)
    - Show Congestion
        - change color of bunching buses on the map? 
        - indicate congested route segments 
        - indicated bunching at stops - a red dot and the more bunching happens (or the worse it is) the larger the dot
 - **add a higher level of geography**
    - county?
    - for statewide integration
- **test re-skinning for another city: Newark**
    - what needs to be changed (just route-config.py?)
 
---
# BUSWATCHER

### Version 2

Improvements over v1
- rewritten in Python 3
- new localization and stop assignment algorithm is based on geographicposition and stop proximity not API arrival predictions
- full SQLalchemy database implementation for easier mix and match backend


### Overview

Buswatcher is a Python web app to collect bus position and stop arrival prediction data from several API endpoints maintained by NJTransit (via vendor Clever Devices), synthesize and summarize this information, and present to riders in a number of useful ways via a simple, interactive web application. Its implemented in Python using flask, pandas, and geopandas.

Check out a live version focusing on Jersey City  [buswatcher.code4jc.org](http://buswatcher.code4jc.org)

### Installation

It's all dockerized now. Use `docker-compose` and build from the project root.

#### Manual MySQL Database Creation

(for testing)

```
sudo mysql -u root -p
mysql> CREATE USER 'buswatcher'@'localhost' IDENTIFIED BY 'njtransit';
Query OK, 0 rows affected (0.00 sec)

mysql> GRANT ALL PRIVILEGES ON buses . * TO 'buswatcher'@'localhost';
Query OK, 0 rows affected (0.00 sec)

mysql> ALTER USER 'buswatcher'@'localhost' IDENTIFIED WITH mysql_native_password BY 'njtransit';
Query OK, 0 rows affected (0.00 sec)

mysql> flush privileges;
Query OK, 0 rows affected (0.00 sec)
```

### Components

- **tripwatcher.py**. Fetches bus current locations for a route from the NJT API, creates a `Trip` instance for each, and populates it with `ScheduledStop` instances for each stop on the service its running, and a `BusPosition` instance for each observed position.
- **reportcard.py** The flask app for routing incoming requests.
- **/lib** Core classes.
    - **DataBases.py**
        - *`Trip` Class*. The basis for all route performance metrics are Trips, represented in buswatcher by the `Trip` class. `Trip` instances are created by `tripwatcher.py` as needed to hold `BusPosition` instances (`BusPosition` is an inner class of `Trip`. `TripDB` instances handle writing to the database.
        
### API 

The API is a work in progress, but we will try to keep it robust and exposing all of the internal data used in the web app.

### endpoint: /api/v1/positions

We have a simple API set up with one endpoint for the bus positions data -- this is currently not used by the web app but will be once the new Localizer is done.

Usage with arguments
```
http://buswatcher.code4jc.org/api/v1/positions?rt=119&period=weekly
```

#### required arguments
`rt`    NJ transit route number (e.g. 119)
#### optional arguments
`period`  How much data to grab ('daily'=today, 'yesterday', 'weekly'=week to date,'history'=all time(default)) -- n.b. soon we'll add ability to query on specific dates in 'yyyy-mm-dd' format

`pd` Destination name (be careful will need an exact match)

`fs` Headsign display text

`dn` Compass direction of vehicle travel

`bid` Vehicle (e.g. bus) id, useful if you want to track a particular journey

`run` A specific scheduled trip (which ought to be but is not the GTFS trip_id which drives me bananas.) Actually better for tracking a journey, as you can compare between days and over periods even if the equipment changes.

`op` Probably operator(driver) id number.

`pid` Unknown purpose. But possibly a service identfier (e.g. direction or local/express or branch or some combination).

`dip` Unknown purpose.

`id` Unknown purpose.



#### response format

Reponses are geoJSON. Here's a typical record.
```
    {
      "geometry": {
        "coordinates": [
          -74.138438, 
          40.647728
        ], 
        "type": "Point"
      }, 
      "properties": {
        "bid": "8272", 
        "dip": "72242", 
        "dn": "SW", 
        "fs": "119 JERSEY CITY VIA CENTRAL BAYOONNE VIA JFK BLVD", 
        "id": "6053", 
        "op": "1031", 
        "pd": "Bayonne", 
        "pid": "1860", 
        "run": "916", 
        "timestamp": "Thu, 04 Oct 2018 20:10:01 GMT"
      }, 
      "type": "Feature"
    }, 

```

### endpoint: /api/v1/arrivals

This endpoint exposes the predictions about when buses running on a specific route will arrive at specific stops. This data is drawn off the NJT API and is the heart of how we currently log when buses call at stops. (This will be depreceated when the Localizer is done and we do it basedon actual observed bus locations.)

Usage with arguments
```
http://buswatcher.code4jc.org/api/v1/arrivals?rt=119&stop_id=30189&period=weekly
```

#### required arguments
`rt`    NJ transit route number (e.g. 119)

`stop_id`   NJ transit stop number (e.g. 30189)

#### optional arguments

Any of the fields in the JSON response below may be used as arguments. You'll get an error if you use an invalid query.

#### response format

Reponses are geoJSON. Here's a typical record.
```
    "{"pkey":28831,
    "pt":"APPROACHING",
    "rd":"87",
    "stop_id":"21062",
    "stop_name":"PALISADE AVE + SOUTH ST",
    "v":"5737",
    "timestamp":1540903024000,
    "delta":599000},
```


## External Resources

#### NJTransit API

Clever Devices API maintained by NJ Transit at http://mybusnow.njtransit.com/bustime/map/. For instance, here are all the buses on the #87, right now: [http://mybusnow.njtransit.com/bustime/map/getBusesForRoute.jsp?route=87](http://mybusnow.njtransit.com/bustime/map/getBusesForRoute.jsp?route=87)

#### Bus Metrics
Examples of transit agency and transit advocate bus metrics:
- [MBTA Back on Track](http://www.mbtabackontrack.com/performance/index.html#/detail/reliability/2018-12-01/Bus/Key%20Bus/1/)
- [BusTurnaround:Scorecards - Transit Center](http://busturnaround.nyc/#bus-report-cards)
- [NYC Bus Profile (BusStat.nyc)](http://www.busstat.nyc/methodology)
