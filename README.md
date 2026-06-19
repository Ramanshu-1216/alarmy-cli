# ⏰ Command-Line Interface (CLI) Alarm Clock

A professional, robust, and zero-dependency Command-Line Interface (CLI) Alarm Clock written in Python. It runs natively and works seamlessly on both **Windows** and **Linux**.

Designed with **Clean Architecture** and **Unix-style CLI daemon patterns**, the application supports:
1. **Interactive Shell Mode**: A fully interactive console screen with a live ticking clock header and dynamic command prompt.
2. **Direct CLI / Single-Command Mode**: Run command-line utilities directly from your terminal (e.g. `alarm-clock add 07:30`) which persist state to disk, paired with a background daemon process (`alarm-clock daemon`).

---

## ✨ Features

- **Global CLI command integration**: Can be installed and executed globally as `alarm-clock` in the system shell.
- **Persistent JSON State Storage**: State is automatically persisted to `~/.cli_alarms.json`, enabling state synchronization between different terminals and processes.
- **Atomic File Writing**: Prevents file corruption by writing changes to a temporary file before atomically swapping it with the target database file.
- **Thread-Safe Memory Lock**: Synchronizes all database reads and writes under a shared mutex lock to isolate background checks from user adjustments.
- **Automatic Encoding Fallback**: Prevents crashes on legacy Windows cmd consoles that default to non-Unicode codepages (e.g., CP1252) by automatically replacing emojis with safe fallback indicators.
- **Cross-Platform Audio alerts**:
  - Windows: Uses native `winsound.Beep`.
  - Linux/macOS: Uses terminal buzzer beeps (`\a`).
- **Flexible alarm operations**: `add`, `list`, `remove`, `snooze`, and `dismiss`.

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
A comprehensive test suite is included in `/tests` covering the parser, models, scheduler, serialization, and persistence. Run it with:
```bash
python -m unittest discover -s tests
```

---

## 🕹️ Command Reference

### Option A: Direct CLI Mode (Persistent Single-Commands)
You can call commands directly from any shell. Alarms are updated on disk instantly.

1. **Start the monitor daemon** (run this in a separate terminal window or pane to play sound when alarms go off):
   ```bash
   alarm-clock daemon
   ```
2. **Add an alarm**:
   ```bash
   alarm-clock add 07:30 "Wake Up"
   ```
3. **List alarms**:
   ```bash
   alarm-clock list
   ```
4. **Snooze a ringing alarm** (e.g. snooze alarm 1 for 10 minutes):
   ```bash
   alarm-clock snooze 1 10
   ```
5. **Dismiss a ringing alarm**:
   ```bash
   alarm-clock dismiss 1
   ```
6. **Remove an alarm**:
   ```bash
   alarm-clock remove 1
   ```

### Option B: Interactive Shell Mode
If you run `alarm-clock` without any arguments, it launches a persistent, interactive console session. It manages its own background timing thread and audio loops automatically in a single terminal.

```bash
alarm-clock
```
Inside the interactive session, the prompt updates live and you can type sub-commands like `add`, `list`, `snooze`, `dismiss`, and `exit` directly:
```
(22:15:30) alarm-clock > add 07:30 Morning Workout
Success: Created Alarm 1 for 07:30 ('Morning Workout')
```
