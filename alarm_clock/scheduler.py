import datetime
import threading
import time
import os
import json
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
    Saves and synchronizes state via a local JSON file to support multi-process CLI usage.
    """
    def __init__(self, on_trigger_callback: Optional[Callable[[Alarm], None]] = None, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.expanduser("~/.cli_alarms.json")
        self._alarms: Dict[int, Alarm] = {}
        self._next_id = 1
        self._lock = threading.Lock()
        
        self._sound_controller = AlarmSoundController()
        self._on_trigger_callback = on_trigger_callback
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # Load initial state
        with self._lock:
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        """
        Loads alarms from the JSON file. Assumes lock is held.
        """
        if not os.path.exists(self.storage_path):
            self._alarms = {}
            self._next_id = 1
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            
            alarms = {}
            max_id = 0
            for item in data:
                alarm = Alarm.from_dict(item)
                alarms[alarm.id] = alarm
                if alarm.id > max_id:
                    max_id = alarm.id
            self._alarms = alarms
            self._next_id = max_id + 1
        except Exception:
            # Fallback gracefully if file is empty or corrupted
            self._alarms = {}
            self._next_id = 1

    def _save_to_disk(self) -> None:
        """
        Saves alarms atomically to the JSON file using a temp file. Assumes lock is held.
        """
        temp_path = self.storage_path + ".tmp"
        try:
            dir_name = os.path.dirname(self.storage_path)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
                
            with open(temp_path, "w") as f:
                data = [alarm.to_dict() for alarm in self._alarms.values()]
                json.dump(data, f, indent=4)
            
            # Atomic swap
            os.replace(temp_path, self.storage_path)
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
            raise e

    def add_alarm(self, time_str: str, label: str = "Alarm") -> Alarm:
        """
        Parses time string, creates an alarm, and saves it thread-safely.
        """
        time_obj = parse_time(time_str)
        with self._lock:
            self._load_from_disk()
            alarm_id = self._next_id
            self._next_id += 1
            alarm = Alarm(alarm_id, time_obj, label)
            self._alarms[alarm_id] = alarm
            self._save_to_disk()
            return alarm

    def remove_alarm(self, alarm_id: int) -> bool:
        """
        Removes an alarm by ID. Returns True if found and removed.
        """
        with self._lock:
            self._load_from_disk()
            if alarm_id in self._alarms:
                del self._alarms[alarm_id]
                self._save_to_disk()
                return True
            return False

    def snooze_alarm(self, alarm_id: int, minutes: int = 5) -> Optional[Alarm]:
        """
        Snoozes a ringing or pending alarm.
        """
        with self._lock:
            self._load_from_disk()
            alarm = self._alarms.get(alarm_id)
            if alarm:
                alarm.snooze(minutes)
                self._save_to_disk()
                return alarm
            return None

    def dismiss_alarm(self, alarm_id: int) -> Optional[Alarm]:
        """
        Dismisses a ringing or snoozed alarm.
        """
        with self._lock:
            self._load_from_disk()
            alarm = self._alarms.get(alarm_id)
            if alarm:
                alarm.dismiss()
                self._save_to_disk()
                return alarm
            return None

    def get_all_alarms(self) -> List[Alarm]:
        """
        Returns a copy of all alarms loaded from disk and sorted by time.
        """
        with self._lock:
            self._load_from_disk()
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
        Reloads database state from disk each cycle to sync with the single-command CLI.
        """
        while not self._stop_event.is_set():
            now = datetime.datetime.now()
            
            with self._lock:
                self._load_from_disk()
                
                any_state_changed = False
                for alarm in self._alarms.values():
                    if alarm.should_trigger(now):
                        if alarm.state == AlarmState.PENDING:
                            alarm.state = AlarmState.RINGING
                            any_state_changed = True
                            if self._on_trigger_callback:
                                threading.Thread(
                                    target=self._on_trigger_callback, 
                                    args=(alarm,), 
                                    daemon=True
                                ).start()
                        elif alarm.state == AlarmState.SNOOZED:
                            alarm.state = AlarmState.RINGING
                            any_state_changed = True
                            if self._on_trigger_callback:
                                threading.Thread(
                                    target=self._on_trigger_callback, 
                                    args=(alarm,), 
                                    daemon=True
                                ).start()
                
                if any_state_changed:
                    self._save_to_disk()
            
            # Manage sound controller state
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
