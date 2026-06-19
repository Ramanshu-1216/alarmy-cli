import time
import threading
import platform
import sys
import logging

logger = logging.getLogger(__name__)

class AlarmSoundController:
    """
    Manages non-blocking audio alerts across platforms.
    On Windows, it uses the built-in winsound.Beep API.
    On Linux, it uses the terminal bell character (\a) with a quiet sleep.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def _beep_loop(self) -> None:
        system = platform.system()
        while not self._stop_event.is_set():
            if system == "Windows":
                try:
                    import winsound
                    # 1000 Hz frequency, 600 ms duration
                    winsound.Beep(1000, 600)
                except Exception as e:
                    # Fallback to ASCII bell if winsound fails
                    sys.stdout.write('\a')
                    sys.stdout.flush()
            else:
                # Linux/macOS fallback using ASCII bell character
                sys.stdout.write('\a')
                sys.stdout.flush()
            
            # Sleep in small increments to respond quickly to stop events
            for _ in range(10):
                if self._stop_event.is_set():
                    break
                time.sleep(0.1)

    def start(self) -> bool:
        """
        Starts the alarm beep loop in a background thread if not already running.
        Returns True if a new thread was started, False otherwise.
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False  # Already running
            
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._beep_loop, name="AlarmSoundThread", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        """
        Stops the alarm beep loop.
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                self._stop_event.set()
                # Wait briefly for the thread to stop, but don't block indefinitely
                self._thread.join(timeout=1.5)
                self._thread = None
