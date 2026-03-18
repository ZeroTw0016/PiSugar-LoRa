import subprocess
import re

def scan_bluetooth_devices(scan_on=True):
    # scan_on=True: scan on, False: scan off, None: nur Liste abfragen
    if scan_on is True:
        try:
            subprocess.check_call(['bluetoothctl', 'scan', 'on'], timeout=3)
        except Exception:
            pass
    elif scan_on is False:
        try:
            subprocess.check_call(['bluetoothctl', 'scan', 'off'], timeout=3)
        except Exception:
            pass
    # Geräte-Liste abfragen
    try:
        output = subprocess.check_output(['bluetoothctl', 'devices']).decode()
    except Exception:
        output = ''
    devices = set()
    for line in output.splitlines():
        m = re.search(r'Device ([0-9A-F:]{17}) (.+)', line)
        if m:
            devices.add({'address': m.group(1), 'name': m.group(2)})
    return list(devices)

def pair_bluetooth_device(address):
    try:
        subprocess.check_call(['bluetoothctl', 'pair', address], timeout=10)
        subprocess.check_call(['bluetoothctl', 'trust', address], timeout=5)
        subprocess.check_call(['bluetoothctl', 'connect', address], timeout=10)
        return True
    except Exception as e:
        return False

def list_paired_devices():
    try:
        output = subprocess.check_output(['bluetoothctl', 'paired-devices']).decode()
    except Exception:
        output = ''
    devices = []
    for line in output.splitlines():
        m = re.search(r'Device ([0-9A-F:]{17}) (.+)', line)
        if m:
            devices.append({'address': m.group(1), 'name': m.group(2)})
    return devices
