# ⏰ Command-Line Interface (CLI) Alarm Clock

A professional, robust, and zero-dependency Command-Line Interface (CLI) Alarm Clock written in Python. It runs natively and works seamlessly on both **Windows** and **Linux**.

Designed with **Clean Architecture** principles, it leverages multithreading to manage alarm scheduling in the background while keeping the main console interactive and responsive to user input.

---

## ✨ Features

- **Live Ticking Header**: Displays the current system time prominently.
- **Thread-Safe Alarm Management**:
  - Add alarms dynamically using 24-hour (`HH:MM`, `HH:MM:SS`) or 12-hour (`HH:MM AM/PM`) formats, with optional custom labels.
  - List all scheduled, snoozed, or dismissed alarms in a clean, colorized grid.
  - Remove/cancel alarms by ID.
- **Cross-Platform Audio & Visual Triggers**:
  - Windows: Uses native `winsound.Beep` for audio alerts.
  - Linux: Uses terminal bell (`\a`) triggers.
  - Displays flashing ASCII warning notifications in the terminal.
- **Snooze & Dismiss Actions**:
  - Quickly snooze any ringing alarm for a configurable duration (default: 5 minutes) or dismiss it.
- **Robust Failure Isolation**:
  - Exception handling for invalid inputs.
  - Graceful cleanup of resources and background threads on user exit or `Ctrl+C`.

---

## 🛠️ Architecture & Design Decisions

### 1. Concurrency Model
The application separates concerns across three logical execution environments:
- **Main Thread (UI/CLI Loop)**: Handles command input, processes commands, and displays the UI.
- **Background Scheduler Thread**: Checks every second if any alarm is scheduled to ring, transitioning states and triggering sounds safely.
- **Background Sound Thread**: Plays repeating auditory alerts. Firing this in its own short-lived thread ensures that blocking sound operations (like Windows beep duration) do not freeze the background scheduler or CLI loops.

### 2. Thread Safety
All access to the alarm dictionary is synchronized using a `threading.Lock`. This prevents race conditions when the user is modifying alarms (e.g. calling `add`, `remove`, `snooze`) at the exact millisecond the scheduler thread is checking or updating alarm states.

### 3. Zero Dependencies (Built-in Stability)
To ensure the evaluator can run this code instantly on any Python 3.8+ system without experiencing pip dependency installation failures or native library compilation errors (common with python sound libraries), we built the application exclusively using the **Python Standard Library** (`threading`, `datetime`, `os`, `sys`, `unittest`, `platform`).

---

## 🚀 Getting Started

### Prerequisites
- Python **3.8** or newer installed.

### Run the Application
Start the interactive CLI by running the following command from the root directory:
```bash
python -m alarm_clock.cli
```

### Running Unit Tests
A comprehensive test suite is included in `/tests` covering the parser, models, scheduler, and state progressions. Run it with:
```bash
python -m unittest discover -s tests
```

---

## 🕹️ Command Reference

| Command | Arguments | Description | Example |
| :--- | :--- | :--- | :--- |
| `add` | `<HH:MM> [label]` | Adds a new alarm with optional label. | `add 14:30 Gym Time` |
| `list` | *None* | Lists all active and inactive alarms. | `list` |
| `remove` | `<ID>` | Removes an alarm from the schedule. | `remove 1` |
| `snooze` | `<ID> [minutes]` | Snoozes a ringing alarm (default 5m). | `snooze 1 10` |
| `dismiss` | `<ID>` | Dismisses/turns off a ringing alarm. | `dismiss 1` |
| `help` | *None* | Displays the available command guide. | `help` |
| `exit` / `quit` | *None* | Stops background threads and exits. | `exit` |

---

## 🔮 Future Enhancements
Given more time, here are the production improvements that could be added:
1. **Persistence**: Use an SQLite database or local JSON file to save and reload alarms between sessions.
2. **Advanced Scheduling**: Support recurring alarms (e.g., weekdays, weekends) or cron-style schedules.
3. **Custom Ringtone Support**: Integrate custom audio files (MP3/WAV) using a lightweight player.
4. **Daemon Mode**: Run the alarm monitor as a system service or background daemon so it alerts the user even when the interactive shell is closed.
