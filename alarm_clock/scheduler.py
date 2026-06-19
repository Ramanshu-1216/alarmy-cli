import datetime
import threading
import time
from typing import Dict, List, Optional, Callable
from alarm_clock.models import Alarm, AlarmState
from alarm_clock.audio import AlarmSoundController

def parse_time(time_str: str) -> datetime.time:
    """
    Parses a time string into a datetime.time object.
    Supports formats: HH:MM, HH:MM:SS, H:MM, and 12-hour formats like "02:30 PM".
    """
    time_str = time_str.strip()
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%H.%M"):
        try:
            return datetime.datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: '{time_str}'. Please use HH:MM (e.g. 14:30) or HH:MM PM.")

class AlarmScheduler:
    """
    Thread-safe manager for scheduling, monitoring, and triggering alarms.
    Runs a background thread to check alarm states and trigger audio alerts.
    """
    def __init__(self, on_trigger_callback: Optional[Callable[[Alarm], None]] = None):
        self._alarms: Dict[int, Alarm] = {}
        self._next_id = 1
        self._lock = threading.Lock()
        
        self._sound_controller = AlarmSoundController()
        self._on_trigger_callback = on_trigger_callback
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def add_alarm(self, time_str: str, label: str = "Alarm") -> Alarm:
        """
        Parses time string, creates an alarm, and adds it thread-safely.
        """
        time_obj = parse_time(time_str)
        with self._lock:
            alarm_id = self._next_id
            self._next_id += 1
            alarm = Alarm(alarm_id, time_obj, label)
            self._alarms[alarm_id] = alarm
            return alarm

    def remove_alarm(self, alarm_id: int) -> bool:
        """
        Removes an alarm by ID. Returns True if found and removed.
        """
        with self._lock:
            if alarm_id in self._alarms:
                # If the deleted alarm was ringing, the run loop will automatically turn off sound
                del self._alarms[alarm_id]
                return True
            return False

    def snooze_alarm(self, alarm_id: int, minutes: int = 5) -> Optional[Alarm]:
        """
        Snoozes a ringing or pending alarm. Returns the Alarm if found.
        """
        with self._lock:
            alarm = self._alarms.get(alarm_id)
            if alarm:
                alarm.snooze(minutes)
                return alarm
            return None

    def dismiss_alarm(self, alarm_id: int) -> Optional[Alarm]:
        """
        Dismisses a ringing or snoozed alarm. Returns the Alarm if found.
        """
        with self._lock:
            alarm = self._alarms.get(alarm_id)
            if alarm:
                alarm.dismiss()
                return alarm
            return None

    def get_all_alarms(self) -> List[Alarm]:
        """
        Returns a copy of all alarms sorted by scheduled time.
        """
        with self._lock:
            return sorted(list(self._alarms.values()), key=lambda a: a.time)

    def start(self) -> None:
        """
        Starts the background scheduler thread.
        """
        if self._thread and self._thread.is_alive():
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="SchedulerThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """
        Stops the background scheduler and sound controller.
        """
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        self._sound_controller.stop()

    def _run(self) -> None:
        """
        Background monitoring loop that runs every second to check if any alarms need to ring.
        """
        last_minute = -1
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            
            with self._lock:
                for alarm in self._alarms.values():
                    # 1. Check if alarm should ring (handles PENDING and SNOOZED triggers)
                    if alarm.should_trigger(now):
                        # For PENDING state alarms, make sure we only trigger once per minute to avoid re-triggering
                        if alarm.state == AlarmState.PENDING:
                            # To prevent immediate re-triggering within the same minute,
                            # we can mark it as RINGING. But we must be careful:
                            # If it triggers, it enters RINGING. If the user dismisses it in the SAME minute,
                            # we don't want it to re-trigger.
                            # So a dismissed alarm should not trigger again on the same day unless reset.
                            alarm.state = AlarmState.RINGING
                            if self._on_trigger_callback:
                                threading.Thread(
                                    target=self._on_trigger_callback, 
                                    args=(alarm,), 
                                    daemon=True
                                ).start()
                        elif alarm.state == AlarmState.SNOOZED:
                            alarm.state = AlarmState.RINGING
                            if self._on_trigger_callback:
                                threading.Thread(
                                    target=self._on_trigger_callback, 
                                    args=(alarm,), 
                                    daemon=True
                                ).start()
            
            # 2. Manage the audio alarm state
            # If any alarm is in RINGING state, trigger the buzzer
            ringing_alarms = [a for a in self.get_all_alarms() if a.state == AlarmState.RINGING]
            if ringing_alarms:
                self._sound_controller.start()
            else:
                self._sound_controller.stop()

            # Sleep in short increments to remain responsive to shutdown signals
            for _ in range(10):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)
