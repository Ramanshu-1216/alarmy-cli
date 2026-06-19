import sys
import datetime
import argparse
from typing import List

from alarm_clock.models import Alarm, AlarmState
from alarm_clock.scheduler import AlarmScheduler, parse_time
from alarm_clock.ui import TerminalUI, Colors, enable_ansi_support

def on_alarm_trigger(alarm: Alarm) -> None:
    """
    Callback executed when an alarm fires.
    """
    # Print warning banner immediately to stdout
    TerminalUI.print_alarm_trigger(alarm)
    # Reprompt indicator (since standard input is active, we print a fresh line to prompt the user)
    sys.stdout.write(f"\n({datetime.datetime.now().strftime('%H:%M:%S')}) alarm-clock > ")
    sys.stdout.flush()

def handle_add(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        print(f"{Colors.RED}Error: 'add' command requires a time (HH:MM).{Colors.RESET}")
        print("Usage: add <HH:MM> [label]")
        return
    
    time_str = args[0]
    label = " ".join(args[1:]) if len(args) > 1 else "Alarm"
    
    try:
        alarm = scheduler.add_alarm(time_str, label)
        print(f"{Colors.GREEN}Success: Created Alarm {alarm.id} for {alarm.time.strftime('%H:%M')} ('{alarm.label}'){Colors.RESET}")
    except ValueError as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")

def handle_list(scheduler: AlarmScheduler) -> None:
    alarms = scheduler.get_all_alarms()
    # Print status bar with current time first
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    TerminalUI.print_status_bar(now_str)
    TerminalUI.print_alarms_table(alarms)

def handle_remove(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        print(f"{Colors.RED}Error: 'remove' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        success = scheduler.remove_alarm(alarm_id)
        if success:
            print(f"{Colors.GREEN}Success: Removed alarm {alarm_id}.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        print(f"{Colors.RED}Error: Alarm ID must be an integer.{Colors.RESET}")

def handle_snooze(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        print(f"{Colors.RED}Error: 'snooze' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        minutes = int(args[1]) if len(args) > 1 else 5
        
        # Verify the alarm exists
        alarm = scheduler.snooze_alarm(alarm_id, minutes)
        if alarm:
            resume_time = alarm.snooze_until.strftime('%H:%M:%S')
            print(f"{Colors.GREEN}Success: Alarm {alarm_id} snoozed for {minutes} minutes (until {resume_time}).{Colors.RESET}")
        else:
            print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        print(f"{Colors.RED}Error: Invalid arguments. Usage: snooze <ID> [minutes]{Colors.RESET}")

def handle_dismiss(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        print(f"{Colors.RED}Error: 'dismiss' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        alarm = scheduler.dismiss_alarm(alarm_id)
        if alarm:
            print(f"{Colors.GREEN}Success: Alarm {alarm_id} dismissed.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        print(f"{Colors.RED}Error: Alarm ID must be an integer.{Colors.RESET}")

def main() -> None:
    enable_ansi_support()
    
    # Initialize scheduler with trigger callback
    scheduler = AlarmScheduler(on_trigger_callback=on_alarm_trigger)
    scheduler.start()
    
    TerminalUI.clear_screen()
    TerminalUI.print_banner()
    print(f"{Colors.CYAN}Welcome to the CLI Alarm Clock!{Colors.RESET}")
    TerminalUI.print_help()
    
    try:
        while True:
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            prompt = f"({now_str}) alarm-clock > "
            
            try:
                cmd_line = input(prompt).strip()
            except EOFError:
                # Handle standard stream closure (e.g. pipe redirection)
                break
                
            if not cmd_line:
                continue
                
            parts = cmd_line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd in ("exit", "quit"):
                print(f"\n{Colors.CYAN}Exiting Alarm Clock. Goodbye!{Colors.RESET}")
                break
            elif cmd == "help":
                TerminalUI.print_help()
            elif cmd == "add":
                handle_add(scheduler, args)
            elif cmd == "list":
                handle_list(scheduler)
            elif cmd == "remove":
                handle_remove(scheduler, args)
            elif cmd == "snooze":
                handle_snooze(scheduler, args)
            elif cmd == "dismiss":
                handle_dismiss(scheduler, args)
            else:
                print(f"{Colors.RED}Unknown command: '{cmd}'. Type 'help' for a list of commands.{Colors.RESET}")
                
    except KeyboardInterrupt:
        print(f"\n\n{Colors.CYAN}Session interrupted. Exiting Alarm Clock. Goodbye!{Colors.RESET}")
    finally:
        scheduler.stop()

if __name__ == "__main__":
    main()
