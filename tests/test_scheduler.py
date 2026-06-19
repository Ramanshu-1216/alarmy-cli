import unittest
import datetime
from unittest.mock import MagicMock, patch

from alarm_clock.models import Alarm, AlarmState
from alarm_clock.scheduler import AlarmScheduler, parse_time

class TestTimeParser(unittest.TestCase):
    def test_valid_formats(self):
        self.assertEqual(parse_time("14:30"), datetime.time(14, 30))
        self.assertEqual(parse_time("09:15:45"), datetime.time(9, 15, 45))
        self.assertEqual(parse_time("03:45 PM"), datetime.time(15, 45))
        self.assertEqual(parse_time("12:00 AM"), datetime.time(0, 0))
        self.assertEqual(parse_time("  18:05  "), datetime.time(18, 5))
        self.assertEqual(parse_time("21.30"), datetime.time(21, 30))

    def test_invalid_formats(self):
        with self.assertRaises(ValueError):
            parse_time("25:00")
        with self.assertRaises(ValueError):
            parse_time("14:61")
        with self.assertRaises(ValueError):
            parse_time("not-a-time")
        with self.assertRaises(ValueError):
            parse_time("12:30 XM")

class TestAlarmModel(unittest.TestCase):
    def test_alarm_initialization(self):
        t = datetime.time(10, 0)
        alarm = Alarm(1, t, "Workout")
        self.assertEqual(alarm.id, 1)
        self.assertEqual(alarm.time, t)
        self.assertEqual(alarm.label, "Workout")
        self.assertEqual(alarm.state, AlarmState.PENDING)
        self.assertIsNone(alarm.snooze_until)
        self.assertEqual(alarm.snoozed_count, 0)

    def test_should_trigger_pending(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t)
        
        # Test exact match
        now_match = datetime.datetime(2026, 6, 19, 8, 30, 15)
        self.assertTrue(alarm.should_trigger(now_match))
        
        # Test mismatch
        now_mismatch = datetime.datetime(2026, 6, 19, 8, 29, 59)
        self.assertFalse(alarm.should_trigger(now_mismatch))

    def test_snooze_and_trigger(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t)
        
        # Snooze for 5 minutes
        snooze_time = alarm.snooze(5)
        self.assertEqual(alarm.state, AlarmState.SNOOZED)
        self.assertEqual(alarm.snoozed_count, 1)
        self.assertIsNotNone(alarm.snooze_until)
        
        # Before snooze elapsed
        now_before = snooze_time - datetime.timedelta(seconds=1)
        self.assertFalse(alarm.should_trigger(now_before))
        
        # After snooze elapsed
        now_after = snooze_time + datetime.timedelta(seconds=1)
        self.assertTrue(alarm.should_trigger(now_after))

    def test_dismiss(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t)
        alarm.snooze(5)
        alarm.dismiss()
        self.assertEqual(alarm.state, AlarmState.DISMISSED)
        self.assertIsNone(alarm.snooze_until)

    def test_reset(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t)
        alarm.snooze(5)
        alarm.reset()
        self.assertEqual(alarm.state, AlarmState.PENDING)
        self.assertIsNone(alarm.snooze_until)
        self.assertEqual(alarm.snoozed_count, 0)

class TestAlarmScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = AlarmScheduler()

    def tearDown(self):
        self.scheduler.stop()

    def test_add_and_get_alarms(self):
        alarm1 = self.scheduler.add_alarm("10:00", "Morning Alarm")
        alarm2 = self.scheduler.add_alarm("08:00", "Early Alarm")
        
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(len(alarms), 2)
        # Should be sorted by time (08:00 first, then 10:00)
        self.assertEqual(alarms[0].id, alarm2.id)
        self.assertEqual(alarms[1].id, alarm1.id)

    def test_remove_alarm(self):
        alarm = self.scheduler.add_alarm("09:00")
        self.assertEqual(len(self.scheduler.get_all_alarms()), 1)
        
        success = self.scheduler.remove_alarm(alarm.id)
        self.assertTrue(success)
        self.assertEqual(len(self.scheduler.get_all_alarms()), 0)
        
        # Remove non-existent
        fail = self.scheduler.remove_alarm(999)
        self.assertFalse(fail)

    def test_snooze_and_dismiss_scheduler(self):
        alarm = self.scheduler.add_alarm("12:00")
        
        # Test dismiss
        self.scheduler.dismiss_alarm(alarm.id)
        self.assertEqual(alarm.state, AlarmState.DISMISSED)
        
        # Test snooze
        self.scheduler.snooze_alarm(alarm.id, 10)
        self.assertEqual(alarm.state, AlarmState.SNOOZED)

if __name__ == "__main__":
    unittest.main()
