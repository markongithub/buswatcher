# -*- coding: utf-8 -*-
import datetime, sys
from sqlalchemy import inspect, create_engine, Date, Column, Integer, DateTime, Float, String, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from . import BusAPI

#####################################################
# base
#####################################################
Base = declarative_base()


# from https://medium.com/@ramojol/python-context-managers-and-the-with-statement-8f53d4d9f87
class SQLAlchemyDBConnection(object):
    def __init__(self):
        self.connection_string = 'mysql+pymysql://buswatcher:njtransit@localhost/buses'
        # self.connection_string = 'postgresql://buswatcher:njtransit@localhost/buses'
        # self.connection_string = 'sqlite:///jc_buswatcher.db'  # WORKS

        self.session = None

    def __enter__(self):
        engine = create_engine(self.connection_string)
        Session = sessionmaker()
        self.session = Session(bind=engine)
        Base.metadata.create_all(bind=engine)
        return self

    def __relax__(self):
        self.session.execute('SET FOREIGN_KEY_CHECKS = 0;')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.execute('SET FOREIGN_KEY_CHECKS = 1;')
        self.session.close()


#####################################################
# CLASS Trip
#####################################################

class Trip(Base):

    def __init__(self, source, route, v, run, pid):
        self.source = source
        self.rt = route
        self.v = v
        self.run = run
        self.pid = pid
        self.date = datetime.datetime.today().strftime('%Y%m%d')
        self.trip_id=('{v}_{run}_{date}').format(v=v,run=run,date=self.date)

    __tablename__ = 'trip_log'
    __table_args__ = {'extend_existing': True}

    pkey = Column(Integer(), primary_key=True)
    trip_id = Column(String(127), index=True, unique=True)
    source = Column(String(8))
    rt = Column(Integer())
    v = Column(Integer())
    run = Column(String(8))
    pid = Column(Integer())
    date = Column(Date())
    coordinate_bundle = Column(Text())

    # relationships
    children_ScheduledStops = relationship("ScheduledStop", backref='trip_log')
    children_BusPositions = relationship("BusPosition", backref='trip_log')

    # create a corresponding set of ScheduledStop records for each new Trip
    # and populate the self.stoplist and self.coordinates_bundle
    def populate_stoplist(self):
        with SQLAlchemyDBConnection() as db:
            self.db = db
            self.stop_list = []
            routes, self.coordinates_bundle = BusAPI.parse_xml_getRoutePoints(BusAPI.get_xml_data(self.source, 'routes', route=self.rt))
            self.routename=routes[0].nm
            for path in routes[0].paths:
                if path.id == self.pid:
                    for point in path.points:
                        if isinstance(point, BusAPI.Route.Stop):
                            this_stop = ScheduledStop(self.trip_id,self.v,self.run,self.date,point.identity,point.st,point.lat,point.lon)
                            self.stop_list.append((point.identity,point.st))
                            for stop in self.stop_list:
                                self.db.session.add(this_stop)
                else:
                    pass
            self.db.session.commit()


################################################################
# CLASS ScheduledStop
################################################################

class ScheduledStop(Base):

    def __init__(self, trip_id,v,run,date,stop_id,stop_name,lat,lon):
        self.trip_id = trip_id
        self.v = v
        self.run = run
        self.date = date
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.lat = lat
        self.lon = lon

    __tablename__ = 'scheduledstop_log'
    __table_args__ = {'extend_existing': True}

    pkey = Column(Integer(), primary_key=True)
    run = Column(String(8))
    v = Column(Integer())
    date = Column(Date())
    stop_id = Column(Integer(), index=True)
    stop_name = Column(String(255))
    lat = Column(Float())
    lon = Column(Float())
    arrival_timestamp = Column(DateTime(), index=True)

    # relationships
    trip_id = Column(String(127), ForeignKey('trip_log.trip_id'))
    parent_Trip = relationship("Trip",backref='scheduledstop_log')


#####################################################
# CLASS BusPosition
#####################################################

class BusPosition(Base):

    __tablename__ ='position_log'
    __table_args__ = {'extend_existing': True}

    pkey = Column(Integer(), primary_key=True)
    lat = Column(Float)
    lon = Column(Float)
    cars = Column(String(20))
    consist = Column(String(20))
    d = Column(String(20))
    dip = Column(String(20))
    dn = Column(String(20))
    fs = Column(String(127))
    id = Column(String(20))
    # id = Column(String(20), index=True)
    m = Column(String(20))
    op = Column(String(20))
    pd = Column(String(255))
    pdrtpifeedname = Column(String(255))
    pid = Column(String(20))
    rt = Column(String(20))
    rtrtpifeedname = Column(String(20))
    rtdd = Column(String(20))
    rtpifeedname = Column(String(20))
    run = Column(String(8))
    wid1 = Column(String(20))
    wid2 = Column(String(20))
    timestamp = Column(DateTime())

    distance_to_stop = Column(Float())
    arrival_flag = Column(Boolean())

    # relationships
    trip_id = Column(String(127), ForeignKey('trip_log.trip_id'), index=True)
    stop_id = Column(Integer(), ForeignKey('scheduledstop_log.stop_id'), index=True)
    parent_Trip = relationship("Trip",backref='position_log')
    parent_ScheduledStop = relationship("ScheduledStop",backref='position_log')
