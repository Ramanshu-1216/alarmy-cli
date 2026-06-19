import unittest
import datetime
import tempfile
import os
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
        
        now_match = datetime.datetime(2026, 6, 19, 8, 30, 15)
        self.assertTrue(alarm.should_trigger(now_match))
        
        now_mismatch = datetime.datetime(2026, 6, 19, 8, 29, 59)
        self.assertFalse(alarm.should_trigger(now_mismatch))

    def test_snooze_and_trigger(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t)
        
        snooze_time = alarm.snooze(5)
        self.assertEqual(alarm.state, AlarmState.SNOOZED)
        self.assertEqual(alarm.snoozed_count, 1)
        self.assertIsNotNone(alarm.snooze_until)
        
        now_before = snooze_time - datetime.timedelta(seconds=1)
        self.assertFalse(alarm.should_trigger(now_before))
        
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

    def test_json_serialization(self):
        t = datetime.time(12, 30, 45)
        alarm = Alarm(42, t, "Eat Lunch")
        alarm.snooze(15)
        
        serialized = alarm.to_dict()
        self.assertEqual(serialized["id"], 42)
        self.assertEqual(serialized["time"], "12:30:45")
        self.assertEqual(serialized["label"], "Eat Lunch")
        self.assertEqual(serialized["state"], "SNOOZED")
        self.assertIsNotNone(serialized["snooze_until"])
        self.assertEqual(serialized["snoozed_count"], 1)

        deserialized = Alarm.from_dict(serialized)
        self.assertEqual(deserialized.id, alarm.id)
        self.assertEqual(deserialized.time, alarm.time)
        self.assertEqual(deserialized.label, alarm.label)
        self.assertEqual(deserialized.state, alarm.state)
        self.assertEqual(deserialized.snooze_until, alarm.snooze_until)
        self.assertEqual(deserialized.snoozed_count, alarm.snoozed_count)

class TestAlarmScheduler(unittest.TestCase):
    def setUp(self):
        # Create a unique temporary file path for scheduler persistence tests
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
        # Close the file descriptor, scheduler will manage open/close
        os.close(self.temp_db_fd)
        
        self.scheduler = AlarmScheduler(storage_path=self.temp_db_path)

    def tearDown(self):
        self.scheduler.stop()
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_add_and_get_alarms(self):
        alarm1 = self.scheduler.add_alarm("10:00", "Morning Alarm")
        alarm2 = self.scheduler.add_alarm("08:00", "Early Alarm")
        
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(len(alarms), 2)
        self.assertEqual(alarms[0].id, alarm2.id)
        self.assertEqual(alarms[1].id, alarm1.id)

    def test_remove_alarm(self):
        alarm = self.scheduler.add_alarm("09:00")
        self.assertEqual(len(self.scheduler.get_all_alarms()), 1)
        
        success = self.scheduler.remove_alarm(alarm.id)
        self.assertTrue(success)
        self.assertEqual(len(self.scheduler.get_all_alarms()), 0)
        
        fail = self.scheduler.remove_alarm(999)
        self.assertFalse(fail)

    def test_snooze_and_dismiss_scheduler(self):
        alarm = self.scheduler.add_alarm("12:00")
        
        self.scheduler.dismiss_alarm(alarm.id)
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.DISMISSED)
        
        self.scheduler.snooze_alarm(alarm.id, 10)
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.SNOOZED)

    def test_persistence_between_instances(self):
        # Add alarm to self.scheduler (points to temp file)
        alarm1 = self.scheduler.add_alarm("15:45", "Test Persistence")
        self.scheduler.snooze_alarm(alarm1.id, 5)
        
        # Instantiate a new scheduler pointing to same file path
        new_scheduler = AlarmScheduler(storage_path=self.temp_db_path)
        loaded_alarms = new_scheduler.get_all_alarms()
        
        # Verify the saved state is correctly reloaded
        self.assertEqual(len(loaded_alarms), 1)
        loaded = loaded_alarms[0]
        self.assertEqual(loaded.id, alarm1.id)
        self.assertEqual(loaded.time, alarm1.time)
        self.assertEqual(loaded.label, alarm1.label)
        self.assertEqual(loaded.state, AlarmState.SNOOZED)
        self.assertIsNotNone(loaded.snooze_until)

if __name__ == "__main__":
    unittest.main()
