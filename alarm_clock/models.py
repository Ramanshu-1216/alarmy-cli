from enum import Enum, auto
import datetime
from typing import Optional, List

class AlarmState(Enum):
    PENDING = auto()
    RINGING = auto()
    SNOOZED = auto()
    DISMISSED = auto()

DAYS_MAP = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday"
}

def parse_days(days_str: str) -> List[str]:
    """
    Parses a string representing days into canonical day names.
    Supports comma-separated values, "daily", "weekdays", "weekends".
    Returns an empty list for one-time alarms.
    """
    days_str = days_str.lower().strip()
    if not days_str or days_str in ("none", "once", "one-time"):
        return []
    
    if days_str in ("daily", "all", "everyday"):
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    elif days_str in ("weekday", "weekdays", "workdays"):
        return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    elif days_str in ("weekend", "weekends"):
        return ["Saturday", "Sunday"]
        
    parts = [p.strip() for p in days_str.split(",") if p.strip()]
    result = []
    for p in parts:
        if p in DAYS_MAP:
            day_name = DAYS_MAP[p]
            if day_name not in result:
                result.append(day_name)
        else:
            raise ValueError(f"Unknown day: '{p}'. Use short formats like Mon, Tue or full names.")
    return result

class Alarm:
    def __init__(self, alarm_id: int, time_obj: datetime.time, label: str = "Alarm", days: Optional[List[str]] = None, auto_dismiss_sec: int = 60):
        self.id = alarm_id
        self.time = time_obj  # datetime.time object (HH:MM)
        self.label = label
        self.days = days or []  # List of canonical day names, empty for one-time
        self.auto_dismiss_sec = auto_dismiss_sec
        self.state = AlarmState.PENDING
        self.snooze_until: Optional[datetime.datetime] = None
        self.snoozed_count: int = 0
        self.ring_start_time: Optional[datetime.datetime] = None

    def should_trigger(self, now: datetime.datetime) -> bool:
        """
        Determines whether the alarm should transition to RINGING.
        - PENDING: Triggers if time and day of week match.
        - SNOOZED: Triggers if snooze period elapsed.
        """
        if self.state == AlarmState.PENDING:
            if self.days:
                current_day = now.strftime("%A")
                if current_day not in self.days:
                    return False
            
            now_time = now.time()
            return now_time.hour == self.time.hour and now_time.minute == self.time.minute
        
        elif self.state == AlarmState.SNOOZED:
            if self.snooze_until is not None:
                return now >= self.snooze_until
                
        return False

    def snooze(self, minutes: int = 5) -> datetime.datetime:
        """
        Transitions the alarm to SNOOZED state and calculates the target wakeup time.
        """
        now = datetime.datetime.now()
        self.state = AlarmState.SNOOZED
        self.snooze_until = now + datetime.timedelta(minutes=minutes)
        self.snoozed_count += 1
        self.ring_start_time = None
        return self.snooze_until

    def dismiss(self) -> None:
        """
        Dismisses the alarm.
        """
        self.state = AlarmState.DISMISSED
        self.snooze_until = None
        self.ring_start_time = None

    def reset(self) -> None:
        """
        Resets an alarm back to PENDING.
        """
        self.state = AlarmState.PENDING
        self.snooze_until = None
        self.snoozed_count = 0
        self.ring_start_time = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "time": self.time.strftime("%H:%M:%S"),
            "label": self.label,
            "days": self.days,
            "auto_dismiss_sec": self.auto_dismiss_sec,
            "state": self.state.name,
            "snooze_until": self.snooze_until.isoformat() if self.snooze_until else None,
            "snoozed_count": self.snoozed_count,
            "ring_start_time": self.ring_start_time.isoformat() if self.ring_start_time else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Alarm':
        time_parts = [int(p) for p in data["time"].split(":")]
        if len(time_parts) == 3:
            time_obj = datetime.time(time_parts[0], time_parts[1], time_parts[2])
        else:
            time_obj = datetime.time(time_parts[0], time_parts[1])
            
        alarm = cls(
            data["id"], 
            time_obj, 
            data["label"], 
            data.get("days", []), 
            data.get("auto_dismiss_sec", 60)
        )
        alarm.state = AlarmState[data["state"]]
        
        snooze_until_str = data.get("snooze_until")
        if snooze_until_str:
            alarm.snooze_until = datetime.datetime.fromisoformat(snooze_until_str)
        else:
            alarm.snooze_until = None
            
        alarm.snoozed_count = data.get("snoozed_count", 0)
        
        ring_start_str = data.get("ring_start_time")
        if ring_start_str:
            alarm.ring_start_time = datetime.datetime.fromisoformat(ring_start_str)
        else:
            alarm.ring_start_time = None
            
        return alarm

    def __str__(self) -> str:
        snooze_info = f" (Snoozed until {self.snooze_until.strftime('%H:%M:%S')})" if self.state == AlarmState.SNOOZED and self.snooze_until else ""
        days_info = f" [Days: {','.join(self.days)}]" if self.days else " [Once]"
        return f"[{self.id}] {self.time.strftime('%H:%M')} - '{self.label}'{days_info} | State: {self.state.name}{snooze_info}"
