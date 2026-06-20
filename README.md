# ⏰ Alarmy CLI - Dual-Mode Command-Line Alarm System

A professional, robust, and zero-dependency CLI alarm system (Alarmy) written in Python. It runs natively and works seamlessly on **Windows**, **Linux**, and **macOS**.

Designed with **Clean Architecture** and **Unix-style CLI daemon patterns**, the application supports:
1. **Interactive Shell Mode**: A fully interactive console screen with a live ticking clock header and dynamic command prompt.
2. **Daemon Mode**: Run the background sound and time monitor (`alarmy daemon`).
3. **OS-Native Task Mode (Zero Manual Daemon)**: Alarms automatically register with the operating system scheduler (Windows Task Scheduler via `schtasks` or Linux via `crontab`). When the time is reached, the OS automatically pops up a terminal instance to play sound and accept user inputs.

---

## ✨ Features

- **Global PyPI Package**: Install globally as `alarmy-cli` and run using the `alarmy` command.
- **Text-to-Speech (TTS) Briefings**: Plays a non-blocking voice synthesis briefing (greeting, current local time, alarm label, and random motivational quote) using native OS engines at the start of ringing.
- **Customizable Tones**:
  - `default`: standard 1000Hz beep pattern.
  - `digital`: rapid dual-beep pattern at 1500Hz.
  - `chime`: rising musical chimes (C-E-G-C).
  - Local Audio File: Pass any local path to a `.wav` file to play it in a loop.
- **OS-Native Task Automation**:
  - Windows: Creates user-level tasks using `schtasks` with automatic date fallback mechanisms for locale compatibility (`dd/mm/yyyy` vs `mm/dd/yyyy`).
  - Linux: Appends entries programmatically to the user's `crontab`.
- **Atomic File Writing**: Prevents state corruption by writing changes to a temporary file before atomically swapping it with the target database file (`~/.cli_alarms.json`).
- **Thread-Safe Memory Lock**: Synchronizes all database reads and writes under a shared mutex lock to isolate background checks from user adjustments.
- **Automatic Encoding Fallback**: Prevents crashes on legacy Windows cmd consoles that default to non-Unicode codepages (e.g., CP1252) by automatically replacing emojis with safe fallback indicators.
- **CI/CD Integrated**: Automated 15-job matrix testing across OS platforms and Python versions, with secure OIDC publishing to PyPI.

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
 │  │ Windows Task Scheduler ├──────►│ alarmy ring        │  │
 │  │       / Linux Cron     │       │ (Terminal Pop-Up)  │  │
 │  └────────────────────────┘       └────────────────────┘  │
 └───────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### 1. Installation

**Install from PyPI (Recommended):**
```bash
pip install alarmy-cli
```

**Install from Local Source (for Development):**
To register the `alarmy` terminal command locally, install the package from the root directory.
* On Windows: `pip install --user -e .`
* On Linux/macOS: `pip install -e .`

*Note: Make sure your user script folder is in your system's PATH. If it's not, you can run the executable directly by targeting its path, or use `python -m alarm_clock.cli`.*

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
   alarmy add 07:30 "Wake Up" --snooze-minutes 8 --auto-dismiss 30 --tts --tone chime --math
   ```
   *Flags:*
   - `--snooze-minutes`: default snooze duration in minutes.
   - `--auto-dismiss`: auto-dismiss duration in seconds.
   - `--tts`: enable the native Text-to-Speech briefing.
   - `--tone`: select a preset tone (`default`, `digital`, `chime`) or specify a path to a local `.wav` file.
   - `--math`: enable the Math Challenge (forces you to solve a simple addition or multiplication problem to dismiss the alarm).

2. **List alarms**:
   ```bash
   alarmy list
   ```
3. When the time is reached, the operating system launches a terminal window automatically, starts speaking the TTS briefing, triggers the tone audio player, and prompts you:
   ```
   Press Enter to dismiss, or type 'snooze' to snooze:
   ```
   *If you type `snooze`, it automatically snoozes for 8 minutes (respecting the custom snooze parameter).*

4. **Remove an alarm** (cleans it up from both disk and OS task registries):
   ```bash
   alarmy remove 1
   ```

### Option B: Daemon Mode (Manual Persistent Process)
1. **Start the monitor daemon** (run this in a separate terminal window or pane to play sound when alarms go off):
   ```bash
   alarmy daemon
   ```
2. **Snooze/Dismiss** from your main terminal:
   ```bash
   alarmy snooze 1 10
   alarmy dismiss 1
   ```

### Option C: Interactive Shell Mode
If you run `alarmy` without any arguments, it launches a persistent, interactive console session. It manages its own background timing thread and audio loops automatically in a single terminal.

```bash
alarmy
```
Inside the interactive session, the prompt updates live and you can type sub-commands like `add`, `list`, `snooze`, `dismiss`, and `exit` directly:
```
(12:10:30) alarmy > add 07:30 Morning Workout --tts --tone digital
Success: Created Alarm 1 for 07:30 ('Morning Workout') - one-time, auto-dismiss: 60s, snooze: 5m, TTS Enabled, Tone: digital.
```
