# ⏰ Command-Line Interface (CLI) Alarm Clock

A professional, robust, and zero-dependency Command-Line Interface (CLI) Alarm Clock written in Python. It runs natively and works seamlessly on both **Windows** and **Linux**.

Designed with **Clean Architecture** and **Unix-style CLI daemon patterns**, the application supports:
1. **Interactive Shell Mode**: A fully interactive console screen with a live ticking clock header and dynamic command prompt.
2. **Daemon Mode**: Run the background sound and time monitor (`alarm-clock daemon`).
3. **OS-Native Task Mode (Zero Manual Daemon)**: Alarms automatically register with the operating system scheduler (Windows Task Scheduler via `schtasks` or Linux via `crontab`). When the time is reached, the OS automatically pops up a terminal instance to play sound and accept user inputs.

---

## ✨ Features

- **Global CLI command integration**: Can be installed and executed globally as `alarm-clock` in the system shell.
- **Dual Sound Alert Modes**:
  - Background Python daemon checks system time and plays sound.
  - OS-native schedulers trigger short-lived processes to ring.
- **OS-Native Task Automation**:
  - Windows: Creates user-level tasks using `schtasks` with automatic date fallback mechanisms for locale compatibility (`dd/mm/yyyy` vs `mm/dd/yyyy`).
  - Linux: Appends entries programmatically to the user's `crontab`.
- **Atomic File Writing**: Prevents state corruption by writing changes to a temporary file before atomically swapping it with the target database file (`~/.cli_alarms.json`).
- **Thread-Safe Memory Lock**: Synchronizes all database reads and writes under a shared mutex lock to isolate background checks from user adjustments.
- **Automatic Encoding Fallback**: Prevents crashes on legacy Windows cmd consoles that default to non-Unicode codepages (e.g., CP1252) by automatically replacing emojis with safe fallback indicators.
- **Cross-Platform Audio alerts**:
  - Windows: Uses native `winsound.Beep`.
  - Linux/macOS: Uses terminal buzzer beeps (`\a`).
- **Flexible Alarm Operations**: `add`, `list`, `remove`, `snooze`, and `dismiss`.
  - Supports setting an alarm-specific default snooze limit (`--snooze-minutes`) which is automatically respected if no snooze duration is entered during rings.

---

## 🛠️ Architecture & Design Decisions

```
               ┌───────────────────────┐
               │    Local CLI Shell    │
               │ (Direct Single-Cmds)  │
               └───────────┬───────────┘
                           │ Writes/Reads
                           ▼
               ┌───────────────────────┐
               │  ~/.cli_alarms.json   │◄─── (Atomic State DB)
               └───────────────────────┘
                           ▲
                           │ Reads/Updates State
                           ▼
 ┌───────────────────────────────────────────────────────────┐
 │                   Background Daemon Mode                  │
 │                                                           │
 │  ┌───────────────────────┐       ┌─────────────────────┐  │
 │  │   Scheduler Thread    ├──────►│ Sound Loop Thread   │  │
 │  │ (Monitors System Time)│       │ (Non-blocking Beep) │  │
 │  └───────────────────────┘       └─────────────────────┘  │
 └───────────────────────────────────────────────────────────┘
                           ▲
                           │ Triggers Subprocess Ring Command
                           ▼
 ┌───────────────────────────────────────────────────────────┐
 │                  OS-Scheduled Task Mode                   │
 │                                                           │
 │  ┌────────────────────────┐       ┌────────────────────┐  │
 │  │ Windows Task Scheduler ├──────►│ alarm-clock ring   │  │
 │  │       / Linux Cron     │       │ (Terminal Pop-Up)  │  │
 │  └────────────────────────┘       └────────────────────┘  │
 └───────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Installation
To register the `alarm-clock` terminal command, install the package locally from the root workspace directory.

**On Windows (without requiring admin privileges):**
```powershell
pip install --user -e .
```
*Note: Make sure your user script folder (e.g. `C:\Users\<username>\AppData\Roaming\Python\Python312\Scripts`) is in your system's PATH. If it's not, you can run the executable directly by targeting its path, or use `python -m alarm_clock.cli`.*

**On Linux / macOS:**
```bash
pip install -e .
```

### 2. Running Unit Tests
A comprehensive test suite is included in `/tests` covering the parser, models, scheduler, serialization, persistence, and OS scheduler triggers. Run it with:
```bash
python -m unittest discover -s tests
```

---

## 🕹️ Command Reference

### Option A: OS-Native Mode (Recommended - Zero Manual Daemon)
When you add an alarm, it is registered automatically with the operating system.

1. **Add an alarm**:
   ```bash
   alarm-clock add 07:30 "Wake Up" --snooze-minutes 8 --auto-dismiss 30
   ```
2. **List alarms**:
   ```bash
   alarm-clock list
   ```
3. When the time is reached, the operating system launches a terminal window automatically, starts beep-beeping, and prompts you:
   ```
   Press Enter to dismiss, or type 'snooze' to snooze:
   ```
   *If you type `snooze`, it automatically snoozes for 8 minutes (respecting the custom snooze parameter).*
4. **Remove an alarm** (cleans it up from both disk and OS task registries):
   ```bash
   alarm-clock remove 1
   ```

### Option B: Daemon Mode (Manual Persistent Process)
1. **Start the monitor daemon** (run this in a separate terminal window or pane to play sound when alarms go off):
   ```bash
   alarm-clock daemon
   ```
2. **Snooze/Dismiss** from your main terminal:
   ```bash
   alarm-clock snooze 1 10
   alarm-clock dismiss 1
   ```

### Option C: Interactive Shell Mode
If you run `alarm-clock` without any arguments, it launches a persistent, interactive console session. It manages its own background timing thread and audio loops automatically in a single terminal.

```bash
alarm-clock
```
Inside the interactive session, the prompt updates live and you can type sub-commands like `add`, `list`, `snooze`, `dismiss`, and `exit` directly:
```
(22:15:30) alarm-clock > add 07:30 Morning Workout
Success: Created Alarm 1 for 07:30 ('Morning Workout')
```
