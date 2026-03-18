import subprocess
import re

def scan_bluetooth_devices():
    # Returns a list of (address, name) tuples
    try:
        output = subprocess.check_output(['bluetoothctl', 'scan', 'on'], timeout=5).decode()
    except Exception:
        output = ''
    # Parse output for MAC addresses and names
    devices = set()
    for line in output.splitlines():
        m = re.search(r'Device ([0-9A-F:]{17}) (.+)', line)
        if m:
            devices.add((m.group(1), m.group(2)))
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
