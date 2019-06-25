mapboxgl.accessToken = 'pk.eyJ1IjoiYml0c2FuZGF0b21zIiwiYSI6ImNqbDhvZnl1YjB4NHczcGxsbTF6bWRjMWQifQ.w2TI_q7ClI4JE5I7QU3hEA';
var map = new mapboxgl.Map({
    container: 'map',
    style: "mapbox://styles/mapbox/light-v9",
    center: [-74.50, 40], // starting position [lng, lat]
    zoom: 7 // starting zoom
});

// new endpoints
//var url_stops =  ("/api/v1/maps/stops?rt="+passed_route+"&stop_id="+passed_stop_id  );
var url_waypoints = ("/api/v1/maps/waypoints?rt="+passed_route);
var url_vehicles = ("/api/v1/maps/vehicles?rt="+passed_route);


// old endpoints
var url_stops =  ("/api/v1/maps?layer=stops&rt="+passed_route+"&stop_id="+passed_stop_id);
// var url_waypoints = ("/api/v1/maps?layer=waypoints&rt="+passed_route);
// var url_vehicles = ("/api/v1/maps?layer=vehicles&rt="+passed_route);

map.on('load', function() {


    $.getJSON(url_vehicles, (geojson) => {
        map.addSource('vehicles_source', {
            type: 'geojson',
            data: geojson
        });
        /* map.fitBounds(turf.bbox(geojson), {padding: 20}); */

        map.addLayer({
            "id": "vehicles",
            "type": "circle",
            "source": "vehicles_source",
            "paint": {
                "circle-radius": 4,
                "circle-opacity": 1,
                "circle-stroke-width": 3,
                "circle-stroke-color": "#f6c"
            }
         })
        ;

    });

    $.getJSON(url_stops, (geojson) => {
        map.addSource('stops_source', {
            type: 'geojson',
            data: geojson
        });
        map.fitBounds(turf.bbox(geojson), {padding: 20});

        map.addLayer({
            "id": "route",
            "type": "circle",
            "source": "stops_source",
            "paint": {
                "circle-radius": 2,
                "circle-opacity": 1,
                "circle-stroke-width": 2,
                "circle-stroke-color": "#fff"
            }
        });
    });


/*    $.getJSON(url_waypoints, (geojson) => {
        map.addSource('waypoints_source', {
            type: 'geojson',
            data: geojson
        });
        // map.fitBounds(turf.bbox(geojson), {padding: 50});

        map.addLayer({
            "id": "route",
            "type": "line",
            "source": "waypoints_source",
            "paint": {
                "line-color": "blue",
                "line-opacity": 0.75,
                "line-width": 3
            }
        });
    });
    */

    window.setInterval(function() {
        map.getSource('vehicles_source').setData(url_vehicles);
        }, 2000)


    // HOVER TOOLTIPS
    var popup = new mapboxgl.Popup({
        closeButton: false,
        closeOnClick: false
    });

    map.on('mouseenter', 'vehicles', function(e) {
        // Change the cursor style as a UI indicator.
        map.getCanvas().style.cursor = 'pointer';

        var coordinates = e.features[0].geometry.coordinates.slice();
        var description = (e.features[0].properties.fs + ", Bus " + e.features[0].properties.id + ", Driver " + e.features[0].properties.op + ", Run " + e.features[0].properties.run);

        // Ensure that if the map is zoomed out such that multiple
        // copies of the feature are visible, the popup appears
        // over the copy being pointed to.
        while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
            coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
        }

        // Populate the popup and set its coordinates
        // based on the feature found.
        popup.setLngLat(coordinates)
            .setHTML(description)
            .addTo(map);
    });

    map.on('mouseleave', 'vehicles', function() {
        map.getCanvas().style.cursor = '';
        popup.remove();
    });




});


// todo restore tooltips to busmap-route.js

map.addControl(new mapboxgl.NavigationControl());

