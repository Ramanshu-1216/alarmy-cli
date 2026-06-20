import sys
import datetime
import time
import os
import threading
from typing import List, Optional

from alarm_clock.models import Alarm, AlarmState, parse_days
from alarm_clock.scheduler import AlarmScheduler, parse_time
from alarm_clock.ui import TerminalUI, Colors, enable_ansi_support, safe_print

def on_alarm_trigger(alarm: Alarm) -> None:
    """
    Callback executed when an alarm fires during interactive mode.
    """
    TerminalUI.print_alarm_trigger(alarm)
    sys.stdout.write(f"\n({datetime.datetime.now().strftime('%H:%M:%S')}) alarmy > ")
    sys.stdout.flush()

def run_add_wizard(scheduler: AlarmScheduler) -> None:
    """
    Guides the user step-by-step to create an alarm with input validation.
    """
    safe_print(f"\n{Colors.CYAN}{Colors.BOLD}--- Interactive Alarm Setup Wizard ---{Colors.RESET}")
    
    # 1. Prompt Time
    while True:
        try:
            time_input = input("Enter alarm time (HH:MM or HH:MM PM) [e.g., 08:30]: ").strip()
            if not time_input:
                safe_print(f"{Colors.RED}Time cannot be empty.{Colors.RESET}")
                continue
            parse_time(time_input)
            break
        except ValueError as e:
            safe_print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # 2. Prompt Label
    try:
        label_input = input("Enter alarm label [default: 'Alarm']: ").strip()
        label = label_input if label_input else "Alarm"
    except KeyboardInterrupt:
        safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
        return

    # 3. Prompt Days (Recurrence)
    while True:
        try:
            days_input = input("Repeat on days (e.g. Mon,Wed,Fri, or 'daily', or press Enter for Once): ").strip()
            days = parse_days(days_input)
            break
        except ValueError as e:
            safe_print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # 4. Prompt Auto-dismiss Seconds
    while True:
        try:
            dismiss_input = input("Auto-dismiss duration in seconds [default: 60]: ").strip()
            if not dismiss_input:
                auto_dismiss = 60
                break
            auto_dismiss = int(dismiss_input)
            if auto_dismiss <= 0:
                safe_print(f"{Colors.RED}Duration must be a positive integer.{Colors.RESET}")
                continue
            break
        except ValueError:
            safe_print(f"{Colors.RED}Please enter a valid integer.{Colors.RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # 5. Prompt Snooze Minutes
    while True:
        try:
            snooze_input = input("Default snooze duration in minutes [default: 5]: ").strip()
            if not snooze_input:
                snooze_minutes = 5
                break
            snooze_minutes = int(snooze_input)
            if snooze_minutes <= 0:
                safe_print(f"{Colors.RED}Snooze duration must be a positive integer.{Colors.RESET}")
                continue
            break
        except ValueError:
            safe_print(f"{Colors.RED}Please enter a valid integer.{Colors.RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # 6. Prompt TTS
    while True:
        try:
            tts_input = input("Enable Text-to-Speech briefing? (y/n) [default: n]: ").strip().lower()
            if not tts_input or tts_input in ('n', 'no'):
                tts = False
                break
            elif tts_input in ('y', 'yes'):
                tts = True
                break
            else:
                safe_print(f"{Colors.RED}Please enter 'y' or 'n'.{Colors.RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # 7. Prompt Tone
    while True:
        try:
            tone_input = input("Enter alarm tone (default, digital, chime or path to .wav file) [default: default]: ").strip()
            tone = tone_input if tone_input else "default"
            if tone not in ("default", "digital", "chime") and not os.path.exists(tone):
                safe_print(f"{Colors.YELLOW}Warning: Local file '{tone}' not found. Will default to beep if triggered.{Colors.RESET}")
            break
        except KeyboardInterrupt:
            safe_print(f"\n{Colors.YELLOW}Setup cancelled.{Colors.RESET}")
            return

    # Create the alarm
    try:
        alarm = scheduler.add_alarm(time_input, label, days, auto_dismiss, snooze_minutes, tts, tone)
        recurrence_text = f"repeating on {','.join(alarm.days)}" if alarm.days else "one-time"
        tts_text = ", TTS Enabled" if alarm.tts else ""
        tone_text = f", Tone: {alarm.tone}" if alarm.tone != "default" else ""
        safe_print(f"\n{Colors.GREEN}Success: Created Alarm {alarm.id} for {alarm.time.strftime('%H:%M')} ('{alarm.label}') - {recurrence_text}, auto-dismiss: {alarm.auto_dismiss_sec}s, snooze: {alarm.snooze_duration_min}m{tts_text}{tone_text}.{Colors.RESET}\n")
    except Exception as e:
        safe_print(f"{Colors.RED}Error creating alarm: {e}{Colors.RESET}")

def handle_add(scheduler: AlarmScheduler, args: List[str]) -> None:
    # If no arguments, fallback to interactive setup wizard
    if not args:
        run_add_wizard(scheduler)
        return

    days = []
    auto_dismiss = 60
    snooze_minutes = 5
    tts = False
    tone = "default"

    # Parse optional --tts flag
    if "--tts" in args:
        tts = True
        args.remove("--tts")

    # Parse optional --tone flag
    if "--tone" in args:
        try:
            idx = args.index("--tone")
            if idx + 1 < len(args):
                tone = args[idx + 1]
                if tone not in ("default", "digital", "chime") and not os.path.exists(tone):
                    safe_print(f"{Colors.YELLOW}Warning: Tone file '{tone}' does not exist. Defaulting to beep if triggered.{Colors.RESET}")
                args.pop(idx + 1)
                args.pop(idx)
            else:
                safe_print(f"{Colors.RED}Error: --tone flag requires a value (e.g. chime or path to .wav).{Colors.RESET}")
                return
        except ValueError as e:
            safe_print(f"{Colors.RED}Error parsing --tone: {e}{Colors.RESET}")
            return

    # Parse optional --days flag
    if "--days" in args:
        try:
            idx = args.index("--days")
            if idx + 1 < len(args):
                days_str = args[idx + 1]
                days = parse_days(days_str)
                args.pop(idx + 1)
                args.pop(idx)
            else:
                safe_print(f"{Colors.RED}Error: --days flag requires a value (e.g. Mon,Wed).{Colors.RESET}")
                return
        except ValueError as e:
            safe_print(f"{Colors.RED}Error parsing --days: {e}{Colors.RESET}")
            return

    # Parse optional --auto-dismiss flag
    if "--auto-dismiss" in args:
        try:
            idx = args.index("--auto-dismiss")
            if idx + 1 < len(args):
                dismiss_str = args[idx + 1]
                auto_dismiss = int(dismiss_str)
                if auto_dismiss <= 0:
                    raise ValueError("Duration must be a positive integer.")
                args.pop(idx + 1)
                args.pop(idx)
            else:
                safe_print(f"{Colors.RED}Error: --auto-dismiss flag requires an integer value.{Colors.RESET}")
                return
        except ValueError as e:
            safe_print(f"{Colors.RED}Error parsing --auto-dismiss: {e}{Colors.RESET}")
            return

    # Parse optional --snooze-minutes flag
    if "--snooze-minutes" in args:
        try:
            idx = args.index("--snooze-minutes")
            if idx + 1 < len(args):
                snooze_str = args[idx + 1]
                snooze_minutes = int(snooze_str)
                if snooze_minutes <= 0:
                    raise ValueError("Snooze duration must be a positive integer.")
                args.pop(idx + 1)
                args.pop(idx)
            else:
                safe_print(f"{Colors.RED}Error: --snooze-minutes flag requires an integer value.{Colors.RESET}")
                return
        except ValueError as e:
            safe_print(f"{Colors.RED}Error parsing --snooze-minutes: {e}{Colors.RESET}")
            return

    if not args:
        safe_print(f"{Colors.RED}Error: 'add' command requires a time (HH:MM).{Colors.RESET}")
        return

    time_str = args[0]
    label = " ".join(args[1:]) if len(args) > 1 else "Alarm"
    
    try:
        alarm = scheduler.add_alarm(time_str, label, days, auto_dismiss, snooze_minutes, tts, tone)
        recurrence_text = f"repeating on {','.join(alarm.days)}" if alarm.days else "one-time"
        tts_text = ", TTS Enabled" if alarm.tts else ""
        tone_text = f", Tone: {alarm.tone}" if alarm.tone != "default" else ""
        safe_print(f"{Colors.GREEN}Success: Created Alarm {alarm.id} for {alarm.time.strftime('%H:%M')} ('{alarm.label}') - {recurrence_text}, auto-dismiss: {alarm.auto_dismiss_sec}s, snooze: {alarm.snooze_duration_min}m{tts_text}{tone_text}.{Colors.RESET}")
    except ValueError as e:
        safe_print(f"{Colors.RED}Error: {e}{Colors.RESET}")

def handle_list(scheduler: AlarmScheduler) -> None:
    alarms = scheduler.get_all_alarms()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    TerminalUI.print_status_bar(now_str)
    TerminalUI.print_alarms_table(alarms)

def handle_remove(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        safe_print(f"{Colors.RED}Error: 'remove' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        success = scheduler.remove_alarm(alarm_id)
        if success:
            safe_print(f"{Colors.GREEN}Success: Removed alarm {alarm_id}.{Colors.RESET}")
        else:
            safe_print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        safe_print(f"{Colors.RED}Error: Alarm ID must be an integer.{Colors.RESET}")

def handle_snooze(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        safe_print(f"{Colors.RED}Error: 'snooze' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        minutes = int(args[1]) if len(args) > 1 else None
        
        alarm = scheduler.snooze_alarm(alarm_id, minutes)
        if alarm:
            resume_time = alarm.snooze_until.strftime('%H:%M:%S')
            snooze_len = minutes if minutes is not None else alarm.snooze_duration_min
            safe_print(f"{Colors.GREEN}Success: Alarm {alarm_id} snoozed for {snooze_len} minutes (until {resume_time}).{Colors.RESET}")
        else:
            safe_print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        safe_print(f"{Colors.RED}Error: Invalid arguments. Usage: snooze <ID> [minutes]{Colors.RESET}")

def handle_dismiss(scheduler: AlarmScheduler, args: List[str]) -> None:
    if not args:
        safe_print(f"{Colors.RED}Error: 'dismiss' command requires an alarm ID.{Colors.RESET}")
        return
    
    try:
        alarm_id = int(args[0])
        alarm = scheduler.dismiss_alarm(alarm_id)
        if alarm:
            safe_print(f"{Colors.GREEN}Success: Alarm {alarm_id} dismissed.{Colors.RESET}")
        else:
            safe_print(f"{Colors.RED}Error: Alarm ID {alarm_id} not found.{Colors.RESET}")
    except ValueError:
        safe_print(f"{Colors.RED}Error: Alarm ID must be an integer.{Colors.RESET}")

def run_daemon() -> None:
    """
    Runs the Alarm Scheduler process indefinitely in the foreground.
    Monitors database JSON, updates states, and plays audio when alarms trigger.
    """
    enable_ansi_support()
    safe_print(f"{Colors.CYAN}Starting Alarm Clock Daemon...{Colors.RESET}")
    safe_print(f"{Colors.DIM}Monitoring alarms. Press Ctrl+C to terminate.{Colors.RESET}\n")
    
    def daemon_trigger_callback(alarm: Alarm) -> None:
        TerminalUI.print_alarm_trigger(alarm)
        
    scheduler = AlarmScheduler(on_trigger_callback=daemon_trigger_callback)
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        safe_print(f"\n{Colors.CYAN}Stopping Daemon. Goodbye!{Colors.RESET}")
    finally:
        scheduler.stop()

def get_non_blocking_input(stop_event: threading.Event) -> Optional[str]:
    """
    Reads user input from terminal in a non-blocking manner to watch the stop_event.
    Uses msvcrt on Windows and select on Linux.
    """
    import platform
    if platform.system() == "Windows":
        import msvcrt
        input_str = ""
        while not stop_event.is_set():
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                if char in ('\r', '\n'):
                    sys.stdout.write('\n')
                    sys.stdout.flush()
                    return input_str
                elif char == '\b':  # Backspace
                    if len(input_str) > 0:
                        input_str = input_str[:-1]
                        sys.stdout.write('\b \b')
                        sys.stdout.flush()
                elif ord(char) >= 32:  # Printable
                    input_str += char
                    sys.stdout.write(char)
                    sys.stdout.flush()
            time.sleep(0.05)
        return None
    else:
        import select
        while not stop_event.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                return sys.stdin.readline().strip()
        return None

def run_ring(alarm_id: int) -> None:
    """
    Plays audio buzzer and displays prompt when scheduled task triggers.
    Executed in a short-lived subprocess task window.
    """
    enable_ansi_support()
    scheduler = AlarmScheduler()
    alarm = scheduler.ring_alarm(alarm_id)
    if not alarm:
        # Alarm deleted, or already handled in another process
        return

    # Start audio buzz
    scheduler._sound_controller.start(tone=alarm.tone, tts=alarm.tts, label=alarm.label)
    
    TerminalUI.clear_screen()
    TerminalUI.print_alarm_trigger(alarm)
    
    stop_event = threading.Event()
    
    def monitor_disk_state() -> None:
        """
        Monitors database file changes externally or handles sound expiry.
        """
        while not stop_event.is_set():
            time.sleep(0.5)
            alarms = {a.id: a for a in scheduler.get_all_alarms()}
            if alarm_id not in alarms:
                stop_event.set()
                break
                
            current_alarm = alarms[alarm_id]
            if current_alarm.state != AlarmState.RINGING:
                stop_event.set()
                break
                
            # Handle sound expiry (auto-dismiss)
            if current_alarm.ring_start_time:
                elapsed = (datetime.datetime.now() - current_alarm.ring_start_time).total_seconds()
                if elapsed >= current_alarm.auto_dismiss_sec:
                    scheduler.dismiss_alarm(alarm_id)
                    stop_event.set()
                    safe_print(f"\n{Colors.YELLOW}Alarm auto-dismissed after {current_alarm.auto_dismiss_sec} seconds.{Colors.RESET}")
                    break
                    
    monitor_thread = threading.Thread(target=monitor_disk_state, name="RingMonitorThread", daemon=True)
    monitor_thread.start()
    
    try:
        while not stop_event.is_set():
            sys.stdout.write("Press Enter to dismiss, or type 'snooze' to snooze: ")
            sys.stdout.flush()
            
            user_input = get_non_blocking_input(stop_event)
            if stop_event.is_set() or user_input is None:
                break
                
            cmd = user_input.strip().lower()
            if cmd == "snooze":
                scheduler.snooze_alarm(alarm_id, None)  # Pass None to trigger alarm-specific snooze duration
                # Calculate correct snooze length for stdout log print
                snooze_len = alarm.snooze_duration_min
                safe_print(f"{Colors.GREEN}Alarm snoozed for {snooze_len} minutes.{Colors.RESET}")
                break
            else:
                scheduler.dismiss_alarm(alarm_id)
                safe_print(f"{Colors.GREEN}Alarm dismissed.{Colors.RESET}")
                break
    except KeyboardInterrupt:
        scheduler.dismiss_alarm(alarm_id)
    finally:
        stop_event.set()
        scheduler.stop()

def print_cli_help() -> None:
    enable_ansi_support()
    TerminalUI.print_banner()
    help_text = f"""
{Colors.BOLD}CLI Alarm Clock Usage:{Colors.RESET}
  {Colors.GREEN}alarmy{Colors.RESET}                                           - Launches the interactive console
  {Colors.GREEN}alarmy add{Colors.RESET}                                       - Start the interactive Setup Wizard
  {Colors.GREEN}alarmy add <HH:MM> [label] [options]{Colors.RESET}             - Create a new alarm directly
                                                       Options:
                                                         --days <d>           Repeat on comma-separated days (e.g. Mon,Wed or daily)
                                                         --auto-dismiss <s>    Dismiss alarm automatically after <s> seconds
                                                         --snooze-minutes <m>  Set custom snooze duration in <m> minutes
                                                         --tts                 Enable native Text-to-Speech morning briefing
                                                         --tone <t>            Set tone: preset (default, digital, chime) or path to .wav
  {Colors.GREEN}alarmy list{Colors.RESET}                                      - List all alarms and exit
  {Colors.GREEN}alarmy remove <ID>{Colors.RESET}                                - Remove an alarm and exit
  {Colors.GREEN}alarmy snooze <ID> [minutes]{Colors.RESET}                      - Snooze a ringing alarm and exit
  {Colors.GREEN}alarmy dismiss <ID>{Colors.RESET}                               - Dismiss a ringing alarm and exit
  {Colors.GREEN}alarmy clear{Colors.RESET}                                     - Wipes the database and cancels all OS tasks
  {Colors.GREEN}alarmy daemon{Colors.RESET}                                    - Run the background sound and time monitor
  {Colors.GREEN}alarmy help{Colors.RESET}                                       - Show this CLI command usage
"""
    print(help_text)

def run_interactive() -> None:
    """
    Runs the interactive menu loop.
    """
    enable_ansi_support()
    scheduler = AlarmScheduler(on_trigger_callback=on_alarm_trigger)
    scheduler.start()
    
    TerminalUI.clear_screen()
    TerminalUI.print_banner()
    safe_print(f"{Colors.CYAN}Welcome to the CLI Alarm Clock! (Interactive Mode){Colors.RESET}")
    TerminalUI.print_help()
    
    try:
        while True:
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            prompt = f"({now_str}) alarmy > "
            
            try:
                cmd_line = input(prompt).strip()
            except EOFError:
                break
                
            if not cmd_line:
                continue
                
            parts = cmd_line.split()
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd in ("exit", "quit"):
                safe_print(f"\n{Colors.CYAN}Exiting Alarm Clock. Goodbye!{Colors.RESET}")
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
            elif cmd == "clear":
                scheduler.clear_all_alarms()
                safe_print(f"{Colors.GREEN}Success: Cleared all alarms and OS tasks.{Colors.RESET}")
            else:
                safe_print(f"{Colors.RED}Unknown command: '{cmd}'. Type 'help' for a list of commands.{Colors.RESET}")
                
    except KeyboardInterrupt:
        safe_print(f"\n\n{Colors.CYAN}Session interrupted. Exiting Alarm Clock. Goodbye!{Colors.RESET}")
    finally:
        scheduler.stop()

def main() -> None:
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        args = sys.argv[2:]
        
        if cmd == "help":
            print_cli_help()
        elif cmd == "daemon":
            run_daemon()
        elif cmd == "ring":
            if args:
                try:
                    alarm_id = int(args[0])
                    run_ring(alarm_id)
                except ValueError:
                    print("Error: Alarm ID must be an integer.")
                    sys.exit(1)
            else:
                print("Error: Ring command requires an Alarm ID.")
                sys.exit(1)
        elif cmd == "clear":
            scheduler = AlarmScheduler()
            scheduler.clear_all_alarms()
            safe_print(f"{Colors.GREEN}Success: Cleared all alarms and OS tasks.{Colors.RESET}")
        else:
            scheduler = AlarmScheduler()
            if cmd == "add":
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
                safe_print(f"Unknown command: '{cmd}'. Type 'alarmy help' for usage.")
                sys.exit(1)
    else:
        run_interactive()

if __name__ == "__main__":
    main()
