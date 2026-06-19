import os
import platform
import sys
import datetime
from typing import List
from alarm_clock.models import Alarm, AlarmState

# ANSI Color Codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    BLINK = '\033[5m'
    RESET = '\033[0m'

    # Backgrounds for alerts
    BG_RED = '\033[41m'

def enable_ansi_support() -> None:
    """
    Enables ANSI escape sequence support on Windows by invoking os.system('').
    On Linux/macOS, this is supported natively.
    """
    if platform.system() == "Windows":
        # Classic Windows trick to enable virtual terminal processing (ANSI escape sequences)
        os.system('')

def safe_print(text: str = "") -> None:
    """
    Prints text safely. If the terminal encoding (e.g., CP1252 on legacy Windows cmd)
    does not support emojis or Unicode characters, it encodes it with 'replace'
    to prevent program crashes.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or 'ascii'
        encoded = text.encode(encoding, errors='replace')
        print(encoded.decode(encoding))

class TerminalUI:
    @staticmethod
    def clear_screen() -> None:
        """
        Clears the terminal screen.
        """
        sys.stdout.write('\033[H\033[2J')
        sys.stdout.flush()

    @staticmethod
    def print_banner() -> None:
        """
        Prints a stylized ASCII art banner for the Alarm Clock application.
        """
        banner = rf"""{Colors.CYAN}{Colors.BOLD}
  ⏰  ___  _    ___  ___  ___  ___   ___  _    ___  ___  _  __ ⏰
     / _ \| |  / _ \| _ \/ __|/ _ \ / __|| |  / _ \|  _|| |/ /
    |  _  | |_|  _  |   /|__ |  _  | (__ | |_|  _  |  __|   < 
    |_| |_|___|_| |_|_|\\|___/|_| |_|\___||___|_| |_|___||_|\_\
{Colors.RESET}"""
        safe_print(banner)

    @staticmethod
    def print_status_bar(current_time_str: str) -> None:
        """
        Prints the current system time in a prominent styled format.
        """
        bar = f"{Colors.HEADER}{Colors.BOLD}[ CURRENT TIME: {current_time_str} ]{Colors.RESET}"
        safe_print(bar)
        safe_print(f"{Colors.DIM}-------------------------------------------------------{Colors.RESET}")

    @staticmethod
    def print_alarms_table(alarms: List[Alarm]) -> None:
        """
        Renders a clean, formatted table of all alarms with color-coded states.
        """
        if not alarms:
            safe_print(f"\n{Colors.YELLOW}No alarms scheduled. Use 'add <HH:MM> [label]' to create one.{Colors.RESET}\n")
            return

        # Print Table Headers
        safe_print(f"{Colors.BOLD}{'ID':<6} | {'TIME':<8} | {'LABEL':<18} | {'RECURRING':<15} | {'STATE':<10} | {'DETAILS'}{Colors.RESET}")
        safe_print(f"{Colors.DIM}{'-'*85}{Colors.RESET}")

        for alarm in alarms:
            # Color code based on alarm state
            if alarm.state == AlarmState.PENDING:
                state_str = f"{Colors.GREEN}PENDING{Colors.RESET}"
            elif alarm.state == AlarmState.RINGING:
                state_str = f"{Colors.BLINK}{Colors.RED}{Colors.BOLD}RINGING{Colors.RESET}"
            elif alarm.state == AlarmState.SNOOZED:
                state_str = f"{Colors.YELLOW}SNOOZED{Colors.RESET}"
            else:
                state_str = f"{Colors.DIM}DISMISSED{Colors.RESET}"

            # Recurrence text
            days_str = ",".join([d[:3] for d in alarm.days]) if alarm.days else "Once"
            if len(days_str) > 15:
                days_str = days_str[:12] + "..."

            # Detail rendering (e.g. snooze count, auto-dismiss, ring expiry)
            details = ""
            if alarm.state == AlarmState.SNOOZED and alarm.snooze_until:
                time_rem = alarm.snooze_until - datetime.datetime.now()
                sec_rem = int(time_rem.total_seconds())
                min_rem = sec_rem // 60
                sec_rem %= 60
                details = f"Resumes in {min_rem:02d}m {sec_rem:02d}s (Snoozed {alarm.snoozed_count}x)"
            elif alarm.state == AlarmState.RINGING:
                details = f"Auto-dismiss: {alarm.auto_dismiss_sec}s limit"
            else:
                details = f"Auto-dismiss: {alarm.auto_dismiss_sec}s"

            safe_print(f"{alarm.id:<6} | {alarm.time.strftime('%H:%M'):<8} | {alarm.label:<18} | {days_str:<15} | {state_str:<10} | {Colors.DIM}{details}{Colors.RESET}")
        safe_print()

    @staticmethod
    def print_alarm_trigger(alarm: Alarm) -> None:
        """
        Displays a flashing ASCII art alert when an alarm goes off.
        """
        alert = rf"""
{Colors.BG_RED}{Colors.BOLD}{Colors.BLINK}  🔔  !!! ALARM TRIGGERED !!!  🔔  {Colors.RESET}
{Colors.RED}{Colors.BOLD}  Time  : {alarm.time.strftime('%H:%M')}
  Label : {alarm.label.upper()}
  State : {Colors.BLINK}RINGING{Colors.RESET}

  {Colors.BOLD}Commands to respond:{Colors.RESET}
  - Type {Colors.GREEN}dismiss {alarm.id}{Colors.RESET} to stop the alarm.
  - Type {Colors.YELLOW}snooze {alarm.id} [minutes]{Colors.RESET} to snooze (default: 5 min).
"""
        safe_print(alert)

    @staticmethod
    def print_help() -> None:
        """
        Displays all available command commands and descriptions.
        """
        help_text = f"""
{Colors.BOLD}Available Commands:{Colors.RESET}
  {Colors.GREEN}add <HH:MM> [label]{Colors.RESET}     - Create a new alarm (e.g. `add 07:30 Morning Run`)
  {Colors.GREEN}list{Colors.RESET}                    - List all active and past alarms
  {Colors.GREEN}remove <ID>{Colors.RESET}             - Remove an alarm by its numerical ID
  {Colors.GREEN}snooze <ID> [minutes]{Colors.RESET}   - Snooze a ringing alarm (default: 5 minutes)
  {Colors.GREEN}dismiss <ID>{Colors.RESET}            - Dismiss a ringing or active alarm
  {Colors.GREEN}help{Colors.RESET}                    - Show this menu
  {Colors.GREEN}exit{Colors.RESET} / {Colors.GREEN}quit{Colors.RESET}             - Quit the application
"""
        safe_print(help_text)
