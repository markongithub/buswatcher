from pathlib import Path
import json
import datetime
import geojson
import pickle
import os
import sys
import time

from . import NJTransitAPI, Generators
from .wwwAPI import RouteReport
from .CommonTools import get_config_path
from .DataBases import SQLAlchemyDBConnection, ScheduledStop

class SystemMap:

    def __init__(self):

        # read the /config files -- grades, route metadata and overrides, collection metadata
        try:
            with open(get_config_path() + 'grade_descriptions.json') as f:
                self.grade_descriptions = json.load(f)
            with open(get_config_path() + 'route_descriptions.json') as f:
                self.route_descriptions = json.load(f)
            with open(get_config_path() + 'collection_descriptions.json') as f:
                self.collection_descriptions = json.load(f)
            with open(get_config_path() + 'period_descriptions.json') as f:
                self.period_descriptions = json.load(f)
        except:
            import sys
            sys.exit("<BUSWATCHER>One or more of the config files isn't loading properly")

        # load the route geometries
        self.route_geometries = self.get_route_geometries()
        self.routelist = self.get_routelist()
        self.grade_roster = self.get_grade_roster()

        # create database connection
        self.db = SQLAlchemyDBConnection()


    # def watch_system_map_pickle(self):
    #     # Call this function each time a change happens
    #     def custom_action(text):
    #         self.__reset__()
    #     watch_file = find_pickle_file()
    #     # watcher = Watcher(watch_file)  # simple
    #     watcher = Watcher(watch_file, custom_action, text='pickle file changed, resetting system_map')  # also call custom action function
    #     watcher.watch()  # start the watch going

    def get_route_geometries(self):
        route_geometries={}
        for rd in self.route_descriptions['routedata']:
            # print('getting route geometry for '+rd['route'])
            route = rd['route']
            route_geometries[route]=self.get_single_route_geometry(route)
        return route_geometries

    def get_single_route_geometry(self, route, force_download=False):
        route_xml = self.get_single_route_xml(route, force_download)
        return {
          'route':route,
          'xml':route_xml,
          'paths': self.get_single_route_Paths(route)[0],
          'coordinate_bundle': self.get_single_route_Paths(route)[1]
        }

    def available_path_ids(self, route):
        path_ids = set()
        for direction in self.route_geometries[route]['paths']:
            for path in direction.paths:
                path_ids.add(path.id)
        return path_ids

    def update_single_route_geometry(self, route):
        new_geometry = self.get_single_route_geometry(
                route, force_download=True)
        self.route_geometries[route]=new_geometry
        print('paths available after update: {paths}'.format(paths=self.available_path_ids(route)))

    def get_routelist(self):
        routelist = (list(set(r['route'] for r in self.route_descriptions['routedata'])))
        return routelist

    def get_single_route_xml(self, route, force_download=False):

        if force_download:
            return self.download_route_xml(route)

        try:# load locally
            return self.get_cached_route_xml(route)

        except: #  if missing download and load
            return self.download_route_xml(route)

    def download_route_xml(self, route):
        print ('fetching xmldata for '+route)
        route_xml = NJTransitAPI.get_xml_data('centro', 'routes', route=route)
        outfile = (get_config_path() + 'route_geometry/' + route + '.xml')
        f = open(outfile, 'wb') # overwrite existing file
        f.write(route_xml)
        # need an explicit close because other code tries to read it soon
        f.close()
        return route_xml

    def get_cached_route_xml(self, route):
        infile = (get_config_path() + 'route_geometry/' + route + '.xml')
        with open(infile, 'rb') as f:
            return(f.read())

    def get_single_route_Paths(self, route):
        while True:
            try:
                route_xml = self.get_cached_route_xml(route)
                return NJTransitAPI.parse_xml_getRoutePoints(route_xml)
            except:
                pass

    def route_in_route_descriptions(self, route):
        return (route in self.route_geometries)

    def get_single_route_paths_and_coordinatebundle(self, route, path_id=None):
        print('paths available now: {paths} and we want {path_id}'.format(paths=self.available_path_ids(route), path_id=path_id))
        if path_id and path_id not in self.available_path_ids(route):
            self.update_single_route_geometry(route)
        routes = self.route_geometries[route]['paths']
        coordinates_bundle = self.route_geometries[route]['coordinate_bundle']
        return routes, coordinates_bundle

    def get_path_points(self, route, path_id):
        routedata, coordinate_bundle = self.get_single_route_paths_and_coordinatebundle(route, path_id)
        for rt in routedata:
            for path in rt.paths:
                if path.id == path_id:
                  return path.points
        return []

    def get_single_route_stoplist_for_localizer(self, route, path_id):

        routedata, coordinate_bundle = self.get_single_route_paths_and_coordinatebundle(route, path_id)
        stoplist=[]
        for rt in routedata:
            for path in rt.paths:
                for p in path.points:
                    if p.__class__.__name__ == 'Stop':
                        stoplist.append(
                            {'stop_id': p.identity, 'st': p.st, 'd': p.d, 'lat': p.lat, 'lon': p.lon})
        return stoplist

    def get_single_route_stoplist_for_wwwAPI(self, route):
        route_stop_list = []

        for direction in self.get_single_route_Paths(route)[0]:
            path_list = []
            for path in direction.paths:
                stops_points = RouteReport.Path()
                for point in path.points:
                    if isinstance(point, NJTransitAPI.Route.Stop):
                        stops_points.stops.append(point)
                stops_points.id = path.id
                stops_points.d = path.d
                stops_points.dd = path.dd
                path_list.append(
                    stops_points)  # path_list is now a couple of Path instances, plus the metadata id,d,dd fields
            route_stop_list.append(path_list)
            return route_stop_list[0]  # transpose a single copy since the others are all repeats (can be verified by path ids)

    def extract_geojson_features_from_system_map(self, route):
        waypoints_feature = geojson.Feature(geometry=json.loads(self.route_geometries[route]['coordinate_bundle']['waypoints_geojson']))
        stops_feature = geojson.Feature(geometry=json.loads(self.route_geometries[route]['coordinate_bundle']['stops_geojson']))
        return waypoints_feature, stops_feature

    def render_geojson(self, args):

        try:
            # if we only want a single stop geojson
            if 'stop_id' in args.keys():
                # query the db and grab the lat lon for the first record that stop_id matches this one
                with self.db as db:
                    stop_query = db.session.query(
                        ScheduledStop.stop_id,
                        ScheduledStop.lat,
                        ScheduledStop.lon) \
                        .filter(ScheduledStop.stop_id == args['stop_id']) \
                        .first()
                    # format for geojson
                    stop_point = geojson.Point((float(stop_query[2]), float(stop_query[1])))
                    stop_feature = geojson.Feature(geometry=stop_point)
                    return stop_feature

            # otherwise continue to get waypoints/stops for all routes, one route
            elif 'rt' in args.keys():
                waypoints = []
                stops = []
                if args['rt'] == 'all':
                    for r in self.route_descriptions['routedata']:
                        waypoints_item, stops_item = self.extract_geojson_features_from_system_map(r['route'])
                        waypoints.append(waypoints_item)
                        stops.append(stops_item)
                else:
                    waypoints_item, stops_item = self.extract_geojson_features_from_system_map(args['rt'])
                    waypoints.append(waypoints_item)
                    stops.append(stops_item)

            # or a collection of routes
            elif 'collection' in args.keys():
                waypoints = []
                stops = []

                # pick the right collection
                for route in self.collection_descriptions[args['collection']]['routelist']:
                    waypoints_item, stops_item = self.extract_geojson_features_from_system_map(route)
                    waypoints.append(waypoints_item)
                    stops.append(stops_item)

            # now render the layers as geojson
            if args['layer'] == 'waypoints':
                waypoints_featurecollection = geojson.FeatureCollection(waypoints)
                return waypoints_featurecollection
            elif args['layer'] == 'stops':
                stops_featurecollection = geojson.FeatureCollection(stops)
                return stops_featurecollection

            return
        except:
            from flask import abort
            abort(404)
            pass

    def get_grade_roster(self):
        grade_roster=dict()
        for rt in self.routelist:
            report_fetcher = Generators.Generator()
            try:
                grade_report = report_fetcher.retrieve_json(rt, 'grade', 'day')
            except:
                grade_report = {'grade':'N/A'}
            grade_roster[rt]=grade_report['grade']
        return grade_roster




##################################################################
# Class TransitSystem bootstrappers
##################################################################

def flush_system_map():
    system_map_pickle_file = Path("config/system_map.pickle")
    try:
        os.remove(system_map_pickle_file)
        print ('deleted system_map.pickle file')
    except:
        print ('error. could NOT delete system_map.pickle file')
        pass
    return

def find_pickle_file():
    # find the pickle file
    if os.getcwd() == "/":  # docker
        prefix = "/buswatcher/buswatcher/"
    elif "Users" in os.getcwd():  # osx
        prefix = ""
    else:  # linux & default
        prefix = ""
    pickle_filename = (prefix + "config/system_map.pickle")
    return {'prefix':prefix, 'pickle_filename':pickle_filename}

def load_system_map(**kwargs):
    pickle_filename = find_pickle_file()['pickle_filename']

    # force regen (optional)
    if 'force_regen' in kwargs.keys():
        if kwargs['force_regen'] == True:
            flush_system_map()
            system_map = SystemMap()
            with open(pickle_filename, "wb") as f:
                pickle.dump(system_map, f)

    # if there's a pickle, load it
    try:
        with open(pickle_filename, "rb") as f:
            system_map = pickle.load(f)
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(pickle_filename)).strftime('%Y-%m-%d %H:%M:%S')
            print("Loading existing pickle file, last modified at " + mod_time)

    # otherwise regen and load it
    except FileNotFoundError:
        print(str(pickle_filename) + " pickle file not found. Rebuilding, may take a minute or so..")
        system_map = SystemMap()
        with open(pickle_filename, "wb") as f:
            pickle.dump(system_map, f)

    return system_map
