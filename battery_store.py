import json
import os
from datetime import datetime

DATA_FILE = 'battery_data.json'
MAX_HISTORY = 100  # Maximal gespeicherte Werte

class BatteryDataStore:
    def __init__(self, path=DATA_FILE):
        self.path = path
        self.data = {'history': [], 'shutdowns': []}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r') as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {'history': [], 'shutdowns': []}

    def save(self):
        try:
            with open(self.path, 'w') as f:
                json.dump(self.data, f, separators=(',', ':'))
        except Exception:
            pass

    def add_battery(self, percent, timestamp):
        self.data['history'].append({'percent': percent, 'time': timestamp})
        if len(self.data['history']) > MAX_HISTORY:
            self.data['history'] = self.data['history'][-MAX_HISTORY:]
        self.save()

    def add_shutdown(self, timestamp):
        self.data['shutdowns'].append(timestamp)
        if len(self.data['shutdowns']) > 20:
            self.data['shutdowns'] = self.data['shutdowns'][-20:]
        self.save()

    def get_battery_history(self):
        return self.data['history']

    def get_shutdowns(self):
        return self.data['shutdowns']

store = BatteryDataStore()
