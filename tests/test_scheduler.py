import unittest
import datetime
import tempfile
import os
import time
from unittest.mock import MagicMock, patch

from alarm_clock.models import Alarm, AlarmState, parse_days
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

class TestDayParser(unittest.TestCase):
    def test_valid_days_parsing(self):
        self.assertEqual(parse_days("mon,wed,fri"), ["Monday", "Wednesday", "Friday"])
        self.assertEqual(parse_days("daily"), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        self.assertEqual(parse_days("weekdays"), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.assertEqual(parse_days("weekends"), ["Saturday", "Sunday"])
        self.assertEqual(parse_days(""), [])
        self.assertEqual(parse_days("once"), [])
        self.assertEqual(parse_days("none"), [])

    def test_invalid_days_parsing(self):
        with self.assertRaises(ValueError):
            parse_days("not-a-day")
        with self.assertRaises(ValueError):
            parse_days("Mon,tue,XYZ")

class TestAlarmModel(unittest.TestCase):
    def test_alarm_initialization(self):
        t = datetime.time(10, 0)
        alarm = Alarm(1, t, "Workout", ["Monday", "Wednesday"], 30)
        self.assertEqual(alarm.id, 1)
        self.assertEqual(alarm.time, t)
        self.assertEqual(alarm.label, "Workout")
        self.assertEqual(alarm.days, ["Monday", "Wednesday"])
        self.assertEqual(alarm.auto_dismiss_sec, 30)
        self.assertEqual(alarm.state, AlarmState.PENDING)
        self.assertIsNone(alarm.snooze_until)
        self.assertEqual(alarm.snoozed_count, 0)

    def test_should_trigger_recurring(self):
        t = datetime.time(8, 30)
        alarm = Alarm(1, t, days=["Monday", "Wednesday"])
        
        # Test match day and match time (2026-06-22 is a Monday)
        now_match = datetime.datetime(2026, 6, 22, 8, 30, 15)
        self.assertTrue(alarm.should_trigger(now_match))
        
        # Test mismatch day (2026-06-23 is a Tuesday)
        now_wrong_day = datetime.datetime(2026, 6, 23, 8, 30, 15)
        self.assertFalse(alarm.should_trigger(now_wrong_day))

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

    def test_json_serialization(self):
        t = datetime.time(12, 30, 45)
        alarm = Alarm(42, t, "Eat Lunch", ["Friday"], 120)
        alarm.snooze(15)
        
        serialized = alarm.to_dict()
        self.assertEqual(serialized["id"], 42)
        self.assertEqual(serialized["time"], "12:30:45")
        self.assertEqual(serialized["label"], "Eat Lunch")
        self.assertEqual(serialized["days"], ["Friday"])
        self.assertEqual(serialized["auto_dismiss_sec"], 120)
        self.assertEqual(serialized["state"], "SNOOZED")
        self.assertIsNotNone(serialized["snooze_until"])
        
        deserialized = Alarm.from_dict(serialized)
        self.assertEqual(deserialized.id, alarm.id)
        self.assertEqual(deserialized.time, alarm.time)
        self.assertEqual(deserialized.label, alarm.label)
        self.assertEqual(deserialized.days, alarm.days)
        self.assertEqual(deserialized.auto_dismiss_sec, alarm.auto_dismiss_sec)
        self.assertEqual(deserialized.state, alarm.state)

class TestAlarmScheduler(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp()
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

    def test_snooze_and_dismiss_scheduler(self):
        alarm = self.scheduler.add_alarm("12:00")
        
        self.scheduler.dismiss_alarm(alarm.id)
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.DISMISSED)
        
        self.scheduler.snooze_alarm(alarm.id, 10)
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.SNOOZED)

    def test_persistence_between_instances(self):
        alarm1 = self.scheduler.add_alarm("15:45", "Test Persistence", ["Monday"], 45)
        self.scheduler.snooze_alarm(alarm1.id, 5)
        
        new_scheduler = AlarmScheduler(storage_path=self.temp_db_path)
        loaded_alarms = new_scheduler.get_all_alarms()
        
        self.assertEqual(len(loaded_alarms), 1)
        loaded = loaded_alarms[0]
        self.assertEqual(loaded.id, alarm1.id)
        self.assertEqual(loaded.days, ["Monday"])
        self.assertEqual(loaded.auto_dismiss_sec, 45)
        self.assertEqual(loaded.state, AlarmState.SNOOZED)

    def test_background_auto_dismiss(self):
        # Create alarm with 1-second auto-dismiss
        alarm = self.scheduler.add_alarm("12:00", "Fast Expiry", auto_dismiss_sec=1)
        
        # Manually trigger ringing
        with self.scheduler._lock:
            self.scheduler._load_from_disk()
            scheduler_alarm = self.scheduler._alarms[alarm.id]
            scheduler_alarm.state = AlarmState.RINGING
            scheduler_alarm.ring_start_time = datetime.datetime.now() - datetime.timedelta(seconds=2)
            self.scheduler._save_to_disk()
            
        # Run background evaluation cycle once manually to simulate scheduler thread logic
        self.scheduler._run_loop_cycle_for_testing()
        
        # Verify it automatically transitioned to DISMISSED
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.DISMISSED)

    def test_background_auto_reset(self):
        # Create recurring alarm
        alarm = self.scheduler.add_alarm("08:30", "Recurring Workout", days=["Monday"])
        
        # Set state to DISMISSED (e.g. user turned it off)
        self.scheduler.dismiss_alarm(alarm.id)
        
        # Run cycle when current time has moved past 08:30 (e.g., system is at 08:31)
        # We patch datetime inside the scheduler's lock block
        with patch('datetime.datetime') as mock_dt:
            # We mock datetime.now() to return 08:31:00 on a Monday
            mock_dt.now.return_value = datetime.datetime(2026, 6, 22, 8, 31, 0)
            self.scheduler._run_loop_cycle_for_testing()
            
        # Verify it automatically transitioned back to PENDING for the next day
        alarms = self.scheduler.get_all_alarms()
        self.assertEqual(alarms[0].state, AlarmState.PENDING)

# Patching _run_loop_cycle_for_testing helper onto AlarmScheduler for direct unit testing
def _run_loop_cycle_for_testing(self):
    now = datetime.datetime.now()
    with self._lock:
        self._load_from_disk()
        any_state_changed = False
        for alarm in self._alarms.values():
            if alarm.state == AlarmState.RINGING:
                if alarm.ring_start_time:
                    elapsed = (now - alarm.ring_start_time).total_seconds()
                    if elapsed >= alarm.auto_dismiss_sec:
                        alarm.dismiss()
                        any_state_changed = True
            elif alarm.state == AlarmState.DISMISSED and alarm.days:
                now_time = now.time()
                if now_time.hour != alarm.time.hour or now_time.minute != alarm.time.minute:
                    alarm.reset()
                    any_state_changed = True
            elif alarm.should_trigger(now):
                alarm.state = AlarmState.RINGING
                alarm.ring_start_time = now
                any_state_changed = True
        if any_state_changed:
            self._save_to_disk()

AlarmScheduler._run_loop_cycle_for_testing = _run_loop_cycle_for_testing

if __name__ == "__main__":
    unittest.main()
