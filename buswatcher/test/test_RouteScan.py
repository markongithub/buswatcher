import datetime
import unittest
from lib import RouteScan
from lib.DataBases import ScheduledStop

class TestRouteScan(unittest.TestCase):

    def test_make_trip_intervals(self):
        self.assertEqual(RouteScan.make_trip_intervals([], [], {}), {})
        scheduled_stops = [
            ScheduledStop(0,0,0,datetime.datetime(2019, 8, 12),100,100,0,0),
            ScheduledStop(0,0,0,datetime.datetime(2019, 8, 12),101,101,1,1),
            ScheduledStop(0,0,0,datetime.datetime(2019, 8, 12),102,102,2,2),
            ScheduledStop(0,0,0,datetime.datetime(2019, 8, 12),103,103,3,3)
            ]
        scheduled_stops[0].arrival_timestamp = datetime.datetime(2019, 8, 12, 22, 30)
        # the second one ([1]) has no arrival timestamp
        scheduled_stops[2].arrival_timestamp = datetime.datetime(2019, 8, 12, 22, 31)
        # the interval of 100,101,102 should be all under 100 in the dict
        calculated_intervals = RouteScan.make_trip_intervals(scheduled_stops, [], {})
        self.assertEqual(list(calculated_intervals.keys()), [100])
        self.assertEqual(len(calculated_intervals[100]), 3)

if __name__ == '__main__':
    unittest.main()
