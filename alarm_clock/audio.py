import time
import threading
import platform
import sys
import os
import logging
import subprocess
import shutil
from typing import Optional

logger = logging.getLogger(__name__)

def _get_tts_briefing_text(label: str) -> str:
    import datetime
    import random
    now = datetime.datetime.now()
    hour_str = now.strftime("%I:%M %p")
    
    greetings = ["Good morning", "Good afternoon", "Good evening"]
    hour = now.hour
    if hour < 12:
        greet = greetings[0]
    elif hour < 17:
        greet = greetings[1]
    else:
        greet = greetings[2]
        
    quotes = [
        "Make today amazing!",
        "Every day is a fresh start.",
        "You've got this!",
        "Believing in yourself is the first step.",
        "Success is the sum of small efforts repeated daily."
    ]
    quote = random.choice(quotes)
    
    return f"{greet}! It is {hour_str}. Your alarm '{label}' is active. {quote}"


class AlarmSoundController:
    """
    Manages non-blocking audio alerts across platforms.
    Supports TTS briefs, custom tone presets (default, digital, chime), and custom wav files.
    """
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._tone = "default"
        self._wav_process: Optional[subprocess.Popen] = None

    def _speak(self, text: str) -> None:
        """
        Synthesizes text using native OS TTS engines.
        """
        system = platform.system()
        try:
            if system == "Windows":
                # Escape single quotes for PowerShell
                safe_text = text.replace("'", "''")
                ps_cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe_text}')"
                subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            elif system == "Darwin":  # macOS
                subprocess.run(["say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            elif system == "Linux":
                if shutil.which("spd-say"):
                    subprocess.run(["spd-say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                elif shutil.which("espeak"):
                    subprocess.run(["espeak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except Exception as e:
            logger.error(f"TTS Speech synthesis failed: {e}")

    def _beep_loop(self) -> None:
        system = platform.system()
        is_wav = self._tone not in ("default", "digital", "chime") and os.path.exists(self._tone)
        
        if is_wav:
            if system == "Windows":
                try:
                    import winsound
                    # Play sound asynchronously and loop
                    winsound.PlaySound(self._tone, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_LOOP)
                except Exception as e:
                    logger.error(f"Failed to play wav file: {e}")
                    is_wav = False  # Fallback to beep if PlaySound fails
            else:
                # Unix systems: spawn audio player in loop
                player = None
                if system == "Darwin" and shutil.which("afplay"):
                    player = "afplay"
                elif shutil.which("aplay"):
                    player = "aplay"
                elif shutil.which("paplay"):
                    player = "paplay"
                
                if player:
                    try:
                        self._wav_process = subprocess.Popen(
                            [player, self._tone], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.DEVNULL
                        )
                    except Exception as e:
                        logger.error(f"Failed to spawn {player} process: {e}")
                        is_wav = False

        while not self._stop_event.is_set():
            if is_wav:
                if system != "Windows" and self._wav_process:
                    # For Unix, if the sound process terminated, loop it
                    if self._wav_process.poll() is not None:
                        try:
                            player = "afplay" if system == "Darwin" else ("aplay" if shutil.which("aplay") else "paplay")
                            self._wav_process = subprocess.Popen(
                                [player, self._tone], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL
                            )
                        except Exception:
                            pass
                # Simply sleep in small increments
                time.sleep(0.2)
                continue

            # Fallback/Preset Beeping Logic
            if system == "Windows":
                try:
                    import winsound
                    if self._tone == "digital":
                        winsound.Beep(1500, 150)
                        time.sleep(0.1)
                        if not self._stop_event.is_set():
                            winsound.Beep(1500, 150)
                        # Sleep remainder of loop
                        for _ in range(8):
                            if self._stop_event.is_set():
                                break
                            time.sleep(0.1)
                    elif self._tone == "chime":
                        notes = [523, 659, 784, 1047]
                        for note in notes:
                            if self._stop_event.is_set():
                                break
                            winsound.Beep(note, 180)
                            time.sleep(0.05)
                        for _ in range(12):
                            if self._stop_event.is_set():
                                break
                            time.sleep(0.1)
                    else:  # default
                        winsound.Beep(1000, 600)
                        for _ in range(10):
                            if self._stop_event.is_set():
                                break
                            time.sleep(0.1)
                except Exception:
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    time.sleep(1.0)
            else:
                # Unix fallback using ASCII bells
                sys.stdout.write('\a')
                sys.stdout.flush()
                if self._tone == "digital":
                    time.sleep(0.15)
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    time.sleep(1.0)
                elif self._tone == "chime":
                    time.sleep(0.2)
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    time.sleep(0.2)
                    sys.stdout.write('\a')
                    sys.stdout.flush()
                    time.sleep(1.2)
                else:
                    time.sleep(1.0)

    def start(self, tone: str = "default", tts: bool = False, label: str = "Alarm") -> bool:
        """
        Starts the alarm audio loop and plays TTS if enabled.
        """
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False  # Already running
            
            self._tone = tone
            self._stop_event.clear()
            self._wav_process = None
            
            # Start TTS briefing if enabled in a non-blocking helper thread
            if tts:
                briefing_text = _get_tts_briefing_text(label)
                threading.Thread(target=self._speak, args=(briefing_text,), name="TTSThread", daemon=True).start()
            
            self._thread = threading.Thread(target=self._beep_loop, name="AlarmSoundThread", daemon=True)
            self._thread.start()
            return True

    def stop(self) -> None:
        """
        Stops the alarm audio loop and stops any active media players.
        """
        with self._lock:
            self._stop_event.set()
            
            # Stop Windows WAV audio loop if active
            if platform.system() == "Windows":
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
            
            # Stop Unix WAV player process if active
            if self._wav_process:
                try:
                    self._wav_process.terminate()
                    self._wav_process.wait(timeout=1.0)
                except Exception:
                    pass
                self._wav_process = None

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.5)
                self._thread = None
