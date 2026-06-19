from enum import Enum, auto
import datetime
from typing import Optional

class AlarmState(Enum):
    PENDING = auto()
    RINGING = auto()
    SNOOZED = auto()
    DISMISSED = auto()

class Alarm:
    def __init__(self, alarm_id: int, time_obj: datetime.time, label: str = "Alarm"):
        self.id = alarm_id
        self.time = time_obj  # datetime.time object (HH:MM)
        self.label = label
        self.state = AlarmState.PENDING
        self.snooze_until: Optional[datetime.datetime] = None
        self.snoozed_count: int = 0

    def should_trigger(self, now: datetime.datetime) -> bool:
        """
        Determines whether the alarm should transition to RINGING.
        - PENDING: Triggers if the current time matches/passed the scheduled time on the current day.
        - SNOOZED: Triggers if current time has passed snooze_until.
        """
        if self.state == AlarmState.PENDING:
            # Alarm triggers when current hour/minute matches the scheduled time
            # and it is within the same minute. We check if the alarm time is <= now's time.
            # To avoid firing multiple times in the same minute or missing it,
            # we compare the current time's HH:MM directly.
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
        return self.snooze_until

    def dismiss(self) -> None:
        """
        Dismisses the alarm.
        """
        self.state = AlarmState.DISMISSED
        self.snooze_until = None

    def reset(self) -> None:
        """
        Resets a dismissed or triggered alarm back to PENDING.
        """
        self.state = AlarmState.PENDING
        self.snooze_until = None
        self.snoozed_count = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "time": self.time.strftime("%H:%M:%S"),
            "label": self.label,
            "state": self.state.name,
            "snooze_until": self.snooze_until.isoformat() if self.snooze_until else None,
            "snoozed_count": self.snoozed_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Alarm':
        time_parts = [int(p) for p in data["time"].split(":")]
        if len(time_parts) == 3:
            time_obj = datetime.time(time_parts[0], time_parts[1], time_parts[2])
        else:
            time_obj = datetime.time(time_parts[0], time_parts[1])
            
        alarm = cls(data["id"], time_obj, data["label"])
        alarm.state = AlarmState[data["state"]]
        
        snooze_until_str = data.get("snooze_until")
        if snooze_until_str:
            alarm.snooze_until = datetime.datetime.fromisoformat(snooze_until_str)
        else:
            alarm.snooze_until = None
            
        alarm.snoozed_count = data.get("snoozed_count", 0)
        return alarm

    def __str__(self) -> str:
        snooze_info = f" (Snoozed until {self.snooze_until.strftime('%H:%M:%S')})" if self.state == AlarmState.SNOOZED and self.snooze_until else ""
        return f"[{self.id}] {self.time.strftime('%H:%M')} - '{self.label}' | State: {self.state.name}{snooze_info}"

