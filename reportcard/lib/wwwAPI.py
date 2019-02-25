import pickle
import datetime
import pandas as pd
import geojson, json

from sqlalchemy import inspect, func

import lib.BusAPI as BusAPI
from lib.DataBases import SQLAlchemyDBConnection, Trip, BusPosition, ScheduledStop

from route_config import reportcard_routes, grade_descriptions


# primary classes
class RouteReport:

    class Path():
        def __init__(self):
            self.name = 'Path'
            self.stops = []
            self.id = ''
            self.d = ''
            self.dd = ''

    def __init__(self, source, route):

        # apply passed parameters to instance
        self.source = source
        self.route = route

        # populate route basics from config
        self.reportcard_routes = reportcard_routes
        self.grade_descriptions = grade_descriptions

        # populate static report card data
        self.routename, self.waypoints_coordinates, self.stops_coordinates, self.waypoints_geojson, self.stops_geojson = self.get_route_geojson_and_name(self.route) #todo -- would be nice to read this from Trip, but since RouteReport has more than 1 trip, which path will we use? this is why buses sometimes show up on maps not on a route
        self.load_route_description()
        self.route_stop_list = self.get_stoplist(self.route)

        # populate live report card data
        # self.active_trips = self.get_activetrips()
        self.tripdash = self.get_tripdash()


    def get_route_geojson_and_name(self, route):
        routes, coordinate_bundle = BusAPI.parse_xml_getRoutePoints(BusAPI.get_xml_data(self.source, 'routes', route=route))
        return routes[0].nm, coordinate_bundle['waypoints_coordinates'], coordinate_bundle['stops_coordinates'], coordinate_bundle['waypoints_geojson'], coordinate_bundle['stops_geojson']

    def load_route_description(self):
        for route in self.reportcard_routes:
            if route['route'] == self.route:
                self.frequency = route['frequency']
                self.description_long = route['description_long']
                self.prettyname = route['prettyname']
                self.schedule_url = route['schedule_url']
            else:
                pass
        return

    # gets all stops on all active routes
    def get_stoplist(self, route):
        routes, coordinate_bundle = BusAPI.parse_xml_getRoutePoints(BusAPI.get_xml_data(self.source, 'routes', route=self.route))
        route_stop_list = []
        for r in routes:
            path_list = []
            for path in r.paths:
                stops_points = RouteReport.Path()
                for point in path.points:
                    if isinstance(point, BusAPI.Route.Stop):
                        stops_points.stops.append(point)
                stops_points.id=path.id
                stops_points.d=path.d
                stops_points.dd=path.dd
                path_list.append(stops_points) # path_list is now a couple of Path instances, plus the metadata id,d,dd fields
            route_stop_list.append(path_list)
        return route_stop_list[0] # transpose a single copy since the others are all repeats (can be verified by path ids)

    # gets all arrivals (see limit) for all runs on current route
    def get_tripdash(self):
        with SQLAlchemyDBConnection() as db:
            # build a list of tuples with (run, trip_id)
            v_on_route = BusAPI.parse_xml_getBusesForRoute(BusAPI.get_xml_data(self.source, 'buses_for_route', route=self.route))
            todays_date = datetime.datetime.today().strftime('%Y%m%d')
            trip_list=list()

            for v in v_on_route:
                trip_id=('{a}_{b}_{c}').format(a=v.id,b=v.run, c=todays_date)
                trip_list.append((trip_id, v.pd, v.bid, v.run))

            tripdash = dict()
            for trip_id,pd,bid,run in trip_list:

                # load the trip card - full with all the missed stops
                # scheduled_stops = db.session.query(ScheduledStop) \
                #     .join(Trip) \
                #     .filter(Trip.trip_id == trip_id) \
                #     .order_by(ScheduledStop.pkey.asc()) \
                #     .all()

                # load the trip card - pretty
                scheduled_stops = db.session.query(ScheduledStop) \
                    .join(Trip) \
                    .filter(Trip.trip_id == trip_id) \
                    .filter(ScheduledStop.arrival_timestamp != None) \
                    .order_by(ScheduledStop.pkey.desc()) \
                    .limit(5) \
                    .all()

                trip_dict=dict()
                trip_dict['stoplist']=scheduled_stops
                trip_dict['pd'] = pd
                trip_dict['v'] = bid
                trip_dict['run'] = run
                tripdash[trip_id] = trip_dict

        return tripdash


    # def generate_bunching_leaderboard(self, period, route):
    #
    #     with SQLAlchemyDBConnection() as db:
    #         # generates top 10 list of stops on the route by # of bunching incidents for period
    #         bunching_leaderboard = []
    #         cum_arrival_total = 0
    #         cum_bunch_total = 0
    #         for service in self.route_stop_list:
    #             for stop in service.stops:
    #                 bunch_total = 0
    #                 arrival_total = 0
    #                 report = StopReport(self.route, stop.identity,period)
    #                 for (index, row) in report.arrivals_list_final_df.iterrows():
    #                     arrival_total += 1
    #                     if (row.delta > report.bigbang) and (row.delta <= report.bunching_interval):
    #                         bunch_total += 1
    #                 cum_bunch_total = cum_bunch_total+bunch_total
    #                 cum_arrival_total = cum_arrival_total + arrival_total
    #                 bunching_leaderboard.append((stop.st, bunch_total,stop.identity))
    #         bunching_leaderboard.sort(key=itemgetter(1), reverse=True)
    #         bunching_leaderboard = bunching_leaderboard[:10]
    #
    #         # compute grade passed on pct of all stops on route during period that were bunched
    #         try:
    #             grade_numeric = (cum_bunch_total / cum_arrival_total) * 100
    #             for g in self.grade_descriptions:
    #                 if g['bounds'][0] < grade_numeric <= g['bounds'][1]:
    #                     self.grade = g['grade']
    #                     self.grade_description = g['description']
    #         except:
    #             self.grade = 'N/A'
    #             self.grade_description = 'Unable to determine grade.'
    #             pass
    #
    #         time_created = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    #         bunching_leaderboard_pickle = dict(bunching_leaderboard=bunching_leaderboard, grade=self.grade,
    #                                            grade_numeric=grade_numeric, grade_description=self.grade_description, time_created=time_created)
    #         outfile = ('data/bunching_leaderboard_'+route+'.pickle')
    #         with open(outfile, 'wb') as handle:
    #             pickle.dump(bunching_leaderboard_pickle, handle, protocol=pickle.HIGHEST_PROTOCOL)
    #     return
    #
    #
    # def load_bunching_leaderboard(self,route):
    #         infile = ('data/bunching_leaderboard_'+route+'.pickle')
    #         with open(infile, 'rb') as handle:
    #             b = pickle.load(handle)
    #         return b['bunching_leaderboard'], b['grade'], b['grade_numeric'], b['grade_description'], b['time_created']


class StopReport:

    def __init__(self, source, route, stop, period):
        # apply passed parameters to instance
        self.source = source
        self.route = route
        self.stop = stop
        self.period = period

        # constants
        self.bunching_interval = datetime.timedelta(minutes=3)
        self.bigbang = datetime.timedelta(seconds=0)

        # populate data for webpage
        self.arrivals_list_final_df, self.stop_name = self.get_arrivals(self.route, self.stop, self.period)
        self.hourly_frequency = self.get_hourly_frequency()

        # self.citywide_waypoints_geojson = get_systemwide_geojson(reportcard_routes)
        # self.stop_lnglatlike, self.stop_geojson = self.get_stop_lnglatlike()

    # fetch arrivals into a df
    def get_arrivals(self,route,stop,period):

        with SQLAlchemyDBConnection() as db:
            today_date = datetime.date.today()
            yesterday = datetime.date.today() - datetime.timedelta(1)

            if period == "daily":
                arrivals_here = pd.read_sql(
                                db.session.query(
                                     Trip.rt,
                                     Trip.v,
                                     Trip.pid,
                                     ScheduledStop.trip_id,
                                     ScheduledStop.stop_id,
                                     ScheduledStop.stop_name,
                                     ScheduledStop.arrival_timestamp)
                                .join(ScheduledStop)
                                .filter(Trip.rt == route)
                                .filter(ScheduledStop.stop_id == stop)
                                .filter(ScheduledStop.arrival_timestamp != None)
                                .filter(func.date(ScheduledStop.arrival_timestamp) == today_date)
                                .statement
                                ,db.session.bind)
                print (db.session.query(
                                     Trip.rt,
                                     Trip.v,
                                     Trip.pid,
                                     Trip.trip_id,
                                     ScheduledStop.trip_id,
                                     ScheduledStop.stop_id,
                                     ScheduledStop.stop_name,
                                     ScheduledStop.arrival_timestamp)
                                .join(ScheduledStop)
                                .filter(Trip.rt == route)
                                .filter(ScheduledStop.stop_id == stop)
                                .filter(ScheduledStop.arrival_timestamp != None)
                                .filter(func.date(ScheduledStop.arrival_timestamp) == today_date)
                                .statement)


            elif period == "yesterday":
                arrivals_here = pd.read_sql(
                                db.session.query(
                                    Trip.rt,
                                    Trip.v,
                                    Trip.pid,
                                    Trip.trip_id,
                                    ScheduledStop.trip_id,
                                    ScheduledStop.stop_id,
                                    ScheduledStop.stop_name,
                                    ScheduledStop.arrival_timestamp)
                                .join(ScheduledStop)
                                .filter(Trip.rt == route)
                                .filter(ScheduledStop.stop_id == stop)
                                .filter(ScheduledStop.arrival_timestamp != None)
                                .filter(func.date(ScheduledStop.arrival_timestamp) == yesterday)
                                .statement
                                 ,db.session.bind)

            elif period == "history":
                arrivals_here = pd.read_sql(
                                db.session.query(
                                    Trip.rt,
                                    Trip.v,
                                    Trip.pid,
                                    Trip.trip_id,
                                    ScheduledStop.trip_id,
                                    ScheduledStop.stop_id,
                                    ScheduledStop.stop_name,
                                    ScheduledStop.arrival_timestamp)
                                .join(ScheduledStop)
                                .filter(Trip.rt == route)
                                .filter(ScheduledStop.stop_id == stop)
                                .filter(ScheduledStop.arrival_timestamp != None)
                                .statement
                                ,db.session.bind)

            elif period is True:
                try:
                    int(period)  # check if it digits (e.g. period=20180810)
                    request_date = datetime.datetime.strptime(period, '%Y%m%d')  # make a datetime object
                    arrivals_here = pd.read_sql(
                                db.session.query(
                                    Trip.rt,
                                    Trip.v,
                                    Trip.pid,
                                    Trip.trip_id,
                                    ScheduledStop.trip_id,
                                    ScheduledStop.stop_id,
                                    ScheduledStop.stop_name,
                                    ScheduledStop.arrival_timestamp)
                                .join(ScheduledStop)
                                .filter(Trip.rt == route)
                                .filter(ScheduledStop.stop_id == stop)
                                .filter(ScheduledStop.arrival_timestamp != None)
                                .filter(func.date(ScheduledStop.arrival_timestamp) == request_date)
                                .statement
                                , db.session.bind)

                except ValueError:
                        pass


            # split by vehicle and calculate arrival intervals
            final_approach_dfs = [g for i, g in arrivals_here.groupby(arrivals_here['v'].ne(arrivals_here['v'].shift()).cumsum())] # split final approach history (sorted by timestamp) at each change in vehicle_id outputs a list of dfs per https://stackoverflow.com/questions/41144231/python-how-to-split-pandas-dataframe-into-subsets-based-on-the-value-in-the-fir
            arrivals_list_final_df = pd.DataFrame() # take the last V(ehicle) approach in each df and add it to final list of arrivals
            for final_approach in final_approach_dfs:  # iterate over every final approach
                arrival_insert_df = final_approach.tail(1)  # take the last observation
                arrivals_list_final_df = arrivals_list_final_df.append(arrival_insert_df)  # insert into df
            arrivals_list_final_df['delta']=(arrivals_list_final_df['arrival_timestamp'] - arrivals_list_final_df['arrival_timestamp'].shift(1)).fillna(0) # calc interval between last bus for each row, fill NaNs

            stop_name = arrivals_list_final_df['stop_name'].iloc[0]

            return arrivals_list_final_df, stop_name


            # except:
            #     arrivals_list_final_df = pd.DataFrame(
            #         columns=['rt', 'v', 'pid', 'trip_trip_id', 'stop_trip_id', 'stop_name', 'arrival_timestamp'],
            #         data=['0', '0000', '0', '0000_000_00000000', '0000_000_00000000', 'N/A', datetime.time(0, 1)]
            #     )
            #     stop_name = 'N/A'
            #     self.arrivals_table_time_created = datetime.datetime.now()
            #     return arrivals_list_final_df, stop_name


    def get_hourly_frequency(self):
        results = pd.DataFrame()
        self.arrivals_list_final_df['delta_int'] = self.arrivals_list_final_df['delta'].dt.seconds

        try:

            # results['frequency']= (self.arrivals_list_final_df.delta_int.resample('H').mean())//60
            results = (self.arrivals_list_final_df.groupby(self.arrivals_list_final_df.index.hour).mean())//60
            results = results.rename(columns={'delta_int': 'frequency'})
            results = results.drop(['pkey'], axis=1)
            results['hour'] = results.index

        except TypeError:
            pass

        except AttributeError:
            results = pd.DataFrame()

        return results


