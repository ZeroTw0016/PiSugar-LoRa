import pyttsx3
import threading

class TTSBluetoothSpeaker:
    def __init__(self, device_name=None):
        self.device_name = device_name
        self.engine = pyttsx3.init()
        self.lock = threading.Lock()
        # Optionally set output device here if needed

    def say(self, text):
        with self.lock:
            self.engine.say(text)
            self.engine.runAndWait()

    def set_output_device(self, device_name):
        # Optional: Implement device selection if multiple outputs
        pass

tts_speaker = TTSBluetoothSpeaker()
