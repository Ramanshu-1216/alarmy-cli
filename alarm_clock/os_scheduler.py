import subprocess
import sys
import platform
import datetime
from typing import List

def schedule_alarm_task(alarm_id: int, time_obj: datetime.time, days: List[str] = None) -> None:
    """
    Schedules an OS-level task to execute the CLI 'ring' command when the alarm is due.
    On Windows, it uses 'schtasks' with a fallback mechanism for regional date formats.
    On Linux, it updates the user's crontab.
    """
    system = platform.system()
    python_bin = sys.executable
    
    # Calculate target datetime for one-time alarm
    now = datetime.datetime.now()
    alarm_dt = datetime.datetime.combine(now.date(), time_obj)
    if alarm_dt <= now:
        alarm_dt += datetime.timedelta(days=1)
        
    time_str = alarm_dt.strftime("%H:%M")
    
    if system == "Windows":
        task_name = f"AlarmClock_Alarm_{alarm_id}"
        tr_cmd = f'"{python_bin}" -m alarm_clock.cli ring {alarm_id}'
        
        if days:
            day_codes = {
                "Monday": "MON", "Tuesday": "TUE", "Wednesday": "WED",
                "Thursday": "THU", "Friday": "FRI", "Saturday": "SAT", "Sunday": "SUN"
            }
            windows_days = ",".join([day_codes[d] for d in days if d in day_codes])
            cmd = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc weekly /d {windows_days} /st {time_str} /f'
            try:
                subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception:
                pass
        else:
            # One-time schedule with dual-format fallback
            # Try International DD/MM/YYYY format first
            date_str_1 = alarm_dt.strftime("%d/%m/%Y")
            cmd_1 = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc once /st {time_str} /sd {date_str_1} /f'
            res = subprocess.run(cmd_1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if res.returncode != 0:
                # Fall back to US MM/DD/YYYY format
                date_str_2 = alarm_dt.strftime("%m/%d/%Y")
                cmd_2 = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc once /st {time_str} /sd {date_str_2} /f'
                try:
                    subprocess.run(cmd_2, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    pass
            
    elif system == "Linux":
        cron_comment = f"# AlarmClock ID {alarm_id}"
        python_cmd = f"{python_bin} -m alarm_clock.cli ring {alarm_id}"
        
        if days:
            day_nums = {
                "Sunday": "0", "Monday": "1", "Tuesday": "2", "Wednesday": "3",
                "Thursday": "4", "Friday": "5", "Saturday": "6"
            }
            cron_days = ",".join([day_nums[d] for d in days if d in day_nums])
            cron_line = f"{time_obj.minute} {time_obj.hour} * * {cron_days} {python_cmd} {cron_comment}"
        else:
            cron_line = f"{alarm_dt.minute} {alarm_dt.hour} {alarm_dt.day} {alarm_dt.month} * {python_cmd} {cron_comment}"
            
        try:
            current_cron = ""
            try:
                res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    current_cron = res.stdout
            except Exception:
                pass
                
            lines = current_cron.splitlines()
            new_lines = [line for line in lines if cron_comment not in line and python_cmd not in line]
            new_lines.append(cron_line)
            new_cron = "\n".join(new_lines) + "\n"
            
            subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass

def cancel_alarm_task(alarm_id: int) -> None:
    """
    Deletes the OS-scheduled task/cron job for a given alarm ID.
    Also removes any snooze task for this alarm.
    """
    system = platform.system()
    cancel_snooze_task(alarm_id)
    
    if system == "Windows":
        task_name = f"AlarmClock_Alarm_{alarm_id}"
        cmd = f'schtasks /delete /tn "{task_name}" /f'
        try:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
    elif system == "Linux":
        cron_comment = f"# AlarmClock ID {alarm_id}"
        try:
            current_cron = ""
            res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                current_cron = res.stdout
                
            lines = current_cron.splitlines()
            new_lines = [line for line in lines if cron_comment not in line]
            new_cron = "\n".join(new_lines) + "\n"
            
            subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass

def schedule_snooze_task(alarm_id: int, snooze_until: datetime.datetime) -> None:
    """
    Schedules a one-off temporary task to sound the alarm again when the snooze duration expires.
    """
    system = platform.system()
    python_bin = sys.executable
    time_str = snooze_until.strftime("%H:%M")
    task_name = f"AlarmClock_Alarm_{alarm_id}_Snooze"
    tr_cmd = f'"{python_bin}" -m alarm_clock.cli ring {alarm_id}'
    
    if system == "Windows":
        # Try International DD/MM/YYYY first
        date_str_1 = snooze_until.strftime("%d/%m/%Y")
        cmd_1 = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc once /st {time_str} /sd {date_str_1} /f'
        res = subprocess.run(cmd_1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if res.returncode != 0:
            # Fall back to US MM/DD/YYYY
            date_str_2 = snooze_until.strftime("%m/%d/%Y")
            cmd_2 = f'schtasks /create /tn "{task_name}" /tr "{tr_cmd}" /sc once /st {time_str} /sd {date_str_2} /f'
            try:
                subprocess.run(cmd_2, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception:
                pass
                
    elif system == "Linux":
        cron_comment = f"# AlarmClock ID {alarm_id} Snooze"
        cron_line = f"{snooze_until.minute} {snooze_until.hour} {snooze_until.day} {snooze_until.month} * {tr_cmd} {cron_comment}"
        try:
            current_cron = ""
            try:
                res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    current_cron = res.stdout
            except Exception:
                pass
            lines = current_cron.splitlines()
            new_lines = [line for line in lines if cron_comment not in line and tr_cmd not in line]
            new_lines.append(cron_line)
            new_cron = "\n".join(new_lines) + "\n"
            subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass

def cancel_snooze_task(alarm_id: int) -> None:
    """
    Cancels any active snooze task scheduled for this alarm.
    """
    system = platform.system()
    if system == "Windows":
        task_name = f"AlarmClock_Alarm_{alarm_id}_Snooze"
        cmd = f'schtasks /delete /tn "{task_name}" /f'
        try:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
    elif system == "Linux":
        cron_comment = f"# AlarmClock ID {alarm_id} Snooze"
        try:
            current_cron = ""
            res = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0:
                current_cron = res.stdout
            lines = current_cron.splitlines()
            new_lines = [line for line in lines if cron_comment not in line]
            new_cron = "\n".join(new_lines) + "\n"
            subprocess.run(["crontab", "-"], input=new_cron, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
